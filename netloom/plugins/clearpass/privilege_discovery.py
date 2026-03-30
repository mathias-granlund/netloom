from __future__ import annotations

import argparse
import copy
import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
import urllib3

from netloom.core.config import load_settings_for_profile
from netloom.plugins.clearpass.catalog import (
    OAUTH_ENDPOINTS,
    ApiEndpointCache,
    project_catalog_view,
)
from netloom.plugins.clearpass.plugin import build_client, resolve_auth_token
from netloom.plugins.clearpass.privileges import service_privilege_rule_index

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DEFAULT_MODULES = (
    "enforcementprofile",
    "globalserverconfiguration",
    "identities",
    "localserverconfiguration",
    "logs",
    "policyelements",
)
DEFAULT_OUT_FILE = "clearpass_privilege_discovery.json"
LIST_QUERY_DEFAULTS = {
    "limit": 1,
    "offset": 0,
    "calculate_count": "false",
    "filter": "{}",
}
MODULE_PREFIX_VARIANTS = {
    "enforcementprofile": ("enforcement_profile",),
}
_WRITE_PROBE_NAME_PREFIX = "netloom-privilege-probe"


def _pluralize_token(token: str) -> str:
    if token.endswith("ies"):
        return token
    if token.endswith(("ses", "xes", "zes", "ches", "shes")):
        return token
    if token.endswith("y") and len(token) > 1 and token[-2] not in "aeiou":
        return token[:-1] + "ies"
    if token.endswith("s"):
        return token
    return token + "s"


def _singularize_token(token: str) -> str:
    if token.endswith("ies") and len(token) > 3:
        return token[:-3] + "y"
    if token.endswith("s") and len(token) > 1:
        return token[:-1]
    return token


def _candidate_keys(module_name: str, service_name: str) -> list[str]:
    tokens = [token for token in service_name.split("-") if token]
    if not tokens:
        return []

    variants: list[str] = []

    def add_variant(parts: list[str]) -> None:
        if not parts:
            return
        variants.append("cppm_" + "_".join(parts))

    add_variant(tokens)
    add_variant(tokens[:-1] + [_pluralize_token(tokens[-1])])
    add_variant(tokens[:-1] + [_singularize_token(tokens[-1])])

    prefixes = MODULE_PREFIX_VARIANTS.get(module_name, ())
    for prefix in prefixes:
        prefix_tokens = [token for token in prefix.split("_") if token]
        add_variant(prefix_tokens + tokens)
        add_variant(prefix_tokens + tokens[:-1] + [_pluralize_token(tokens[-1])])

    ordered: list[str] = []
    seen: set[str] = set()
    for variant in variants:
        if variant in seen:
            continue
        seen.add(variant)
        ordered.append(variant)
    return ordered


