from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from netloom.core.config import RESERVED_ARGS, Settings
from netloom.io.files import load_payload_file

_LIST_QUERY_PARAMS = {"filter", "sort", "offset", "limit", "calculate_count"}
_FILTER_OPERATOR_ALIASES = {
    "$eq": "$eq",
    "eq": "$eq",
    "equals": "$eq",
    "$ne": "$ne",
    "ne": "$ne",
    "not-equals": "$ne",
    "$contains": "$contains",
    "contains": "$contains",
    "$in": "$in",
    "in": "$in",
    "$nin": "$nin",
    "nin": "$nin",
    "not-in": "$nin",
    "$gt": "$gt",
    "gt": "$gt",
    "$gte": "$gte",
    "gte": "$gte",
    "$lt": "$lt",
    "lt": "$lt",
    "$lte": "$lte",
    "lte": "$lte",
    "$exists": "$exists",
    "exists": "$exists",
}

_TEXT_CONTENT_MARKERS = (
    "json",
    "xml",
    "javascript",
    "yaml",
    "html",
    "csv",
    "x-www-form-urlencoded",
)
_CONTENT_TYPE_EXTENSIONS = {
    "application/x-pkcs12": "p12",
    "application/pkcs12": "p12",
    "application/x-pkcs7-certificates": "p7b",
    "application/pkix-cert": "cer",
    "application/x-x509-ca-cert": "cer",
    "application/x-pem-file": "pem",
    "application/pem-certificate-chain": "pem",
    "application/octet-stream": "bin",
    "application/zip": "zip",
    "application/gzip": "gz",
    "application/pdf": "pdf",
    "text/plain": "txt",
}
_RANDOM_PASSWORD_METHOD_ALIASES = {
    "1": "nwa_digits_password",
    "digits": "nwa_digits_password",
    "nwa_digits_password": "nwa_digits_password",
    "2": "nwa_letters_password",
    "letters": "nwa_letters_password",
    "nwa_letters_password": "nwa_letters_password",
    "3": "nwa_lettersdigits_password",
    "lettersdigits": "nwa_lettersdigits_password",
    "nwa_lettersdigits_password": "nwa_lettersdigits_password",
    "4": "nwa_words_password",
    "words": "nwa_words_password",
    "nwa_words_password": "nwa_words_password",
    "5": "nwa_alnum_password",
    "alnum": "nwa_alnum_password",
    "nwa_alnum_password": "nwa_alnum_password",
    "6": "nwa_complex_password",
    "complex": "nwa_complex_password",
    "nwa_complex_password": "nwa_complex_password",
    "7": "nwa_strong_password",
    "strong": "nwa_strong_password",
    "nwa_strong_password": "nwa_strong_password",
}


def _normalize_content_type(value: str | None) -> str:
    return (value or "").split(";", 1)[0].strip().lower()


def _looks_like_json_filter(raw: str) -> bool:
    stripped = raw.lstrip()
    return stripped.startswith("{") or stripped.startswith("[")


def _coerce_filter_scalar(raw: str):
    stripped = raw.strip()
    if stripped == "":
        return ""

    lowered = stripped.lower()
    if lowered in {"true", "false", "null"}:
        return json.loads(lowered)

    try:
        if stripped[0] in {'"', "["} or stripped[0].isdigit() or stripped[0] == "-":
            return json.loads(stripped)
    except (IndexError, json.JSONDecodeError):
        return stripped

    return stripped


