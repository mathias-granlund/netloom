from __future__ import annotations

import json
import shlex
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from pathlib import Path
from typing import Any

from netloom.cli.commands import (
    _prepare_plugin_write_payload,
    _request_args_and_payload,
)
from netloom.cli.parser import BOOLEAN_FLAGS, _normalize_flag_name
from netloom.cli.show import (
    _exclude_scope_from_settings,
    _parse_scope,
    _render_command,
    _selector_args_for_item,
    render_running_config,
)
from netloom.core.config import SECRET_FIELDS, Settings
from netloom.core.resolver import query_params_for_action
from netloom.io.files import ensure_parent_dir, load_payload_json
from netloom.io.output import (
    sanitize_secrets,
    should_mask_secrets,
    write_value_to_file,
)

_IMPORT_ACTIONS = {"add", "replace", "update"}
_CHANGE_ACTION_ORDER = ("replace", "update")
_SOURCE_IDENTITY_FIELDS = ("id", "uuid")
_MASKED_SECRET_VALUES = {"", "********", "******", "*****", "<hidden>", "<masked>"}


@dataclass(frozen=True)
class ConfigCommand:
    line_no: int
    text: str
    args: dict[str, Any]
    source_identity: dict[str, Any] = dataclass_field(default_factory=dict)


@dataclass(frozen=True)
class ConfigObject:
    command: ConfigCommand
    payload: dict[str, Any]

    @property
    def module(self) -> str:
        return str(self.command.args["module"])

    @property
    def service(self) -> str:
        return str(self.command.args["service"])

    @property
    def action(self) -> str:
        return str(self.command.args["action"])


def _parse_metadata_value(raw: str) -> Any:
    text = raw.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _metadata_from_comment(line: str) -> tuple[str, Any] | None:
    stripped = line.strip()
    for field in _SOURCE_IDENTITY_FIELDS:
        prefix = f"# source-{field}:"
        if stripped.startswith(prefix):
            return field, _parse_metadata_value(stripped[len(prefix) :])
    return None


def _parse_command_line(
    line: str, *, line_no: int, source_identity: dict[str, Any]
) -> ConfigCommand | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None

    try:
        tokens = shlex.split(stripped, posix=True)
    except ValueError as exc:
        raise ValueError(f"line {line_no}: unable to parse command: {exc}") from exc

    if not tokens:
        return None
    if tokens[0] != "netloom":
        raise ValueError(f"line {line_no}: expected a netloom command")
    if len(tokens) < 4:
        raise ValueError(
            f"line {line_no}: expected netloom <module> <service> <action>"
        )

    module, service, action = tokens[1:4]
    if action not in _IMPORT_ACTIONS:
        supported = ", ".join(sorted(_IMPORT_ACTIONS))
        raise ValueError(
            f"line {line_no}: only importable mutation actions are supported "
            f"({supported})"
        )

    args: dict[str, Any] = {
        "module": module,
        "service": service,
        "action": action,
    }
    for token in tokens[4:]:
        if token == "--":
            continue
        if token.startswith("--") and "=" in token:
            key, value = token[2:].split("=", 1)
            args[_normalize_flag_name(key)] = value
            continue
        if token.startswith("--"):
            key = _normalize_flag_name(token[2:])
            if key in BOOLEAN_FLAGS:
                args[key] = True
                continue
            raise ValueError(f"line {line_no}: unsupported flag {token}")
        raise ValueError(f"line {line_no}: unsupported argument {token}")

    if "payload_json" not in args:
        raise ValueError(f"line {line_no}: import commands must use --payload-json")

    return ConfigCommand(
        line_no=line_no,
        text=stripped,
        args=args,
        source_identity=dict(source_identity),
    )


def parse_running_config_text(text: str) -> list[ConfigCommand]:
    commands: list[ConfigCommand] = []
    source_identity: dict[str, Any] = {}
    for line_no, line in enumerate(text.splitlines(), 1):
        metadata = _metadata_from_comment(line)
        if metadata is not None:
            key, value = metadata
            source_identity[key] = value
            continue

        command = _parse_command_line(
            line, line_no=line_no, source_identity=source_identity
        )
        if command is not None:
            commands.append(command)
            source_identity = {}
    return commands