def _load_candidate_overrides(
    path: str | None,
) -> dict[str, list[str] | list[list[str]]]:
    if not path:
        return {}
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Candidate override file must contain a JSON object.")
    out: dict[str, list[str] | list[list[str]]] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not isinstance(value, list):
            continue
        combo_candidates: list[list[str]] = []
        string_candidates: list[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                string_candidates.append(item)
            elif isinstance(item, list):
                combo = [
                    part for part in item if isinstance(part, str) and part.strip()
                ]
                if combo:
                    combo_candidates.append(combo)
        if combo_candidates:
            out[key] = combo_candidates
        elif string_candidates:
            out[key] = string_candidates
    return out


def _merge_candidate_keys(*candidate_groups: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for group in candidate_groups:
        for value in group:
            normalized = value.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            ordered.append(normalized)
    return ordered


def _normalize_candidate_specs(
    override_value: list[str] | list[list[str]] | None,
    default_candidates: list[str],
) -> list[list[str]]:
    specs: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()

    def add_spec(values: list[str]) -> None:
        normalized = [value.strip() for value in values if value.strip()]
        if not normalized:
            return
        key = tuple(normalized)
        if key in seen:
            return
        seen.add(key)
        specs.append(normalized)

    if isinstance(override_value, list):
        if override_value and all(isinstance(item, list) for item in override_value):
            for item in override_value:
                add_spec([part for part in item if isinstance(part, str)])
        else:
            add_spec([item for item in override_value if isinstance(item, str)])

    for candidate in default_candidates:
        add_spec([candidate])
    return specs


def _operator_profile_path(name: str) -> str:
    return "/api/operator-profile/name/" + quote(name, safe="")


def _operator_profile_item_path(profile: dict[str, Any]) -> str:
    self_href = (((profile.get("_links") or {}).get("self") or {}).get("href")) or ""
    if isinstance(self_href, str) and self_href:
        if "/api/" in self_href:
            return self_href.split("/api/", 1)[1].join(("/api/", ""))
        return self_href

    profile_id = profile.get("id")
    if profile_id is not None:
        return f"/api/operator-profile/{profile_id}"

    name = profile.get("name")
    if isinstance(name, str) and name:
        return _operator_profile_path(name)

    raise ValueError("Operator profile payload does not include a usable identity.")


def _fetch_operator_profile(admin_cp, admin_token: str, name: str) -> dict[str, Any]:
    try:
        return admin_cp.request_path(
            "GET",
            _operator_profile_path(name),
            token=admin_token,
        )
    except requests.HTTPError as exc:
        response = exc.response
        if response is None or response.status_code != 404:
            raise

    listing = admin_cp.request_path(
        "GET",
        "/api/operator-profile?calculate_count=false&offset=0&limit=200&filter=%7B%7D",
        token=admin_token,
    )
    items = ((listing.get("_embedded") or {}).get("items")) or []
    for item in items:
        if isinstance(item, dict) and item.get("name") == name:
            return item
    raise ValueError(f"Operator profile '{name}' was not found.")


def _update_operator_profile(
    admin_cp, admin_token: str, profile: dict[str, Any], privileges: list[str]
) -> dict[str, Any]:
    payload = dict(profile)
    payload.pop("_links", None)
    payload["privileges"] = privileges
    return admin_cp.request_path(
        "PATCH",
        _operator_profile_item_path(profile),
        token=admin_token,
        json_body=payload,
    )


def _effective_privileges(discovery_cp, discovery_token: str) -> list[dict[str, str]]:
    response = discovery_cp.request(
        OAUTH_ENDPOINTS, "GET", "oauth-privileges", token=discovery_token
    )
    privileges = response.get("privileges") or [] if isinstance(response, dict) else []
    items: list[dict[str, str]] = []
    for raw in privileges:
        if not isinstance(raw, str):
            continue
        access = "full"
        name = raw
        if raw.startswith("#"):
            access = "read-only"
            name = raw[1:].strip()
        elif raw.startswith("?"):
            access = "allowed"
            name = raw[1:].strip()
        items.append({"raw": raw, "name": name, "access": access})
    return items


def _probe_action_for_service(service_entry: dict[str, Any]) -> str | None:
    actions = service_entry.get("actions") or {}
    for action_name in ("list", "get"):
        action_def = actions.get(action_name)
        if isinstance(action_def, dict) and _has_non_parameterized_action_path(
            service_entry, action_name
        ):
            return action_name
    return None


def _service_supports_reversible_write_probe(service_entry: dict[str, Any]) -> bool:
    actions = service_entry.get("actions") or {}
    add_action = actions.get("add")
    delete_action = actions.get("delete")
    if not isinstance(add_action, dict) or not isinstance(delete_action, dict):
        return False
    if any("{" in str(path) for path in add_action.get("paths") or []):
        return False
    return _build_write_probe_payload("probe", "probe", add_action) is not None


def _has_non_parameterized_action_path(
    service_entry: dict[str, Any], action_name: str
) -> bool:
    actions = service_entry.get("actions") or {}
    action_def = actions.get(action_name) or {}
    for path in action_def.get("paths") or []:
        if "{" not in str(path):
            return True
    return False


def _probe_params(action_def: dict[str, Any]) -> dict[str, Any] | None:
    params = action_def.get("params") or []
    if not isinstance(params, list):
        return None
    chosen = {
        key: value for key, value in LIST_QUERY_DEFAULTS.items() if key in set(params)
    }
    return chosen or None


def _make_probe_name(module_name: str, service_name: str) -> str:
    normalized = f"{module_name}-{service_name}".replace("/", "-").replace("_", "-")
    return f"{_WRITE_PROBE_NAME_PREFIX}-{normalized}-{int(time.time() * 1000)}"


def _placeholder_collection(value: Any) -> bool:
    if isinstance(value, list):
        return not value or all(_is_placeholder_value(item) for item in value)
    if isinstance(value, dict):
        return not value or all(_is_placeholder_value(item) for item in value.values())
    return False


def _is_placeholder_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, dict)):
        return _placeholder_collection(value)
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return value == 0
    return False


