#!/usr/bin/env python3
# ======================================================================
# title             :ClearPass API
# description       :
# author            :Mathias Granlund [mathias.granlund@aranya.se]
# date              :2026-02-20
# script version    :1.2.5
# clearpass version :6.11.13
# python_version    :3.10.12
# ======================================================================

import sys
import urllib3

from .clearpass import ClearPassClient
from . import config
from . import commands
from . import get_version
from .logger import build_logger_from_env
from .api_catalog import OAUTH_ENDPOINTS, get_api_paths, clear_api_cache, load_cached_catalog

if not config.VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def print_help(args=None):
    """
    Help is driven entirely by the dynamically discovered API catalog.
    The catalog is cached in cache/api_endpoints_cache.json after the first
    authenticated run.

    If the cache does not exist yet (or is empty), arapy cannot show modules/services,
    because it has no authoritative source of truth without contacting ClearPass.
    """
    if args is None:
        args = {}

    module = args.get("module")
    service = args.get("service")
    action = args.get("action")

    header = f"ClearPass API tool v{get_version()}\n"

    global_usage = (
        "Usage:\n"
        "  arapy <module> <service> <action> [--key=value] [--log_level=debug|info|warning|error|critical] [--console]\n"
        "  arapy [--help | --version]\n"
        "\n"
        "Logging:\n"
        "  - Use --log_level=LEVEL to set log level (default: info).\n"
        "  - Use --console to also print output to console (default: logs to file only).\n"
        "\n"
        "Common options:\n"
        "  --out=FILE                         Override default log output path.\n"
        "  --data_format=json|csv|raw         Output format (default: json).\n"
        "  --csv_fieldnames=a,b,c             Fields and order for CSV output.\n"
        "  --filter=JSON                      Server-side JSON filter expression (URL-encoded).\n"
        "  --calculate_count=true|false       Request a total count from the server.\n"
        "  --limit=N                          Limit results (default: 25, max: 1000).\n"
        "  --offset=N                         Pagination offset.\n"
        "  --sort=+id|-id                     Sort order (default: +id).\n"
    )

    action_options = {
        "list": [
            ("--limit=N", "Max items (default: 25, max: 1000)."),
            ("--offset=N", "Pagination offset."),
            ("--sort=+id|-id", "Sort order (default: +id)."),
            ("--filter=JSON", "Server-side filter expression (URL-encoded)."),
            ("--calculate_count=true|false", "Request total count from the server."),
        ],
        "get": [
            ("--id=N", "Object id."),
            ("--name=NAME", "Object name (when supported)."),
        ],
        "add": [
            ("--file=FILE", "Create from file."),
            ("--key=value", "Any non-reserved keys become JSON payload fields."),
        ],
        "delete": [
            ("--id=N", "Object id."),
            ("--name=NAME", "Object name (when supported)."),
            ("--file=FILE", "Delete from file."),
        ],
    }

    def render_kv(opts):
        return "\n".join(f"  {flag:<28} {desc}" for flag, desc in opts)

    catalog = load_cached_catalog()
    modules = (catalog or {}).get("modules") or {}

    if not modules:
        msg = (
            "No API catalog cache found.\n"
            "  arapy relies on ClearPass /api-docs for modules/services/actions.\n\n"
            "To build the catalog cache run:\n"
            "  arapy cache update"
        )
        # Still show global usage so users know how to proceed
        print(header + global_usage + "\n" + msg)
        return

    # --- TOP LEVEL HELP ---
    if not module:
        mod_list = "\n".join(f"- {m}" for m in sorted(modules.keys()))
        examples = (
            "Tip:\n"
            "  Clear and rebuild the API cache if ClearPass version was changed:\n"
            "  arapy cache clear\n"
        )
        print(header + global_usage + "\nAvailable modules:\n  " + mod_list.replace("\n", "\n  ") + "\n\n" + examples)
        return

    # --- MODULE HELP ---
    if module not in modules:
        print(header + f"Unknown module '{module}'. Available modules: {', '.join(sorted(modules.keys()))}")
        return

    services_dict = modules[module]

    if not service:
        services = "\n".join(f"- {s}" for s in sorted(services_dict.keys()))
        print(header + global_usage + f"\nModule: {module}\nAvailable services:\n  " + services.replace("\n", "\n  "))
        return

    # --- SERVICE HELP ---
    if service not in services_dict:
        print(
            header
            + f"Unknown service '{service}' under module '{module}'. Available services: {', '.join(sorted(services_dict.keys()))}"
        )
        return

    svc_entry = services_dict[service]
    route = svc_entry.get("route", "<unknown>")
    actions = svc_entry.get("actions") or ["list", "get", "add", "delete"]

    if not action:
        out = header + global_usage + f"\nModule: {module}\nService: {service}\n"
        out += f"Route: {route}\n"
        out += "Available actions:\n  " + "\n  ".join(actions)
        print(out)
        return

    # --- ACTION HELP ---
    if action not in actions:
        print(header + f"Unknown action '{action}' for {module} {service}. Available actions: {', '.join(actions)}")
        return

    out = header
    out += "Usage:\n"
    out += f"  arapy {module} {service} {action} [--key=value] [--log_level=debug|info|warning|error|critical] [--console]\n"
    out += f"\nRoute:\n  {route}\n"

    opts = action_options.get(action, [])
    if opts:
        out += "\nOptions:\n" + render_kv(opts) + "\n"

    print(out)


