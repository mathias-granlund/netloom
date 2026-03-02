#commands.py

#---- standard libs
from multiprocessing.util import debug
from unittest.mock import call
#---- custom libs
from . import config
from .io_utils import log_to_file, load_payload_file
from .logger import AppLogger
log = AppLogger().get_logger(__name__)

def resolve_out_path(args: dict, service: str, action: str, data_format: str) -> str:
    out_arg = args.get("out")
    if out_arg:
        return out_arg
    # Use centralized output paths; pass ext so templates with trailing '.' get proper extension
    base = service.replace("-", "_")
    return str(config.LOG_DIR / f"{base}_{action}.{data_format}")

def build_payload_from_args(args, reserved_keys):
    # Removes reserved keys from args (config.RESERVED = reserved keys) to build the payload for API calls.
    # This allows users to specify payload fields directly as command-line arguments, while keeping reserved keys for internal use.
    payload = {k: v for k, v in args.items() if k not in reserved_keys}
    return payload

# ---- Generic handler for all add calls ----
def add_handler(cp, token, APIPath, args):
    console = args.get("console", config.CONSOLE)
    log_level = args.get("log_level")
    csv_fieldnames = args.get("csv_fieldnames", config.DEFAULT_CSV_FIELDNAMES)
    # normalize csv_fieldnames from "a,b,c" -> ["a","b","c"]
    if isinstance(csv_fieldnames, str):
        csv_fieldnames = [s.strip() for s in csv_fieldnames.split(",") if s.strip()]

    data_format = args.get("data_format", config.DEFAULT_FORMAT)
    out_path = resolve_out_path(args, args["service"], args["action"], data_format)

    # File-based payload
    if "file" in args:
        payload = load_payload_file(args["file"])

        if isinstance(payload, list):
            call = [cp._add(APIPath, token, args, p) for p in payload]
            log_to_file(call, filename=out_path, data_format=data_format, csv_fieldnames=csv_fieldnames, also_console=console, log_level=log_level)
            return

    else:
        payload = build_payload_from_args(args, config.RESERVED)

    # Required fields depending on API [method] [service]
    required = ("")
    missing = [k for k in required if not payload.get(k)]
    if missing:
        raise ValueError(
            f"{args['service']} {args['action']} requires: "
            f"{', '.join(f'--{k}=...' for k in required)}. "
            f"Missing: {', '.join(missing)}"
    )

    call = cp._add(APIPath, token, args, payload)

    log_to_file(call,filename=out_path,data_format=data_format, csv_fieldnames=csv_fieldnames, also_console=console, log_level=log_level)

# ---- Generic handler for all delete calls ----
def delete_handler(cp, token, APIPath, args):
    console = args.get("console", config.CONSOLE)
    csv_fieldnames = args.get("csv_fieldnames", config.DEFAULT_CSV_FIELDNAMES)
    # normalize csv_fieldnames from "a,b,c" -> ["a","b","c"]
    if isinstance(csv_fieldnames, str):
        csv_fieldnames = [s.strip() for s in csv_fieldnames.split(",") if s.strip()]

    data_format = args.get("data_format", config.DEFAULT_FORMAT)
    out_path = resolve_out_path(args, args["service"], args["action"], data_format)

    if "file" in args:
        payload = load_payload_file(args["file"])

        if isinstance(payload, list):
            call = [cp._add(APIPath, token, args, p) for p in payload]
            log_to_file(call, filename=out_path, data_format=data_format, also_console=console)
            return
    else:
        payload = build_payload_from_args(args, config.RESERVED)

    id = args.get("id")
    name = args.get("name")
    if id is not None:
        try:
            cp._delete(APIPath, token, args, id)
            call = {"deleted": id, "status": "ok"}
        except ValueError:
            raise ValueError("--id must be numeric")
    elif name is not None:
        api_name = "name/" + name  # API expects name-based GETs to be in the format /name/{name}
        cp._delete(APIPath, token, args, api_name)
        call = {"deleted": args.get("name"), "status": "ok"}
    else:
        log.error(f"{args['service']} delete requires --id=<id> or --name=<name>")
        raise ValueError(f"{args['service']} delete requires --id=<id> or --name=<name>")
                
    log_to_file(call, filename=out_path, data_format=data_format, also_console=console)

