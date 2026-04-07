from __future__ import annotations

from typing import TYPE_CHECKING, Any

from netloom.cli import deps as cli_deps
from netloom.cli.telemetry import CliProfiler

if TYPE_CHECKING:
    from netloom.core.config import Settings

_COMPACT_HELP_ACTIONS = {
    "copy",
    "diff",
    "list",
    "get",
    "add",
    "update",
    "replace",
    "delete",
}

_HELP_PLUGIN_MARKER = object()


def _needs_full_settings(settings) -> bool:
    return settings is None or not hasattr(settings, "server")


def catalog_view_from_args(args: dict | None) -> str:
    value = (args or {}).get("catalog_view")
    if isinstance(value, str) and value.strip().lower() == "full":
        return "full"
    return "visible"


def catalog_view_from_completion_words(words: list[str]) -> str:
    for word in words:
        if not isinstance(word, str):
            continue
        if word.startswith("--catalog-view="):
            if word.split("=", 1)[1].strip().lower() == "full":
                return "full"
            break
    return "visible"


def completion_needs_catalog(words: list[str]) -> bool:
    positionals = [word for word in words if not word.startswith("-")]
    if not positionals:
        return True

    module = positionals[0]
    return module not in {"cache", "load", "server"}


def load_catalog_for_cli(
    plugin,
    *,
    settings: Settings | None,
    catalog_view: str,
    prefer_index: bool = False,
) -> dict | None:
    if prefer_index:
        loader = getattr(plugin, "load_cached_index", None)
        if callable(loader):
            try:
                catalog = loader(settings=settings, catalog_view=catalog_view)
            except TypeError as exc:
                if "catalog_view" not in str(exc):
                    raise
                catalog = loader(settings=settings)
            if catalog is not None:
                return catalog
    try:
        return plugin.load_cached_catalog(settings=settings, catalog_view=catalog_view)
    except TypeError as exc:
        if "catalog_view" not in str(exc):
            raise
        return plugin.load_cached_catalog(settings=settings)


def catalog_has_action(
    catalog: dict | None, module: str | None, service: str | None, action: str | None
) -> bool:
    if not all((isinstance(catalog, dict), module, service, action)):
        return False
    modules = catalog.get("modules") or {}
    service_entry = (modules.get(module) or {}).get(service)
    if not isinstance(service_entry, dict):
        return False
    actions = service_entry.get("actions") or {}
    return action in actions


def help_prefers_index(args: dict | None) -> bool:
    if not args:
        return True
    action = args.get("action")
    if not action:
        return True
    return action in _COMPACT_HELP_ACTIONS


def help_needs_catalog(args: dict | None) -> bool:
    module = (args or {}).get("module")
    return module not in {"cache", "load", "server"}


def get_catalog_for_cli(
    plugin,
    cp,
    *,
    token: str,
    settings: Settings | None,
    force_refresh: bool = False,
    catalog_view: str,
    timing_sink=None,
    progress_sink=None,
) -> dict:
    kwargs = {
        "token": token,
        "force_refresh": force_refresh,
        "settings": settings,
        "catalog_view": catalog_view,
    }
    if timing_sink is not None:
        kwargs["timing_sink"] = timing_sink
    if progress_sink is not None:
        kwargs["progress_sink"] = progress_sink

    while True:
        try:
            return plugin.get_api_catalog(cp, **kwargs)
        except TypeError as exc:
            message = str(exc)
            if "progress_sink" in message and "progress_sink" in kwargs:
                kwargs.pop("progress_sink", None)
                continue
            if "timing_sink" in message and "timing_sink" in kwargs:
                kwargs.pop("timing_sink", None)
                continue
            if "catalog_view" in message and "catalog_view" in kwargs:
                kwargs.pop("catalog_view", None)
                continue
            raise


def print_help(
    args: dict | None = None,
    *,
    plugin=None,
    settings: Settings | None = None,
    deps: Any = cli_deps,
) -> None:
    effective_settings = settings
    if effective_settings is None and deps._env_cli_timing_value() is None:
        try:
            effective_settings = deps.load_interactive_settings()
        except Exception:
            effective_settings = None
    profiler = CliProfiler(
        "help",
        settings=effective_settings,
        env_value=deps._env_cli_timing_value(),
    )
    selected_plugin = plugin
    selected_args = args or {}
    catalog_view = catalog_view_from_args(selected_args)
    catalog = None
    needs_catalog = help_needs_catalog(selected_args)
    prefer_index = help_prefers_index(selected_args)
    active_settings = effective_settings
    plugin_name = getattr(active_settings, "plugin", None) if active_settings else None
    if needs_catalog and selected_plugin is None:
        profiler.call("import_interactive_layer", deps._import_interactive_layer)
        profiler.call("import_cache_layer", deps._import_cache_layer)
        active_settings = active_settings or profiler.call(
            "load_interactive_settings", deps.load_interactive_settings
        )
        plugin_name = getattr(active_settings, "plugin", None)
        catalog = profiler.call(
            "load_core_cached_catalog",
            deps.load_cached_catalog_for_plugin,
            plugin_name,
            settings=active_settings,
            catalog_view=catalog_view,
            prefer_index=prefer_index,
        )
        effective_settings = active_settings
    if needs_catalog and selected_plugin is None and catalog is None:
        profiler.call("import_plugin_layer", deps._import_plugin_layer)
        if _needs_full_settings(effective_settings):
            effective_settings = profiler.call("load_settings", deps.load_settings)
        try:
            selected_plugin = profiler.call(
                "plugin_fallback_get_plugin",
                deps.get_plugin,
                None,
                settings=effective_settings,
            )
        except ValueError:
            selected_plugin = None
    render_plugin = selected_plugin
    if render_plugin is None and plugin_name:
        render_plugin = _HELP_PLUGIN_MARKER
    if selected_plugin is not None and catalog is None:
        if plugin_name is None:
            plugin_name = getattr(selected_plugin, "name", None)
        if plugin_name:
            catalog = profiler.call(
                "load_core_cached_catalog",
                deps.load_cached_catalog_for_plugin,
                plugin_name,
                settings=effective_settings,
                catalog_view=catalog_view,
                prefer_index=prefer_index,
            )
    if selected_plugin is not None and catalog is None:
        catalog = profiler.call(
            "plugin_fallback_cached_catalog",
            load_catalog_for_cli,
            selected_plugin,
            settings=effective_settings,
            catalog_view=catalog_view,
            prefer_index=prefer_index,
        )
        action = selected_args.get("action")
        if (
            action
            and action not in _COMPACT_HELP_ACTIONS
            and catalog_has_action(
                catalog,
                selected_args.get("module"),
                selected_args.get("service"),
                action,
            )
        ):
            catalog = profiler.call(
                "load_cached_catalog",
                load_catalog_for_cli,
                selected_plugin,
                settings=effective_settings,
                catalog_view=catalog_view,
                prefer_index=False,
            )
    profiler.call("import_help_layer", deps._import_help_layer)
    text = profiler.call(
        "render_help",
        deps.render_help,
        catalog,
        selected_args,
        version=deps.get_version(),
        plugin=render_plugin,
    )
    print(text)
    profiler.emit()


