from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from netloom.core.config import Settings, plugins_config_dir


@dataclass(frozen=True)
class PluginDefinition:
    name: str
    display_name: str
    build_client: Callable[..., Any]
    resolve_auth_token: Callable[..., str]
    get_api_catalog: Callable[..., dict[str, Any]]
    load_cached_catalog: Callable[..., dict[str, Any] | None]
    clear_api_cache: Callable[..., bool]
    normalize_copy_payload: Callable[..., dict[str, Any]]
    restore_secret_fields: Callable[..., Any]
    preflight_error_for_payload: Callable[..., str | None]
    help_context: Callable[[], dict[str, Any]] | None = None


def _registry() -> dict[str, PluginDefinition]:
    from netloom.plugins.clearpass.plugin import PLUGIN

    return {PLUGIN.name: PLUGIN}


def list_runtime_plugins() -> list[str]:
    return sorted(_registry().keys())


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
    return name in _registry()


def get_plugin(
    name: str | None, *, settings: Settings | None = None
) -> PluginDefinition:
    plugin_name = name or (settings.plugin if settings else None)
    if plugin_name is None:
        raise ValueError(
            "No active plugin selected. Use `netloom load <plugin>` before "
            "running plugin-backed commands."
        )
    try:
        return _registry()[plugin_name]
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
