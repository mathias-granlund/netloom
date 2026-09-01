from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from netloom.contracts import PluginDefinition
from netloom.core.config import Settings, plugins_config_dir
from netloom.core.interactive_cache import (
    load_cached_interactive_catalog,
    supports_interactive_catalog,
)


def _load_clearpass_plugin() -> PluginDefinition:
    from netloom.plugins.clearpass.plugin import PLUGIN

    return PLUGIN


_RUNTIME_PLUGIN_LOADERS: dict[str, Callable[[], PluginDefinition]] = {
    "clearpass": _load_clearpass_plugin
}


def _normalize_plugin_name(name: str | None) -> str | None:
    if name is None:
        return None
    normalized = name.strip().lower().replace("-", "_")
    return normalized or None


def list_runtime_plugins() -> list[str]:
    return sorted(_RUNTIME_PLUGIN_LOADERS.keys())


def list_configured_plugins() -> list[str]:
    plugins_dir = plugins_config_dir()
    try:
        entries = plugins_dir.iterdir()
    except FileNotFoundError:
        return []

    configured: list[str] = []
    for entry in entries:
        if not entry.is_dir():
            continue
        configured.append(entry.name)
    return sorted(configured)


def list_plugins() -> list[str]:
    return sorted(set(list_runtime_plugins()) | set(list_configured_plugins()))


def has_runtime_plugin(name: str) -> bool:
    return _normalize_plugin_name(name) in _RUNTIME_PLUGIN_LOADERS


def load_cached_catalog_for_plugin(
    name: str | None,
    *,
    settings: Settings | None = None,
    catalog_view: str = "visible",
    prefer_index: bool = False,
) -> dict[str, Any] | None:
    return load_cached_interactive_catalog(
        name,
        settings=settings,
        catalog_view=catalog_view,
        prefer_index=prefer_index,
    )


def supports_lightweight_cached_catalog(name: str | None) -> bool:
    return supports_interactive_catalog(name)


def get_plugin(
    name: str | None, *, settings: Settings | None = None
) -> PluginDefinition:
    plugin_name = _normalize_plugin_name(
        name or (settings.plugin if settings else None)
    )
    if plugin_name is None:
        raise ValueError(
            "No active plugin selected. Use `netloom load <plugin>` before "
            "running plugin-backed commands."
        )
    try:
        return _RUNTIME_PLUGIN_LOADERS[plugin_name]()
    except KeyError as exc:
        if plugin_name in list_configured_plugins():
            raise ValueError(
                f"Plugin '{plugin_name}' has config files under "
                f"{Path(plugins_config_dir()) / plugin_name}, but no runtime "
                "implementation is installed."
            ) from exc
        available = ", ".join(list_plugins())
        raise ValueError(
            f"Unknown plugin '{plugin_name}'. Available plugins: {available}"
        ) from exc