def complete(
    words: list[str],
    settings: Settings | None = None,
    *,
    deps: Any = cli_deps,
) -> None:
    effective_settings = settings
    if effective_settings is None and deps._env_completion_timing_value() is None:
        try:
            effective_settings = deps.load_interactive_settings()
        except Exception:
            effective_settings = None
    profiler = CliProfiler(
        "complete",
        settings=effective_settings,
        env_value=deps._env_completion_timing_value(),
        allow_settings_fallback=False,
    )
    catalog = None
    if completion_needs_catalog(words):
        profiler.call("import_interactive_layer", deps._import_interactive_layer)
        profiler.call("import_cache_layer", deps._import_cache_layer)
        active_settings = effective_settings or profiler.call(
            "load_interactive_settings", deps.load_interactive_settings
        )
        plugin_name = getattr(active_settings, "plugin", None)
        catalog_view = catalog_view_from_completion_words(words)
        catalog = profiler.call(
            "load_core_cached_catalog",
            deps.load_cached_catalog_for_plugin,
            plugin_name,
            settings=active_settings,
            catalog_view=catalog_view,
            prefer_index=True,
        )
        if catalog is None:
            profiler.call("import_plugin_layer", deps._import_plugin_layer)
            if _needs_full_settings(active_settings):
                active_settings = profiler.call("load_settings", deps.load_settings)
            try:
                plugin = profiler.call(
                    "plugin_fallback_get_plugin",
                    deps.get_plugin,
                    None,
                    settings=active_settings,
                )
            except ValueError:
                plugin = None
            catalog = (
                profiler.call(
                    "plugin_fallback_cached_catalog",
                    load_catalog_for_cli,
                    plugin,
                    settings=active_settings,
                    catalog_view=catalog_view,
                    prefer_index=True,
                )
                if plugin is not None
                else None
            )
    profiler.call("import_completion_layer", deps._import_completion_layer)
    profiler.call("print_completions", deps.print_completions, words, catalog)
    profiler.emit()


def describe(
    words: list[str],
    settings: Settings | None = None,
    *,
    deps: Any = cli_deps,
) -> None:
    effective_settings = settings
    if effective_settings is None and deps._env_completion_timing_value() is None:
        try:
            effective_settings = deps.load_interactive_settings()
        except Exception:
            effective_settings = None
    profiler = CliProfiler(
        "describe",
        settings=effective_settings,
        env_value=deps._env_completion_timing_value(),
        allow_settings_fallback=False,
    )
    catalog = None
    if completion_needs_catalog(words):
        profiler.call("import_interactive_layer", deps._import_interactive_layer)
        profiler.call("import_cache_layer", deps._import_cache_layer)
        active_settings = effective_settings or profiler.call(
            "load_interactive_settings", deps.load_interactive_settings
        )
        plugin_name = getattr(active_settings, "plugin", None)
        catalog_view = catalog_view_from_completion_words(words)
        catalog = profiler.call(
            "load_core_cached_catalog",
            deps.load_cached_catalog_for_plugin,
            plugin_name,
            settings=active_settings,
            catalog_view=catalog_view,
            prefer_index=True,
        )
        if catalog is None:
            profiler.call("import_plugin_layer", deps._import_plugin_layer)
            if _needs_full_settings(active_settings):
                active_settings = profiler.call("load_settings", deps.load_settings)
            try:
                plugin = profiler.call(
                    "plugin_fallback_get_plugin",
                    deps.get_plugin,
                    None,
                    settings=active_settings,
                )
            except ValueError:
                plugin = None
            catalog = (
                profiler.call(
                    "plugin_fallback_cached_catalog",
                    load_catalog_for_cli,
                    plugin,
                    settings=active_settings,
                    catalog_view=catalog_view,
                    prefer_index=True,
                )
                if plugin is not None
                else None
            )
    profiler.call("import_help_layer", deps._import_help_layer)
    text = profiler.call("describe_context", deps.describe_context, words, catalog)
    if text:
        print(text)
    profiler.emit()
