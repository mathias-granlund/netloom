#!/usr/bin/env python3
# ======================================================================
# title             :ClearPass API
# description       :
# author            :Mathias Granlund [mathias.granlund@aranya.se]
# date              :2026-02-20
# script version    :1.1.6
# clearpass version :6.11.13
# python_version    :3.10.12
# ======================================================================

#---- standard libs
from doctest import debug
import sys
from tabnanny import verbose
import urllib3
#---- custom libs start
from .api_endpoints import API_ENDPOINTS as APIPath
from .clearpass import ClearPassClient
from . import config
from . import commands
from . import get_version
from .gui import run_gui
from .logger import build_logger_from_env
#---- globals start
if not config.VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ACTION_DOCS = {
    "list": {
        "summary": "",
        "options": [
            ("--limit=N", "Max items (1..1000)."),
            ("--offset=N", "Pagination offset."),
            ("--sort=+id|-id", "Sort order (default: +id)."),
            ("--filter=JSON", "Server-side filter expression."),
            ("--calculate_count=true|false", "Request total count."),
            ("--data_format=json|csv|raw", "Output format (default: json)."),
            ("--csv_fieldnames=a,b,c", "CSV columns and order."),
            ("--out=FILE", "Write output to this file."),
            ("--console", "Also print output to terminal."),
        ],
    },
    "get": {
        "summary": "",
        "options": [
            ("--id=N", "Numeric id."),
            ("--name=NAME", "Name."),
            ("--data_format=json|csv|raw", "Output format."),
            ("--out=FILE", "Write output to this file."),
            ("--console", "Also print output to terminal."),
        ],
    },
    "add": {
        "summary": "",
        "options": [
            ("--file=FILE.json|FILE.csv", "Create multiple objects from file."),
            ("--key=value", "Any non-reserved keys become JSON payload fields."),
            ("--data_format=json|csv|raw", "Output format."),
            ("--out=FILE", "Write output to this file."),
            ("--console", "Also print output to terminal."),
        ],
    },
    "delete": {
        "summary": "",
        "options": [
            ("--id=N", "Numeric id."),
            ("--name=NAME", "Name."),
            ("--out=FILE", "Write output to this file."),
            ("--console", "Also print output to terminal."),
        ],
    },
    "replace": {"summary": "Replace a resource (not implemented yet).", "options": []},
    "update": {"summary": "Update a resource (not implemented yet).", "options": []},
}

def print_help(args=None):
    if args is None:
        args = {}

    module = args.get("module")
    service = args.get("service")
    action = args.get("action")

    dispatch = commands.DISPATCH  # dynamic tree :contentReference[oaicite:2]{index=2}

    def list_keys(d):
        return sorted(d.keys())

    def indent(lines, n=2):
        pad = " " * n
        return "\n".join(pad + line if line else "" for line in lines.splitlines())

    def render_kv(options):
        if not options:
            return ""
        return "\n".join(f"  {flag:<28} {desc}" for flag, desc in options)

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
        "Options:\n"
        "  - Use --out=FILE to override default log output path.\n"
        "  - Use --data_format=json|csv|raw to specify output format (default: json).\n"
        "  - Use --csv_fieldnames=field1,field2,... to specify fields and order for CSV output.\n"
        "  - Use --filter=JSON to provide a server-side JSON filter expression (URL-encoded).\n"
        "  - Use --calculate_count=true|false to request a total count from the server.\n"
        "  - Use --limit=N to limit results (default: 25, max: 1000)\n"
    )

   # ---- TOP LEVEL HELP ----
    if not module:
        modules = "\n".join(f"- {m}" for m in list_keys(dispatch))
        examples = (
            "Examples:\n"
            "  arapy policy-elements network-device list --help\n"
            "  arapy policy-elements network-device list --data_format=csv --csv_fieldnames=id,name,ip_address --console\n"
            "  arapy identities endpoint list --limit=5\n"
            "  arapy identities endpoint get --id=1234\n"
        )
        print(header + global_usage + "\nAvailable modules:\n" + indent(modules) + "\n\n" + examples)
        return

    # ---- MODULE HELP ----
    if module not in dispatch:
        available = ", ".join(list_keys(dispatch))
        print(header + f"Unknown module '{module}'. Available modules: {available}")
        return

    services_dict = dispatch[module]
    if not service:
        services = "\n".join(f"- {s}" for s in list_keys(services_dict))
        print(header + global_usage + f"\nModule: {module}\nAvailable services:\n" + indent(services))
        return

    # ---- SERVICE HELP ----
    if service not in services_dict:
        available = ", ".join(list_keys(services_dict))
        print(header + f"Unknown service '{service}' under module '{module}'. Available services: {available}")
        return

    actions_dict = services_dict[service]
    if not action:
        actions = "\n".join(f"- {a}" for a in list_keys(actions_dict))
        print(header + global_usage + f"\nModule: {module}\nService: {service}\nAvailable actions:\n" + indent(actions))
        return

    # ---- ACTION HELP ----
    if action not in actions_dict:
        available = ", ".join(list_keys(actions_dict))
        print(header + f"Unknown action '{action}' for {module} {service}. Available actions: {available}")
        return

    # Generic action docs (no per-service static blocks)
    doc = ACTION_DOCS.get(action, {"summary": "", "options": []})
    summary = doc.get("summary", "")
    options = doc.get("options", [])

    action_usage = (
        "Usage:\n"
        f"  arapy {module} {service} {action} [--key=value] "
        "[--log_level=debug|info|warning|error|critical] [--console]\n"
    )

    out = header
    if summary:
        out += summary + "\n"
    out += action_usage
    if options:
        out += "\nOptions:\n" + render_kv(options) + "\n"

    print(out)

def parse_cli(argv):
    args = {}
    positionals = []

    for item in argv[1:]:
        if item in ("-h", "--help"):
            args["help"] = True
        elif item in ("--verbose"):
            args["verbose"] = True
        elif item in ("--version"):
            args["version"] = True
        elif item in ("--console"):
            args["console"] = True
        elif item.startswith("--") and "=" in item:
            key, value = item[2:].split("=", 1)
            args[key] = value
        elif item.startswith("-"):
            raise ValueError(f"Unknown flag: {item}")
        else:
            # bare word => positional
            positionals.append(item)

    if len(positionals) >= 1:
        args["module"] = positionals[0]
    if len(positionals) >= 2:
        args["service"] = positionals[1]
    if len(positionals) >= 3:
        args["action"] = positionals[2]

    return args

def main():
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
    log.debug(f"Parsed CLI arguments: {args}")

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

    if args.get("module") == "gui":
        run_gui()
        return
    
    module = args.get("module")
    service = args.get("service")
    action = args.get("action")

    if not (module and service and action):
        print_help(args)   # contextual help
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

    token = cp.login(APIPath, config.CREDENTIALS)["access_token"]
    command(cp, token, APIPath, args)

if __name__ == "__main__":
    main()