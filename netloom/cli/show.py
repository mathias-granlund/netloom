from __future__ import annotations

import json
import re
import shlex
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from netloom.core.config import Settings
from netloom.core.help_shared import display_services_for_module, resolve_service_entry
from netloom.core.pagination import fetch_all_list_results
from netloom.core.resolver import query_params_for_action
from netloom.io.files import ensure_parent_dir
from netloom.io.output import sanitize_secrets, should_mask_secrets

_READ_ACTION_ORDER = ("list", "get")
_WRITE_ACTION_ORDER = ("add", "replace", "update")
_SOURCE_IDENTITY_FIELDS = ("id", "uuid")
_HYDRATE_MODES = {"auto", "never", "always"}
_PLACEHOLDER_RE = re.compile(r"\{([^}]+)\}")
_SELECTOR_ALIASES = {
    "services_name": ("name",),
}


def _action_map(api_catalog: dict[str, Any], module: str, service: str) -> dict:
    entry = resolve_service_entry(api_catalog, module, service) or {}
    actions = entry.get("actions") or {}
    return actions if isinstance(actions, dict) else {}


def _has_action(
    api_catalog: dict[str, Any], module: str, service: str, action: str
) -> bool:
    return action in _action_map(api_catalog, module, service)


def _service_args(module: str, service: str, action: str, **extra) -> dict[str, Any]:
    return {
        "module": module,
        "service": service,
        "action": action,
        **{key: value for key, value in extra.items() if value not in (None, "")},
    }


