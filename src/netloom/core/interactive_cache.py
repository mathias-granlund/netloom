from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

CATALOG_VIEW_VISIBLE = "visible"
CATALOG_VIEW_FULL = "full"

_INTERACTIVE_CATALOG_SPECS = {
    "clearpass": {
        "cache_filename": "api_endpoints_cache.json",
        "index_filename": "api_endpoints_index.json",
        "catalog_versions": (2, 3, 4, 5),
        "index_version": 1,
    }
}


def _normalize_plugin_name(name: str | None) -> str | None:
    if name is None:
        return None
    normalized = name.strip().lower().replace("-", "_")
    return normalized or None


def supports_interactive_catalog(plugin_name: str | None) -> bool:
    normalized = _normalize_plugin_name(plugin_name)
    return normalized in _INTERACTIVE_CATALOG_SPECS


def _catalog_spec(plugin_name: str | None) -> dict[str, Any] | None:
    normalized = _normalize_plugin_name(plugin_name)
    if normalized is None:
        return None
    return _INTERACTIVE_CATALOG_SPECS.get(normalized)


def normalize_catalog_view(value: str | None) -> str:
    if isinstance(value, str) and value.strip().lower() == CATALOG_VIEW_FULL:
        return CATALOG_VIEW_FULL
    return CATALOG_VIEW_VISIBLE


def project_catalog_view(
    catalog: dict[str, Any] | None, *, catalog_view: str = CATALOG_VIEW_VISIBLE
) -> dict[str, Any] | None:
    if not isinstance(catalog, dict):
        return None

    normalized_view = normalize_catalog_view(catalog_view)
    projected = dict(catalog)
    full_modules = catalog.get("full_modules")
    if normalized_view == CATALOG_VIEW_FULL:
        if isinstance(full_modules, dict):
            projected["modules"] = copy.deepcopy(full_modules)
    elif isinstance(full_modules, dict):
        refreshed = _reproject_visible_modules(catalog)
        if refreshed is not None:
            projected["modules"] = refreshed
    projected["catalog_view"] = normalized_view
    return projected


def _best_access_level(levels: list[str]) -> str | None:
    rank = {"allowed": 1, "read-only": 2, "full": 3}
    normalized = [level for level in levels if level in rank]
    if not normalized:
        return None
    return max(normalized, key=lambda value: rank[value])


def _lowest_access_level(levels: list[str]) -> str | None:
    rank = {"allowed": 1, "read-only": 2, "full": 3}
    normalized = [level for level in levels if level in rank]
    if not normalized:
        return None
    return min(normalized, key=lambda value: rank[value])


def _filter_actions_for_access(
    actions: dict[str, Any], access_level: str
) -> dict[str, Any]:
    if access_level == "full":
        return dict(actions)
    allowed_actions = {"list", "get"}
    return {
        action_name: action_def
        for action_name, action_def in actions.items()
        if action_name in allowed_actions
    }


def _service_visible_by_default(
    module_name: str, service_name: str, service_entry: dict[str, Any]
) -> bool:
    visibility = service_entry.get("catalog_visibility")
    if visibility in {
        "privilege_gated_verified",
        "baseline_verified",
        "verified",
        "baseline",
    }:
        return True
    required = service_entry.get("required_privileges") or []
    if isinstance(required, list) and required:
        return True
    return (module_name, service_name) in {
        ("apioperations", "oauth"),
        ("apioperations", "oauth-me"),
        ("apioperations", "oauth-privileges"),
    }


def _effective_access_map(effective_privileges: list[dict[str, str]]) -> dict[str, str]:
    effective_access: dict[str, str] = {}
    for item in effective_privileges:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        access = item.get("access")
        if not isinstance(name, str) or not isinstance(access, str):
            continue
        current = effective_access.get(name)
        best = _best_access_level([access, current] if current else [access])
        if best is not None:
            effective_access[name] = best
    return effective_access


