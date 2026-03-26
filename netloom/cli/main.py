from __future__ import annotations

import importlib
import os
import sys
import time
from dataclasses import is_dataclass, replace
from typing import TYPE_CHECKING

from netloom import get_version
from netloom.cli.parser import CliParseError, parse_cli

if TYPE_CHECKING:
    from netloom.core.config import Settings

_CLI_TIMING_ENV = "NETLOOM_CLI_TIMING"
_COMPLETION_TIMING_ENV = "NETLOOM_COMPLETION_TIMING"

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
ACTIONS: dict[str, object] = {}


def _env_cli_timing_value() -> str | None:
    return os.getenv(_CLI_TIMING_ENV)


def _env_completion_timing_value() -> str | None:
    return os.getenv(_COMPLETION_TIMING_ENV)


def _import_completion_layer() -> None:
    importlib.import_module("netloom.cli.completion")


def _import_help_layer() -> None:
    importlib.import_module("netloom.core.interactive_help")


def _import_cache_layer() -> None:
    importlib.import_module("netloom.core.interactive_cache")


def _import_interactive_layer() -> None:
    importlib.import_module("netloom.core.interactive")


def _import_plugin_layer() -> None:
    importlib.import_module("netloom.core.plugin")


def print_completions(*args, **kwargs):
    from netloom.cli.completion import print_completions as impl

    return impl(*args, **kwargs)


def render_help(*args, **kwargs):
    from netloom.core.interactive_help import render_help as impl

    return impl(*args, **kwargs)


def load_interactive_settings():
    from netloom.core.interactive import load_interactive_settings as impl

    return impl()


def load_settings() -> Settings:
    from netloom.core.config import load_settings as impl

    return impl()


def get_plugin(*args, **kwargs):
    from netloom.core.plugin import get_plugin as impl

    return impl(*args, **kwargs)


def load_cached_catalog_for_plugin(*args, **kwargs):
    from netloom.core.interactive_cache import load_cached_interactive_catalog as impl

    return impl(*args, **kwargs)


def _needs_full_settings(settings) -> bool:
    return settings is None or not hasattr(settings, "server")


class _CliProfiler:
    def __init__(
        self,
        label: str,
        *,
        settings: Settings | None = None,
        env_value: str | None = None,
        allow_settings_fallback: bool = True,
    ):
        self.label = label
        if env_value is not None:
            self.enabled = env_value.strip().lower() not in {"", "0", "false", "no"}
        elif allow_settings_fallback:
            self.enabled = bool(getattr(settings, "cli_timing", False))
        else:
            self.enabled = False
        self.records: list[tuple[str, float]] = []
        self._start = time.perf_counter()

    def call(self, name: str, func, *args, **kwargs):
        if not self.enabled:
            return func(*args, **kwargs)
        started = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            self.records.append((name, (time.perf_counter() - started) * 1000.0))

    def emit(self) -> None:
        if not self.enabled:
            return
        total_ms = (time.perf_counter() - self._start) * 1000.0
        parts = [f"{name}={duration:.1f}ms" for name, duration in self.records]
        summary = ", ".join(parts)
        print(
            f"[netloom timing] {self.label} total={total_ms:.1f}ms"
            + (f" ({summary})" if summary else ""),
            file=sys.stderr,
        )


def _catalog_view_from_args(args: dict | None) -> str:
    value = (args or {}).get("catalog_view")
    if isinstance(value, str) and value.strip().lower() == "full":
        return "full"
    return "visible"


def _catalog_view_from_completion_words(words: list[str]) -> str:
    for word in words:
        if not isinstance(word, str):
            continue
        if word.startswith("--catalog-view="):
            if word.split("=", 1)[1].strip().lower() == "full":
                return "full"
            break
    return "visible"


def _completion_needs_catalog(words: list[str]) -> bool:
    positionals = [word for word in words if not word.startswith("-")]
    if not positionals:
        return True

    module = positionals[0]
    return module not in {"cache", "load", "server"}


