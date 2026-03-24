from __future__ import annotations

import sys
from dataclasses import is_dataclass, replace

import urllib3

from netloom import get_version
from netloom.cli.commands import ACTIONS
from netloom.cli.completion import print_completions
from netloom.cli.copy import handle_copy_command
from netloom.cli.diff import handle_diff_command
from netloom.cli.help import render_help
from netloom.cli.load import handle_load_command
from netloom.cli.parser import CliParseError, parse_cli
from netloom.cli.server import handle_server_command
from netloom.core.config import Settings, load_settings
from netloom.core.plugin import get_plugin
from netloom.io.output import should_mask_secrets
from netloom.logging.setup import LOG_LEVELS, configure_logging


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
) -> dict | None:
    try:
        return plugin.load_cached_catalog(settings=settings, catalog_view=catalog_view)
    except TypeError as exc:
        if "catalog_view" not in str(exc):
            raise
        return plugin.load_cached_catalog(settings=settings)


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
    selected_plugin = plugin
    if selected_plugin is None:
        try:
            selected_plugin = get_plugin(None, settings=settings or load_settings())
        except ValueError:
            selected_plugin = None
    catalog_view = _catalog_view_from_args(args)
    catalog = (
        _load_catalog_for_cli(
            selected_plugin,
            settings=settings,
            catalog_view=catalog_view,
        )
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
    catalog = None
    if _completion_needs_catalog(words):
        active_settings = settings or load_settings()
        try:
            plugin = get_plugin(None, settings=active_settings)
        except ValueError:
            plugin = None
        catalog_view = _catalog_view_from_completion_words(words)
        catalog = (
            _load_catalog_for_cli(
                plugin,
                settings=active_settings,
                catalog_view=catalog_view,
            )
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
    if "--_complete" in sys.argv:
        words = [word for word in sys.argv[1:] if word != "--_complete"]
        complete(words)
        return

    settings = load_settings()
    if not settings.verify_ssl:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    log_mgr = configure_logging(settings, root_name="netloom")
    log = log_mgr.get_logger(__name__)

    try:
        args = parse_cli(sys.argv)
    except CliParseError as exc:
        print_help(exc.context, settings=settings)
        message = str(exc).strip()
        if message:
            print(f"\n{message}")
        return

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
    api_catalog = _get_catalog_for_cli(
        plugin,
        cp,
        token=token,
        settings=active_settings,
        catalog_view=_catalog_view_from_args(args),
    )
    command(cp, token, api_catalog, args, settings=active_settings)
