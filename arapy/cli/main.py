from __future__ import annotations

import sys
from dataclasses import replace

import urllib3

from arapy import get_version
from arapy.cli.commands import ACTIONS
from arapy.cli.completion import print_completions
from arapy.cli.copy import handle_copy_command
from arapy.cli.help import render_help
from arapy.cli.parser import parse_cli
from arapy.cli.server import handle_server_command
from arapy.core.catalog import (
    OAUTH_ENDPOINTS,
    clear_api_cache,
    get_api_catalog,
    load_cached_catalog,
)
from arapy.core.client import ClearPassClient
from arapy.core.config import Settings, load_settings
from arapy.io.files import load_api_token_file
from arapy.io.output import should_mask_secrets
from arapy.logging.setup import LOG_LEVELS, configure_logging


def build_client(settings: Settings, *, mask_secrets: bool = True) -> ClearPassClient:
    if not settings.server:
        raise ValueError(
            "ARAPY_SERVER is not configured. Set it in the "
            "environment before running network actions."
        )
    try:
        return ClearPassClient(
            server=settings.server,
            https_prefix=settings.https_prefix,
            verify_ssl=settings.verify_ssl,
            timeout=settings.timeout,
            mask_secrets=mask_secrets,
        )
    except TypeError as exc:
        if "mask_secrets" not in str(exc):
            raise
        cp = ClearPassClient(
            server=settings.server,
            https_prefix=settings.https_prefix,
            verify_ssl=settings.verify_ssl,
            timeout=settings.timeout,
        )
        setattr(cp, "mask_secrets", mask_secrets)
        return cp


def print_help(args: dict | None = None) -> None:
    catalog = load_cached_catalog()
    print(render_help(catalog, args or {}, version=get_version()))


def complete(words: list[str], settings: Settings | None = None) -> None:
    catalog = load_cached_catalog(settings=settings)
    print_completions(words, catalog)


def settings_with_cli_overrides(settings: Settings, args: dict) -> Settings:
    api_token = args.get("api_token") or args.get("token") or settings.api_token
    token_file = (
        args.get("token_file")
        or args.get("api_token_file")
        or settings.api_token_file
    )
    return replace(settings, api_token=api_token, api_token_file=token_file)


def resolve_auth_token(cp: ClearPassClient, settings: Settings) -> str:
    if settings.api_token:
        return settings.api_token
    if settings.api_token_file:
        return load_api_token_file(settings.api_token_file)
    return cp.login(OAUTH_ENDPOINTS, settings.credentials)["access_token"]


def main() -> None:
    settings = load_settings()
    if not settings.verify_ssl:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    if "--_complete" in sys.argv:
        words = [word for word in sys.argv[1:] if word != "--_complete"]
        complete(words, settings=settings)
        return

    log_mgr = configure_logging(settings, root_name="arapy")
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
        print_help(args)
        return

    if not args.get("module"):
        print_help({})
        return

    if args.get("module") == "cache":
        service = args.get("service")
        if service == "clear" and not args.get("action"):
            removed = clear_api_cache(settings=active_settings)
            if removed:
                log.info("API endpoint cache cleared.")
            else:
                log.info("No API endpoint cache file found (already clear).")
            return
        if service == "update" and not args.get("action"):
            cp = build_client(active_settings)
            token = resolve_auth_token(cp, active_settings)
            get_api_catalog(
                cp, token=token, force_refresh=True, settings=active_settings
            )
            return
        print_help({"module": "cache"})
        return

    if args.get("module") == "server":
        if handle_server_command(args):
            return
        print_help({"module": "server", "service": args.get("service")})
        return

    if args.get("module") == "copy":
        handle_copy_command(
            args,
            settings=active_settings,
            build_client=build_client,
            resolve_auth_token=resolve_auth_token,
            get_api_catalog=get_api_catalog,
        )
        return

    module = args.get("module")
    service = args.get("service")
    action = args.get("action")

    if not (module and service and action):
        print_help(args)
        return

    try:
        command = ACTIONS[action]
    except KeyError:
        print_help(args)
        print(f"\nUnknown command: {module} {service} {action}")
        return

    mask_secrets = should_mask_secrets(args, active_settings)
    cp = build_client(active_settings, mask_secrets=mask_secrets)
    log.info(
        "Connecting to ClearPass server: %s (SSL verify: %s)",
        active_settings.server,
        active_settings.verify_ssl,
    )
    token = resolve_auth_token(cp, active_settings)
    api_catalog = get_api_catalog(cp, token=token, settings=active_settings)
    command(cp, token, api_catalog, args, settings=active_settings)