def _reproject_visible_modules(catalog: dict[str, Any]) -> dict[str, Any] | None:
    full_modules = catalog.get("full_modules")
    filter_metadata = catalog.get("filter_metadata")
    if not isinstance(full_modules, dict) or not isinstance(filter_metadata, dict):
        return None

    from netloom.plugins.clearpass.privileges import service_privilege_rule_index

    rules = service_privilege_rule_index()
    effective_access = _effective_access_map(
        filter_metadata.get("effective_privileges") or []
    )

    visible_modules: dict[str, dict[str, Any]] = {}
    for module_name, services in full_modules.items():
        if not isinstance(services, dict):
            continue
        next_services: dict[str, Any] = {}
        for service_name, service_entry in services.items():
            if not isinstance(service_entry, dict):
                continue
            next_entry: dict[str, Any] | None = None
            rule = rules.get((module_name, service_name))

            if rule is None:
                if _service_visible_by_default(
                    module_name, service_name, service_entry
                ):
                    next_entry = copy.deepcopy(service_entry)
                    next_entry.setdefault("catalog_visibility", "baseline")
            elif (
                getattr(rule, "source", "privilege_gated_verified")
                == "baseline_verified"
            ):
                next_entry = copy.deepcopy(service_entry)
                next_entry["catalog_visibility"] = "baseline_verified"
                next_entry["granted_access"] = "full"
            else:
                if getattr(rule, "match", "any") == "all":
                    if not all(name in effective_access for name in rule.privileges):
                        continue
                    matched_levels = [
                        effective_access[name] for name in rule.privileges
                    ]
                    access_level = _lowest_access_level(matched_levels)
                else:
                    matched_levels = [
                        effective_access[name]
                        for name in rule.privileges
                        if name in effective_access
                    ]
                    access_level = _best_access_level(matched_levels)
                if access_level is None:
                    continue
                actions = service_entry.get("actions") or {}
                filtered_actions = _filter_actions_for_access(actions, access_level)
                if not filtered_actions:
                    continue
                next_entry = copy.deepcopy(service_entry)
                next_entry["actions"] = filtered_actions
                next_entry["required_privileges"] = list(rule.privileges)
                next_entry["privilege_match"] = getattr(rule, "match", "any")
                next_entry["granted_access"] = access_level
                next_entry["catalog_visibility"] = "privilege_gated_verified"

            if next_entry is not None and _service_visible_by_default(
                module_name, service_name, next_entry
            ):
                next_services[service_name] = next_entry
        if next_services:
            visible_modules[module_name] = next_services

    return visible_modules


def _read_json_dict(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _valid_catalog(
    data: dict[str, Any] | None, spec: dict[str, Any]
) -> dict[str, Any] | None:
    if (
        isinstance(data, dict)
        and data.get("version") in spec["catalog_versions"]
        and isinstance(data.get("modules"), dict)
    ):
        return data
    return None


def _valid_index(
    data: dict[str, Any] | None, spec: dict[str, Any]
) -> dict[str, Any] | None:
    if (
        isinstance(data, dict)
        and data.get("index_version") == spec["index_version"]
        and data.get("version") in spec["catalog_versions"]
        and isinstance(data.get("modules"), dict)
    ):
        return data
    return None


def _cache_file_path(spec: dict[str, Any], settings) -> Path:
    return settings.paths.cache_dir / spec["cache_filename"]


def _index_file_path(spec: dict[str, Any], settings) -> Path:
    return settings.paths.cache_dir / spec["index_filename"]


def load_cached_interactive_catalog(
    plugin_name: str | None,
    *,
    settings=None,
    catalog_view: str = CATALOG_VIEW_VISIBLE,
    prefer_index: bool = False,
) -> dict[str, Any] | None:
    spec = _catalog_spec(plugin_name)
    if spec is None:
        return None

    normalized_view = normalize_catalog_view(catalog_view)
    active_settings = settings
    if active_settings is None:
        from netloom.core.interactive import load_interactive_settings

        active_settings = load_interactive_settings()

    if prefer_index:
        index = _valid_index(
            _read_json_dict(_index_file_path(spec, active_settings)),
            spec,
        )
        if index is not None:
            if (
                normalized_view == CATALOG_VIEW_VISIBLE
                and isinstance(index.get("full_modules"), dict)
                and not isinstance(index.get("filter_metadata"), dict)
            ):
                catalog = _valid_catalog(
                    _read_json_dict(_cache_file_path(spec, active_settings)),
                    spec,
                )
                if catalog is not None:
                    return project_catalog_view(catalog, catalog_view=catalog_view)
            return project_catalog_view(index, catalog_view=catalog_view)

    catalog = _valid_catalog(
        _read_json_dict(_cache_file_path(spec, active_settings)),
        spec,
    )
    if catalog is not None:
        return project_catalog_view(catalog, catalog_view=catalog_view)

    return None


__all__ = [
    "CATALOG_VIEW_FULL",
    "CATALOG_VIEW_VISIBLE",
    "load_cached_interactive_catalog",
    "normalize_catalog_view",
    "project_catalog_view",
    "supports_interactive_catalog",
]
