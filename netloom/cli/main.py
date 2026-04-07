from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from netloom.cli import catalog_runtime as _catalog_runtime
from netloom.cli import deps as _deps
from netloom.cli import runtime as _runtime
from netloom.cli.parser import CliParseError, parse_cli
from netloom.cli.telemetry import CacheUpdateProgressReporter, CliProfiler

if TYPE_CHECKING:
    from netloom.core.config import Settings

_env_cli_timing_value = _deps._env_cli_timing_value
_env_completion_timing_value = _deps._env_completion_timing_value
_import_completion_layer = _deps._import_completion_layer
_import_help_layer = _deps._import_help_layer
_import_cache_layer = _deps._import_cache_layer
_import_interactive_layer = _deps._import_interactive_layer
_import_plugin_layer = _deps._import_plugin_layer
print_completions = _deps.print_completions
render_help = _deps.render_help
describe_context = _deps.describe_context
load_interactive_settings = _deps.load_interactive_settings
load_settings = _deps.load_settings
get_plugin = _deps.get_plugin
load_cached_catalog_for_plugin = _deps.load_cached_catalog_for_plugin
handle_copy_command = _deps.handle_copy_command
handle_diff_command = _deps.handle_diff_command
handle_load_command = _deps.handle_load_command
handle_server_command = _deps.handle_server_command
configure_logging = _deps.configure_logging
_log_levels = _deps._log_levels
should_mask_secrets = _deps.should_mask_secrets
_CliProfiler = CliProfiler
_CacheUpdateProgressReporter = CacheUpdateProgressReporter
ACTIONS = _deps._ACTIONS


def get_version() -> str:
    return _deps.get_version()


def _catalog_view_from_args(args: dict | None) -> str:
    return _catalog_runtime.catalog_view_from_args(args)


def _catalog_view_from_completion_words(words: list[str]) -> str:
    return _catalog_runtime.catalog_view_from_completion_words(words)


def _completion_needs_catalog(words: list[str]) -> bool:
    return _catalog_runtime.completion_needs_catalog(words)


def _load_catalog_for_cli(
    plugin,
    *,
    settings: Settings | None,
    catalog_view: str,
    prefer_index: bool = False,
) -> dict | None:
    return _catalog_runtime.load_catalog_for_cli(
        plugin,
        settings=settings,
        catalog_view=catalog_view,
        prefer_index=prefer_index,
    )


def _catalog_has_action(
    catalog: dict | None, module: str | None, service: str | None, action: str | None
) -> bool:
    return _catalog_runtime.catalog_has_action(catalog, module, service, action)


def _help_prefers_index(args: dict | None) -> bool:
    return _catalog_runtime.help_prefers_index(args)


def _help_needs_catalog(args: dict | None) -> bool:
    return _catalog_runtime.help_needs_catalog(args)


def _actions() -> dict[str, object]:
    return _deps._actions()


def _get_catalog_for_cli(
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
    return _catalog_runtime.get_catalog_for_cli(
        plugin,
        cp,
        token=token,
        settings=settings,
        force_refresh=force_refresh,
        catalog_view=catalog_view,
        timing_sink=timing_sink,
        progress_sink=progress_sink,
    )


def print_help(
    args: dict | None = None,
    *,
    plugin=None,
    settings: Settings | None = None,
) -> None:
    return _catalog_runtime.print_help(
        args,
        plugin=plugin,
        settings=settings,
        deps=sys.modules[__name__],
    )


def complete(words: list[str], settings: Settings | None = None) -> None:
    return _catalog_runtime.complete(
        words,
        settings=settings,
        deps=sys.modules[__name__],
    )


def describe(words: list[str], settings: Settings | None = None) -> None:
    return _catalog_runtime.describe(
        words,
        settings=settings,
        deps=sys.modules[__name__],
    )


def settings_with_cli_overrides(settings: Settings, args: dict) -> Settings:
    return _runtime.settings_with_cli_overrides(settings, args)


def run_cli(args: dict) -> None:
    return _runtime.run_cli(args, deps=sys.modules[__name__])


def main() -> None:
    if "--_complete" in sys.argv:
        words = [word for word in sys.argv[1:] if word != "--_complete"]
        complete(words)
        return
    if "--_describe" in sys.argv:
        words = [word for word in sys.argv[1:] if word != "--_describe"]
        describe(words)
        return

    try:
        args = parse_cli(sys.argv)
    except CliParseError as exc:
        print_help(exc.context)
        message = str(exc).strip()
        if message:
            print(f"\n{message}")
        return

    run_cli(args)


__all__ = [
    "ACTIONS",
    "CliParseError",
    "complete",
    "describe",
    "get_version",
    "main",
    "parse_cli",
    "print_help",
    "run_cli",
    "settings_with_cli_overrides",
]
