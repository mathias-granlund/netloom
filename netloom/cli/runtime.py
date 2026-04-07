from __future__ import annotations

from dataclasses import is_dataclass, replace
from typing import TYPE_CHECKING, Any

from netloom.cli import deps as cli_deps
from netloom.cli.builtins import (
    handle_lightweight_builtin_command,
    handle_plugin_builtin_command,
)

if TYPE_CHECKING:
    from netloom.core.config import Settings


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

    settings = deps.load_settings()
    active_settings = settings_with_cli_overrides(settings, args)
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
            return
        log_mgr.set_level(levels[normalized])

    try:
        plugin = deps.get_plugin(None, settings=active_settings)
    except ValueError as exc:
        deps.print_help(args, settings=active_settings)
        print(f"\n{exc}")
        return

    if handle_plugin_builtin_command(
        args,
        plugin=plugin,
        settings=active_settings,
        log=log,
        deps=deps,
    ):
        return

    module = args.get("module")
    service = args.get("service")
    action = args.get("action")

    if not (module and service and action):
        deps.print_help(args, plugin=plugin, settings=active_settings)
        return

    if action == "copy":
        deps.handle_copy_command(args, settings=active_settings, plugin=plugin)
        return
    if action == "diff":
        deps.handle_diff_command(args, settings=active_settings, plugin=plugin)
        return

    try:
        command = deps._actions()[action]
    except KeyError:
        deps.print_help(args, plugin=plugin, settings=active_settings)
        print(f"\nUnknown command: {module} {service} {action}")
        return

    mask_secrets = deps.should_mask_secrets(args, active_settings)
    cp = plugin.build_client(active_settings, mask_secrets=mask_secrets)
    log.info(
        "Connecting via plugin '%s' to server: %s (SSL verify: %s)",
        plugin.name,
        active_settings.server,
        active_settings.verify_ssl,
    )
    token = plugin.resolve_auth_token(cp, active_settings)
    print(token)
    api_catalog = deps._get_catalog_for_cli(
        plugin,
        cp,
        token=token,
        settings=active_settings,
        catalog_view=deps._catalog_view_from_args(args),
    )
    command(cp, token, api_catalog, args, settings=active_settings)
