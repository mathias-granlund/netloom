#!/usr/bin/env python3
# ======================================================================
# title             :arapy
# description       :A modern, modular CLI toolkit for interacting with
#                   :Aruba ClearPass Policy Manager REST API.
# author            :Mathias Granlund [mathias.granlund@aranya.se]
# date              :2026-03-09
# script version    :1.3.0
# clearpass version :6.5+
# python_version    :3.10.12
# ======================================================================

import sys

import urllib3

from . import commands, config, get_version
from .api_catalog import OAUTH_ENDPOINTS, clear_api_cache, get_api_catalog, load_cached_catalog
from .clearpass import ClearPassClient
from .logger import build_logger_from_env

if not config.VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _build_client() -> ClearPassClient:
    return ClearPassClient(
        server=config.SERVER,
        https_prefix=config.HTTPS,
        verify_ssl=config.VERIFY_SSL,
        timeout=config.DEFAULT_TIMEOUT,
    )


def _print_help(args=None) -> None:
    cp = _build_client()
    catalog = load_cached_catalog()
    print(cp._help(catalog, args or {}, version=get_version()))


def parse_cli(argv):
    args = {}
    positionals = []

    completing = "--_complete" in argv

    for item in argv[1:]:
        if item == "--_complete":
            args["_complete"] = True
        elif item.startswith("--_cword="):
            args["_cword"] = int(item.split("=", 1)[1])
        elif item.startswith("--_cur="):
            args["_cur"] = item.split("=", 1)[1]
        elif item in ("?", "-h", "--help"):
            args["help"] = True
        elif item == "--verbose":
            args["verbose"] = True
        elif item == "--version":
            args["version"] = True
        elif item == "--debug":
            args["debug"] = True
        elif item == "--console":
            args["console"] = True
        elif item == "--all":
            args["all"] = True
        elif item.startswith("--") and "=" in item:
            key, value = item[2:].split("=", 1)
            args[key] = value
        elif item.startswith("-"):
            if completing:
                continue
            raise ValueError(f"Unknown flag: {item}")
        else:
            positionals.append(item)

    if len(positionals) >= 1:
        args["module"] = positionals[0]
    if len(positionals) >= 2:
        args["service"] = positionals[1]
    if len(positionals) >= 3:
        args["action"] = positionals[2]

    return args


def _service_cli_actions(service_entry: dict) -> list[str]:
    actions = service_entry.get("actions") or {}
    cli_actions: list[str] = []
    if "get" in actions or "list" in actions:
        cli_actions.append("get")
    if "list" in actions:
        cli_actions.append("list")
    for name in ("add", "delete", "update", "replace"):
        if name in actions:
            cli_actions.append(name)
    return cli_actions


# Bash completion helper driven by the cached v2 API catalog.
def _complete(words: list[str]) -> None:
    catalog = load_cached_catalog()
    modules = (catalog or {}).get("modules") or {}

    cur = ""
    for word in words:
        if word.startswith("--_cur="):
            cur = word.split("=", 1)[1]

    pos = [word for word in words if not word.startswith("-")]

    if len(pos) == 0:
        print("\n".join(["cache"] + sorted(modules.keys())))
        return

    module = pos[0]
    if module == "cache":
        if len(pos) == 1:
            print("\n".join(["clear", "update"]))
            return
        print("")
        return

    if module not in modules:
        print("\n".join(["cache"] + sorted(modules.keys())))
        return

    services = modules[module]
    if len(pos) == 1:
        print("\n".join(sorted(services.keys())))
        return

    if len(pos) == 2 and cur != "":
        print("\n".join(sorted(services.keys())))
        return

    service = pos[1]
    if service not in services:
        print("\n".join(sorted(services.keys())))
        return

    if len(pos) == 2:
        print("\n".join(_service_cli_actions(services[service])))
        return

    print("")


def main():
    if "--_complete" in sys.argv:
        words = [w for w in sys.argv[1:] if w != "--_complete"]
        _complete(words)
        return

    log_mgr = build_logger_from_env(root_name=sys.argv[0])
    log = log_mgr.get_logger(__name__)

    args = parse_cli(sys.argv)

    log_level = args.get("log_level")
    if log_level:
        import logging

        level_map = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL,
        }
        if log_level not in level_map:
            log.error("Invalid log level: %s. Valid options are: %s", log_level, ", ".join(level_map.keys()))
            return
        log_mgr.set_level(level_map[log_level])

    if args.get("version"):
        print(get_version())
        return

    if args.get("help"):
        _print_help(args)
        return

    if not args.get("module"):
        _print_help({})
        return

    if args.get("module") == "cache":
        service = args.get("service")
        if service == "clear" and not args.get("action"):
            removed = clear_api_cache()
            if removed:
                log.info("API endpoint cache cleared.")
            else:
                log.info("No API endpoint cache file found (already clear).")
            return
        if service == "update" and not args.get("action"):
            cp = _build_client()
            token = cp.login(OAUTH_ENDPOINTS, config.CREDENTIALS)["access_token"]
            get_api_catalog(cp, token=token, force_refresh=True)
            return
        _print_help({"module": "cache"})
        return

    module = args.get("module")
    service = args.get("service")
    action = args.get("action")

    if not (module and service and action):
        _print_help(args)
        return

    try:
        command = commands.ACTIONS[action]
    except KeyError:
        _print_help(args)
        print(f"\nUnknown command: {module} {service} {action}")
        return

    cp = _build_client()
    log.info("Connecting to ClearPass server: %s (SSL verify: %s)", config.SERVER, config.VERIFY_SSL)
    token = cp.login(OAUTH_ENDPOINTS, config.CREDENTIALS)["access_token"]
    api_catalog = get_api_catalog(cp, token=token)

    command(cp, token, api_catalog, args)


if __name__ == "__main__":
    main()
