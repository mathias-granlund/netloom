from __future__ import annotations

import json
from typing import Any

import requests

from arapy.core.config import (
    SECRET_FIELDS,
    Settings,
    list_profiles,
    load_settings_for_profile,
)
from arapy.core.resolver import normalize_file_payload_for_action, query_params_for_action
from arapy.io.output import sanitize_secrets, should_mask_secrets, write_value_to_file

VALID_CONFLICT_MODES = {"fail", "skip", "update", "replace"}
VALID_MATCH_MODES = {"auto", "name", "id"}
_SECRET_PAYLOAD_FIELDS = ("radius_secret", "tacacs_secret")
_NETWORK_DEVICE_SNMP_FIELDS = ("snmp_read", "snmp_write")


def _copy_item_label(item: dict[str, Any]) -> str:
    if item.get("name") not in (None, ""):
        return str(item["name"])
    if item.get("id") not in (None, ""):
        return str(item["id"])
    return "<unknown>"


def _extract_items(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        embedded = value.get("_embedded")
        if isinstance(embedded, dict):
            items = embedded.get("items")
            if isinstance(items, list):
                return [item for item in items if isinstance(item, dict)]
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _has_action(api_catalog: dict, module: str, service: str, action: str) -> bool:
    return (
        action
        in (((api_catalog.get("modules") or {}).get(module) or {}).get(service) or {}).get(
            "actions", {}
        )
    )


def _service_args(module: str, service: str, action: str, **extra) -> dict[str, Any]:
    return {
        "module": module,
        "service": service,
        "action": action,
        **{key: value for key, value in extra.items() if value is not None},
    }


def _is_not_found(exc: requests.HTTPError) -> bool:
    response = getattr(exc, "response", None)
    return getattr(response, "status_code", None) == 404


def _load_catalog(catalog_loader, cp, token: str, settings: Settings) -> dict:
    try:
        return catalog_loader(cp, token=token, force_refresh=False, settings=settings)
    except TypeError as exc:
        if "force_refresh" not in str(exc):
            raise
        return catalog_loader(cp, token=token, settings=settings)


def _fetch_source_items(
    cp, token: str, api_catalog: dict, module: str, service: str, args: dict[str, Any]
) -> list[dict[str, Any]]:
    if args.get("id") not in (None, "") or args.get("name") not in (None, ""):
        get_args = _service_args(
            module,
            service,
            "get",
            id=args.get("id"),
            name=args.get("name"),
        )
        params = query_params_for_action(cp, api_catalog, get_args, "get")
        result = cp.get(api_catalog, token, get_args, params=params or None)
        return _extract_items(result)

    list_args = _service_args(
        module,
        service,
        "list",
        filter=args.get("filter"),
        limit=args.get("limit"),
        offset=args.get("offset"),
        sort=args.get("sort"),
        calculate_count=args.get("calculate_count"),
    )
    params = query_params_for_action(cp, api_catalog, list_args, "list")
    result = cp.list(api_catalog, token, list_args, params=params or None)
    return _extract_items(result)


def _fetch_target_by_name(
    cp, token: str, api_catalog: dict, module: str, service: str, name: str
) -> dict[str, Any] | None:
    if _has_action(api_catalog, module, service, "get"):
        get_args = _service_args(module, service, "get", name=name)
        try:
            params = query_params_for_action(cp, api_catalog, get_args, "get")
            result = cp.get(api_catalog, token, get_args, params=params or None)
            items = _extract_items(result)
            return items[0] if items else None
        except (ValueError, KeyError):
            pass
        except requests.HTTPError as exc:
            if not _is_not_found(exc):
                raise

    if not _has_action(api_catalog, module, service, "list"):
        return None

    list_args = _service_args(
        module,
        service,
        "list",
        filter=json.dumps({"name": name}),
        limit="1",
    )
    params = query_params_for_action(cp, api_catalog, list_args, "list")
    result = cp.list(api_catalog, token, list_args, params=params or None)
    for item in _extract_items(result):
        if item.get("name") == name:
            return item
    return None


def _fetch_target_by_id(
    cp, token: str, api_catalog: dict, module: str, service: str, item_id: Any
) -> dict[str, Any] | None:
    if not _has_action(api_catalog, module, service, "get"):
        return None

    get_args = _service_args(module, service, "get", id=item_id)
    try:
        params = query_params_for_action(cp, api_catalog, get_args, "get")
        result = cp.get(api_catalog, token, get_args, params=params or None)
        items = _extract_items(result)
        return items[0] if items else None
    except requests.HTTPError as exc:
        if _is_not_found(exc):
            return None
        raise


def _resolve_match(
    cp,
    token: str,
    api_catalog: dict,
    module: str,
    service: str,
    item: dict[str, Any],
    match_mode: str,
) -> tuple[dict[str, Any] | None, str | None]:
    if match_mode in {"auto", "name"} and item.get("name") not in (None, ""):
        match = _fetch_target_by_name(
            cp, token, api_catalog, module, service, str(item["name"])
        )
        if match is not None or match_mode == "name":
            return match, "name"

    if match_mode in {"auto", "id"} and item.get("id") not in (None, ""):
        match = _fetch_target_by_id(cp, token, api_catalog, module, service, item["id"])
        if match is not None or match_mode == "id":
            return match, "id"

    return None, None


def _restore_secret_fields(result, payload, *, mask_secrets: bool):
    if mask_secrets:
        return result

    if isinstance(result, dict) and isinstance(payload, dict):
        restored = dict(result)
        for field in SECRET_FIELDS:
            incoming = payload.get(field)
            if incoming not in (None, "") and restored.get(field) in (None, ""):
                restored[field] = incoming
        return restored

    return result


def _drop_blank_secret_fields(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if key not in _SECRET_PAYLOAD_FIELDS or value not in (None, "")
    }


def _normalize_copy_payload(
    cp, api_catalog: dict, args: dict[str, Any], action: str, item: dict[str, Any]
) -> dict[str, Any]:
    payload = normalize_file_payload_for_action(cp, api_catalog, args, action, item)
    return _drop_blank_secret_fields(payload)


def _network_device_credentials_present(payload: dict[str, Any]) -> bool:
    for field in _SECRET_PAYLOAD_FIELDS:
        if payload.get(field) not in (None, ""):
            return True
    for field in _NETWORK_DEVICE_SNMP_FIELDS:
        if payload.get(field) not in (None, {}, []):
            return True
    return False


def _preflight_error_for_payload(
    module: str, service: str, action_name: str, payload: dict[str, Any] | None
) -> str | None:
    if (
        action_name == "create"
        and module == "policyelements"
        and service == "network-device"
        and isinstance(payload, dict)
        and not _network_device_credentials_present(payload)
    ):
        return (
            "source response did not include usable RADIUS, TACACS+, or SNMP "
            "credentials for network-device create"
        )
    return None


def _emit_summary(report: dict[str, Any]) -> None:
    mode = "Dry run" if report.get("dry_run") else "Copy completed"
    summary = report["summary"]
    print(mode)
    print(f"Source profile: {report['source_profile']}")
    print(f"Target profile: {report['target_profile']}")
    print(f"Service: {report['module']} {report['service']}")
    print(f"Selected: {summary['selected']}")
    print(f"Created: {summary['created']}")
    print(f"Updated: {summary['updated']}")
    print(f"Replaced: {summary['replaced']}")
    print(f"Skipped: {summary['skipped']}")
    print(f"Failed: {summary['failed']}")
    failed_items = [item for item in report.get("items", []) if item.get("status") == "failed"]
    if failed_items:
        print("Failure reasons:")
        for item in failed_items[:10]:
            print(f"- {item.get('label', '<unknown>')}: {item.get('reason', 'unknown error')}")


def _validate_copy_args(args: dict[str, Any]) -> None:
    copy_module = args.get("copy_module")
    copy_service = args.get("copy_service")
    source_profile = args.get("from")
    target_profile = args.get("to")

    if not copy_module or not copy_service:
        raise ValueError("Usage: arapy copy <module> <service> --from=... --to=...")

    if not source_profile or not target_profile:
        raise ValueError("--from and --to are required for copy")

    if source_profile == target_profile:
        raise ValueError("--from and --to must be different profiles")

    profiles = set(list_profiles())
    missing = [
        profile
        for profile in (str(source_profile), str(target_profile))
        if profile not in profiles
    ]
    if missing:
        raise ValueError(f"Unknown profile(s): {', '.join(sorted(missing))}")

    selectors = [
        args.get("id") not in (None, ""),
        args.get("name") not in (None, ""),
        bool(args.get("filter")),
        bool(args.get("all")),
    ]
    if sum(bool(value) for value in selectors) != 1:
        raise ValueError("Use exactly one selector: --id, --name, --filter, or --all")

    if args.get("id") not in (None, "") and any(
        args.get(name) not in (None, "", False)
        for name in ("filter", "all", "limit", "offset", "sort")
    ):
        raise ValueError("--id cannot be combined with list selectors")

    if args.get("name") not in (None, "") and any(
        args.get(name) not in (None, "", False)
        for name in ("filter", "all", "limit", "offset", "sort")
    ):
        raise ValueError("--name cannot be combined with list selectors")

    on_conflict = str(args.get("on_conflict", "fail"))
    if on_conflict not in VALID_CONFLICT_MODES:
        raise ValueError(
            "--on-conflict must be one of: fail, skip, update, replace"
        )

    match_by = str(args.get("match_by", "auto"))
    if match_by not in VALID_MATCH_MODES:
        raise ValueError("--match-by must be one of: auto, name, id")


def handle_copy_command(
    args: dict[str, Any],
    *,
    settings: Settings | None,
    build_client,
    resolve_auth_token,
    get_api_catalog,
) -> dict[str, Any]:
    _validate_copy_args(args)

    module = str(args["copy_module"])
    service = str(args["copy_service"])
    source_profile = str(args["from"])
    target_profile = str(args["to"])
    on_conflict = str(args.get("on_conflict", "fail"))
    match_by = str(args.get("match_by", "auto"))
    dry_run = bool(args.get("dry_run"))
    continue_on_error = bool(args.get("continue_on_error"))

    source_settings = load_settings_for_profile(source_profile)
    target_settings = load_settings_for_profile(target_profile)
    active_settings = settings or target_settings
    mask_secrets = should_mask_secrets(args, active_settings)

    source_cp = build_client(source_settings, mask_secrets=mask_secrets)
    source_token = resolve_auth_token(source_cp, source_settings)
    source_catalog = _load_catalog(
        get_api_catalog, source_cp, source_token, source_settings
    )

    target_cp = build_client(target_settings, mask_secrets=mask_secrets)
    target_token = resolve_auth_token(target_cp, target_settings)
    target_catalog = _load_catalog(
        get_api_catalog, target_cp, target_token, target_settings
    )

    source_items = _fetch_source_items(
        source_cp, source_token, source_catalog, module, service, args
    )
    if not source_items:
        raise ValueError("No source objects matched the requested selector")

    plan_items: list[dict[str, Any]] = []
    for item in source_items:
        label = _copy_item_label(item)
        target_match, resolved_match = _resolve_match(
            target_cp, target_token, target_catalog, module, service, item, match_by
        )

        if target_match is None:
            action_name = "create"
            action_args = _service_args(module, service, "add")
            payload = _normalize_copy_payload(
                target_cp, target_catalog, action_args, "add", item
            )
        elif on_conflict == "skip":
            action_name = "skip"
            payload = None
        elif on_conflict == "fail":
            action_name = "conflict"
            payload = None
        elif on_conflict == "update":
            action_name = "update"
            action_args = _service_args(
                module, service, "update", id=target_match.get("id")
            )
            payload = _normalize_copy_payload(
                target_cp, target_catalog, action_args, "update", item
            )
        else:
            action_name = "replace"
            action_args = _service_args(
                module, service, "replace", id=target_match.get("id")
            )
            payload = _normalize_copy_payload(
                target_cp, target_catalog, action_args, "replace", item
            )
        preflight_error = _preflight_error_for_payload(
            module, service, action_name, payload
        )

        plan_items.append(
            {
                "source_name": item.get("name"),
                "source_id": item.get("id"),
                "label": label,
                "match_by": resolved_match,
                "target_match": {
                    "id": target_match.get("id"),
                    "name": target_match.get("name"),
                }
                if isinstance(target_match, dict)
                else None,
                "action": action_name,
                "payload": payload,
                "reason": preflight_error,
            }
        )

    result_items: list[dict[str, Any]] = []
    if dry_run:
        for item in plan_items:
            result_items.append(
                {
                    **item,
                    "status": "failed" if item.get("reason") else "planned",
                    "reason": (
                        item.get("reason")
                        or (
                            None
                            if item["action"] != "conflict"
                            else "target object already exists"
                        )
                    ),
                }
            )
    else:
        for item in plan_items:
            action_name = item["action"]
            try:
                if item.get("reason"):
                    result_items.append({**item, "status": "failed"})
                    if not continue_on_error:
                        break
                elif action_name == "create":
                    request_args = _service_args(module, service, "add")
                    response = target_cp.add(
                        target_catalog, target_token, request_args, item["payload"]
                    )
                    response = _restore_secret_fields(
                        response, item["payload"], mask_secrets=mask_secrets
                    )
                    result_items.append(
                        {**item, "status": "success", "response": response}
                    )
                elif action_name == "update":
                    request_args = _service_args(
                        module,
                        service,
                        "update",
                        id=item["target_match"]["id"],
                    )
                    response = target_cp.update(
                        target_catalog, target_token, request_args, item["payload"]
                    )
                    response = _restore_secret_fields(
                        response, item["payload"], mask_secrets=mask_secrets
                    )
                    result_items.append(
                        {**item, "status": "success", "response": response}
                    )
                elif action_name == "replace":
                    request_args = _service_args(
                        module,
                        service,
                        "replace",
                        id=item["target_match"]["id"],
                    )
                    response = target_cp.replace(
                        target_catalog, target_token, request_args, item["payload"]
                    )
                    response = _restore_secret_fields(
                        response, item["payload"], mask_secrets=mask_secrets
                    )
                    result_items.append(
                        {**item, "status": "success", "response": response}
                    )
                elif action_name == "skip":
                    result_items.append({**item, "status": "skipped"})
                else:
                    result_items.append(
                        {
                            **item,
                            "status": "failed",
                            "reason": "target object already exists",
                        }
                    )
                    if not continue_on_error:
                        break
            except Exception as exc:  # pragma: no cover - exercised by integration behavior
                result_items.append({**item, "status": "failed", "reason": str(exc)})
                if not continue_on_error:
                    break

    summary = {
        "selected": len(source_items),
        "created": sum(
            1
            for item in result_items
            if item["action"] == "create" and item["status"] in {"success", "planned"}
        ),
        "updated": sum(
            1
            for item in result_items
            if item["action"] == "update" and item["status"] in {"success", "planned"}
        ),
        "replaced": sum(
            1
            for item in result_items
            if item["action"] == "replace"
            and item["status"] in {"success", "planned"}
        ),
        "skipped": sum(
            1
            for item in result_items
            if item["status"] == "skipped"
            or item["action"] == "skip"
            and item["status"] == "planned"
        ),
        "failed": sum(1 for item in result_items if item["status"] == "failed"),
    }

    report = {
        "mode": "copy",
        "module": module,
        "service": service,
        "source_profile": source_profile,
        "target_profile": target_profile,
        "dry_run": dry_run,
        "match_by": match_by,
        "on_conflict": on_conflict,
        "summary": summary,
        "items": result_items,
    }

    save_source = args.get("save_source")
    if save_source:
        write_value_to_file(
            source_items,
            save_source,
            data_format="json",
            mask_secrets=mask_secrets,
        )

    save_payload = args.get("save_payload")
    if save_payload:
        write_value_to_file(
            [item["payload"] for item in plan_items if item.get("payload") is not None],
            save_payload,
            data_format="json",
            mask_secrets=mask_secrets,
        )

    save_plan = args.get("save_plan")
    if save_plan:
        write_value_to_file(
            plan_items,
            save_plan,
            data_format="json",
            mask_secrets=mask_secrets,
        )

    out_path = args.get("out")
    if out_path:
        write_value_to_file(
            report,
            out_path,
            data_format="json",
            mask_secrets=mask_secrets,
        )

    _emit_summary(report)
    if args.get("console"):
        print(
            json.dumps(
                sanitize_secrets(report, mask_secrets=mask_secrets),
                indent=2,
                ensure_ascii=False,
            )
        )

    return report