def parse_running_config(path: str | Path) -> list[ConfigCommand]:
    return parse_running_config_text(Path(path).read_text(encoding="utf-8"))


def _is_excluded_scope(
    module: str,
    service: str,
    exclude: set[tuple[str, str | None]],
) -> bool:
    return (module, None) in exclude or (module, service) in exclude


def _importable_commands(
    commands: list[ConfigCommand],
    *,
    exclude: set[tuple[str, str | None]] | None = None,
) -> list[ConfigCommand]:
    active_exclude = exclude or set()
    return [
        command
        for command in commands
        if not _is_excluded_scope(
            str(command.args.get("module")),
            str(command.args.get("service")),
            active_exclude,
        )
    ]


def _command_payload(command: ConfigCommand) -> dict[str, Any]:
    payload = load_payload_json(str(command.args["payload_json"]))
    if not isinstance(payload, dict):
        raise ValueError(
            f"line {command.line_no}: import payload must be a JSON object"
        )
    return payload


def _objects_from_commands(commands: list[ConfigCommand]) -> list[ConfigObject]:
    return [
        ConfigObject(command=command, payload=_command_payload(command))
        for command in commands
    ]


def _is_masked_secret_placeholder(key: str, value: Any) -> bool:
    if not isinstance(value, str):
        return False
    key_text = str(key).lower()
    if key_text not in SECRET_FIELDS and "secret" not in key_text:
        return False
    return value.strip().lower() in _MASKED_SECRET_VALUES


def _drop_masked_secret_placeholders(value: Any) -> Any:
    if isinstance(value, dict):
        normalized = {}
        for key, item in value.items():
            if _is_masked_secret_placeholder(str(key), item):
                continue
            normalized[key] = _drop_masked_secret_placeholders(item)
        return normalized
    if isinstance(value, list):
        return [_drop_masked_secret_placeholders(item) for item in value]
    return value


