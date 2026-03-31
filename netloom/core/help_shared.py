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


def combined_catalog_modules(api_catalog: dict | None) -> dict[str, dict]:
    modules = (api_catalog or {}).get("modules") or {}
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


def combined_services_for_module(
    api_catalog: dict | None, module: str
) -> dict[str, dict]:
    modules = combined_catalog_modules(api_catalog)
    services = modules.get(module)
    return services if isinstance(services, dict) else {}


def service_is_hidden_alias(
    service_name: str, service_entry: dict, services: dict[str, dict]
) -> bool:
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

    if len(set(summary_candidates)) == 1:
        return True
    return len(set(suffix_candidates)) == 1


def display_services_for_module(
    api_catalog: dict | None, module: str
) -> dict[str, dict]:
    combined = combined_services_for_module(api_catalog, module)
    return {
        service_name: service_entry
        for service_name, service_entry in combined.items()
        if not service_is_hidden_alias(service_name, service_entry, combined)
    }


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
    services = combined_services_for_module(api_catalog, module)
    entry = services.get(service)
    if not isinstance(entry, dict):
        return None

    merged = dict(entry)
    for alias_name, alias_entry in services.items():
        if alias_name == service or not isinstance(alias_entry, dict):
            continue
        if service_is_hidden_alias(alias_name, alias_entry, services):
            summary = service_display_summary(alias_entry)
            target_summary = service_display_summary(entry)
            if service.endswith(f"-{alias_name}") or (
                summary and target_summary and summary == target_summary
            ):
                merged = merge_service_entries(merged, alias_entry)

    return merged


__all__ = [
    "BUILTIN_MODULES",
    "CLI_ACTION_ORDER",
    "combined_catalog_modules",
    "combined_services_for_module",
    "display_services_for_module",
    "NETLOOM_BANNER",
    "PLUGIN_SELECTION_HINT",
    "merge_service_entries",
    "resolve_service_entry",
    "service_display_summary",
    "service_cli_actions",
    "service_is_hidden_alias",
]
