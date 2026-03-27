from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_ACCESS_LEVEL_SETS = [
    ["No Access", "Read", "Read, Write", "Read, Write, Delete"],
    ["No Access", "Read Only", "Full"],
    ["No Access", "Read Only"],
    ["No Access", "Allow Access"],
]
_ACCESS_SUFFIXES = [
    (" ".join(levels), levels)
    for levels in sorted(_ACCESS_LEVEL_SETS, key=len, reverse=True)
]
_STOPWORDS = {
    "access",
    "allow",
    "api",
    "can",
    "configure",
    "full",
    "legacy",
    "list",
    "manage",
    "manager",
    "no",
    "only",
    "operators",
    "perform",
    "policy",
    "privilege",
    "privileges",
    "read",
    "services",
    "system",
    "this",
    "through",
    "use",
    "users",
    "web",
    "with",
    "write",
}
_SYNONYMS = {
    "admins": "admin",
    "attributes": "attribute",
    "certificates": "certificate",
    "clients": "client",
    "devices": "device",
    "dictionary": "dictionary",
    "dictionaries": "dictionary",
    "endpoints": "endpoint",
    "events": "event",
    "groups": "group",
    "identities": "identity",
    "licenses": "license",
    "mappings": "mapping",
    "policies": "policy",
    "portals": "portal",
    "privileges": "privilege",
    "profiles": "profile",
    "roles": "role",
    "servers": "server",
    "services": "service",
    "settings": "setting",
    "users": "user",
}


@dataclass(frozen=True)
class ServicePrivilegeRule:
    module: str
    service: str
    privileges: tuple[str, ...]
    match: str = "any"
    source: str = "verified"


SERVICE_PRIVILEGE_RULES: tuple[ServicePrivilegeRule, ...] = (
    ServicePrivilegeRule(
        module="enforcementprofile",
        service="enforcement-profile",
        privileges=("cppm_enforcement_profile",),
    ),
    ServicePrivilegeRule(
        module="globalserverconfiguration",
        service="admin-privilege",
        privileges=("cppm_admin_privileges",),
    ),
    ServicePrivilegeRule(
        module="globalserverconfiguration",
        service="admin-user",
        privileges=("cppm_admin_users",),
    ),
    ServicePrivilegeRule(
        module="globalserverconfiguration",
        service="application-license",
        privileges=("cppm_licenses",),
    ),
    ServicePrivilegeRule(
        module="globalserverconfiguration",
        service="attribute",
        privileges=("cppm_attributes",),
    ),
    ServicePrivilegeRule(
        module="globalserverconfiguration",
        service="clearpass-portal",
        privileges=("cppm_clearpass_portal",),
    ),
    ServicePrivilegeRule(
        module="globalserverconfiguration",
        service="data-filter",
        privileges=("cppm_data_filters",),
    ),
    ServicePrivilegeRule(
        module="globalserverconfiguration",
        service="file-backup-server",
        privileges=("cppm_file_backup_server",),
    ),
    ServicePrivilegeRule(
        module="globalserverconfiguration",
        service="operator-profile",
        privileges=("auth_profiles",),
    ),
    ServicePrivilegeRule(
        module="globalserverconfiguration",
        service="policy-manager-zones",
        privileges=("cppm_server_policy_manager_zones",),
    ),
    ServicePrivilegeRule(
        module="globalserverconfiguration",
        service="snmp-trap-receiver",
        privileges=("cppm_snmp_trap_receivers",),
    ),
    ServicePrivilegeRule(
        module="identities",
        service="api-client",
        privileges=("api_clients",),
    ),
    ServicePrivilegeRule(
        module="identities",
        service="deny-listed-users",
        privileges=("cppm_deny_listed_users",),
    ),
    ServicePrivilegeRule(
        module="identities",
        service="device",
        privileges=("mac", "guest_users"),
        match="all",
    ),
    ServicePrivilegeRule(
        module="identities",
        service="guest",
        privileges=("guest_users",),
    ),
    ServicePrivilegeRule(
        module="identities",
        service="endpoint",
        privileges=("cppm_endpoints",),
    ),
    ServicePrivilegeRule(
        module="identities",
        service="external-account",
        privileges=("cppm_external_account",),
    ),
    ServicePrivilegeRule(
        module="identities",
        service="local-user",
        privileges=("cppm_local_users",),
    ),
    ServicePrivilegeRule(
        module="identities",
        service="static-host-list",
        privileges=("cppm_static_host_list",),
    ),
    ServicePrivilegeRule(
        module="localserverconfiguration",
        service="server",
        privileges=("platform",),
    ),
    ServicePrivilegeRule(
        module="logs",
        service="system-event",
        privileges=("cppm_system_events",),
    ),
    ServicePrivilegeRule(
        module="policyelements",
        service="application-dictionary",
        privileges=("cppm_application_dict",),
    ),
    ServicePrivilegeRule(
        module="policyelements",
        service="auth-source",
        privileges=("auth_config", "cppm_config"),
        match="all",
    ),
    ServicePrivilegeRule(
        module="policyelements",
        service="auth-method",
        privileges=("cppm_auth_methods",),
    ),
    ServicePrivilegeRule(
        module="policyelements",
        service="enforcement-policy",
        privileges=("cppm_enforcement_policy",),
    ),
    ServicePrivilegeRule(
        module="policyelements",
        service="network-device",
        privileges=("cppm_network_devices",),
    ),
    ServicePrivilegeRule(
        module="policyelements",
        service="network-device-group",
        privileges=("cppm_network_device_groups",),
    ),
    ServicePrivilegeRule(
        module="policyelements",
        service="posture-policy",
        privileges=("cppm_posture_policy",),
    ),
    ServicePrivilegeRule(
        module="policyelements",
        service="proxy-target",
        privileges=("cppm_network_proxy_targets",),
    ),
    ServicePrivilegeRule(
        module="policyelements",
        service="radius-dictionary",
        privileges=("cppm_radius_dict",),
    ),
    ServicePrivilegeRule(
        module="policyelements",
        service="radius-dynamic-authorization-template",
        privileges=("cppm_radius_dyn_autz_template",),
    ),
    ServicePrivilegeRule(
        module="policyelements",
        service="role",
        privileges=("cppm_roles",),
    ),
    ServicePrivilegeRule(
        module="policyelements",
        service="role-mapping",
        privileges=("cppm_role_mapping",),
    ),
    ServicePrivilegeRule(
        module="policyelements",
        service="service",
        privileges=("cppm_services",),
    ),
    ServicePrivilegeRule(
        module="policyelements",
        service="tacacs-service-dictionary",
        privileges=("cppm_tacacs_service_dict",),
    ),
)


