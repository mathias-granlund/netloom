#!/usr/bin/env python3
# ======================================================================
# title             :ClearPass API
# description       :
# author            :Mathias Granlund [mathias.granlund@aranya.se]
# date              :2026-02-20
# script version    :1.1.3
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

def print_help(args=None):
    """
    Context-aware help, driven by commands.DISPATCH.

    Examples:
      arapy --help
      arapy identities --help
      arapy identities endpoint --help
      arapy identities endpoint add --help
    """
    if args is None:
        args = {}

    module = args.get("module")
    service = args.get("service")
    action = args.get("action")

    dispatch = commands.DISPATCH

    def list_keys(d):
        return sorted(d.keys())

    def indent(lines, n=2):
        pad = " " * n
        return "\n".join(pad + line if line else "" for line in lines.splitlines())

    header = f"ClearPass API tool v{get_version()}\n"

    usage = (
        "Usage:\n"
        "  arapy <module> <service> <action> [--key=value] [--verbose | --debug]\n"
        "  arapy [--help | --version]\n"
        "\n"
        "Notes:\n"
        "  - Use --verbose to print output to console (otherwise logs to file only).\n"
        "  - Use --debug to print detailed output to console (otherwise logs to file only).\n"
        "  - Use --out=FILE to override default log output path.\n"
        "  - Use --data_format=json|csv to specify output format (default: json).\n"
        "  - Use --csv_fieldnames=field1,field2,... to specify fields and order for CSV output.\n"
        #"  - Use --filter=JSON to provide a server-side JSON filter expression (URL-encoded).\n"
        "  - Use --calculate_count=true|false to request a total count from the server.\n"
        "  - Note: --limit must be between 1 and 1000 per API constraints.\n"
        #"  - Set ARAPY_OUT_DIR to override the default output directory for logs.\n"
    )

    # ---- TOP LEVEL HELP ----
    if not module:
        modules = "\n".join(f"- {m}" for m in list_keys(dispatch))
        examples = (
            "Examples:\n"
            "  arapy policy-elements network-device list\n"
            "  arapy policy-elements network-device list --data_format=csv --csv_fieldnames=id, name, ip_address\n"
            "  arapy identities endpoint list --limit=5\n"
            "  arapy identities endpoint get --id=1234\n"
        )
        print(header + usage + "\nAvailable modules:\n" + indent(modules) + "\n\n" + examples)
        return

    # ---- MODULE HELP ----
    if module not in dispatch:
        available = ", ".join(list_keys(dispatch))
        print(header + f"Unknown module '{module}'. Available modules: {available}")
        return

    services_dict = dispatch[module]
    if not service:
        services = "\n".join(f"- {s}" for s in list_keys(services_dict))
        examples = (
            "Examples:\n"
            f"  arapy {module} {list_keys(services_dict)[0]} list\n"
            f"  arapy {module} {list_keys(services_dict)[0]} --help\n"
        )
        print(header + usage + f"\nModule: {module}\nAvailable services:\n" + indent(services) + "\n\n" + examples)
        return

    # ---- SERVICE HELP ----
    if service not in services_dict:
        available = ", ".join(list_keys(services_dict))
        print(header + f"Unknown service '{service}' under module '{module}'. Available services: {available}")
        return

    actions_dict = services_dict[service]
    if not action:
        actions = "\n".join(f"- {a}" for a in list_keys(actions_dict))
        examples = (
            "Examples:\n"
            f"  arapy {module} {service} list\n"
            f"  arapy {module} {service} add --help\n"
        )
        print(
            header
            + usage
            + f"\nModule: {module}\nService: {service}\nAvailable actions:\n"
            + indent(actions)
            + "\n\n"
            + examples
        )
        return

    # ---- ACTION HELP ----
    if action not in actions_dict:
        available = ", ".join(list_keys(actions_dict))
        print(header + f"Unknown action '{action}' for {module} {service}. Available actions: {available}")
        return

    # Action-specific help (hand-written “best” docs per action)
    # You can expand this incrementally.
    action_help = ""

    #### BAD STATIC HELP, REPLACE WITH DYNAMIC GENERATION BASED ON ARG SPECS IN COMMANDS.py LATER ####
    if (module, service, action) == ("policy-elements", "network-device", "list"):
        action_help = (
            "Network Device list\n"
            "Usage:\n"
            "  arapy policy-elements network-device list [--limit=N] [--offset=N] [--sort=+id] [--out=FILE] [-vvv]\n"
            "  Optional: --csv_fieldnames=id,name,ip_address\n"
        )

    elif (module, service, action) == ("policy-elements", "network-device", "add"):
        action_help = (
            "Network Device add\n"
            "Usage:\n"
            "  arapy policy-elements network-device add --name=NAME --ip_address=IP --vendor_name=VENDOR "
            "[--radius_secret=SECRET] [--out=FILE] [-vvv]\n"
            "  Or from file:\n"
            "  arapy policy-elements network-device add --file=devices.csv [--out=FILE] [-vvv]\n"
            "  arapy policy-elements network-device add --file=devices.json [--out=FILE] [-vvv]\n"
        )

    elif (module, service, action) == ("policy-elements", "network-device", "delete"):
        action_help = (
            "Network Device delete\n"
            "Usage:\n"
            "  arapy policy-elements network-device delete --id=1234 [--out=FILE] [-vvv]\n"
        )

    elif (module, service, action) == ("policy-elements", "network-device", "get"):
        action_help = (
            "Network Device get\n"
            "Usage:\n"
            "  arapy policy-elements network-device get --id=1234 [--out=FILE] [-vvv]\n"
        )

    elif (module, service, action) == ("identities", "endpoint", "list"):
        action_help = (
            "Endpoint list\n"
            "Usage:\n"
            "  arapy identities endpoint list [--limit=N] [--offset=N] [--sort=+id] [--out=FILE] [-vvv]\n"
            "  Optional: --csv_fieldnames=id,mac_address,description,status,device_insight_tags\n"
            "  Optional: --filter=JSON (server-side filter expression)\n"
            "  Optional: --calculate_count=true|false\n"
        )

    elif (module, service, action) == ("identities", "endpoint", "get"):
        action_help = (
            "Endpoint get\n"
            "Usage:\n"
            "  arapy identities endpoint get --id=1234 [--out=FILE] [-vvv]\n"
            "  arapy identities endpoint get --mac_address=aa:bb:cc:dd:ee:ff [--out=FILE] [-vvv]\n"
        )

    elif (module, service, action) == ("identities", "endpoint", "add"):
        action_help = (
            "Endpoint add\n"
            "Usage:\n"
            "  arapy identities endpoint add --mac_address=aa:bb:cc:dd:ee:ff --status=Known "
            "[--description=TEXT] [--device_insight_tags=...] [--out=FILE] [-vvv]\n"
            "  Or from file:\n"
            "  arapy identities endpoint add --file=endpoints.csv [--out=FILE] [-vvv]\n"
            "  arapy identities endpoint add --file=endpoints.json [--out=FILE] [-vvv]\n"
            "\n"
            "Notes:\n"
            "  status must be one of: Known, Unknown, Disabled\n"
        )

    elif (module, service, action) == ("identities", "endpoint", "delete"):
        action_help = (
            "Endpoint delete\n"
            "Usage:\n"
            "  arapy identities endpoint delete --id=1234 [--out=FILE] [-vvv]\n"
            "  arapy identities endpoint delete --mac_address=aa:bb:cc:dd:ee:ff [--out=FILE] [-vvv]\n"
        )

    elif (module, service, action) == ("identities", "device", "list"):
        action_help = (
            "Device Account list\n"
            "Usage:\n"
            "  arapy identities device list [--limit=N] [--offset=N] [--sort=-id] [--filter=JSON] [--out=FILE] [-vvv]\n"
        )

    elif (module, service, action) == ("identities", "device", "add"):
        action_help = (
            "Device Account add\n"
            "Usage:\n"
            "  arapy identities device add --mac=MACADDR [--enabled=true|false] [--role_id=N] [--out=FILE] [-vvv]\n"
            "  Or from file:\n"
            "  arapy identities device add --file=devices.json [--out=FILE] [-vvv]\n"
        )

    elif (module, service, action) == ("identities", "device", "delete"):
        action_help = (
            "Device Account delete\n"
            "Usage:\n"
            "  arapy identities device delete --id=DEVID [--out=FILE] [-vvv]\n"
            "  arapy identities device delete --mac_address=MACADDR [--out=FILE] [-vvv]\n"
        )

    elif (module, service, action) == ("identities", "device", "get"):
        action_help = (
            "Device Account get\n"
            "Usage:\n"
            "  arapy identities device get --id=DEVID [--out=FILE] [-vvv]\n"
            "  arapy identities device get --mac_address=MACADDR [--out=FILE] [-vvv]\n"
        )

    elif (module, service, action) == ("identities", "user", "list"):
        action_help = (
            "Guest User list\n"
            "Usage:\n"
            "  arapy identities user list [--limit=N] [--filter=JSON] [--out=FILE] [-vvv]\n"
        )

    elif (module, service, action) == ("identities", "user", "add"):
        action_help = (
            "Guest User add\n"
            "Usage:\n"
            "  arapy identities user add --username=USERNAME [--password=PASSWORD] [--out=FILE] [-vvv]\n"
            "  Or from file:\n"
            "  arapy identities user add --file=users.json [--out=FILE] [-vvv]\n"
        )

    elif (module, service, action) == ("identities", "user", "delete"):
        action_help = (
            "Guest User delete\n"
            "Usage:\n"
            "  arapy identities user delete --id=USERID [--out=FILE] [-vvv]\n"
        )

    elif (module, service, action) == ("identities", "user", "get"):
        action_help = (
            "Guest User get\n"
            "Usage:\n"
            "  arapy identities user get --id=USERID [--out=FILE] [-vvv]\n"
        )

    elif (module, service, action) == ("identities", "api-client", "list"):
        action_help = (
            "API Client list\n"
            "Usage:\n"
            "  arapy identities api-client list [--limit=N] [--filter=JSON] [--out=FILE] [-vvv]\n"
        )

    elif (module, service, action) == ("identities", "api-client", "add"):
        action_help = (
            "API Client add\n"
            "Usage:\n"
            "  arapy identities api-client add --client_id=ID [--client_secret=SECRET] [--out=FILE] [-vvv]\n"
            "  Or from file:\n"
            "  arapy identities api-client add --file=clients.json [--out=FILE] [-vvv]\n"
        )

    elif (module, service, action) == ("identities", "api-client", "delete"):
        action_help = (
            "API Client delete\n"
            "Usage:\n"
            "  arapy identities api-client delete --id=CLIENT_ID [--out=FILE] [-vvv]\n"
        )

    elif (module, service, action) == ("identities", "api-client", "get"):
        action_help = (
            "API Client get\n"
            "Usage:\n"
            "  arapy identities api-client get --id=CLIENT_ID [--out=FILE] [-vvv]\n"
        )

    elif (module, service, action) == ("policy-elements", "auth-method", "list"):
        action_help = (
            "Authentication Method list\n"
            "Usage:\n"
            "  arapy policy-elements auth-method list [--limit=N] [--filter=JSON] [--out=FILE] [-vvv]\n"
        )

    elif (module, service, action) == ("policy-elements", "auth-method", "add"):
        action_help = (
            "Authentication Method add\n"
            "Usage:\n"
            "  arapy policy-elements auth-method add --name=NAME --method_type=TYPE [--out=FILE] [-vvv]\n"
            "  Or from file:\n"
            "  arapy policy-elements auth-method add --file=methods.json [--out=FILE] [-vvv]\n"
        )

    elif (module, service, action) == ("policy-elements", "auth-method", "delete"):
        action_help = (
            "Authentication Method delete\n"
            "Usage:\n"
            "  arapy policy-elements auth-method delete --id=METHOD_ID [--out=FILE] [-vvv]\n"
        )

    elif (module, service, action) == ("policy-elements", "auth-method", "get"):
        action_help = (
            "Authentication Method get\n"
            "Usage:\n"
            "  arapy policy-elements auth-method get --id=METHOD_ID [--out=FILE] [-vvv]\n"
        )

    elif (module, service, action) == ("policy-elements", "enforcement-profile", "list"):
        action_help = (
            "Enforcement Profile list\n"
            "Usage:\n"
            "  arapy policy-elements enforcement-profile list [--limit=N] [--filter=JSON] [--out=FILE] [-vvv]\n"
        )

    elif (module, service, action) == ("policy-elements", "enforcement-profile", "get"):
        action_help = (
            "Enforcement Profile get\n"
            "Usage:\n"
            "  arapy policy-elements enforcement-profile get --id=PROFILE_ID [--out=FILE] [-vvv]\n"
        )

    else:
        action_help = (
            f"Help for: {module} {service} {action}\n"
            "No detailed help is defined yet for this action.\n"
            "Tip: run with -vvv to see console output while logging.\n"
        )

    print(header + action_help)

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
        elif item in ("--debug"):
            args["debug"] = True
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
    log_mgr.set_debug_mode(config.DEBUG)

    args = parse_cli(sys.argv)

    debug = args.get("debug", False)
    verbose = args.get("verbose", config.VERBOSE)
    if debug:
        log_mgr.set_debug_mode(True)
        log.debug("Debug mode enabled via CLI argument.")
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
        command = commands.FUNCTIONS[action]
    except KeyError:
        print_help(args)
        print(f"\nUnknown command: {module} {service} {action}")
        return
    
    cp = ClearPassClient(
        config.SERVER,
        https_prefix=config.HTTPS,
        verify_ssl=config.VERIFY_SSL,
        timeout=config.DEFAULT_TIMEOUT,
    )
    if verbose:
        log.info(f"Connecting to ClearPass server: {config.SERVER} (SSL verify: {config.VERIFY_SSL})")

    token = cp.login(APIPath, config.CREDENTIALS)["access_token"]
    command(cp, token, APIPath, args)

if __name__ == "__main__":
    main()