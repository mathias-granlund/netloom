from __future__ import annotations

from pathlib import Path

from arapy.core.config import Settings, load_settings
from arapy.core.resolver import (
    output_settings,
    payload_for_write_action,
    payload_from_args,
    query_params_for_action,
)
from arapy.core.resolver import (
    resolve_out_path as _resolve_out_path,
)
from arapy.io.output import log_to_file, should_mask_secrets


def _settings_or_default(settings: Settings | None) -> Settings:
    return settings or load_settings()


def resolve_out_path(
    args: dict,
    service: str,
    action: str,
    data_format: str,
    settings: Settings | None = None,
) -> str:
    if args.get("out"):
        return str(Path(args["out"]))
    active_settings = _settings_or_default(settings)
    return _resolve_out_path(args, service, action, data_format, active_settings)


def payload_from_cli_args(args: dict, excluded_keys: set[str]) -> dict:
    return payload_from_args(args, excluded_keys)


def add_handler(cp, token, api_catalog, args, settings: Settings | None = None):
    active_settings = _settings_or_default(settings)
    action_def = cp.get_action_definition(
        api_catalog, args["module"], args["service"], "add"
    )
    mask_secrets = should_mask_secrets(args, active_settings)
    payload = payload_for_write_action(cp, api_catalog, args, "add")

    if isinstance(payload, list):
        result = [
            cp.add(api_catalog, token, {**args, **item}, item) for item in payload
        ]
    else:
        result = cp.add(api_catalog, token, args, payload)

    console, data_format, out_path, csv_fieldnames = output_settings(
        args,
        active_settings,
        action_def=action_def,
        response_meta=getattr(cp, "last_response_meta", None),
    )
    return log_to_file(
        result,
        filename=out_path,
        data_format=data_format,
        csv_fieldnames=csv_fieldnames,
        also_console=console,
        mask_secrets=mask_secrets,
    )


def delete_handler(cp, token, api_catalog, args, settings: Settings | None = None):
    active_settings = _settings_or_default(settings)
    action_def = cp.get_action_definition(
        api_catalog, args["module"], args["service"], "delete"
    )
    mask_secrets = should_mask_secrets(args, active_settings)
    params = query_params_for_action(cp, api_catalog, args, "delete")
    result = cp.delete(api_catalog, token, args, params=params or None)
    console, data_format, out_path, csv_fieldnames = output_settings(
        args,
        active_settings,
        action_def=action_def,
        response_meta=getattr(cp, "last_response_meta", None),
    )
    return log_to_file(
        result,
        filename=out_path,
        data_format=data_format,
        csv_fieldnames=csv_fieldnames,
        also_console=console,
        mask_secrets=mask_secrets,
    )


def get_handler(cp, token, api_catalog, args, settings: Settings | None = None):
    active_settings = settings or load_settings()
    mask_secrets = should_mask_secrets(args, active_settings)

    if args.get("all"):
        action_name = "list"
        params = query_params_for_action(cp, api_catalog, args, "list")
        result = cp.list(api_catalog, token, args, params=params or None)
    else:
        action_name = "get"
        params = query_params_for_action(cp, api_catalog, args, "get")
        result = cp.get(api_catalog, token, args, params=params or None)

    action_def = cp.get_action_definition(
        api_catalog, args["module"], args["service"], action_name
    )
    console, data_format, out_path, csv_fieldnames = output_settings(
        args,
        active_settings,
        action_def=action_def,
        response_meta=getattr(cp, "last_response_meta", None),
    )
    return log_to_file(
        result,
        filename=out_path,
        data_format=data_format,
        csv_fieldnames=csv_fieldnames,
        also_console=console,
        mask_secrets=mask_secrets,
    )


def list_handler(cp, token, api_catalog, args, settings: Settings | None = None):
    alias_args = dict(args)
    alias_args["all"] = True
    alias_args["action"] = "list"
    return get_handler(cp, token, api_catalog, alias_args, settings=settings)


def replace_handler(cp, token, api_catalog, args, settings: Settings | None = None):
    active_settings = _settings_or_default(settings)
    action_def = cp.get_action_definition(
        api_catalog, args["module"], args["service"], "replace"
    )
    mask_secrets = should_mask_secrets(args, active_settings)
    payload = payload_for_write_action(cp, api_catalog, args, "replace")

    if isinstance(payload, list):
        result = [
            cp.replace(api_catalog, token, {**args, **item}, item) for item in payload
        ]
    else:
        result = cp.replace(api_catalog, token, args, payload)

    console, data_format, out_path, csv_fieldnames = output_settings(
        args,
        active_settings,
        action_def=action_def,
        response_meta=getattr(cp, "last_response_meta", None),
    )
    return log_to_file(
        result,
        filename=out_path,
        data_format=data_format,
        csv_fieldnames=csv_fieldnames,
        also_console=console,
        mask_secrets=mask_secrets,
    )


def update_handler(cp, token, api_catalog, args, settings: Settings | None = None):
    active_settings = _settings_or_default(settings)
    action_def = cp.get_action_definition(
        api_catalog, args["module"], args["service"], "update"
    )
    mask_secrets = should_mask_secrets(args, active_settings)
    payload = payload_for_write_action(cp, api_catalog, args, "update")

    if isinstance(payload, list):
        result = [
            cp.update(api_catalog, token, {**args, **item}, item) for item in payload
        ]
    else:
        result = cp.update(api_catalog, token, args, payload)

    console, data_format, out_path, csv_fieldnames = output_settings(
        args,
        active_settings,
        action_def=action_def,
        response_meta=getattr(cp, "last_response_meta", None),
    )
    return log_to_file(
        result,
        filename=out_path,
        data_format=data_format,
        csv_fieldnames=csv_fieldnames,
        also_console=console,
        mask_secrets=mask_secrets,
    )


ACTIONS = {
    "add": add_handler,
    "delete": delete_handler,
    "get": get_handler,
    "list": list_handler,
    "replace": replace_handler,
    "update": update_handler,
}

__all__ = [
    "ACTIONS",
    "add_handler",
    "delete_handler",
    "get_handler",
    "list_handler",
    "payload_from_args",
    "payload_from_cli_args",
    "query_params_for_action",
    "replace_handler",
    "resolve_out_path",
    "update_handler",
]