def _extract_items(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        embedded = value.get("_embedded")
        if isinstance(embedded, dict):
            items = embedded.get("items")
            if isinstance(items, list):
                return [item for item in items if isinstance(item, dict)]
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _path_placeholders(path: str) -> list[str]:
    return _PLACEHOLDER_RE.findall(path)


def _required_selector_options_for_unscoped_action(
    api_catalog: dict[str, Any],
    module: str,
    service: str,
    action: str,
) -> list[tuple[str, ...]]:
    action_def = _action_map(api_catalog, module, service).get(action) or {}
    paths = action_def.get("paths") or []
    options: list[tuple[str, ...]] = []

    for path in paths:
        placeholders = tuple(_path_placeholders(str(path)))
        if not placeholders:
            return []
        options.append(placeholders)

    return options


def _format_selector_options(options: list[tuple[str, ...]]) -> str:
    rendered: list[str] = []
    for option in options:
        flags = [
            f"--{name.replace('_', '-')}=..."
            for name in option
            if name not in (None, "")
        ]
        if flags:
            rendered.append(" ".join(flags))
    return " OR ".join(rendered)


def _selector_args_for_item(
    api_catalog: dict[str, Any],
    module: str,
    service: str,
    action: str,
    item: dict[str, Any],
) -> dict[str, Any] | None:
    action_def = _action_map(api_catalog, module, service).get(action) or {}
    paths = action_def.get("paths") or []
    candidate_sets: list[list[str]] = []

    for path in paths:
        placeholders = _path_placeholders(str(path))
        if not placeholders:
            return {}
        candidate_sets.append(placeholders)

    if not candidate_sets:
        return {}

    candidate_sets.sort(key=lambda names: (-len(names), names))
    for names in candidate_sets:
        selectors: dict[str, Any] = {}
        for name in names:
            value = item.get(name)
            if value in (None, ""):
                for alias in _SELECTOR_ALIASES.get(name, ()):
                    value = item.get(alias)
                    if value not in (None, ""):
                        break
            if value in (None, ""):
                break
            selectors[name] = value
        if len(selectors) == len(names):
            return selectors
    return None


def _read_args_for_item(
    api_catalog: dict[str, Any],
    module: str,
    service: str,
    item: dict[str, Any],
) -> dict[str, Any] | None:
    selectors = _selector_args_for_item(api_catalog, module, service, "get", item)
    if selectors is None:
        return None
    return _service_args(module, service, "get", **selectors)


def _select_write_action(api_catalog: dict[str, Any], module: str, service: str):
    actions = _action_map(api_catalog, module, service)
    for action in _WRITE_ACTION_ORDER:
        if action in actions:
            return action
    return None


def _quote_value(value: Any) -> str:
    if isinstance(value, bool):
        text = "true" if value else "false"
    else:
        text = str(value)
    return shlex.quote(text)


def _quote_json(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return shlex.quote(text)


def _format_metadata_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _source_identity_comments(*items: dict[str, Any]) -> list[str]:
    values: dict[str, Any] = {}
    for item in items:
        for field in _SOURCE_IDENTITY_FIELDS:
            value = item.get(field)
            if value not in (None, ""):
                values[field] = value
    return [
        f"# source-{field}: {_format_metadata_value(values[field])}"
        for field in _SOURCE_IDENTITY_FIELDS
        if field in values
    ]


def _render_command(
    module: str,
    service: str,
    action: str,
    selectors: dict[str, Any],
    payload: dict[str, Any],
) -> str:
    parts = ["netloom", module, service, action]
    for key, value in sorted(selectors.items()):
        parts.append(f"--{key.replace('_', '-')}={_quote_value(value)}")
    parts.append(f"--payload-json={_quote_json(payload)}")
    return " ".join(parts)


def _render_selector_flags(args: dict[str, Any]) -> str:
    selectors = {
        key: value
        for key, value in args.items()
        if key not in {"module", "service", "action"} and value not in (None, "")
    }
    if not selectors:
        return ""
    return " " + " ".join(
        f"--{key.replace('_', '-')}={_quote_value(value)}"
        for key, value in sorted(selectors.items())
    )


def _emit_info(log, message: str, *args) -> None:
    if log is not None:
        log.info(message, *args)


def _emit_debug(log, message: str, *args) -> None:
    if log is not None:
        log.debug(message, *args)


def _emit_line(
    lines: list[str],
    line_sink: Callable[[str], None] | None,
    line: str = "",
) -> None:
    lines.append(line)
    if line_sink is not None:
        line_sink(line)


def _emit_lines(
    lines: list[str],
    line_sink: Callable[[str], None] | None,
    values: list[str],
) -> None:
    for value in values:
        _emit_line(lines, line_sink, value)


def _normalize_payload(
    plugin,
    cp,
    api_catalog: dict[str, Any],
    module: str,
    service: str,
    action: str,
    selectors: dict[str, Any],
    item: dict[str, Any],
) -> dict[str, Any] | None:
    action_args = _service_args(module, service, action, **selectors)
    normalizer = getattr(plugin, "normalize_copy_payload", None)
    if callable(normalizer):
        payload = normalizer(cp, api_catalog, action_args, action, item)
    else:
        payload = dict(item)

    if not isinstance(payload, dict):
        return None
    return {
        key: value for key, value in payload.items() if value not in (None, "", [], {})
    }


def _parse_scope(value: Any) -> set[tuple[str, str | None]]:
    if value in (None, ""):
        return set()
    scope: set[tuple[str, str | None]] = set()
    for raw_item in str(value).split(","):
        item = raw_item.strip()
        if not item:
            continue
        if "/" in item:
            module, service = item.split("/", 1)
            module = module.strip()
            service = service.strip()
            if module and service:
                scope.add((module, service))
        else:
            scope.add((item, None))
    return scope


def _exclude_scope_from_settings(settings: Settings) -> set[tuple[str, str | None]]:
    return _parse_scope(getattr(settings, "running_config_exclude", None))


def _in_scope(
    module: str,
    service: str,
    *,
    include: set[tuple[str, str | None]],
    exclude: set[tuple[str, str | None]],
) -> bool:
    key = (module, service)
    module_key = (module, None)
    if include and key not in include and module_key not in include:
        return False
    return key not in exclude and module_key not in exclude


def _default_out_path(settings: Settings) -> Path:
    return Path(settings.paths.response_dir) / "running-config.txt"


def _header(
    settings: Settings, plugin, catalog_view: str, hydrate_mode: str
) -> list[str]:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return [
        "# netloom running-config",
        f"# generated-at: {generated_at}",
        f"# profile: {getattr(settings, 'active_profile', None) or '<unset>'}",
        f"# plugin: {getattr(plugin, 'name', None) or '<unset>'}",
        f"# server: {getattr(settings, 'server', None) or '<unset>'}",
        f"# catalog-view: {catalog_view}",
        f"# hydrate: {hydrate_mode}",
        "",
    ]


def _netloom_format_header(
    settings: Settings, plugin, args: dict[str, Any], hydrate_mode: str
) -> list[str]:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    source = " ".join(
        str(args.get(key))
        for key in ("module", "service", "action")
        if args.get(key) not in (None, "")
    )
    return [
        "# netloom export",
        f"# generated-at: {generated_at}",
        f"# profile: {getattr(settings, 'active_profile', None) or '<unset>'}",
        f"# plugin: {getattr(plugin, 'name', None) or '<unset>'}",
        f"# server: {getattr(settings, 'server', None) or '<unset>'}",
        f"# source: netloom {source}",
        f"# hydrate: {hydrate_mode}",
        "",
    ]


def _hydrate_item(
    cp,
    token: str,
    api_catalog: dict[str, Any],
    module: str,
    service: str,
    item: dict[str, Any],
    *,
    log=None,
) -> dict[str, Any]:
    if not _has_action(api_catalog, module, service, "get"):
        return item

    get_args = _read_args_for_item(api_catalog, module, service, item)
    if get_args is None:
        _emit_debug(
            log,
            "running-config: skip hydrate %s %s item=%s: no get selector",
            module,
            service,
            item.get("id") or item.get("name") or "<unknown>",
        )
        return item
    if "action" not in get_args:
        get_args = _service_args(module, service, "get", **get_args)

    params = query_params_for_action(cp, api_catalog, get_args, "get")
    _emit_debug(
        log,
        "running-config: GET via netloom %s %s get%s",
        module,
        service,
        _render_selector_flags(get_args),
    )
    result = cp.get(api_catalog, token, get_args, params=params or None)
    items = _extract_items(result)
    return items[0] if items else item


def _render_item(
    plugin,
    cp,
    api_catalog: dict[str, Any],
    module: str,
    service: str,
    item: dict[str, Any],
    *,
    mask_secrets: bool,
) -> str | None:
    write_action = _select_write_action(api_catalog, module, service)
    if write_action is None:
        return None

    selectors: dict[str, Any] = {}
    if write_action in {"replace", "update"}:
        resolved = _selector_args_for_item(
            api_catalog, module, service, write_action, item
        )
        if resolved is None:
            return None
        selectors = resolved

    payload = _normalize_payload(
        plugin,
        cp,
        api_catalog,
        module,
        service,
        write_action,
        selectors,
        item,
    )
    if not payload:
        return None
    payload = sanitize_secrets(payload, mask_secrets=mask_secrets)
    return _render_command(module, service, write_action, selectors, payload)


def _normalize_hydrate_mode(value: Any) -> str:
    mode = "auto" if value in (None, "") else str(value).strip().lower()
    if mode not in _HYDRATE_MODES:
        supported = ", ".join(sorted(_HYDRATE_MODES))
        raise ValueError(f"--hydrate must be one of: {supported}")
    return mode


def _item_label(item: dict[str, Any]) -> Any:
    return item.get("id") or item.get("uuid") or item.get("name") or "<unknown>"


def _render_item_for_hydrate_mode(
    plugin,
    cp,
    token: str,
    api_catalog: dict[str, Any],
    module: str,
    service: str,
    item: dict[str, Any],
    *,
    hydrate_mode: str,
    source_action: str,
    mask_secrets: bool,
    log=None,
) -> tuple[list[str], str | None]:
    if source_action != "list":
        command = _render_item(
            plugin,
            cp,
            api_catalog,
            module,
            service,
            item,
            mask_secrets=mask_secrets,
        )
        return _source_identity_comments(item), command

    if hydrate_mode in {"auto", "never"}:
        command = _render_item(
            plugin,
            cp,
            api_catalog,
            module,
            service,
            item,
            mask_secrets=mask_secrets,
        )
        if command or hydrate_mode == "never":
            if command and hydrate_mode == "auto":
                _emit_debug(
                    log,
                    "running-config: use list item for %s %s item=%s",
                    module,
                    service,
                    _item_label(item),
                )
            return _source_identity_comments(item), command

        _emit_debug(
            log,
            "running-config: auto hydrate %s %s item=%s: list item was not renderable",
            module,
            service,
            _item_label(item),
        )

    hydrated = _hydrate_item(
        cp,
        token,
        api_catalog,
        module,
        service,
        item,
        log=log,
    )
    command = _render_item(
        plugin,
        cp,
        api_catalog,
        module,
        service,
        hydrated,
        mask_secrets=mask_secrets,
    )
    return _source_identity_comments(item, hydrated), command


def render_running_config(
    plugin,
    cp,
    token: str,
    api_catalog: dict[str, Any],
    *,
    settings: Settings,
    catalog_view: str,
    include: set[tuple[str, str | None]] | None = None,
    exclude: set[tuple[str, str | None]] | None = None,
    continue_on_error: bool = False,
    mask_secrets: bool = True,
    hydrate_mode: str = "auto",
    line_sink: Callable[[str], None] | None = None,
    log=None,
) -> str:
    hydrate_mode = _normalize_hydrate_mode(hydrate_mode)
    include = include or set()
    exclude = (
        _exclude_scope_from_settings(settings) if exclude is None else set(exclude)
    )
    lines: list[str] = []
    _emit_lines(lines, line_sink, _header(settings, plugin, catalog_view, hydrate_mode))
    modules = api_catalog.get("modules") or {}
    selected_services: list[tuple[str, str]] = []

    for module in sorted(modules):
        services = display_services_for_module(api_catalog, module)
        for service in sorted(services):
            if not _in_scope(module, service, include=include, exclude=exclude):
                continue
            selected_services.append((module, service))

    _emit_info(
        log,
        "running-config: selected %d services from %d modules (hydrate=%s)",
        len(selected_services),
        len(modules),
        hydrate_mode,
    )

    total_services = len(selected_services)
    for service_index, (module, service) in enumerate(selected_services, start=1):
        actions = _action_map(api_catalog, module, service)
        if not any(action in actions for action in _READ_ACTION_ORDER):
            _emit_debug(
                log,
                "running-config: [%d/%d] skip %s %s: no read action",
                service_index,
                total_services,
                module,
                service,
            )
            _emit_line(
                lines, line_sink, f"# skipped {module} {service}: no read action"
            )
            continue
        if _select_write_action(api_catalog, module, service) is None:
            _emit_debug(
                log,
                "running-config: [%d/%d] skip %s %s: no write action",
                service_index,
                total_services,
                module,
                service,
            )
            _emit_line(
                lines,
                line_sink,
                f"# skipped {module} {service}: no add, replace, or update action",
            )
            continue
        if "list" not in actions and "get" in actions:
            selector_options = _required_selector_options_for_unscoped_action(
                api_catalog, module, service, "get"
            )
            if selector_options:
                selectors = _format_selector_options(selector_options)
                _emit_debug(
                    log,
                    ("running-config: [%d/%d] skip %s %s: get requires selectors (%s)"),
                    service_index,
                    total_services,
                    module,
                    service,
                    selectors,
                )
                _emit_line(
                    lines,
                    line_sink,
                    (
                        f"# skipped {module} {service}: "
                        f"get requires selectors ({selectors})"
                    ),
                )
                continue

        _emit_line(lines, line_sink, f"# {module} {service}")
        service_started = time.perf_counter()
        try:
            if "list" in actions:
                list_args = _service_args(module, service, "list")
                _emit_info(
                    log,
                    "running-config: [%d/%d] list %s %s",
                    service_index,
                    total_services,
                    module,
                    service,
                )
                _emit_debug(
                    log,
                    "running-config: LIST via netloom %s %s list",
                    module,
                    service,
                )
                response = fetch_all_list_results(cp, token, api_catalog, list_args)
                items = _extract_items(response)
                source_action = "list"
            else:
                get_args = _service_args(module, service, "get")
                params = query_params_for_action(cp, api_catalog, get_args, "get")
                _emit_info(
                    log,
                    "running-config: [%d/%d] get %s %s",
                    service_index,
                    total_services,
                    module,
                    service,
                )
                _emit_debug(
                    log,
                    "running-config: GET via netloom %s %s get",
                    module,
                    service,
                )
                items = _extract_items(
                    cp.get(api_catalog, token, get_args, params=params or None)
                )
                source_action = "get"

            _emit_info(
                log,
                "running-config: [%d/%d] fetched %d item(s) from %s %s",
                service_index,
                total_services,
                len(items),
                module,
                service,
            )
            rendered = 0
            for item_index, item in enumerate(items, start=1):
                try:
                    _emit_debug(
                        log,
                        "running-config: [%d/%d] render item %d/%d from %s %s",
                        service_index,
                        total_services,
                        item_index,
                        len(items),
                        module,
                        service,
                    )
                    identity_comments, command = _render_item_for_hydrate_mode(
                        plugin,
                        cp,
                        token,
                        api_catalog,
                        module,
                        service,
                        item,
                        hydrate_mode=hydrate_mode,
                        source_action=source_action,
                        mask_secrets=mask_secrets,
                        log=log,
                    )
                except Exception as exc:
                    if not continue_on_error:
                        raise
                    _emit_line(lines, line_sink, f"# error {module} {service}: {exc}")
                    continue
                if command:
                    _emit_lines(lines, line_sink, identity_comments)
                    _emit_line(lines, line_sink, command)
                    rendered += 1

            if rendered == 0:
                _emit_line(
                    lines,
                    line_sink,
                    f"# skipped {module} {service}: no renderable items",
                )
            _emit_info(
                log,
                ("running-config: [%d/%d] rendered %d/%d item(s) from %s %s in %.1fs"),
                service_index,
                total_services,
                rendered,
                len(items),
                module,
                service,
                time.perf_counter() - service_started,
            )
        except Exception as exc:
            if not continue_on_error:
                raise
            _emit_info(
                log,
                "running-config: [%d/%d] error %s %s: %s",
                service_index,
                total_services,
                module,
                service,
                exc,
            )
            _emit_line(lines, line_sink, f"# error {module} {service}: {exc}")
        _emit_line(lines, line_sink, "")

    return "\n".join(lines).rstrip() + "\n"


def render_netloom_format(
    plugin,
    cp,
    token: str,
    api_catalog: dict[str, Any],
    args: dict[str, Any],
    result,
    *,
    settings: Settings,
    source_action: str,
    mask_secrets: bool = True,
    hydrate_mode: str = "auto",
    log=None,
) -> str:
    hydrate_mode = _normalize_hydrate_mode(hydrate_mode)
    module = args["module"]
    service = args["service"]
    lines = _netloom_format_header(settings, plugin, args, hydrate_mode)
    _emit_line(lines, None, f"# {module} {service}")

    items = _extract_items(result)
    rendered = 0
    for item_index, item in enumerate(items, start=1):
        _emit_debug(
            log,
            "netloom-format: render item %d/%d from %s %s",
            item_index,
            len(items),
            module,
            service,
        )
        identity_comments, command = _render_item_for_hydrate_mode(
            plugin,
            cp,
            token,
            api_catalog,
            module,
            service,
            item,
            hydrate_mode=hydrate_mode,
            source_action=source_action,
            mask_secrets=mask_secrets,
            log=log,
        )
        if command:
            _emit_lines(lines, None, identity_comments)
            _emit_line(lines, None, command)
            rendered += 1

    if rendered == 0:
        _emit_line(lines, None, f"# skipped {module} {service}: no renderable items")

    return "\n".join(lines).rstrip() + "\n"


def handle_show_command(
    args: dict[str, Any],
    *,
    plugin,
    settings: Settings,
    deps,
    log=None,
) -> bool:
    if args.get("module") != "show":
        return False
    if args.get("service") != "running-config" or args.get("action"):
        return False

    mask_secrets = should_mask_secrets(args, settings)
    cp = plugin.build_client(settings, mask_secrets=mask_secrets)
    if log is not None:
        log.info(
            "Exporting running config via plugin '%s' from server: %s",
            plugin.name,
            settings.server,
        )
    token = plugin.resolve_auth_token(cp, settings)
    catalog_view = deps._catalog_view_from_args(args)
    api_catalog = deps._get_catalog_for_cli(
        plugin,
        cp,
        token=token,
        settings=settings,
        catalog_view=catalog_view,
    )
    out_path = Path(args.get("out") or _default_out_path(settings))
    ensure_parent_dir(out_path)

    with out_path.open("w", encoding="utf-8") as output_file:

        def stream_line(line: str) -> None:
            rendered = f"{line}\n"
            output_file.write(rendered)
            output_file.flush()
            sys.stdout.write(rendered)
            sys.stdout.flush()

        try:
            render_running_config(
                plugin,
                cp,
                token,
                api_catalog,
                settings=settings,
                catalog_view=catalog_view,
                include=_parse_scope(args.get("include")),
                exclude=(
                    _parse_scope(args.get("exclude"))
                    if args.get("exclude") is not None
                    else None
                ),
                continue_on_error=bool(args.get("continue_on_error")),
                mask_secrets=mask_secrets,
                hydrate_mode=args.get("hydrate") or "auto",
                line_sink=stream_line,
                log=log,
            )
        except KeyboardInterrupt:
            stream_line(
                "# interrupted: running-config export stopped before completion"
            )
            raise
        except Exception as exc:
            stream_line(f"# aborted: {exc}")
            raise
    return True


__all__ = ["handle_show_command", "render_netloom_format", "render_running_config"]