def _load_catalog_for_cli(
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


def _catalog_has_action(
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


def _help_prefers_index(args: dict | None) -> bool:
    if not args:
        return True
    action = args.get("action")
    if not action:
        return True
    return action in _COMPACT_HELP_ACTIONS


def _help_needs_catalog(args: dict | None) -> bool:
    module = (args or {}).get("module")
    return module not in {"cache", "load", "server"}


def _actions() -> dict[str, object]:
    if not ACTIONS:
        from netloom.cli.commands import ACTIONS as imported_actions

        ACTIONS.update(imported_actions)
    return ACTIONS


def handle_copy_command(*args, **kwargs):
    from netloom.cli.copy import handle_copy_command as impl

    return impl(*args, **kwargs)


def handle_diff_command(*args, **kwargs):
    from netloom.cli.diff import handle_diff_command as impl

    return impl(*args, **kwargs)


def handle_load_command(*args, **kwargs):
    from netloom.cli.load import handle_load_command as impl

    return impl(*args, **kwargs)


def handle_server_command(*args, **kwargs):
    from netloom.cli.server import handle_server_command as impl

    return impl(*args, **kwargs)


def configure_logging(*args, **kwargs):
    from netloom.logging.setup import configure_logging as impl

    return impl(*args, **kwargs)


def _log_levels() -> dict[str, int]:
    from netloom.logging.setup import LOG_LEVELS

    return LOG_LEVELS


def should_mask_secrets(*args, **kwargs):
    from netloom.io.output import should_mask_secrets as impl

    return impl(*args, **kwargs)


def _get_catalog_for_cli(
    plugin,
    cp,
    *,
    token: str,
    settings: Settings | None,
    force_refresh: bool = False,
    catalog_view: str,
) -> dict:
    try:
        return plugin.get_api_catalog(
            cp,
            token=token,
            force_refresh=force_refresh,
            settings=settings,
            catalog_view=catalog_view,
        )
    except TypeError as exc:
        if "catalog_view" not in str(exc):
            raise
        return plugin.get_api_catalog(
            cp,
            token=token,
            force_refresh=force_refresh,
            settings=settings,
        )


def print_help(
    args: dict | None = None,
    *,
    plugin=None,
    settings: Settings | None = None,
) -> None:
    effective_settings = settings
    if effective_settings is None and _env_cli_timing_value() is None:
        try:
            effective_settings = load_interactive_settings()
        except Exception:
            effective_settings = None
    profiler = _CliProfiler(
        "help",
        settings=effective_settings,
        env_value=_env_cli_timing_value(),
    )
    selected_plugin = plugin
    selected_args = args or {}
    catalog_view = _catalog_view_from_args(selected_args)
    catalog = None
    needs_catalog = _help_needs_catalog(selected_args)
    prefer_index = _help_prefers_index(selected_args)
    active_settings = effective_settings
    plugin_name = getattr(active_settings, "plugin", None) if active_settings else None
    if needs_catalog and selected_plugin is None:
        profiler.call("import_interactive_layer", _import_interactive_layer)
        profiler.call("import_cache_layer", _import_cache_layer)
        active_settings = active_settings or profiler.call(
            "load_interactive_settings", load_interactive_settings
        )
        plugin_name = getattr(active_settings, "plugin", None)
        catalog = profiler.call(
            "load_core_cached_catalog",
            load_cached_catalog_for_plugin,
            plugin_name,
            settings=active_settings,
            catalog_view=catalog_view,
            prefer_index=prefer_index,
        )
        effective_settings = active_settings
    if needs_catalog and selected_plugin is None and catalog is None:
        profiler.call("import_plugin_layer", _import_plugin_layer)
        if _needs_full_settings(effective_settings):
            effective_settings = profiler.call("load_settings", load_settings)
        try:
            selected_plugin = profiler.call(
                "plugin_fallback_get_plugin",
                get_plugin,
                None,
                settings=effective_settings,
            )
        except ValueError:
            selected_plugin = None
    render_plugin = selected_plugin
    if render_plugin is None and plugin_name:
        render_plugin = _HELP_PLUGIN_MARKER
    if selected_plugin is not None and catalog is None:
        catalog = profiler.call(
            "plugin_fallback_cached_catalog",
            _load_catalog_for_cli,
            selected_plugin,
            settings=effective_settings,
            catalog_view=catalog_view,
            prefer_index=prefer_index,
        )
        action = selected_args.get("action")
        if (
            action
            and action not in _COMPACT_HELP_ACTIONS
            and _catalog_has_action(
                catalog,
                selected_args.get("module"),
                selected_args.get("service"),
                action,
            )
        ):
            catalog = profiler.call(
                "load_cached_catalog",
                _load_catalog_for_cli,
                selected_plugin,
                settings=effective_settings,
                catalog_view=catalog_view,
                prefer_index=False,
            )
    profiler.call("import_help_layer", _import_help_layer)
    text = profiler.call(
        "render_help",
        render_help,
        catalog,
        selected_args,
        version=get_version(),
        plugin=render_plugin,
    )
    print(text)
    profiler.emit()


def complete(words: list[str], settings: Settings | None = None) -> None:
    effective_settings = settings
    if effective_settings is None and _env_completion_timing_value() is None:
        try:
            effective_settings = load_interactive_settings()
        except Exception:
            effective_settings = None
    profiler = _CliProfiler(
        "complete",
        settings=effective_settings,
        env_value=_env_completion_timing_value(),
        allow_settings_fallback=False,
    )
    catalog = None
    if _completion_needs_catalog(words):
        profiler.call("import_interactive_layer", _import_interactive_layer)
        profiler.call("import_cache_layer", _import_cache_layer)
        active_settings = effective_settings or profiler.call(
            "load_interactive_settings", load_interactive_settings
        )
        plugin_name = getattr(active_settings, "plugin", None)
        catalog_view = _catalog_view_from_completion_words(words)
        catalog = profiler.call(
            "load_core_cached_catalog",
            load_cached_catalog_for_plugin,
            plugin_name,
            settings=active_settings,
            catalog_view=catalog_view,
            prefer_index=True,
        )
        if catalog is None:
            profiler.call("import_plugin_layer", _import_plugin_layer)
            if _needs_full_settings(active_settings):
                active_settings = profiler.call("load_settings", load_settings)
            try:
                plugin = profiler.call(
                    "plugin_fallback_get_plugin",
                    get_plugin,
                    None,
                    settings=active_settings,
                )
            except ValueError:
                plugin = None
            catalog = (
                profiler.call(
                    "plugin_fallback_cached_catalog",
                    _load_catalog_for_cli,
                    plugin,
                    settings=active_settings,
                    catalog_view=catalog_view,
                    prefer_index=True,
                )
                if plugin is not None
                else None
            )
    profiler.call("import_completion_layer", _import_completion_layer)
    profiler.call("print_completions", print_completions, words, catalog)
    profiler.emit()


def settings_with_cli_overrides(settings: Settings, args: dict) -> Settings:
    api_token = args.get("api_token") or args.get("token") or settings.api_token
    token_file = (
        args.get("token_file") or args.get("api_token_file") or settings.api_token_file
    )
    if is_dataclass(settings):
        return replace(settings, api_token=api_token, api_token_file=token_file)

    values = dict(vars(settings))
    values.update({"api_token": api_token, "api_token_file": token_file})
    return type(settings)(**values)


def main() -> None:
    if "--_complete" in sys.argv:
        words = [word for word in sys.argv[1:] if word != "--_complete"]
        complete(words)
        return

    try:
        args = parse_cli(sys.argv)
    except CliParseError as exc:
        print_help(exc.context)
        message = str(exc).strip()
        if message:
            print(f"\n{message}")
        return

    if args.get("version"):
        print(get_version())
        return

    if args.get("help"):
        print_help(args)
        return

    if not args.get("module"):
        print_help({})
        return

    if args.get("module") == "server":
        if handle_server_command(args):
            return
        print_help(
            {"module": "server", "service": args.get("service")},
        )
        return

    if args.get("module") == "load":
        if handle_load_command(args):
            return
        print_help(
            {"module": "load", "service": args.get("service")},
        )
        return

    settings = load_settings()
    active_settings = settings_with_cli_overrides(settings, args)
    if not active_settings.verify_ssl:
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    log_mgr = configure_logging(active_settings, root_name="netloom")
    log = log_mgr.get_logger(__name__)

    log_level = args.get("log_level")
    if log_level:
        levels = _log_levels()
        normalized = str(log_level).upper()
        if normalized not in levels:
            valid = ", ".join(name.lower() for name in levels)
            log.error("Invalid log level: %s. Valid options are: %s", log_level, valid)
            return
        log_mgr.set_level(levels[normalized])

    try:
        plugin = get_plugin(None, settings=active_settings)
    except ValueError as exc:
        print_help(args, settings=active_settings)
        print(f"\n{exc}")
        return

    if args.get("module") == "cache":
        service = args.get("service")
        if service == "clear" and not args.get("action"):
            removed = plugin.clear_api_cache(settings=active_settings)
            if removed:
                log.info("API endpoint cache cleared.")
            else:
                log.info("No API endpoint cache file found (already clear).")
            return
        if service == "update" and not args.get("action"):
            cp = plugin.build_client(active_settings)
            token = plugin.resolve_auth_token(cp, active_settings)
            _get_catalog_for_cli(
                plugin,
                cp,
                token=token,
                force_refresh=True,
                settings=active_settings,
                catalog_view=_catalog_view_from_args(args),
            )
            return
        print_help({"module": "cache"}, plugin=plugin, settings=active_settings)
        return

    module = args.get("module")
    service = args.get("service")
    action = args.get("action")

    if not (module and service and action):
        print_help(args, plugin=plugin, settings=active_settings)
        return

    if action == "copy":
        handle_copy_command(args, settings=active_settings, plugin=plugin)
        return
    if action == "diff":
        handle_diff_command(args, settings=active_settings, plugin=plugin)
        return

    try:
        command = _actions()[action]
    except KeyError:
        print_help(args, plugin=plugin, settings=active_settings)
        print(f"\nUnknown command: {module} {service} {action}")
        return

    mask_secrets = should_mask_secrets(args, active_settings)
    cp = plugin.build_client(active_settings, mask_secrets=mask_secrets)
    log.info(
        "Connecting via plugin '%s' to server: %s (SSL verify: %s)",
        plugin.name,
        active_settings.server,
        active_settings.verify_ssl,
    )
    token = plugin.resolve_auth_token(cp, active_settings)
    print(token)
    api_catalog = _get_catalog_for_cli(
        plugin,
        cp,
        token=token,
        settings=active_settings,
        catalog_view=_catalog_view_from_args(args),
    )
    command(cp, token, api_catalog, args, settings=active_settings)