def normalize_filter_value(raw):
    if not isinstance(raw, str):
        return raw

    stripped = raw.strip()
    if stripped == "" or _looks_like_json_filter(stripped):
        return raw

    parts = stripped.split(":", 2)
    if len(parts) != 3:
        raise ValueError(
            "Unsupported --filter syntax. Use JSON like "
            '--filter=\'{"key":{"$eq":"value"}}\' or shorthand like '
            "--filter=key:equals:value."
        )

    field, operator_raw, value_raw = (part.strip() for part in parts)
    if not field or not operator_raw:
        raise ValueError(
            "Shorthand --filter requires field, operator, and value in the form "
            "--filter=key:operator:value."
        )

    operator = _FILTER_OPERATOR_ALIASES.get(operator_raw.lower())
    if operator is None:
        supported = ", ".join(
            [
                "equals",
                "not-equals",
                "contains",
                "in",
                "not-in",
                "gt",
                "gte",
                "lt",
                "lte",
                "exists",
            ]
        )
        raise ValueError(
            f"Unsupported filter operator '{operator_raw}'. "
            f"Supported shorthand operators: {supported}"
        )

    if operator in {"$in", "$nin"}:
        value = [
            _coerce_filter_scalar(part)
            for part in value_raw.split(",")
            if part.strip() != ""
        ]
        if not value:
            raise ValueError(
                f"Filter operator '{operator_raw}' requires at least one value."
            )
    else:
        value = _coerce_filter_scalar(value_raw)

    if operator == "$exists":
        if not isinstance(value, bool):
            raise ValueError(
                "Filter operator 'exists' requires a boolean value: true or false."
            )

    return json.dumps({field: {operator: value}}, ensure_ascii=False)


def _is_binary_content_type(content_type: str | None) -> bool:
    parsed = _normalize_content_type(content_type)
    if not parsed:
        return False
    if parsed.startswith("text/"):
        return False
    return not any(marker in parsed for marker in _TEXT_CONTENT_MARKERS)


def action_response_content_types(action_def: dict | None) -> list[str]:
    if not isinstance(action_def, dict):
        return []
    return [
        _normalize_content_type(str(item))
        for item in action_def.get("response_content_types", []) or []
        if isinstance(item, str) and _normalize_content_type(item)
    ]


def action_prefers_raw_output(action_def: dict | None) -> bool:
    content_types = action_response_content_types(action_def)
    return bool(content_types) and all(
        _is_binary_content_type(content_type) for content_type in content_types
    )


def _extension_for_content_type(content_type: str | None) -> str | None:
    return _CONTENT_TYPE_EXTENSIONS.get(_normalize_content_type(content_type))


def _timestamp_token() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S-%f")


def resolve_out_path(
    args: dict,
    service: str,
    action: str,
    data_format: str,
    settings: Settings,
    *,
    action_def: dict | None = None,
    response_meta=None,
) -> str:
    out_arg = args.get("out")
    if out_arg:
        return str(Path(out_arg))

    if data_format == "raw" and response_meta is not None:
        filename = getattr(response_meta, "filename", None)
        if filename:
            return str(settings.paths.response_dir / Path(str(filename)).name)

    base = service.replace("-", "_")
    stem = f"{base}_{action}_{_timestamp_token()}"
    extension = data_format
    if data_format == "raw":
        content_type = None
        if response_meta is not None:
            content_type = getattr(response_meta, "content_type", None)
        if not content_type:
            action_types = action_response_content_types(action_def)
            content_type = action_types[0] if action_types else None
        extension = _extension_for_content_type(content_type) or "bin"
    return str(settings.paths.response_dir / f"{stem}.{extension}")


def csv_fieldnames_from_args(args: dict, settings: Settings) -> list[str] | None:
    csv_fieldnames = args.get("csv_fieldnames", settings.default_csv_fieldnames)
    if isinstance(csv_fieldnames, str):
        csv_fieldnames = [
            part.strip() for part in csv_fieldnames.split(",") if part.strip()
        ]
    return csv_fieldnames


def output_settings(
    args: dict,
    settings: Settings,
    *,
    action_def: dict | None = None,
    response_meta=None,
) -> tuple[bool, str, str, list[str] | None]:
    console = bool(args.get("console", settings.console))
    if response_meta is not None and getattr(response_meta, "is_binary", False):
        data_format = "raw"
    elif "data_format" in args:
        data_format = str(args["data_format"])
    elif action_prefers_raw_output(action_def):
        data_format = "raw"
    else:
        data_format = settings.default_format
    out_path = resolve_out_path(
        args,
        args["service"],
        args["action"],
        data_format,
        settings,
        action_def=action_def,
        response_meta=response_meta,
    )
    csv_fieldnames = csv_fieldnames_from_args(args, settings)
    return console, data_format, out_path, csv_fieldnames


