from __future__ import annotations

from dataclasses import is_dataclass, replace
from typing import TYPE_CHECKING, Any, Mapping

from netloom.contracts import ExecutionOptions, NetloomRequest, NetloomResult
from netloom.core.catalog_runtime import catalog_view_from_args, get_catalog_for_runtime

if TYPE_CHECKING:
    from netloom.core.config import Settings


class RuntimeDeps:
    def load_settings(self):
        from netloom.core.config import load_settings

        return load_settings()

    def configure_logging(self, *args, **kwargs):
        from netloom.logging.setup import configure_logging

        return configure_logging(*args, **kwargs)

    def _log_levels(self) -> dict[str, int]:
        from netloom.logging.setup import LOG_LEVELS

        return LOG_LEVELS

    def get_plugin(self, *args, **kwargs):
        from netloom.core.plugin_registry import get_plugin

        return get_plugin(*args, **kwargs)

    def should_mask_secrets(self, *args, **kwargs):
        from netloom.io.output import should_mask_secrets

        return should_mask_secrets(*args, **kwargs)

    def _actions(self) -> dict[str, object]:
        from netloom.core.actions import ACTIONS

        return ACTIONS

    def handle_copy_command(self, *args, **kwargs):
        from netloom.core.copy import handle_copy_command

        return handle_copy_command(*args, **kwargs)

    def handle_diff_command(self, *args, **kwargs):
        from netloom.core.diff import handle_diff_command

        return handle_diff_command(*args, **kwargs)

    def handle_import_command(self, *args, **kwargs):
        from netloom.core.import_config import handle_import_command

        return handle_import_command(*args, **kwargs)

    def handle_show_command(self, *args, **kwargs):
        from netloom.core.show import handle_show_command

        return handle_show_command(*args, **kwargs)

    def _catalog_view_from_args(self, args: dict | None) -> str:
        return catalog_view_from_args(args)

    def _get_catalog_for_cli(self, *args, **kwargs) -> dict:
        return get_catalog_for_runtime(*args, **kwargs)

    def _env_cli_timing_value(self) -> str | None:
        import os

        return os.getenv("NETLOOM_CLI_TIMING")

    @staticmethod
    def _CliProfiler(*args, **kwargs):
        from netloom.core.telemetry import CliProfiler

        return CliProfiler(*args, **kwargs)

    @staticmethod
    def _CacheUpdateProgressReporter(*args, **kwargs):
        from netloom.core.telemetry import CacheUpdateProgressReporter

        return CacheUpdateProgressReporter(*args, **kwargs)


def settings_with_execution_overrides(
    settings: Settings, overrides: Mapping[str, Any]
) -> Settings:
    api_token = (
        overrides.get("api_token") or overrides.get("token") or settings.api_token
    )
    token_file = (
        overrides.get("token_file")
        or overrides.get("api_token_file")
        or settings.api_token_file
    )
    log_level = overrides.get("log_level") or settings.log_level
    if is_dataclass(settings):
        return replace(
            settings,
            api_token=api_token,
            api_token_file=token_file,
            log_level=str(log_level).upper(),
        )

    values = dict(vars(settings))
    values.update(
        {
            "api_token": api_token,
            "api_token_file": token_file,
            "log_level": str(log_level).upper(),
        }
    )
    return type(settings)(**values)


def execution_options_from_mapping(values: Mapping[str, Any]) -> ExecutionOptions:
    catalog_view = values.get("catalog_view")
    if not (isinstance(catalog_view, str) and catalog_view.strip().lower() == "full"):
        catalog_view = "visible"
    else:
        catalog_view = "full"

    return ExecutionOptions(
        catalog_view=catalog_view,
        output_format=values.get("data_format"),
        output_path=str(values["out"]) if values.get("out") is not None else None,
        console=bool(values.get("console")),
        dry_run=bool(values.get("dry_run")),
        continue_on_error=bool(values.get("continue_on_error")),
        extra={
            key: value
            for key, value in values.items()
            if key
            not in {
                "catalog_view",
                "console",
                "continue_on_error",
                "data_format",
                "dry_run",
                "out",
            }
        },
    )


def _args_from_request(
    request: NetloomRequest, options: ExecutionOptions
) -> dict[str, Any]:
    args = request.to_mapping()
    args["catalog_view"] = options.catalog_view
    if options.output_format is not None:
        args["data_format"] = options.output_format
    if options.output_path is not None:
        args["out"] = options.output_path
    if options.console:
        args["console"] = True
    if options.dry_run:
        args["dry_run"] = True
    if options.continue_on_error:
        args["continue_on_error"] = True
    if (
        not options.mask_secrets
        and not args.get("decrypt")
        and args.get("encrypt") is None
    ):
        args["decrypt"] = True
    return args


def _help_result(
    *,
    context: dict[str, Any],
    plugin=None,
    settings: Settings | None = None,
    message: str | None = None,
) -> NetloomResult:
    return NetloomResult(
        status="help",
        message=message,
        metadata={"context": context, "plugin": plugin, "settings": settings},
    )


def _artifacts_from_data(data: Any) -> dict[str, str]:
    if not isinstance(data, dict):
        return {}
    artifacts = data.get("artifacts")
    if not isinstance(artifacts, dict):
        return {}
    return {
        str(name): str(path)
        for name, path in artifacts.items()
        if path not in (None, "")
    }


