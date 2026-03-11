from __future__ import annotations

import sys

import urllib3

from arapy import get_version
from arapy.cli.commands import ACTIONS
from arapy.cli.completion import print_completions
from arapy.cli.help import render_help
from arapy.cli.parser import parse_cli
from arapy.core.catalog import (
    OAUTH_ENDPOINTS,
    clear_api_cache,
    get_api_catalog,
    load_cached_catalog,
)
from arapy.core.client import ClearPassClient
from arapy.core.config import Settings, load_settings
from arapy.logging.setup import LOG_LEVELS, configure_logging


def build_client(settings: Settings) -> ClearPassClient:
    if not settings.server:
        raise ValueError(
            "ARAPY_SERVER is not configured. Set it in the "
            "environment before running network actions."
        )
    return ClearPassClient(
        server=settings.server,
        https_prefix=settings.https_prefix,
        verify_ssl=settings.verify_ssl,
        timeout=settings.timeout,
    )


def print_help(args: dict | None = None) -> None:
    catalog = load_cached_catalog()
    print(render_help(catalog, args or {}, version=get_version()))


def complete(words: list[str], settings: Settings | None = None) -> None:
    catalog = load_cached_catalog(settings=settings)
    print_completions(words, catalog)


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
            removed = clear_api_cache(settings=settings)
            if removed:
                log.info("API endpoint cache cleared.")
            else:
                log.info("No API endpoint cache file found (already clear).")
            return
        if service == "update" and not args.get("action"):
            cp = build_client(settings)
            token = cp.login(OAUTH_ENDPOINTS, settings.credentials)["access_token"]
            get_api_catalog(cp, token=token, force_refresh=True, settings=settings)
            return
        print_help({"module": "cache"})
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

    cp = build_client(settings)
    log.info(
        "Connecting to ClearPass server: %s (SSL verify: %s)",
        settings.server,
        settings.verify_ssl,
    )
    token = cp.login(OAUTH_ENDPOINTS, settings.credentials)["access_token"]
    log.debug(f"Session token: {token}")
    api_catalog = get_api_catalog(cp, token=token, settings=settings)
    command(cp, token, api_catalog, args, settings=settings)