def _normalize_random_password_method(value):
    if not isinstance(value, str):
        return value
    normalized = value.strip().lower()
    return _RANDOM_PASSWORD_METHOD_ALIASES.get(normalized, value)


def normalize_special_arg_aliases(args: dict) -> dict:
    if (
        args.get("module") != "toolsandutilities"
        or args.get("service") != "random-password"
        or args.get("action") != "add"
        or "random_password_method" not in args
    ):
        return args

    normalized_args = dict(args)
    normalized_args["random_password_method"] = _normalize_random_password_method(
        args["random_password_method"]
    )
    return normalized_args


def payload_from_args(args: dict, excluded_keys: set[str]) -> dict:
    normalized_args = normalize_special_arg_aliases(args)
    return {
        key: value for key, value in normalized_args.items() if key not in excluded_keys
    }


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


def normalize_file_payload_for_action(
    cp, api_catalog, args: dict, action: str, payload: dict
) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("File payload items must be JSON objects.")

    action_def = cp.get_action_definition(
        api_catalog, args["module"], args["service"], action
    )
    placeholders = set(resolve_placeholders_for_action(cp, api_catalog, args, action))

    body_fields = [
        {
            "name": str(field.get("name")),
            "required": bool(field.get("required")),
        }
        for field in action_def.get("body_fields", []) or []
        if isinstance(field, dict) and isinstance(field.get("name"), str)
    ]
    if body_fields:
        allowed_fields = {field["name"] for field in body_fields}
        required_fields = {
            field["name"] for field in body_fields if field.get("required")
        }
    else:
        params = {
            str(name)
            for name in action_def.get("params", []) or []
            if isinstance(name, str)
        }
        filtered_params = params - placeholders - _LIST_QUERY_PARAMS
        allowed_fields = filtered_params or None
        required_fields: set[str] = set()

    excluded_fields = set(placeholders)
    if action == "add":
        excluded_fields.add("id")

    if allowed_fields is None:
        return {
            key: value for key, value in payload.items() if key not in excluded_fields
        }

    normalized = {
        key: value
        for key, value in payload.items()
        if key in allowed_fields and key not in excluded_fields
    }
    return {
        key: value
        for key, value in normalized.items()
        if key in required_fields or value not in (None, {}, [])
    }


def query_params_for_action(cp, api_catalog, args: dict, action: str) -> dict:
    normalized_args = normalize_special_arg_aliases(args)
    action_def = cp.get_action_definition(
        api_catalog, normalized_args["module"], normalized_args["service"], action
    )
    allowed = list(action_def.get("params") or [])
    params: dict[str, str | int | bool] = {}

    if action == "list":
        if "limit" in allowed:
            limit = int(normalized_args.get("limit", 25))
            if limit < 1 or limit > 1000:
                raise ValueError("--limit must be between 1 and 1000")
            params["limit"] = limit
        if "offset" in allowed:
            params["offset"] = int(normalized_args.get("offset", 0))
        if "sort" in allowed:
            params["sort"] = normalized_args.get("sort")
        if "filter" in allowed and normalized_args.get("filter") is not None:
            params["filter"] = normalize_filter_value(normalized_args["filter"])
        if (
            "calculate_count" in allowed
            and normalized_args.get("calculate_count") is not None
        ):
            raw_value = normalized_args["calculate_count"]
            if isinstance(raw_value, str):
                enabled = raw_value.strip().lower() in {"1", "true", "yes", "on"}
            else:
                enabled = bool(raw_value)
            params["calculate_count"] = "true" if enabled else "false"

    for name in allowed:
        if name in params:
            continue
        if name in normalized_args:
            params[name] = normalized_args[name]

    return params