def _field_type_index(action_def: dict[str, Any]) -> dict[str, str]:
    fields = action_def.get("body_fields") or []
    out: dict[str, str] = {}
    if not isinstance(fields, list):
        return out
    for field in fields:
        if not isinstance(field, dict):
            continue
        name = field.get("name")
        field_type = field.get("type")
        if isinstance(name, str) and isinstance(field_type, str):
            out[name] = field_type
    return out


def _synthetic_field_value(field_name: str, field_type: str, probe_name: str) -> Any:
    lowered_name = field_name.lower()
    lowered_type = field_type.lower()

    if field_name in {"name", "page_name", "description"}:
        return probe_name
    if "password" in lowered_name:
        return "Netloom123!"
    if "email" in lowered_name or "address" in lowered_name:
        return "netloom@example.com"
    if "server" in lowered_name or "host" in lowered_name:
        return "localhost"
    if lowered_name == "subject_cn":
        return f"{probe_name}.example.com"
    if lowered_name == "subject_c":
        return "SE"
    if lowered_name == "subject_san":
        return f"DNS:{probe_name}.example.com"
    if lowered_name == "type":
        return "RADIUS"
    if "connection_security" in lowered_name:
        return "none"
    if "timeout" in lowered_name:
        return 30
    if "port" in lowered_name:
        return 25
    if "country" in lowered_name:
        return "SE"

    if "bool" in lowered_type:
        return True
    if "int" in lowered_type:
        return 1
    if "array" in lowered_type:
        return [probe_name]
    if "string" in lowered_type:
        return probe_name
    return None


def _build_write_probe_payload(
    module_name: str, service_name: str, action_def: dict[str, Any]
) -> dict[str, Any] | None:
    body_example = action_def.get("body_example")
    if not isinstance(body_example, dict):
        return None
    payload = copy.deepcopy(body_example)
    payload.pop("id", None)
    probe_name = _make_probe_name(module_name, service_name)
    field_types = _field_type_index(action_def)

    for field_name in list(payload):
        field_type = field_types.get(field_name, "")
        value = payload[field_name]
        replacement = _synthetic_field_value(field_name, field_type, probe_name)

        if replacement is not None and (
            field_name in {"name", "page_name", "description"}
            or field_name in set(action_def.get("body_required") or [])
        ):
            payload[field_name] = replacement
            continue

        if field_name not in set(action_def.get("body_required") or []) and (
            _is_placeholder_value(value)
        ):
            payload.pop(field_name, None)

    for field_name in action_def.get("body_required") or []:
        value = payload.get(field_name)
        if not _is_placeholder_value(value):
            continue
        replacement = _synthetic_field_value(
            field_name, field_types.get(field_name, ""), probe_name
        )
        if replacement is None or _is_placeholder_value(replacement):
            return None
        payload[field_name] = replacement

    return payload


def _extract_action_args(
    payload: dict[str, Any],
    response_payload: dict[str, Any] | None,
    placeholders: list[str],
) -> dict[str, Any]:
    args: dict[str, Any] = {}
    sources = [response_payload or {}, payload]
    for placeholder in placeholders:
        variants = {
            placeholder,
            placeholder.replace("-", "_"),
            placeholder.replace("_", "-"),
        }
        for source in sources:
            for variant in variants:
                value = source.get(variant) if isinstance(source, dict) else None
                if value not in (None, ""):
                    args[placeholder] = value
                    break
            if placeholder in args:
                break
    return args


