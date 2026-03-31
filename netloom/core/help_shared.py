from __future__ import annotations

import re

CLI_ACTION_ORDER = [
    "list",
    "get",
    "add",
    "update",
    "replace",
    "delete",
    "diff",
    "copy",
]

NETLOOM_BANNER = r"""
 _   _      _   _
| \ | | ___| |_| | ___   ___  _ __ ___
|  \| |/ _ \ __| |/ _ \ / _ \| '_ ` _ \
| |\  |  __/ |_| | (_) | (_) | | | | | |
|_| \_|\___|\__|_|\___/ \___/|_| |_| |_|
""".strip("\n")

PLUGIN_SELECTION_HINT = "<select a plugin with `netloom load <plugin>`>"
BUILTIN_MODULES = ["cache", "load", "server"]
_LIST_SUMMARY_RE = re.compile(r"^Get a list of (?P<target>.+)$")


def service_cli_actions(service_entry: dict) -> list[str]:
    actions = service_entry.get("actions") or {}
    if not actions:
        return []
    cli_actions: list[str] = []
    if "list" in actions:
        cli_actions.append("list")
    if "get" in actions:
        cli_actions.append("get")
    for action in CLI_ACTION_ORDER[2:]:
        if action in {"copy", "diff"}:
            cli_actions.append(action)
        elif action in actions:
            cli_actions.append(action)
    return cli_actions


def service_display_summary(service_entry: dict) -> str | None:
    summary = service_entry.get("summary")
    if isinstance(summary, str) and summary.strip():
        return summary.strip()

    actions = service_entry.get("actions") or {}
    list_summary = (actions.get("list") or {}).get("summary")
    if isinstance(list_summary, str) and list_summary.strip():
        match = _LIST_SUMMARY_RE.match(list_summary.strip())
        if match:
            return f"Manage {match.group('target')}"

    for action_name in ("get", "add", "update", "replace", "delete", "list"):
        action_summary = (actions.get(action_name) or {}).get("summary")
        if isinstance(action_summary, str) and action_summary.strip():
            return action_summary.strip()
    return None


def visible_catalog_modules(api_catalog: dict | None) -> dict[str, dict]:
    modules = (api_catalog or {}).get("modules") or {}
    return dict(modules) if isinstance(modules, dict) else {}


def combined_catalog_modules(api_catalog: dict | None) -> dict[str, dict]:
    modules = visible_catalog_modules(api_catalog)
    full_modules = (api_catalog or {}).get("full_modules") or {}
    if not isinstance(full_modules, dict):
        return dict(modules)

    combined: dict[str, dict] = {}
    module_names = set(full_modules) | set(modules)
    for module_name in module_names:
        full_services = full_modules.get(module_name)
        visible_services = modules.get(module_name)
        if isinstance(full_services, dict) or isinstance(visible_services, dict):
            combined[module_name] = {}
            if isinstance(full_services, dict):
                combined[module_name].update(full_services)
            if isinstance(visible_services, dict):
                combined[module_name].update(visible_services)
    return combined


def visible_services_for_module(
    api_catalog: dict | None, module: str
) -> dict[str, dict]:
    modules = visible_catalog_modules(api_catalog)
    services = modules.get(module)
    return services if isinstance(services, dict) else {}


def combined_services_for_module(
    api_catalog: dict | None, module: str
) -> dict[str, dict]:
    modules = combined_catalog_modules(api_catalog)
    services = modules.get(module)
    return services if isinstance(services, dict) else {}


def _alias_candidates(
    service_name: str, service_entry: dict, services: dict[str, dict]
) -> tuple[list[str], list[str]]:
    suffix_candidates: list[str] = []
    summary_candidates: list[str] = []
    service_summary = service_display_summary(service_entry)

    for canonical_name, canonical_entry in services.items():
        if canonical_name == service_name:
            continue
        if len(canonical_name) <= len(service_name):
            continue
        if canonical_name.endswith(f"-{service_name}"):
            suffix_candidates.append(canonical_name)
        canonical_summary = service_display_summary(canonical_entry)
        if (
            service_summary
            and canonical_summary
            and canonical_summary == service_summary
        ):
            summary_candidates.append(canonical_name)

    return suffix_candidates, summary_candidates


def preferred_service_name(
    service_name: str, service_entry: dict, services: dict[str, dict]
) -> str:
    suffix_candidates, summary_candidates = _alias_candidates(
        service_name, service_entry, services
    )
    if len(set(summary_candidates)) == 1:
        return summary_candidates[0]
    if len(set(suffix_candidates)) == 1:
        return suffix_candidates[0]
    return service_name


def service_is_hidden_alias(
    service_name: str, service_entry: dict, services: dict[str, dict]
) -> bool:
    return preferred_service_name(service_name, service_entry, services) != service_name


def display_services_for_module(
    api_catalog: dict | None, module: str
) -> dict[str, dict]:
    visible = visible_services_for_module(api_catalog, module)
    combined = combined_services_for_module(api_catalog, module)
    display: dict[str, dict] = {}

    for service_name, service_entry in visible.items():
        if not isinstance(service_entry, dict):
            continue
        display_name = preferred_service_name(service_name, service_entry, combined)
        base_entry = combined.get(display_name)
        if not isinstance(base_entry, dict):
            base_entry = service_entry
        merged = merge_service_entries(base_entry, service_entry)
        existing = display.get(display_name)
        if isinstance(existing, dict):
            merged = merge_service_entries(existing, merged)
        display[display_name] = merged

    return display


def merge_service_entries(base: dict, extra: dict) -> dict:
    merged = dict(base)
    merged_actions = dict(base.get("actions") or {})
    for action_name, action_def in (extra.get("actions") or {}).items():
        merged_actions.setdefault(action_name, action_def)
    merged["actions"] = merged_actions

    for key, value in extra.items():
        if key == "actions":
            continue
        merged.setdefault(key, value)

    return merged


def resolve_service_entry(
    api_catalog: dict | None, module: str, service: str
) -> dict | None:
    displayed = display_services_for_module(api_catalog, module)
    entry = displayed.get(service)
    if isinstance(entry, dict):
        return entry

    visible = visible_services_for_module(api_catalog, module)
    raw_entry = visible.get(service)
    if isinstance(raw_entry, dict):
        preferred = preferred_service_name(
            service, raw_entry, combined_services_for_module(api_catalog, module)
        )
        if preferred != service and isinstance(displayed.get(preferred), dict):
            return displayed[preferred]
        return raw_entry

    combined = combined_services_for_module(api_catalog, module)
    for visible_name, visible_entry in visible.items():
        if not isinstance(visible_entry, dict):
            continue
        if preferred_service_name(visible_name, visible_entry, combined) == service:
            candidate = displayed.get(service)
            if isinstance(candidate, dict):
                return candidate
    return None


__all__ = [
    "BUILTIN_MODULES",
    "CLI_ACTION_ORDER",
    "combined_catalog_modules",
    "combined_services_for_module",
    "display_services_for_module",
    "NETLOOM_BANNER",
    "PLUGIN_SELECTION_HINT",
    "merge_service_entries",
    "preferred_service_name",
    "resolve_service_entry",
    "service_display_summary",
    "service_cli_actions",
    "service_is_hidden_alias",
    "visible_catalog_modules",
    "visible_services_for_module",
]
