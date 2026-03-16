from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from netloom.core.config import Settings


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


def _registry() -> dict[str, PluginDefinition]:
    from netloom.plugins.clearpass.plugin import PLUGIN

    return {PLUGIN.name: PLUGIN}


def list_plugins() -> list[str]:
    return sorted(_registry().keys())


def get_plugin(
    name: str | None, *, settings: Settings | None = None
) -> PluginDefinition:
    plugin_name = name or (settings.plugin if settings else None) or "clearpass"
    try:
        return _registry()[plugin_name]
    except KeyError as exc:
        available = ", ".join(list_plugins())
        raise ValueError(
            f"Unknown plugin '{plugin_name}'. Available plugins: {available}"
        ) from exc
