from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from netloom.core.config import SECRET_FIELDS
from netloom.core.resolver import normalize_file_payload_for_action

_SECRET_PAYLOAD_FIELDS = ("radius_secret", "tacacs_secret")
_NETWORK_DEVICE_SNMP_FIELDS = ("snmp_read", "snmp_write")
_DIFF_IGNORE_FIELDS = {
    "id",
    "uuid",
    "_links",
    "links",
    "link",
    "_embedded",
    "created",
    "created_at",
    "updated",
    "updated_at",
    "last_updated",
    "last_modified",
    "modified",
    "modified_by",
    "updated_by",
    "created_by",
    "revision",
    "_revision",
    "revision_id",
    "etag",
    "_etag",
    "change_of_authorization",
}
_MASKED_SECRET_VALUES = {"", "********", "******", "*****", "<hidden>", "<masked>"}


def _is_masked_secret_placeholder(key: str, value: Any) -> bool:
    if not isinstance(value, str):
        return False
    key_text = str(key).lower()
    if "secret" not in key_text and "password" not in key_text:
        return False
    return value.strip().lower() in _MASKED_SECRET_VALUES


def restore_secret_fields(result, payload, *, mask_secrets: bool):
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


def normalize_copy_payload(
    cp, api_catalog: dict, args: dict[str, Any], action: str, item: dict[str, Any]
) -> dict[str, Any]:
    payload = normalize_file_payload_for_action(cp, api_catalog, args, action, item)
    return _drop_blank_secret_fields(payload)


def normalize_diff_item(module: str, service: str, item: Any) -> Any:
    del module, service

    if isinstance(item, Mapping):
        normalized: dict[str, Any] = {}
        for key, value in item.items():
            key_text = str(key)
            if key_text in _DIFF_IGNORE_FIELDS or key_text in SECRET_FIELDS:
                continue
            if _is_masked_secret_placeholder(key_text, value):
                continue
            child = normalize_diff_item("", "", value)
            if child in (None, {}, []):
                continue
            normalized[key_text] = child
        return normalized

    if isinstance(item, list):
        normalized_items = [normalize_diff_item("", "", value) for value in item]
        return [value for value in normalized_items if value not in (None, {}, [])]

    return item


def _network_device_credentials_present(payload: dict[str, Any]) -> bool:
    for field in _SECRET_PAYLOAD_FIELDS:
        if payload.get(field) not in (None, ""):
            return True
    for field in _NETWORK_DEVICE_SNMP_FIELDS:
        if payload.get(field) not in (None, {}, []):
            return True
    return False


def preflight_error_for_payload(
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
