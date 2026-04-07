from __future__ import annotations

from typing import TYPE_CHECKING, Any

from netloom.cli.telemetry import CacheUpdateProgressReporter, CliProfiler

if TYPE_CHECKING:
    from netloom.core.config import Settings


def handle_lightweight_builtin_command(args: dict, *, deps: Any) -> bool:
    if args.get("module") == "server":
        if deps.handle_server_command(args):
            return True
        deps.print_help({"module": "server", "service": args.get("service")})
        return True

    if args.get("module") == "load":
        if deps.handle_load_command(args):
            return True
        deps.print_help({"module": "load", "service": args.get("service")})
        return True

    return False


def handle_plugin_builtin_command(
    args: dict,
    *,
    plugin,
    settings: Settings,
    log,
    deps: Any,
) -> bool:
    if args.get("module") != "cache":
        return False

    service = args.get("service")
    if service == "clear" and not args.get("action"):
        removed = plugin.clear_api_cache(settings=settings)
        if removed:
            log.info("API endpoint cache cleared.")
        else:
            log.info("No API endpoint cache file found (already clear).")
        return True

    if service == "update" and not args.get("action"):
        profiler = CliProfiler(
            "cache_update",
            settings=settings,
            env_value=deps._env_cli_timing_value(),
        )
        progress = CacheUpdateProgressReporter()
        try:
            progress.stage("building client")
            cp = profiler.call("build_client", plugin.build_client, settings)
            progress.stage("authenticating")
            token = profiler.call(
                "resolve_auth_token",
                plugin.resolve_auth_token,
                cp,
                settings,
            )
            deps._get_catalog_for_cli(
                plugin,
                cp,
                token=token,
                force_refresh=True,
                settings=settings,
                catalog_view=deps._catalog_view_from_args(args),
                timing_sink=profiler.add_record,
                progress_sink=progress,
            )
        finally:
            progress("done")
            profiler.emit()
        return True

    deps.print_help({"module": "cache"}, plugin=plugin, settings=settings)
    return True
