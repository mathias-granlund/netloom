from __future__ import annotations

from typing import TYPE_CHECKING, Any

from netloom.cli import deps as cli_deps
from netloom.cli.builtins import (
    handle_lightweight_builtin_command,
)
from netloom.contracts import NetloomRequest
from netloom.core import runtime as core_runtime

if TYPE_CHECKING:
    from netloom.core.config import Settings


def settings_with_cli_overrides(settings: Settings, args: dict) -> Settings:
    return core_runtime.settings_with_execution_overrides(settings, args)


def _render_result(result, args: dict, *, deps: Any) -> None:
    if result.status == "help":
        metadata = result.metadata
        deps.print_help(
            metadata.get("context", args),
            plugin=metadata.get("plugin"),
            settings=metadata.get("settings"),
        )
        if result.message:
            print(f"\n{result.message}")
        return

    if (
        result.status == "error"
        and result.message
        and not result.metadata.get("logged")
    ):
        print(result.message)


def run_cli(args: dict, *, deps: Any = cli_deps) -> None:
    if args.get("version"):
        print(deps.get_version())
        return

    if args.get("help"):
        deps.print_help(args)
        return

    if not args.get("module"):
        deps.print_help({})
        return

    if handle_lightweight_builtin_command(args, deps=deps):
        return

    request = NetloomRequest.from_mapping(args)
    options = core_runtime.execution_options_from_mapping(args)
    result = core_runtime.run_request(request, options, deps=deps)
    _render_result(result, args, deps=deps)