def parse_cli(argv):
    args = {}
    positionals = []

    completing = "--_complete" in argv  # detect early

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

        elif item.startswith("--") and "=" in item:
            key, value = item[2:].split("=", 1)
            args[key] = value

        elif item.startswith("-"):
            # In completion mode, ignore unknown/partial flags so tab completion doesn't crash
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


def _complete(words: list[str]) -> None:
    """
    Bash completion helper driven by the cached API catalog only.
    If the cache doesn't exist yet, we can only suggest the 'cache' command.
    """
    catalog = load_cached_catalog()
    modules = (catalog or {}).get("modules") or {}

    cur = ""
    for w in words:
        if w.startswith("--_cur="):
            cur = w.split("=", 1)[1]

    pos = [w for w in words if not w.startswith("-")]

    # module position
    if len(pos) == 0:
        suggestions = ["cache"] + sorted(modules.keys())
        print("\n".join(suggestions))
        return

    module = pos[0]
    if module == "cache":
        # supports: arapy cache clear
        if len(pos) == 1:
            print("clear")
            return
        print("")
        return

    if module not in modules:
        suggestions = ["cache"] + sorted(modules.keys())
        print("\n".join(suggestions))
        return

    services = modules[module]

    # service position
    if len(pos) == 1:
        print("\n".join(sorted(services.keys())))
        return

    service = pos[1]

    # If user is still typing service token, offer service matches
    if len(pos) == 2 and cur != "":
        print("\n".join(sorted(services.keys())))
        return

    if service not in services:
        print("\n".join(sorted(services.keys())))
        return

    # actions position
    actions = services[service].get("actions") or ["list", "get", "add", "delete"]

    if len(pos) == 2:
        print("\n".join(sorted(actions)))
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
            log.error(f"Invalid log level: {log_level}. Valid options are: {', '.join(level_map.keys())}")
            return
        log_mgr.set_level(level_map[log_level])

    log.debug("Debug mode enabled.")
    log.debug(f"Parsed arguments: {args}")

    # ---- VERSION FIRST ----
    if args.get("version"):
        print(get_version())
        return

    # ---- HELP ----
    if args.get("help"):
        print_help(args)
        return

    # ---- No module provided → show top-level help ----
    if not args.get("module"):
        print_help({})
        return

    # --- CACHE COMMANDS (no ClearPass connection needed) ---
    if args.get("module") == "cache":
        service = args.get("service")

        # supports: arapy cache clear
        if service == "clear" and not args.get("action"):
            removed = clear_api_cache()
            if removed:
                log.info("API endpoint cache cleared.")
            else:
                log.info("No API endpoint cache file found (already clear).")
            return
        if service == "update" and not args.get("action"):
                cp = ClearPassClient(
                    server=config.SERVER,
                    https_prefix=config.HTTPS,
                    verify_ssl=config.VERIFY_SSL,
                    timeout=config.DEFAULT_TIMEOUT,
    )
                token = cp.login(OAUTH_ENDPOINTS, config.CREDENTIALS)["access_token"]
                log.debug(f"Authorization: Bearer {token}")

                api_paths = get_api_paths(cp, token=token)
                log.debug(f"Loaded {len(api_paths)} API endpoints. Example keys: {sorted(list(api_paths))[:20]}")
                return
        return

    module = args.get("module")
    service = args.get("service")
    action = args.get("action")

    if not (module and service and action):
        print_help(args)  # contextual help
        return

    try:
        command = commands.ACTIONS[action]
    except KeyError:
        print_help(args)
        print(f"\nUnknown command: {module} {service} {action}")
        return

    cp = ClearPassClient(
        server=config.SERVER,
        https_prefix=config.HTTPS,
        verify_ssl=config.VERIFY_SSL,
        timeout=config.DEFAULT_TIMEOUT,
    )
    log.info(f"Connecting to ClearPass server: {config.SERVER} (SSL verify: {config.VERIFY_SSL})")

    token = cp.login(OAUTH_ENDPOINTS, config.CREDENTIALS)["access_token"]
    log.debug(f"Authorization: Bearer {token}")

    api_paths = get_api_paths(cp, token=token)
    log.debug(f"Loaded {len(api_paths)} API endpoints. Example keys: {sorted(list(api_paths))[:20]}")

    command(cp, token, api_paths, args)


if __name__ == "__main__":
    main()