def _strip_html_to_text(text: str) -> str:
    cleaned = html.unescape(text)
    cleaned = re.sub(r"(?is)<(script|style)\b[^>]*>.*?</\1>", "\n", cleaned)
    cleaned = re.sub(r"(?i)<br\s*/?>", "\n", cleaned)
    cleaned = re.sub(
        r"(?i)</?(p|div|tr|li|table|thead|tbody|ul|ol|h\d)\b[^>]*>",
        "\n",
        cleaned,
    )
    cleaned = re.sub(r"(?i)</?(td|th)\b[^>]*>", " ", cleaned)
    cleaned = re.sub(r"(?s)<[^>]+>", "", cleaned)
    return cleaned


def _normalize_space(value: str) -> str:
    return " ".join(value.replace("\t", " ").split())


def _is_description_line(line: str) -> bool:
    if not line:
        return False
    lowered = line.lower()
    return lowered.startswith("operators with") or lowered.startswith("select ")


def _line_is_section_heading(lines: list[str], index: int) -> bool:
    line = lines[index]
    if not line:
        return False
    if _is_description_line(line):
        return False
    if _parse_privilege_line(line) is not None:
        return False
    if index + 1 >= len(lines):
        return False

    next_line = lines[index + 1]
    return next_line.lower().startswith("select ")


def _parse_privilege_line(line: str) -> dict[str, Any] | None:
    normalized = _normalize_space(line)
    if not normalized:
        return None

    for suffix, levels in _ACCESS_SUFFIXES:
        if normalized.endswith(suffix):
            name = normalized[: -len(suffix)].strip()
            if not name:
                return None
            return {"name": name, "levels": list(levels)}
    return None


def parse_privilege_definitions(text: str) -> dict[str, Any]:
    source_type = "html" if "<" in text and ">" in text else "text"
    normalized_text = _strip_html_to_text(text) if source_type == "html" else text
    lines = [_normalize_space(line) for line in normalized_text.splitlines()]
    lines = [line for line in lines if line]

    sections: list[dict[str, Any]] = []
    privileges: list[dict[str, Any]] = []
    current_section: dict[str, Any] | None = None
    current_entry: dict[str, Any] | None = None

    for index, line in enumerate(lines):
        lowered = line.lower()
        parsed_privilege = _parse_privilege_line(line)
        if parsed_privilege is not None:
            if current_section is None:
                current_section = {"name": "Uncategorized", "description": None}
                sections.append(current_section)
            entry = {
                "section": current_section["name"],
                "name": parsed_privilege["name"],
                "levels": parsed_privilege["levels"],
                "description": None,
            }
            privileges.append(entry)
            current_entry = entry
            continue

        if lowered.startswith("operators with"):
            if current_entry is not None and not current_entry.get("description"):
                current_entry["description"] = line
            continue

        if lowered.startswith("select "):
            if current_entry is not None and not current_entry.get("description"):
                current_entry["description"] = line
            elif current_section is not None and not current_section.get("description"):
                current_section["description"] = line
            continue

        if _line_is_section_heading(lines, index):
            current_section = {"name": line, "description": None}
            sections.append(current_section)
            current_entry = None
            continue

        if current_entry is not None and not current_entry.get("description"):
            current_entry["description"] = line

    return {
        "source_type": "clearpass-privilege-definitions",
        "input_format": source_type,
        "sections": sections,
        "privileges": privileges,
    }