def _probe_write_actions(
    discovery_cp,
    discovery_token: str,
    catalog: dict[str, Any],
    module_name: str,
    service_name: str,
) -> dict[str, Any]:
    service_entry = ((catalog.get("modules") or {}).get(module_name) or {}).get(
        service_name
    )
    if not isinstance(service_entry, dict):
        return {"status": "missing-service"}
    if not _service_supports_reversible_write_probe(service_entry):
        return {"status": "unsupported"}

    add_action = discovery_cp.get_action_definition(
        catalog, module_name, service_name, "add"
    )
    payload = _build_write_probe_payload(module_name, service_name, add_action)
    if payload is None:
        return {"status": "unsupported"}

    actions_result: list[dict[str, Any]] = []
    created_args: dict[str, Any] = {"module": module_name, "service": service_name}
    cleanup_required = False
    add_payload: dict[str, Any] | None = None

    try:
        add_response = discovery_cp.request_action(
            catalog,
            "add",
            discovery_token,
            created_args,
            json_body=payload,
        )
        add_payload = add_response if isinstance(add_response, dict) else {}
        actions_result.append({"action": "add", "status": "ok"})
        cleanup_required = True

        for followup_action in ("get", "update", "replace", "delete"):
            action_def = (service_entry.get("actions") or {}).get(followup_action)
            if not isinstance(action_def, dict):
                continue
            _, _, placeholders = discovery_cp.resolve_action(
                catalog,
                module_name,
                service_name,
                followup_action,
                {
                    "module": module_name,
                    "service": service_name,
                    **_extract_action_args(
                        payload,
                        add_payload,
                        ["id", "page-name", "page_name", "name"],
                    ),
                },
            )
            action_args = {
                "module": module_name,
                "service": service_name,
                **_extract_action_args(payload, add_payload, placeholders),
            }
            if len(action_args) < len(placeholders) + 2:
                actions_result.append(
                    {
                        "action": followup_action,
                        "status": "skipped",
                        "detail": "missing-path-args",
                    }
                )
                continue

            if followup_action == "get":
                get_response = discovery_cp.request_action(
                    catalog, "get", discovery_token, action_args
                )
                if isinstance(get_response, dict):
                    add_payload = get_response
                actions_result.append({"action": "get", "status": "ok"})
                continue

            if followup_action in {"update", "replace"}:
                probe_payload = copy.deepcopy(
                    add_payload if isinstance(add_payload, dict) else payload
                )
                if isinstance(probe_payload.get("description"), str):
                    probe_payload["description"] = _make_probe_name(
                        module_name, f"{service_name}-{followup_action}"
                    )
                elif isinstance(probe_payload.get("name"), str):
                    probe_payload["name"] = _make_probe_name(
                        module_name, f"{service_name}-{followup_action}"
                    )
                discovery_cp.request_action(
                    catalog,
                    followup_action,
                    discovery_token,
                    action_args,
                    json_body=probe_payload,
                )
                actions_result.append({"action": followup_action, "status": "ok"})
                continue

            if followup_action == "delete":
                discovery_cp.request_action(
                    catalog, "delete", discovery_token, action_args
                )
                actions_result.append({"action": "delete", "status": "ok"})
                cleanup_required = False
                continue
    except ValueError as exc:
        return {"status": "skipped", "detail": str(exc), "actions": actions_result}
    except requests.HTTPError as exc:
        response = exc.response
        return {
            "status": "http-error",
            "http_status": response.status_code if response is not None else None,
            "detail": (response.text or "")[:1000] if response is not None else "",
            "actions": actions_result,
        }
    finally:
        if cleanup_required:
            try:
                _, _, placeholders = discovery_cp.resolve_action(
                    catalog,
                    module_name,
                    service_name,
                    "delete",
                    {
                        "module": module_name,
                        "service": service_name,
                        **_extract_action_args(
                            payload,
                            add_payload,
                            ["id", "page-name", "page_name", "name"],
                        ),
                    },
                )
                cleanup_args = {
                    "module": module_name,
                    "service": service_name,
                    **_extract_action_args(payload, add_payload, placeholders),
                }
                if len(cleanup_args) >= len(placeholders) + 2:
                    discovery_cp.request_action(
                        catalog, "delete", discovery_token, cleanup_args
                    )
            except Exception:
                pass

    return {"status": "ok", "actions": actions_result}


def _probe_service(
    discovery_cp,
    discovery_token: str,
    catalog: dict[str, Any],
    module_name: str,
    service_name: str,
    *,
    probe_writes: bool = False,
) -> dict[str, Any]:
    service_entry = ((catalog.get("modules") or {}).get(module_name) or {}).get(
        service_name
    )
    if not isinstance(service_entry, dict):
        result = {"status": "missing-service"}
        if probe_writes:
            result["write_probe"] = {"status": "missing-service"}
        return result

    action_name = _probe_action_for_service(service_entry)
    if action_name is None:
        result = {"status": "no-probe-action"}
        if probe_writes:
            result["write_probe"] = _probe_write_actions(
                discovery_cp, discovery_token, catalog, module_name, service_name
            )
        return result

    result: dict[str, Any]
    try:
        action_def = discovery_cp.get_action_definition(
            catalog, module_name, service_name, action_name
        )
        params = _probe_params(action_def)
        response = discovery_cp.request_action(
            catalog,
            action_name,
            discovery_token,
            {"module": module_name, "service": service_name},
            params=params,
        )
    except ValueError as exc:
        result = {"status": "skipped", "detail": str(exc), "action": action_name}
    except requests.HTTPError as exc:
        response = exc.response
        detail = ""
        if response is not None:
            detail = (response.text or "")[:1000]
        result = {
            "status": "http-error",
            "action": action_name,
            "http_status": response.status_code if response is not None else None,
            "detail": detail,
        }
    else:
        result = {
            "status": "ok",
            "action": action_name,
            "result_type": type(response).__name__,
        }
    if probe_writes:
        result["write_probe"] = _probe_write_actions(
            discovery_cp, discovery_token, catalog, module_name, service_name
        )
    return result


