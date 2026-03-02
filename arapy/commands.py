#commands.py

#---- standard libs
from multiprocessing.util import debug
import sys
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

def debug_print(message):
    RED = "\033[31m"
    RESET = "\033[0m"
    caller = sys._getframe(1).f_code.co_name
    print(f"{RED}DEBUG:{RESET} In {caller}() calling: {message}")

# ---- Generic handler for all add calls ----
def add_handler(cp, token, APIPath, args):
    info = args.get("verbose", False)
    debug = args.get("debug", False)
    console = args.get("console", False)
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
            if info:
                log.info(f"Adding {len(payload)} items to {args['service']} from file: {args['file']} with payload: {payload}")
            call = [cp._add(APIPath, token, args, p) for p in payload]
            log_to_file(call, filename=out_path, data_format=data_format, csv_fieldnames=csv_fieldnames, also_console=console)
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

    if info:
        log.info(f"Adding {args['service']} with payload: {payload}")
    call = cp._add(APIPath, token, args, payload)

    log_to_file(call,filename=out_path,data_format=data_format, csv_fieldnames=csv_fieldnames, also_console=console)

# ---- Generic handler for all delete calls ----
def delete_handler(cp, token, APIPath, args):
    info = args.get("verbose", False)
    debug = args.get("debug", False)
    console = args.get("console", False)
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
        raise ValueError(f"{args['service']} delete requires --id=<id> or --name=<name>")
        
    if info:
        log.info(f"Deleted {args['service']} with identifier: {id or name}")
        
    log_to_file(call, filename=out_path, data_format=data_format, also_console=console)

# ---- Generic handler for all get calls ----
def get_handler(cp, token, APIPath, args):
    info = args.get("verbose", False)
    debug = args.get("debug", False)
    console = args.get("console", False)
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
    info = args.get("verbose", False)
    debug = args.get("debug", False)
    console = args.get("console", False)
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
    
    if info:
        log.info(f"Listing {args['service']} with filter='{filter_expr}', sort='{sort}', offset={offset}, limit={limit}, calculate_count={calc_count}")

    call = cp._list(APIPath, token, args, offset=offset, limit=limit, sort=sort, filter=filter_expr, calculate_count=calc_count)

    log_to_file(call, filename=out_path, data_format=data_format, csv_fieldnames=csv_fieldnames, also_console=console)

# ---- Generic handler for all replace calls ----
def put_handler():
    return

# ---- Generic handler for all update calls ----
def patch_handler():
    return

FUNCTIONS = {
    "add": add_handler,
    "delete": delete_handler,
    "get": get_handler,
    "list": list_handler,
    "replace": put_handler,
    "update": patch_handler,
}

DISPATCH = {
    "policy-elements": {
        "network-device": FUNCTIONS,
        "network-device-group": FUNCTIONS,
        "auth-method": FUNCTIONS,
        "enforcement-profile": FUNCTIONS,
    },
    "platform-certificates": {
        "cert-sign-request": FUNCTIONS,
        "cert-trust-list": FUNCTIONS,
        "client-cert": FUNCTIONS,
        "revocation-list": FUNCTIONS,
        "self-signed-cert": FUNCTIONS,
        "server-cert": FUNCTIONS,
        "service-cert": FUNCTIONS,
    },
    "identities": {
        "endpoint": FUNCTIONS,
        "device": FUNCTIONS,
        "user": FUNCTIONS,
        "api-client": FUNCTIONS,
    },
}