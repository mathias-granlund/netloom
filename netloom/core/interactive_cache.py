from __future__ import annotations

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
    if normalized_view == CATALOG_VIEW_FULL:
        full_modules = catalog.get("full_modules")
        if isinstance(full_modules, dict):
            import copy

            projected["modules"] = copy.deepcopy(full_modules)
    projected["catalog_view"] = normalized_view
    return projected


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
