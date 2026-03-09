from __future__ import annotations

from . import config
from .io_utils import load_payload_file, log_to_file
from .logger import AppLogger

log = AppLogger().get_logger(__name__)


def resolve_out_path(args: dict, service: str, action: str, data_format: str) -> str:
    out_arg = args.get("out")
    if out_arg:
        return out_arg
    base = service.replace("-", "_")
    return str(config.LOG_DIR / f"{base}_{action}.{data_format}")


def _csv_fieldnames_from_args(args: dict):
    csv_fieldnames = args.get("csv_fieldnames", config.DEFAULT_CSV_FIELDNAMES)
    if isinstance(csv_fieldnames, str):
        csv_fieldnames = [s.strip() for s in csv_fieldnames.split(",") if s.strip()]
    return csv_fieldnames


def _output_settings(args: dict) -> tuple[bool, str, str, list[str] | None]:
    console = args.get("console", config.CONSOLE)
    data_format = args.get("data_format", config.DEFAULT_FORMAT)
    out_path = resolve_out_path(args, args["service"], args["action"], data_format)
    csv_fieldnames = _csv_fieldnames_from_args(args)
    return console, data_format, out_path, csv_fieldnames


def _payload_from_args(args: dict, excluded_keys: set[str]) -> dict:
    return {key: value for key, value in args.items() if key not in excluded_keys}


def _resolve_placeholders_for_action(cp, api_catalog, args: dict, action: str) -> list[str]:
    _action_def, _path, placeholders = cp.resolve_action(api_catalog, args["module"], args["service"], action, args)
    return placeholders


def _payload_for_write_action(cp, api_catalog, args: dict, action: str):
    if "file" in args:
        return load_payload_file(args["file"])

    placeholders = set(_resolve_placeholders_for_action(cp, api_catalog, args, action))
    excluded = set(config.RESERVED) | placeholders
    return _payload_from_args(args, excluded)


def _query_params_for_action(cp, api_catalog, args: dict, action: str) -> dict:
    action_def = cp.get_action_definition(api_catalog, args["module"], args["service"], action)
    allowed = list(action_def.get("params") or [])
    params: dict[str, str | int] = {}

    if action == "list":
        if "limit" in allowed:
            limit = int(args.get("limit", 25))
            if limit < 1 or limit > 1000:
                raise ValueError("--limit must be between 1 and 1000")
            params["limit"] = limit
        if "offset" in allowed:
            params["offset"] = int(args.get("offset", 0))
        if "sort" in allowed:
            params["sort"] = args.get("sort", "+id")
        if "filter" in allowed and args.get("filter") is not None:
            params["filter"] = args["filter"]
        if "calculate_count" in allowed and args.get("calculate_count") is not None:
            params["calculate_count"] = args["calculate_count"]

    for name in allowed:
        if name in params:
            continue
        if name in args:
            params[name] = args[name]

    return params


def add_handler(cp, token, api_catalog, args):
    console, data_format, out_path, csv_fieldnames = _output_settings(args)
    payload = _payload_for_write_action(cp, api_catalog, args, "add")

    if isinstance(payload, list):
        result = [cp._add(api_catalog, token, {**args, **item}, item) for item in payload]
    else:
        result = cp._add(api_catalog, token, args, payload)

    log_to_file(result, filename=out_path, data_format=data_format, csv_fieldnames=csv_fieldnames, also_console=console)


def delete_handler(cp, token, api_catalog, args):
    console, data_format, out_path, csv_fieldnames = _output_settings(args)
    result = cp._delete(api_catalog, token, args)
    log_to_file(result, filename=out_path, data_format=data_format, csv_fieldnames=csv_fieldnames, also_console=console)


def get_handler(cp, token, api_catalog, args):
    console, data_format, out_path, csv_fieldnames = _output_settings(args)

    if args.get("all"):
        params = _query_params_for_action(cp, api_catalog, args, "list")
        result = cp._list(api_catalog, token, args, params=params)
    else:
        params = _query_params_for_action(cp, api_catalog, args, "get")
        result = cp._get(api_catalog, token, args, params=params)

    log_to_file(result, filename=out_path, data_format=data_format, csv_fieldnames=csv_fieldnames, also_console=console)


def list_handler(cp, token, api_catalog, args):
    alias_args = dict(args)
    alias_args["all"] = True
    alias_args["action"] = "list"
    return get_handler(cp, token, api_catalog, alias_args)


def replace_handler(cp, token, api_catalog, args):
    console, data_format, out_path, csv_fieldnames = _output_settings(args)
    payload = _payload_for_write_action(cp, api_catalog, args, "replace")

    if isinstance(payload, list):
        result = [cp._replace(api_catalog, token, {**args, **item}, item) for item in payload]
    else:
        result = cp._replace(api_catalog, token, args, payload)

    log_to_file(result, filename=out_path, data_format=data_format, csv_fieldnames=csv_fieldnames, also_console=console)


def update_handler(cp, token, api_catalog, args):
    console, data_format, out_path, csv_fieldnames = _output_settings(args)
    payload = _payload_for_write_action(cp, api_catalog, args, "update")

    if isinstance(payload, list):
        result = [cp._update(api_catalog, token, {**args, **item}, item) for item in payload]
    else:
        result = cp._update(api_catalog, token, args, payload)

    log_to_file(result, filename=out_path, data_format=data_format, csv_fieldnames=csv_fieldnames, also_console=console)


ACTIONS = {
    "add": add_handler,
    "delete": delete_handler,
    "get": get_handler,
    "list": list_handler,
    "replace": replace_handler,
    "update": update_handler,
}