def _build_admin_catalog(admin_settings) -> dict[str, Any]:
    admin_cp = build_client(admin_settings, mask_secrets=False)
    admin_token = resolve_auth_token(admin_cp, admin_settings)
    cache = ApiEndpointCache(
        admin_cp,
        token=admin_token,
        settings=admin_settings,
    )
    catalog = cache.get_catalog(force_refresh=True)
    return project_catalog_view(catalog, catalog_view="full") or {"modules": {}}


def _iter_target_services(
    catalog: dict[str, Any],
    modules: tuple[str, ...],
    *,
    include_mapped: bool = False,
    explicit_services: set[tuple[str, str]] | None = None,
) -> list[tuple[str, str]]:
    rules = service_privilege_rule_index()
    services: list[tuple[str, str]] = []
    for module_name, module_services in sorted((catalog.get("modules") or {}).items()):
        if module_name not in modules or not isinstance(module_services, dict):
            continue
        for service_name, service_entry in sorted(module_services.items()):
            if not isinstance(service_entry, dict):
                continue
            if (
                explicit_services is not None
                and (module_name, service_name) not in explicit_services
            ):
                continue
            if not include_mapped and (module_name, service_name) in rules:
                continue
            if _probe_action_for_service(service_entry) is None:
                continue
            services.append((module_name, service_name))
    return services


def _default_out_path(raw: str | None) -> Path:
    if raw:
        return Path(raw)
    return Path(DEFAULT_OUT_FILE)


def _parse_service_list(raw: str | None) -> set[tuple[str, str]] | None:
    if not raw:
        return None
    out: set[tuple[str, str]] = set()
    for item in raw.split(","):
        value = item.strip()
        if not value or "/" not in value:
            continue
        module_name, service_name = value.split("/", 1)
        module_name = module_name.strip()
        service_name = service_name.strip()
        if module_name and service_name:
            out.add((module_name, service_name))
    return out or None