def _normalize_token(token: str) -> str:
    token = token.strip().lower()
    if not token:
        return ""
    token = _SYNONYMS.get(token, token)
    if token.endswith("ies") and len(token) > 3:
        token = token[:-3] + "y"
    elif token.endswith("s") and len(token) > 3 and not token.endswith("ss"):
        token = token[:-1]
    return _SYNONYMS.get(token, token)


def _tokenize(value: str) -> list[str]:
    tokens = [
        _normalize_token(part)
        for part in re.split(r"[^a-zA-Z0-9]+", value.lower())
        if part.strip()
    ]
    return [token for token in tokens if token and token not in _STOPWORDS]


def _unique_ordered(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _catalog_candidate_records(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    modules = catalog.get("modules") or {}
    records: list[dict[str, Any]] = []
    for module_name, services in modules.items():
        if not isinstance(services, dict):
            continue
        for service_name, service_entry in services.items():
            if not isinstance(service_entry, dict):
                continue
            actions = service_entry.get("actions") or {}
            action_paths: list[str] = []
            for action_def in actions.values():
                if not isinstance(action_def, dict):
                    continue
                for path in action_def.get("paths") or []:
                    if isinstance(path, str):
                        action_paths.append(path)
            records.append(
                {
                    "module": module_name,
                    "service": service_name,
                    "paths": _unique_ordered(action_paths),
                    "module_tokens": _tokenize(module_name),
                    "service_tokens": _tokenize(service_name),
                    "path_tokens": _tokenize(" ".join(action_paths)),
                }
            )
    return records


def _score_candidate(privilege: dict[str, Any], candidate: dict[str, Any]) -> int:
    privilege_tokens = _unique_ordered(
        _tokenize(privilege.get("name") or "")
        + _tokenize(privilege.get("description") or "")
    )
    if not privilege_tokens:
        return 0

    module_tokens = set(candidate["module_tokens"])
    service_tokens = set(candidate["service_tokens"])
    path_tokens = set(candidate["path_tokens"])

    score = 0
    for token in privilege_tokens:
        if token in service_tokens:
            score += 6
        if token in module_tokens:
            score += 4
        if token in path_tokens:
            score += 2

        if any(
            service_token.startswith(token) or token.startswith(service_token)
            for service_token in service_tokens
        ):
            score += 2
        if any(
            module_token.startswith(token) or token.startswith(module_token)
            for module_token in module_tokens
        ):
            score += 1

    combined_service = " ".join(candidate["service_tokens"])
    combined_privilege = " ".join(_tokenize(privilege.get("name") or ""))
    if combined_privilege and combined_privilege == combined_service:
        score += 10

    return score


def suggest_catalog_mappings(
    definitions: dict[str, Any], catalog: dict[str, Any], *, limit: int = 3
) -> dict[str, Any]:
    candidates = _catalog_candidate_records(catalog)
    suggestions: list[dict[str, Any]] = []

    for privilege in definitions.get("privileges", []) or []:
        ranked = sorted(
            (
                {
                    "module": candidate["module"],
                    "service": candidate["service"],
                    "score": _score_candidate(privilege, candidate),
                    "paths": candidate["paths"],
                }
                for candidate in candidates
            ),
            key=lambda item: (-item["score"], item["module"], item["service"]),
        )
        top_matches = [item for item in ranked if item["score"] > 0][: max(limit, 1)]
        suggestions.append(
            {
                "section": privilege.get("section"),
                "name": privilege.get("name"),
                "levels": privilege.get("levels") or [],
                "description": privilege.get("description"),
                "matches": top_matches,
            }
        )

    return {
        "source_type": "clearpass-privilege-suggestions",
        "catalog_modules": sorted((catalog.get("modules") or {}).keys()),
        "privileges": suggestions,
    }


def load_privilege_definitions(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    stripped = text.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        parsed = json.loads(text)
        if isinstance(parsed, dict) and parsed.get("source_type") in {
            "clearpass-privilege-definitions",
            "clearpass-privilege-suggestions",
        }:
            return parsed
    return parse_privilege_definitions(text)


def normalize_effective_privilege(value: str) -> dict[str, str]:
    raw = str(value).strip()
    access = "full"
    name = raw
    if raw.startswith("#"):
        access = "read-only"
        name = raw[1:].strip()
    elif raw.startswith("?"):
        access = "allowed"
        name = raw[1:].strip()
    return {"raw": raw, "name": name, "access": access}


def normalize_effective_privileges(values: Any) -> list[dict[str, str]]:
    if not isinstance(values, list):
        return []
    return [
        normalize_effective_privilege(value)
        for value in values
        if isinstance(value, str) and value.strip()
    ]


def service_privilege_rule_index() -> dict[tuple[str, str], ServicePrivilegeRule]:
    return {(rule.module, rule.service): rule for rule in SERVICE_PRIVILEGE_RULES}
