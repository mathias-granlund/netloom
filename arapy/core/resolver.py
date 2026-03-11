from __future__ import annotations

from pathlib import Path

from arapy.core.config import RESERVED_ARGS, Settings
from arapy.io.files import load_payload_file


def resolve_out_path(
    args: dict, service: str, action: str, data_format: str, settings: Settings
) -> str:
    out_arg = args.get("out")
    if out_arg:
        return str(Path(out_arg))
    base = service.replace("-", "_")
    return str(settings.paths.response_dir / f"{base}_{action}.{data_format}")


def csv_fieldnames_from_args(args: dict, settings: Settings) -> list[str] | None:
    csv_fieldnames = args.get("csv_fieldnames", settings.default_csv_fieldnames)
    if isinstance(csv_fieldnames, str):
        csv_fieldnames = [
            part.strip() for part in csv_fieldnames.split(",") if part.strip()
        ]
    return csv_fieldnames


def output_settings(
    args: dict, settings: Settings
) -> tuple[bool, str, str, list[str] | None]:
    console = bool(args.get("console", settings.console))
    data_format = str(args.get("data_format", settings.default_format))
    out_path = resolve_out_path(
        args, args["service"], args["action"], data_format, settings
    )
    csv_fieldnames = csv_fieldnames_from_args(args, settings)
    return console, data_format, out_path, csv_fieldnames


def payload_from_args(args: dict, excluded_keys: set[str]) -> dict:
    return {key: value for key, value in args.items() if key not in excluded_keys}


def resolve_placeholders_for_action(
    cp, api_catalog, args: dict, action: str
) -> list[str]:
    _action_def, _path, placeholders = cp.resolve_action(
        api_catalog, args["module"], args["service"], action, args
    )
    return placeholders


def payload_for_write_action(cp, api_catalog, args: dict, action: str):
    if "file" in args:
        return load_payload_file(args["file"])

    placeholders = set(resolve_placeholders_for_action(cp, api_catalog, args, action))
    excluded = set(RESERVED_ARGS) | placeholders
    return payload_from_args(args, excluded)


def query_params_for_action(cp, api_catalog, args: dict, action: str) -> dict:
    action_def = cp.get_action_definition(
        api_catalog, args["module"], args["service"], action
    )
    allowed = list(action_def.get("params") or [])
    params: dict[str, str | int | bool] = {}

    if action == "list":
        if "limit" in allowed:
            limit = int(args.get("limit", 25))
            if limit < 1 or limit > 1000:
                raise ValueError("--limit must be between 1 and 1000")
            params["limit"] = limit
        if "offset" in allowed:
            params["offset"] = int(args.get("offset", 0))
        if "sort" in allowed:
            params["sort"] = args.get("sort")
        if "filter" in allowed and args.get("filter") is not None:
            params["filter"] = args["filter"]
        if "calculate_count" in allowed and args.get("calculate_count") is not None:
            raw_value = args["calculate_count"]
            if isinstance(raw_value, str):
                params["calculate_count"] = raw_value.strip().lower() in {
                    "1",
                    "true",
                    "yes",
                    "on",
                }
            else:
                params["calculate_count"] = bool(raw_value)

    for name in allowed:
        if name in params:
            continue
        if name in args:
            params[name] = args[name]

    return params