# ---- Generic handler for all get calls ----
def get_handler(cp, token, APIPath, args):
    console = args.get("console", config.CONSOLE)
    csv_fieldnames = args.get("csv_fieldnames", config.DEFAULT_CSV_FIELDNAMES)
    # normalize csv_fieldnames from "a,b,c" -> ["a","b","c"]
    if isinstance(csv_fieldnames, str):
        csv_fieldnames = [s.strip() for s in csv_fieldnames.split(",") if s.strip()]

    data_format = args.get("data_format", config.DEFAULT_FORMAT)
    out_path = resolve_out_path(args, args["service"], args["action"], data_format)

    id = args.get("id")
    name = args.get("name")
    if id is not None:
        try:
            call = cp._get(APIPath, token, args, id)
        except ValueError:
            raise ValueError("--id must be numeric")
    elif name is not None:
        api_name = "name/" + name  # API expects name-based GETs to be in the format /name/{name}
        call = cp._get(APIPath, token, args, api_name)
    else:
        raise ValueError(f"{args['service']} get requires --id=<id> or --name=<name>")
    
    log_to_file(call, filename=out_path, data_format=data_format, also_console=console)

# ---- Generic handler for all list calls ----
def list_handler(cp, token, APIPath, args):
    console = args.get("console", config.CONSOLE)
    log_level = args.get("log_level")
    csv_fieldnames = args.get("csv_fieldnames", config.DEFAULT_CSV_FIELDNAMES)
    # normalize csv_fieldnames from "a,b,c" -> ["a","b","c"]
    if isinstance(csv_fieldnames, str):
        csv_fieldnames = [s.strip() for s in csv_fieldnames.split(",") if s.strip()]

    data_format = args.get("data_format", config.DEFAULT_FORMAT)
    out_path = resolve_out_path(args, args["service"], args["action"], data_format)

    filter_expr = args.get("filter")
    sort = args.get("sort", "+id")
    offset = int(args.get("offset", 0))
    limit = int(args.get("limit", 25))
    calc_count_arg = args.get("calculate_count")
    if isinstance(calc_count_arg, str):
        calc_count = calc_count_arg.lower() in ("1", "true", "yes")
    else:
        calc_count = bool(calc_count_arg) if calc_count_arg is not None else None

    if limit < 1 or limit > 1000:
        raise ValueError("--limit must be between 1 and 1000")
    
    call = cp._list(APIPath, token, args, offset=offset, limit=limit, sort=sort, filter=filter_expr, calculate_count=calc_count)

    log_to_file(call, filename=out_path, data_format=data_format, csv_fieldnames=csv_fieldnames, also_console=console, log_level=log_level)

# ---- Generic handler for all replace calls ----
def put_handler(cp, token, APIPath, args):
    return

# ---- Generic handler for all update calls ----
def patch_handler(cp, token, APIPath, args):
    return

ACTIONS = {
    "add": add_handler,
    "delete": delete_handler,
    "get": get_handler,
    "list": list_handler,
    "replace": put_handler,
    "update": patch_handler,
}

ACTIONS_DOCUMENTATION = {
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

DISPATCH = {
    "policy-elements": {
        "network-device": ACTIONS,
        "network-device-group": ACTIONS,
        "auth-method": ACTIONS,
        "enforcement-profile": ACTIONS,
    },
    "platform-certificates": {
        "cert-sign-request": ACTIONS,
        "cert-trust-list": ACTIONS,
        "client-cert": ACTIONS,
        "revocation-list": ACTIONS,
        "self-signed-cert": ACTIONS,
        "server-cert": ACTIONS,
        "service-cert": ACTIONS,
    },
    "identities": {
        "endpoint": ACTIONS,
        "device": ACTIONS,
        "user": ACTIONS,
        "api-client": ACTIONS,
    },
}