def _canonical(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _canonical(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    return value


def _restrict_to_shape(value: Any, shape: Any) -> Any:
    if isinstance(value, dict) and isinstance(shape, dict):
        return {
            key: _restrict_to_shape(value[key], shape[key])
            for key in shape
            if key in value
        }
    return value


def _comparable_payloads(
    desired_payload: dict[str, Any], current_payload: dict[str, Any]
) -> tuple[Any, Any]:
    desired = _drop_masked_secret_placeholders(desired_payload)
    current = _drop_masked_secret_placeholders(current_payload)
    return _canonical(desired), _canonical(_restrict_to_shape(current, desired))


def _payloads_match(
    desired_payload: dict[str, Any], current_payload: dict[str, Any]
) -> bool:
    desired, current = _comparable_payloads(desired_payload, current_payload)
    return desired == current


def _selector_source(
    obj: ConfigObject, *, include_source_identity: bool = True
) -> dict:
    item = dict(obj.payload)
    if include_source_identity:
        item.update(obj.command.source_identity)
    for key, value in obj.command.args.items():
        if key not in {"module", "service", "action", "payload_json"}:
            item[key] = value
    return item


def _object_keys(obj: ConfigObject) -> list[tuple[str, str, str, str]]:
    values: list[tuple[str, Any]] = []
    for field in ("id", "uuid", "name"):
        if field in obj.command.args and obj.command.args[field] not in (None, ""):
            values.append((field, obj.command.args[field]))
    for field in _SOURCE_IDENTITY_FIELDS:
        if obj.command.source_identity.get(field) not in (None, ""):
            values.append((field, obj.command.source_identity[field]))
    for field in ("id", "uuid", "name"):
        if obj.payload.get(field) not in (None, ""):
            values.append((field, obj.payload[field]))

    keys: list[tuple[str, str, str, str]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for field, value in values:
        key = (obj.module, obj.service, field, str(value))
        if key not in seen:
            seen.add(key)
            keys.append(key)
    return keys


def _object_label(obj: ConfigObject) -> str:
    for key in ("name", "id", "uuid"):
        if obj.payload.get(key) not in (None, ""):
            return str(obj.payload[key])
    for key in ("id", "uuid"):
        if obj.command.source_identity.get(key) not in (None, ""):
            return str(obj.command.source_identity[key])
    return "<unknown>"


def _build_index(
    objects: list[ConfigObject],
) -> dict[tuple[str, str, str, str], list[ConfigObject]]:
    index: dict[tuple[str, str, str, str], list[ConfigObject]] = {}
    for obj in objects:
        for key in _object_keys(obj):
            index.setdefault(key, []).append(obj)
    return index


def _find_current_match(
    desired: ConfigObject,
    current_index: dict[tuple[str, str, str, str], list[ConfigObject]],
) -> tuple[ConfigObject | None, tuple[str, str, str, str] | None, str | None]:
    for key in _object_keys(desired):
        matches = current_index.get(key) or []
        if len(matches) == 1:
            return matches[0], key, None
        if len(matches) > 1:
            return None, key, f"multiple current objects matched {key[2]}={key[3]}"
    return None, None, None


def _has_action(api_catalog: dict[str, Any], module: str, service: str, action: str):
    actions = ((api_catalog.get("modules") or {}).get(module) or {}).get(
        service, {}
    ).get("actions") or {}
    return action in actions


def _selector_args(
    api_catalog: dict[str, Any],
    module: str,
    service: str,
    action: str,
    item: dict[str, Any],
) -> dict[str, Any] | None:
    return _selector_args_for_item(api_catalog, module, service, action, item)


def _choose_change_action(
    api_catalog: dict[str, Any],
    current: ConfigObject,
) -> tuple[str, dict[str, Any]] | tuple[None, None]:
    selector_item = _selector_source(current)
    for action in _CHANGE_ACTION_ORDER:
        if not _has_action(api_catalog, current.module, current.service, action):
            continue
        selectors = _selector_args(
            api_catalog, current.module, current.service, action, selector_item
        )
        if selectors is not None:
            return action, selectors
    return None, None


def _render_delete_command(module: str, service: str, selectors: dict[str, Any]) -> str:
    parts = ["netloom", module, service, "delete"]
    for key, value in sorted(selectors.items()):
        parts.append(f"--{key.replace('_', '-')}={shlex.quote(str(value))}")
    return " ".join(parts)


def _render_report_command(
    module: str,
    service: str,
    action: str,
    selectors: dict[str, Any],
    payload: dict[str, Any] | None,
    *,
    mask_secrets: bool,
) -> str:
    if action == "delete":
        return _render_delete_command(module, service, selectors)
    return _render_command(
        module,
        service,
        action,
        selectors,
        sanitize_secrets(payload or {}, mask_secrets=mask_secrets),
    )


def _prepare_write_payload(
    plugin,
    cp,
    token: str,
    api_catalog: dict[str, Any],
    *,
    module: str,
    service: str,
    action: str,
    selectors: dict[str, Any],
    payload: dict[str, Any],
    settings: Settings,
):
    action_args = {
        "module": module,
        "service": service,
        "action": action,
        **selectors,
        "payload_json": json.dumps(payload, ensure_ascii=False),
    }
    request_args, request_payload = _request_args_and_payload(
        cp, api_catalog, action_args, action, payload
    )
    request_payload = _prepare_plugin_write_payload(
        cp,
        token,
        api_catalog,
        request_args,
        action,
        request_payload,
        settings=settings,
    )
    preflight = getattr(plugin, "preflight_error_for_payload", None)
    if callable(preflight):
        preflight_action = "create" if action == "add" else action
        reason = preflight(module, service, preflight_action, request_payload)
        if reason:
            raise ValueError(reason)
    return request_args, request_payload


def _planned_item(
    *,
    desired: ConfigObject | None,
    current: ConfigObject | None,
    action: str,
    selectors: dict[str, Any],
    payload: dict[str, Any] | None,
    rollback_action: str,
    rollback_selectors: dict[str, Any],
    rollback_payload: dict[str, Any] | None,
    match_key: tuple[str, str, str, str] | None,
    mask_secrets: bool,
) -> dict[str, Any]:
    obj = desired or current
    assert obj is not None
    module = obj.module
    service = obj.service
    return {
        "line": (
            desired.command.line_no if desired is not None else current.command.line_no
        ),
        "module": module,
        "service": service,
        "label": _object_label(obj),
        "operation": action,
        "match_key": list(match_key) if match_key is not None else None,
        "command": _render_report_command(
            module,
            service,
            action,
            selectors,
            payload,
            mask_secrets=mask_secrets,
        ),
        "rollback_command": _render_report_command(
            module,
            service,
            rollback_action,
            rollback_selectors,
            rollback_payload,
            mask_secrets=mask_secrets,
        ),
        "_request": {
            "action": action,
            "args": {
                "module": module,
                "service": service,
                "action": action,
                **selectors,
            },
            "payload": payload,
        },
    }


def _plan_change(
    plugin,
    cp,
    token: str,
    api_catalog: dict[str, Any],
    desired: ConfigObject,
    current: ConfigObject,
    *,
    match_key: tuple[str, str, str, str] | None,
    settings: Settings,
    mask_secrets: bool,
) -> dict[str, Any]:
    action, selectors = _choose_change_action(api_catalog, current)
    if action is None or selectors is None:
        return {
            "line": desired.command.line_no,
            "module": desired.module,
            "service": desired.service,
            "label": _object_label(desired),
            "operation": "change",
            "status": "skipped",
            "reason": "no reversible update or replace action is available",
        }

    desired_payload = _drop_masked_secret_placeholders(desired.payload)
    request_args, request_payload = _prepare_write_payload(
        plugin,
        cp,
        token,
        api_catalog,
        module=desired.module,
        service=desired.service,
        action=action,
        selectors=selectors,
        payload=desired_payload,
        settings=settings,
    )
    item = _planned_item(
        desired=desired,
        current=current,
        action=action,
        selectors=selectors,
        payload=request_payload,
        rollback_action=action,
        rollback_selectors=selectors,
        rollback_payload=current.payload,
        match_key=match_key,
        mask_secrets=mask_secrets,
    )
    item["_request"] = {
        "action": action,
        "args": request_args,
        "payload": request_payload,
    }
    item["status"] = "pending"
    return item


def _plan_create(
    plugin,
    cp,
    token: str,
    api_catalog: dict[str, Any],
    desired: ConfigObject,
    *,
    settings: Settings,
    mask_secrets: bool,
) -> dict[str, Any]:
    if not _has_action(api_catalog, desired.module, desired.service, "add"):
        return {
            "line": desired.command.line_no,
            "module": desired.module,
            "service": desired.service,
            "label": _object_label(desired),
            "operation": "add",
            "status": "skipped",
            "reason": "add action is not available",
        }
    if not _has_action(api_catalog, desired.module, desired.service, "delete"):
        return {
            "line": desired.command.line_no,
            "module": desired.module,
            "service": desired.service,
            "label": _object_label(desired),
            "operation": "add",
            "status": "skipped",
            "reason": "create is not reversible because delete is unavailable",
        }

    rollback_selectors = _selector_args(
        api_catalog,
        desired.module,
        desired.service,
        "delete",
        _selector_source(desired, include_source_identity=False),
    )
    if rollback_selectors is None:
        return {
            "line": desired.command.line_no,
            "module": desired.module,
            "service": desired.service,
            "label": _object_label(desired),
            "operation": "add",
            "status": "skipped",
            "reason": "create is not reversible without a stable delete selector",
        }

    desired_payload = _drop_masked_secret_placeholders(desired.payload)
    request_args, request_payload = _prepare_write_payload(
        plugin,
        cp,
        token,
        api_catalog,
        module=desired.module,
        service=desired.service,
        action="add",
        selectors={},
        payload=desired_payload,
        settings=settings,
    )
    item = _planned_item(
        desired=desired,
        current=None,
        action="add",
        selectors={},
        payload=request_payload,
        rollback_action="delete",
        rollback_selectors=rollback_selectors,
        rollback_payload=None,
        match_key=None,
        mask_secrets=mask_secrets,
    )
    item["_request"] = {
        "action": "add",
        "args": request_args,
        "payload": request_payload,
    }
    item["status"] = "pending"
    return item


def _plan_delete(
    current: ConfigObject,
    api_catalog: dict[str, Any],
    *,
    desired_keys: set[tuple[str, str, str, str]],
    mask_secrets: bool,
) -> dict[str, Any] | None:
    current_keys = set(_object_keys(current))
    if current_keys & desired_keys:
        return None
    if not _has_action(api_catalog, current.module, current.service, "delete"):
        return {
            "line": current.command.line_no,
            "module": current.module,
            "service": current.service,
            "label": _object_label(current),
            "operation": "delete",
            "status": "skipped",
            "reason": (
                "current-only object is not reversible because delete is unavailable"
            ),
        }
    if not _has_action(api_catalog, current.module, current.service, "add"):
        return {
            "line": current.command.line_no,
            "module": current.module,
            "service": current.service,
            "label": _object_label(current),
            "operation": "delete",
            "status": "skipped",
            "reason": "delete is not reversible because add is unavailable",
        }
    selectors = _selector_args(
        api_catalog,
        current.module,
        current.service,
        "delete",
        _selector_source(current),
    )
    if selectors is None:
        return {
            "line": current.command.line_no,
            "module": current.module,
            "service": current.service,
            "label": _object_label(current),
            "operation": "delete",
            "status": "skipped",
            "reason": "delete is not reversible without a selector",
        }

    item = _planned_item(
        desired=None,
        current=current,
        action="delete",
        selectors=selectors,
        payload=None,
        rollback_action="add",
        rollback_selectors={},
        rollback_payload=current.payload,
        match_key=None,
        mask_secrets=mask_secrets,
    )
    item["status"] = "pending"
    return item


def build_import_plan(
    plugin,
    cp,
    token: str,
    api_catalog: dict[str, Any],
    desired_commands: list[ConfigCommand],
    current_commands: list[ConfigCommand],
    *,
    settings: Settings,
    exclude: set[tuple[str, str | None]] | None = None,
    mask_secrets: bool = True,
) -> list[dict[str, Any]]:
    active_exclude = exclude or _exclude_scope_from_settings(settings)
    desired_objects = _objects_from_commands(
        _importable_commands(desired_commands, exclude=active_exclude)
    )
    current_objects = _objects_from_commands(
        _importable_commands(current_commands, exclude=active_exclude)
    )
    current_index = _build_index(current_objects)
    plan: list[dict[str, Any]] = []
    matched_current: set[int] = set()

    for desired in desired_objects:
        current, match_key, match_error = _find_current_match(desired, current_index)
        if match_error:
            plan.append(
                {
                    "line": desired.command.line_no,
                    "module": desired.module,
                    "service": desired.service,
                    "label": _object_label(desired),
                    "operation": "match",
                    "status": "skipped",
                    "reason": match_error,
                }
            )
            continue
        if current is None:
            try:
                plan.append(
                    _plan_create(
                        plugin,
                        cp,
                        token,
                        api_catalog,
                        desired,
                        settings=settings,
                        mask_secrets=mask_secrets,
                    )
                )
            except Exception as exc:
                plan.append(
                    {
                        "line": desired.command.line_no,
                        "module": desired.module,
                        "service": desired.service,
                        "label": _object_label(desired),
                        "operation": "add",
                        "status": "skipped",
                        "reason": str(exc),
                    }
                )
            continue

        matched_current.add(id(current))
        if _payloads_match(desired.payload, current.payload):
            plan.append(
                {
                    "line": desired.command.line_no,
                    "module": desired.module,
                    "service": desired.service,
                    "label": _object_label(desired),
                    "operation": "none",
                    "status": "unchanged",
                    "match_key": list(match_key) if match_key is not None else None,
                }
            )
            continue

        try:
            plan.append(
                _plan_change(
                    plugin,
                    cp,
                    token,
                    api_catalog,
                    desired,
                    current,
                    match_key=match_key,
                    settings=settings,
                    mask_secrets=mask_secrets,
                )
            )
        except Exception as exc:
            plan.append(
                {
                    "line": desired.command.line_no,
                    "module": desired.module,
                    "service": desired.service,
                    "label": _object_label(desired),
                    "operation": "change",
                    "status": "skipped",
                    "reason": str(exc),
                }
            )

    desired_services = {(obj.module, obj.service) for obj in desired_objects}
    desired_keys = {key for obj in desired_objects for key in _object_keys(obj)}
    for current in current_objects:
        if id(current) in matched_current:
            continue
        if (current.module, current.service) not in desired_services:
            continue
        item = _plan_delete(
            current,
            api_catalog,
            desired_keys=desired_keys,
            mask_secrets=mask_secrets,
        )
        if item is not None:
            plan.append(item)

    return plan


def _execute_plan_item(
    cp,
    token: str,
    api_catalog: dict[str, Any],
    item: dict[str, Any],
):
    request = item.get("_request") or {}
    action = request.get("action")
    args = request.get("args") or {
        "module": item["module"],
        "service": item["service"],
        "action": action,
    }
    if action == "delete":
        params = query_params_for_action(cp, api_catalog, args, "delete")
        return cp.delete(api_catalog, token, args, params=params or None)
    operation = getattr(cp, str(action))
    return operation(api_catalog, token, args, request.get("payload"))


def _summary(plan: list[dict[str, Any]]) -> dict[str, int]:
    executable = [
        item
        for item in plan
        if item["status"] in {"pending", "planned", "success", "failed"}
    ]
    return {
        "selected": len(plan),
        "unchanged": sum(1 for item in plan if item["status"] == "unchanged"),
        "planned": sum(1 for item in plan if item["status"] == "planned"),
        "applied": sum(1 for item in plan if item["status"] == "success"),
        "skipped": sum(1 for item in plan if item["status"] == "skipped"),
        "failed": sum(1 for item in plan if item["status"] == "failed"),
        "executable": len(executable),
        "create": sum(1 for item in executable if item["operation"] == "add"),
        "update": sum(1 for item in executable if item["operation"] == "update"),
        "replace": sum(1 for item in executable if item["operation"] == "replace"),
        "delete": sum(1 for item in executable if item["operation"] == "delete"),
    }


def import_running_config(
    plugin,
    cp,
    token: str,
    api_catalog: dict[str, Any],
    desired_commands: list[ConfigCommand],
    current_commands: list[ConfigCommand],
    *,
    source: str | Path,
    settings: Settings,
    dry_run: bool = False,
    continue_on_error: bool = False,
    exclude: set[tuple[str, str | None]] | None = None,
    mask_secrets: bool = True,
) -> dict[str, Any]:
    plan = build_import_plan(
        plugin,
        cp,
        token,
        api_catalog,
        desired_commands,
        current_commands,
        settings=settings,
        exclude=exclude,
        mask_secrets=mask_secrets,
    )

    for item in plan:
        if item["status"] != "pending":
            continue
        if dry_run:
            item["status"] = "planned"
            item.pop("_request", None)
            continue
        try:
            response = _execute_plan_item(cp, token, api_catalog, item)
            item["status"] = "success"
            item["response"] = sanitize_secrets(response, mask_secrets=mask_secrets)
        except Exception as exc:
            item["status"] = "failed"
            item["reason"] = str(exc)
            if not continue_on_error:
                item.pop("_request", None)
                break
        item.pop("_request", None)

    for item in plan:
        item.pop("_request", None)

    return {
        "mode": "import",
        "source": str(source),
        "dry_run": dry_run,
        "summary": _summary(plan),
        "items": plan,
    }


def _emit_summary(report: dict[str, Any]) -> None:
    summary = report["summary"]
    print("Import dry run" if report.get("dry_run") else "Import completed")
    print(f"Source: {report['source']}")
    print(f"Selected: {summary['selected']}")
    print(f"Unchanged: {summary['unchanged']}")
    print(f"Planned: {summary['planned']}")
    print(f"Applied: {summary['applied']}")
    print(f"Skipped: {summary['skipped']}")
    print(f"Failed: {summary['failed']}")
    skipped = [item for item in report["items"] if item["status"] == "skipped"]
    failed = [item for item in report["items"] if item["status"] == "failed"]
    if skipped:
        print("Skipped reasons:")
        for item in skipped[:10]:
            print(
                f"- line {item['line']} {item['module']} {item['service']}: "
                f"{item.get('reason', 'not importable')}"
            )
    if failed:
        print("Failure reasons:")
        for item in failed[:10]:
            print(
                f"- line {item['line']} {item['module']} {item['service']}: "
                f"{item.get('reason', 'unknown error')}"
            )
    artifacts = report.get("artifacts") or {}
    if artifacts.get("report"):
        print(f"Report: {artifacts['report']}")


def _current_scope(
    commands: list[ConfigCommand],
    *,
    exclude: set[tuple[str, str | None]],
) -> set[tuple[str, str | None]]:
    return {
        (str(command.args["module"]), str(command.args["service"]))
        for command in commands
        if not _is_excluded_scope(
            str(command.args.get("module")),
            str(command.args.get("service")),
            exclude,
        )
    }


def handle_import_command(
    args: dict[str, Any],
    *,
    plugin,
    settings: Settings,
    deps,
    log=None,
) -> bool:
    if args.get("module") != "import":
        return False
    if args.get("service") or args.get("action") or not args.get("file"):
        return False

    source_path = Path(args["file"])
    desired_commands = parse_running_config(source_path)
    mask_secrets = should_mask_secrets(args, settings)
    dry_run = bool(args.get("dry_run"))
    continue_on_error = bool(args.get("continue_on_error"))
    exclude = (
        _parse_scope(args.get("exclude"))
        if args.get("exclude") is not None
        else _exclude_scope_from_settings(settings)
    )

    if log is not None:
        log.info(
            "Importing config via plugin '%s' to server: %s",
            plugin.name,
            settings.server,
        )

    cp = plugin.build_client(settings, mask_secrets=mask_secrets)
    try:
        setattr(cp, "netloom_plugin", plugin)
    except Exception:
        pass
    token = plugin.resolve_auth_token(cp, settings)
    catalog_view = deps._catalog_view_from_args(args)
    api_catalog = deps._get_catalog_for_cli(
        plugin,
        cp,
        token=token,
        settings=settings,
        catalog_view=catalog_view,
    )

    current_scope = _current_scope(desired_commands, exclude=exclude)
    if current_scope:
        current_text = render_running_config(
            plugin,
            cp,
            token,
            api_catalog,
            settings=settings,
            catalog_view=catalog_view,
            include=current_scope,
            exclude=exclude,
            mask_secrets=False,
            hydrate_mode="auto",
            log=log,
        )
        current_commands = parse_running_config_text(current_text)
    else:
        current_commands = []
    report = import_running_config(
        plugin,
        cp,
        token,
        api_catalog,
        desired_commands,
        current_commands,
        source=source_path,
        settings=settings,
        dry_run=dry_run,
        continue_on_error=continue_on_error,
        exclude=exclude,
        mask_secrets=mask_secrets,
    )

    out_path = args.get("out")
    if out_path:
        report["artifacts"] = {"report": str(out_path)}
        ensure_parent_dir(Path(out_path))
        write_value_to_file(
            report,
            out_path,
            data_format="json",
            mask_secrets=False,
        )
    else:
        report["artifacts"] = {}

    _emit_summary(report)
    if args.get("console"):
        print(json.dumps(report, indent=2, ensure_ascii=False))

    return True


__all__ = [
    "ConfigCommand",
    "build_import_plan",
    "handle_import_command",
    "import_running_config",
    "parse_running_config",
    "parse_running_config_text",
]