def _handle_cache_command(
    args: dict[str, Any],
    *,
    plugin,
    settings: Settings,
    log,
    deps: Any,
) -> NetloomResult:
    service = args.get("service")
    if service == "clear" and not args.get("action"):
        removed = plugin.clear_api_cache(settings=settings)
        if removed:
            log.info("API endpoint cache cleared.")
        else:
            log.info("No API endpoint cache file found (already clear).")
        return NetloomResult(data={"removed": bool(removed)})

    if service == "update" and not args.get("action"):
        profiler = deps._CliProfiler(
            "cache_update",
            settings=settings,
            env_value=deps._env_cli_timing_value(),
        )
        progress = deps._CacheUpdateProgressReporter()
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
                catalog_view=args.get("catalog_view") or "visible",
                timing_sink=profiler.add_record,
                progress_sink=progress,
            )
        finally:
            progress("done")
            profiler.emit()
        return NetloomResult(data={"updated": True})

    return _help_result(context={"module": "cache"}, plugin=plugin, settings=settings)


def _handle_plugin_builtin_request(
    args: dict[str, Any],
    *,
    plugin,
    settings: Settings,
    log,
    deps: Any,
) -> NetloomResult | None:
    module = args.get("module")
    if module == "import":
        handled = deps.handle_import_command(
            args,
            plugin=plugin,
            settings=settings,
            deps=deps,
            log=log,
        )
        if handled:
            return NetloomResult(data=True)
        return _help_result(
            context={"module": "import"}, plugin=plugin, settings=settings
        )

    if module == "show":
        handled = deps.handle_show_command(
            args,
            plugin=plugin,
            settings=settings,
            deps=deps,
            log=log,
        )
        if handled:
            return NetloomResult(data=True)
        return _help_result(
            context={"module": "show"}, plugin=plugin, settings=settings
        )

    if module == "cache":
        return _handle_cache_command(
            args,
            plugin=plugin,
            settings=settings,
            log=log,
            deps=deps,
        )

    return None


def run_request(
    request: NetloomRequest,
    options: ExecutionOptions | None = None,
    *,
    deps: Any | None = None,
) -> NetloomResult:
    deps = deps or RuntimeDeps()
    options = options or execution_options_from_mapping(request.to_mapping())
    args = _args_from_request(request, options)
    module = request.module

    if not module:
        return _help_result(context={})

    settings = deps.load_settings()
    active_settings = settings_with_execution_overrides(settings, args)
    if not active_settings.verify_ssl:
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    log_mgr = deps.configure_logging(active_settings, root_name="netloom")
    log = log_mgr.get_logger(__name__)

    log_level = args.get("log_level")
    if log_level:
        levels = deps._log_levels()
        normalized = str(log_level).upper()
        if normalized not in levels:
            valid = ", ".join(name.lower() for name in levels)
            log.error("Invalid log level: %s. Valid options are: %s", log_level, valid)
            return NetloomResult(
                status="error",
                message=f"Invalid log level: {log_level}. Valid options are: {valid}",
                metadata={"logged": True},
            )
        log_mgr.set_level(levels[normalized])

    try:
        plugin = deps.get_plugin(request.plugin, settings=active_settings)
    except ValueError as exc:
        return _help_result(
            context=args,
            settings=active_settings,
            message=str(exc),
        )

    builtin_result = _handle_plugin_builtin_request(
        args,
        plugin=plugin,
        settings=active_settings,
        log=log,
        deps=deps,
    )
    if builtin_result is not None:
        return builtin_result

    service = request.service
    action = request.action
    if not (module and service and action):
        return _help_result(context=args, plugin=plugin, settings=active_settings)

    if action == "copy":
        data = deps.handle_copy_command(args, settings=active_settings, plugin=plugin)
        return NetloomResult(data=data, artifacts=_artifacts_from_data(data))

    if action == "diff":
        data = deps.handle_diff_command(args, settings=active_settings, plugin=plugin)
        return NetloomResult(data=data, artifacts=_artifacts_from_data(data))

    try:
        command = deps._actions()[action]
    except KeyError:
        return _help_result(
            context=args,
            plugin=plugin,
            settings=active_settings,
            message=f"Unknown command: {module} {service} {action}",
        )

    mask_secrets = deps.should_mask_secrets(args, active_settings)
    cp = plugin.build_client(active_settings, mask_secrets=mask_secrets)
    try:
        setattr(cp, "netloom_plugin", plugin)
    except Exception:
        pass
    log.info(
        "Connecting via plugin '%s' to server: %s (SSL verify: %s)",
        plugin.name,
        active_settings.server,
        active_settings.verify_ssl,
    )
    token = plugin.resolve_auth_token(cp, active_settings)
    api_catalog = deps._get_catalog_for_cli(
        plugin,
        cp,
        token=token,
        settings=active_settings,
        catalog_view=args.get("catalog_view") or "visible",
    )
    data = command(cp, token, api_catalog, args, settings=active_settings)
    return NetloomResult(
        data=data,
        metadata={
            "module": module,
            "service": service,
            "action": action,
            "plugin": getattr(plugin, "name", None),
        },
    )


__all__ = [
    "RuntimeDeps",
    "execution_options_from_mapping",
    "run_request",
    "settings_with_execution_overrides",
]
