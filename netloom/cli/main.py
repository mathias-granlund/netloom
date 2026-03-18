from __future__ import annotations

import sys
from dataclasses import is_dataclass, replace

import urllib3

from netloom import get_version
from netloom.cli.commands import ACTIONS
from netloom.cli.completion import print_completions
from netloom.cli.copy import handle_copy_command
from netloom.cli.help import render_help
from netloom.cli.load import handle_load_command
from netloom.cli.parser import parse_cli
from netloom.cli.server import handle_server_command
from netloom.core.config import Settings, load_settings
from netloom.core.plugin import get_plugin
from netloom.io.output import should_mask_secrets
from netloom.logging.setup import LOG_LEVELS, configure_logging


def print_help(
    args: dict | None = None,
    *,
    plugin=None,
    settings: Settings | None = None,
) -> None:
    selected_plugin = plugin
    if selected_plugin is None:
        try:
            selected_plugin = get_plugin(None, settings=settings or load_settings())
        except ValueError:
            selected_plugin = None
    catalog = (
        selected_plugin.load_cached_catalog(settings=settings)
        if selected_plugin is not None
        else None
    )
    print(
        render_help(
            catalog,
            args or {},
            version=get_version(),
            plugin=selected_plugin,
        )
    )


def complete(words: list[str], settings: Settings | None = None) -> None:
    active_settings = settings or load_settings()
    try:
        plugin = get_plugin(None, settings=active_settings)
    except ValueError:
        plugin = None
    catalog = (
        plugin.load_cached_catalog(settings=active_settings)
        if plugin is not None
        else None
    )
    print_completions(words, catalog)


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
    settings = load_settings()
    if not settings.verify_ssl:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    if "--_complete" in sys.argv:
        words = [word for word in sys.argv[1:] if word != "--_complete"]
        complete(words, settings=settings)
        return

    log_mgr = configure_logging(settings, root_name="netloom")
    log = log_mgr.get_logger(__name__)

    args = parse_cli(sys.argv)
    active_settings = settings_with_cli_overrides(settings, args)

    log_level = args.get("log_level")
    if log_level:
        normalized = str(log_level).upper()
        if normalized not in LOG_LEVELS:
            valid = ", ".join(name.lower() for name in LOG_LEVELS)
            log.error("Invalid log level: %s. Valid options are: %s", log_level, valid)
            return
        log_mgr.set_level(LOG_LEVELS[normalized])

    if args.get("version"):
        print(get_version())
        return

    if args.get("help"):
        print_help(args, settings=active_settings)
        return

    if not args.get("module"):
        print_help({}, settings=active_settings)
        return

    if args.get("module") == "server":
        if handle_server_command(args):
            return
        print_help(
            {"module": "server", "service": args.get("service")},
            settings=active_settings,
        )
        return

    if args.get("module") == "load":
        if handle_load_command(args):
            return
        print_help(
            {"module": "load", "service": args.get("service")},
            settings=active_settings,
        )
        return

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
            plugin.get_api_catalog(
                cp,
                token=token,
                force_refresh=True,
                settings=active_settings,
            )
            return
        print_help({"module": "cache"}, plugin=plugin, settings=active_settings)
        return

    if args.get("module") == "copy":
        handle_copy_command(args, settings=active_settings, plugin=plugin)
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

    try:
        command = ACTIONS[action]
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
    api_catalog = plugin.get_api_catalog(cp, token=token, settings=active_settings)
    command(cp, token, api_catalog, args, settings=active_settings)
