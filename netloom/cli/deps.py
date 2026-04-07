from __future__ import annotations

import importlib
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from netloom.core.config import Settings

_CLI_TIMING_ENV = "NETLOOM_CLI_TIMING"
_COMPLETION_TIMING_ENV = "NETLOOM_COMPLETION_TIMING"
_ACTIONS: dict[str, object] = {}


def get_version() -> str:
    from netloom import get_version as impl

    return impl()


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


def describe_context(*args, **kwargs):
    from netloom.core.interactive_help import describe_context as impl

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


def _actions() -> dict[str, object]:
    if not _ACTIONS:
        from netloom.cli.commands import ACTIONS as imported_actions

        _ACTIONS.update(imported_actions)
    return _ACTIONS