def _default_service_candidates(module_name: str, service_name: str) -> list[str]:
    return _candidate_keys(module_name, service_name)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Discover ClearPass operator-profile privilege mappings."
    )
    parser.add_argument("--admin-profile", default="admin")
    parser.add_argument("--discovery-profile", default="discovery")
    parser.add_argument(
        "--operator-profile-name", default="netloom-privileges-discovery-profile"
    )
    parser.add_argument(
        "--modules",
        default=",".join(DEFAULT_MODULES),
        help="Comma-separated module names to probe",
    )
    parser.add_argument(
        "--services",
        default=None,
        help="Comma-separated module/service targets to probe explicitly.",
    )
    parser.add_argument(
        "--include-mapped",
        action="store_true",
        help="Also probe services that already have verified mappings.",
    )
    parser.add_argument("--sleep-seconds", type=float, default=0.3)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument(
        "--out",
        default=None,
        help=f"Output JSON path (default: .\\{DEFAULT_OUT_FILE})",
    )
    parser.add_argument(
        "--candidate-file",
        default=None,
        help="JSON file with explicit candidate privilege keys per module/service.",
    )
    parser.add_argument(
        "--probe-writes",
        action="store_true",
        help=(
            "Also attempt reversible add/update/replace/delete probes when the "
            "service supports it."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    admin_settings = load_settings_for_profile(args.admin_profile)
    discovery_settings = load_settings_for_profile(args.discovery_profile)

    admin_cp = build_client(admin_settings, mask_secrets=False)
    admin_token = resolve_auth_token(admin_cp, admin_settings)
    discovery_cp = build_client(discovery_settings, mask_secrets=False)

    baseline_profile = _fetch_operator_profile(
        admin_cp, admin_token, args.operator_profile_name
    )
    baseline_privileges = list(baseline_profile.get("privileges") or [])
    candidate_overrides = _load_candidate_overrides(args.candidate_file)

    catalog = _build_admin_catalog(admin_settings)
    modules = tuple(
        module.strip() for module in args.modules.split(",") if module.strip()
    )
    explicit_services = _parse_service_list(args.services)
    target_services = _iter_target_services(
        catalog,
        modules,
        include_mapped=args.include_mapped,
        explicit_services=explicit_services,
    )
    if args.limit > 0:
        target_services = target_services[: args.limit]

    baseline_token = resolve_auth_token(discovery_cp, discovery_settings)
    baseline_effective = _effective_privileges(discovery_cp, baseline_token)

    baseline_access: dict[str, dict[str, Any]] = {}
    for module_name, service_name in target_services:
        baseline_access[f"{module_name}/{service_name}"] = _probe_service(
            discovery_cp,
            baseline_token,
            catalog,
            module_name,
            service_name,
            probe_writes=args.probe_writes,
        )

    results: list[dict[str, Any]] = []
    try:
        for index, (module_name, service_name) in enumerate(target_services, start=1):
            service_key = f"{module_name}/{service_name}"
            baseline_probe = baseline_access[service_key]
            override_candidates = candidate_overrides.get(service_key)
            wildcard_candidates = candidate_overrides.get(f"{module_name}/*")
            default_candidates = _default_service_candidates(module_name, service_name)
            if (
                isinstance(wildcard_candidates, list)
                and wildcard_candidates
                and all(isinstance(item, str) for item in wildcard_candidates)
            ):
                default_candidates = _merge_candidate_keys(
                    wildcard_candidates,
                    default_candidates,
                )
            candidate_specs = _normalize_candidate_specs(
                override_candidates,
                default_candidates,
            )
            service_result: dict[str, Any] = {
                "module": module_name,
                "service": service_name,
                "baseline_probe": baseline_probe,
                "candidate_specs": candidate_specs,
                "attempts": [],
                "verified": None,
            }

            for candidate_spec in candidate_specs:
                attempt: dict[str, Any] = {"candidate_keys": candidate_spec}
                try:
                    _update_operator_profile(
                        admin_cp,
                        admin_token,
                        baseline_profile,
                        baseline_privileges + candidate_spec,
                    )
                except requests.HTTPError as exc:
                    response = exc.response
                    attempt["update_status"] = (
                        response.status_code if response is not None else None
                    )
                    attempt["update_detail"] = (
                        (response.text or "")[:1000] if response is not None else ""
                    )
                    service_result["attempts"].append(attempt)
                    continue

                time.sleep(max(args.sleep_seconds, 0))
                discovery_token = resolve_auth_token(discovery_cp, discovery_settings)
                effective = _effective_privileges(discovery_cp, discovery_token)
                probe = _probe_service(
                    discovery_cp,
                    discovery_token,
                    catalog,
                    module_name,
                    service_name,
                    probe_writes=args.probe_writes,
                )
                attempt["update_status"] = 200
                attempt["effective_privileges"] = effective
                attempt["probe"] = probe
                service_result["attempts"].append(attempt)

                baseline_write = (baseline_probe.get("write_probe") or {}).get("status")
                candidate_write = (probe.get("write_probe") or {}).get("status")
                if baseline_probe.get("status") != "ok" and probe.get("status") == "ok":
                    service_result["verified"] = {
                        "privileges": candidate_spec,
                        "module": module_name,
                        "service": service_name,
                        "probe_action": probe.get("action"),
                    }
                    break
                if baseline_write != "ok" and candidate_write == "ok":
                    write_actions = (probe.get("write_probe") or {}).get(
                        "actions"
                    ) or []
                    first_ok = next(
                        (
                            item.get("action")
                            for item in write_actions
                            if isinstance(item, dict) and item.get("status") == "ok"
                        ),
                        "write",
                    )
                    service_result["verified"] = {
                        "privileges": candidate_spec,
                        "module": module_name,
                        "service": service_name,
                        "probe_action": first_ok,
                    }
                    break

            results.append(service_result)
            verified = service_result["verified"]
            verified_text = (
                "+".join(verified["privileges"]) if verified else "no verified mapping"
            )
            print(f"[{index}/{len(target_services)}] {service_key} -> {verified_text}")
    finally:
        _update_operator_profile(
            admin_cp, admin_token, baseline_profile, baseline_privileges
        )

    output = {
        "operator_profile_name": args.operator_profile_name,
        "modules": modules,
        "services": sorted(
            f"{module}/{service}" for module, service in (explicit_services or set())
        ),
        "baseline_privileges": baseline_privileges,
        "baseline_effective_privileges": baseline_effective,
        "include_mapped": args.include_mapped,
        "candidate_file": args.candidate_file,
        "probe_writes": args.probe_writes,
        "results": results,
    }
    out_path = _default_out_path(args.out)
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Wrote report to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
