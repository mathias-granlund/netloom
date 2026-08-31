from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from netloom.plugins.clearpass.privilege_discovery import _candidate_keys
from netloom.plugins.clearpass.privileges import (
    SERVICE_PRIVILEGE_RULES,
    _tokenize,
    normalize_effective_privilege,
)

DEFAULT_PLANNED_FEATURES_FILE = "PLANNED_FEATURES.md"
DEFAULT_OUT_FILE = "clearpass_privilege_candidates_bruteforce.json"
SERVICE_SUFFIXES = (
    "-disable",
    "-enable",
    "-name-disable",
    "-name-enable",
    "-name",
    "-summary",
    "-details",
    "-message",
    "-notification",
    "-username",
    "-mac",
    "-ip",
    "-coa",
    "-disconnect",
    "-time-range",
    "-operating_system",
    "-start",
    "-stop",
)
MANUAL_SERVICE_CANDIDATES: dict[str, list[str | list[str]]] = {
    "certificateauthority/certificate-export": [
        ["#mdps_view_certificate", "#mdps_export_ca_key"],
        "#mdps_export_ca_key",
        "#mdps_export_private_key",
    ],
    "certificateauthority/certificate-import": ["mdps_csc_import"],
    "certificateauthority/certificate-new": [
        "mdps_create_csr",
        "mdps_issue_certificate",
        ["mdps_create_csr", "mdps_issue_certificate"],
        "mdps_create_ca",
        "mdps_ca",
        ["mdps_create_ca", "mdps_ca"],
    ],
    "certificateauthority/certificate-reject": ["mdps_ca"],
    "certificateauthority/certificate-request": ["mdps_create_csr"],
    "certificateauthority/certificate-revoke": ["mdps_revoke_certificate"],
    "certificateauthority/certificate-sign-request": ["mdps_issue_certificate"],
    "endpointvisibility/device-fingerprint": ["cppm_device_fingerprint"],
    "endpointvisibility/global-settings": ["cppm_onguard_global_settings"],
    "endpointvisibility/onguard-activity": ["cppm_on_guard_activity"],
    "endpointvisibility/onguard-activity-message": ["cppm_on_guard_activity"],
    "endpointvisibility/onguard-activity-notification": ["cppm_on_guard_activity"],
    "endpointvisibility/settings": ["cppm_onguard_settings"],
    "endpointvisibility/subnet-mapping": ["cppm_agentless_onguard_subnet_mapping"],
    "endpointvisibility/subnet-mapping-disable": [
        "cppm_agentless_onguard_subnet_mapping"
    ],
    "endpointvisibility/subnet-mapping-enable": [
        "cppm_agentless_onguard_subnet_mapping"
    ],
    "endpointvisibility/subnet-mapping-name-disable": [
        "cppm_agentless_onguard_subnet_mapping"
    ],
    "endpointvisibility/subnet-mapping-name-enable": [
        "cppm_agentless_onguard_subnet_mapping"
    ],
    "endpointvisibility/windows-hotfix": ["cppm_windows_hotfix"],
    "endpointvisibility/windows-hotfix-kbid-operating_system": ["cppm_windows_hotfix"],
    "enforcementprofile/policy-name": [
        "cppm_policy",
        "cppm_enforcement_policy",
        "cppm_enforcement_profile",
    ],
    "globalserverconfiguration/messaging-setup": [
        "cppm_messaging_setup",
        "smtp_config",
        "sms_setup",
        "smtp_send",
        ["cppm_messaging_setup", "smtp_config"],
        ["cppm_messaging_setup", "sms_setup"],
        ["smtp_config", "sms_setup"],
    ],
    "guestactions/sms": ["sms-send", "sms_setup"],
    "guestactions/smtp": ["smtp_send", "smtp_config", "smtp"],
    "guestconfiguration/authentication": [
        "auth_config",
        "auth_index",
        "auth_ldap",
    ],
    "guestconfiguration/guestmanager": ["guestmanager"],
    "guestconfiguration/pass": [
        "pass_index",
        "pass_config",
        "pass_template",
        "pass_cert_install",
        "pass_cert_view",
        ["pass_index", "pass_config"],
        ["pass_index", "pass_template"],
        ["pass_config", "pass_template"],
    ],
    "guestconfiguration/print": ["guest_print_list"],
    "guestconfiguration/weblogin": ["radius_weblogins"],
    "integrations/config": ["extension_config"],
    "integrations/log": ["extension_logs"],
    "integrations/reinstall": ["extension_control"],
    "integrations/restart": ["extension_control"],
    "integrations/start": ["extension_control"],
    "integrations/stop": ["extension_control"],
    "integrations/upgrade": ["extension_control"],
    "localserverconfiguration/ad-domain": ["cppm_ad_domain"],
    "logs/endpoint": ["cppm_endpoints"],
    "logs/endpoint-time-range": ["cppm_endpoints"],
    "sessioncontrol/active-session": ["cppm_mac_active_session"],
    "sessioncontrol/session-action": ["cppm_session_action"],
    "sessioncontrol/session-action-coa": ["cppm_session_action"],
    "sessioncontrol/session-action-coa-ip": ["cppm_session_action"],
    "sessioncontrol/session-action-coa-mac": ["cppm_session_action"],
    "sessioncontrol/session-action-coa-username": ["cppm_session_action"],
    "sessioncontrol/session-action-disconnect": ["cppm_session_action"],
    "sessioncontrol/session-action-disconnect-ip": ["cppm_session_action"],
    "sessioncontrol/session-action-disconnect-mac": ["cppm_session_action"],
    "sessioncontrol/session-action-disconnect-username": ["cppm_session_action"],
}


def _read_text(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def _extract_json_object(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    if not stripped:
        return None

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end <= start:
        return None

    try:
        parsed = json.loads(stripped[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def parse_admin_privileges(text: str) -> list[str]:
    parsed = _extract_json_object(text)
    if isinstance(parsed, dict):
        values = parsed.get("privileges")
        if isinstance(values, list):
            return [
                str(value).strip()
                for value in values
                if isinstance(value, str) and str(value).strip()
            ]

    privileges: list[str] = []
    quoted_pattern = re.compile(r'^\s*"([^"]+)"\s*,?\s*$')
    plain_pattern = re.compile(r"^[#?A-Za-z0-9][#?A-Za-z0-9_-]*$")
    for line in text.splitlines():
        stripped_line = line.strip()
        if not stripped_line:
            continue
        quoted = quoted_pattern.match(stripped_line)
        if quoted:
            privileges.append(quoted.group(1).strip())
            continue
        if plain_pattern.match(stripped_line):
            privileges.append(stripped_line)
    return _unique_ordered(privileges)


def parse_oauth_privileges(text: str) -> dict[str, dict[str, Any]]:
    parsed = _extract_json_object(text)
    if not isinstance(parsed, dict):
        return {}

    privileges = parsed.get("privileges")
    if not isinstance(privileges, dict):
        return {}

    flattened: dict[str, dict[str, Any]] = {}

    def add_entry(
        key: str,
        payload: dict[str, Any],
        *,
        domain_key: str | None = None,
        domain_payload: dict[str, Any] | None = None,
    ) -> None:
        entry = {
            "key": key,
            "type": payload.get("type"),
            "domain": payload.get("domain") or domain_key,
            "name": payload.get("name"),
            "desc": payload.get("desc"),
        }
        if isinstance(domain_payload, dict):
            entry["domain_name"] = domain_payload.get("name")
            entry["domain_desc"] = domain_payload.get("desc")
        flattened[key] = entry

    for key, payload in privileges.items():
        if not isinstance(key, str) or not isinstance(payload, dict):
            continue
        add_entry(key, payload)

    for domain_key, domain_payload in privileges.items():
        if not isinstance(domain_key, str) or not isinstance(domain_payload, dict):
            continue
        features = domain_payload.get("features")
        if not isinstance(features, dict):
            continue
        for feature_key, feature_payload in features.items():
            if not isinstance(feature_key, str) or not isinstance(
                feature_payload, dict
            ):
                continue
            add_entry(
                feature_key,
                feature_payload,
                domain_key=domain_key,
                domain_payload=domain_payload,
            )

    for entry in flattened.values():
        domain_key = entry.get("domain")
        if not isinstance(domain_key, str):
            continue
        domain_entry = flattened.get(domain_key)
        if not isinstance(domain_entry, dict):
            continue
        entry.setdefault("domain_name", domain_entry.get("name"))
        entry.setdefault("domain_desc", domain_entry.get("desc"))

    return flattened


def parse_unresolved_services(text: str) -> list[tuple[str, str]]:
    services: list[tuple[str, str]] = []
    in_section = False
    current_module: str | None = None
    heading_pattern = re.compile(r"^####\s+`([^`]+)`")
    bullet_pattern = re.compile(r"^-\s+`([^`]+)`\s*$")

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line.startswith("## ") and in_section:
            break
        if line.strip() == "Current unmapped retained services by module:":
            in_section = True
            continue
        if not in_section:
            continue

        heading = heading_pattern.match(line.strip())
        if heading:
            current_module = heading.group(1).strip()
            continue

        bullet = bullet_pattern.match(line.strip())
        if bullet and current_module:
            services.append((current_module, bullet.group(1).strip()))

    return services


def _unique_ordered(items: list[Any]) -> list[Any]:
    seen: set[Any] = set()
    out: list[Any] = []
    for item in items:
        marker = tuple(item) if isinstance(item, list) else item
        if marker in seen:
            continue
        seen.add(marker)
        out.append(item)
    return out


def _service_variants(service_name: str) -> list[str]:
    variants = [service_name]
    for suffix in SERVICE_SUFFIXES:
        if service_name.endswith(suffix):
            variants.append(service_name[: -len(suffix)])
    if "-" in service_name:
        variants.append(service_name.rsplit("-", 1)[0])
    return _unique_ordered([variant for variant in variants if variant])


def _token_overlap(left: list[str], right: list[str]) -> int:
    return len(set(left) & set(right))


def _prefix_overlap(left: list[str], right: list[str]) -> int:
    total = 0
    for left_token in left:
        for right_token in right:
            if left_token.startswith(right_token) or right_token.startswith(left_token):
                total += 1
    return total


def _service_similarity(target_service: str, known_service: str) -> int:
    target_tokens = _tokenize(target_service)
    known_tokens = _tokenize(known_service)
    score = _token_overlap(target_tokens, known_tokens) * 20
    score += _prefix_overlap(target_tokens, known_tokens) * 6
    for target_variant in _service_variants(target_service):
        for known_variant in _service_variants(known_service):
            if target_variant == known_variant:
                score += 40
            elif target_variant.startswith(known_variant) or known_variant.startswith(
                target_variant
            ):
                score += 16
    return score


def _candidate_records(
    admin_privileges: list[str],
    oauth_privileges: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    records_by_raw: dict[str, dict[str, Any]] = {}
    available_lookup = _available_key_lookup(admin_privileges)

    for raw in admin_privileges:
        normalized = normalize_effective_privilege(raw)
        name = normalized["name"]
        records_by_raw[raw] = {
            "raw": raw,
            "name": name,
            "tokens": _tokenize(name),
        }

    if oauth_privileges:
        for key, payload in oauth_privileges.items():
            if not isinstance(key, str) or not isinstance(payload, dict):
                continue
            resolved = _resolve_candidate_key(available_lookup, key)
            if not resolved:
                continue
            record = records_by_raw.setdefault(
                resolved,
                {
                    "raw": resolved,
                    "name": normalize_effective_privilege(resolved)["name"],
                    "tokens": [],
                },
            )
            metadata_text = " ".join(
                str(value).strip()
                for value in (
                    key,
                    payload.get("name"),
                    payload.get("desc"),
                    payload.get("domain"),
                    payload.get("domain_name"),
                    payload.get("domain_desc"),
                )
                if isinstance(value, str) and value.strip()
            )
            record["tokens"] = _unique_ordered(
                record["tokens"] + _tokenize(metadata_text)
            )

    return list(records_by_raw.values())


def _service_metadata_score(
    module_name: str,
    service_name: str,
    record: dict[str, Any],
) -> int:
    target_tokens = _tokenize(f"{module_name} {service_name}")
    score = _token_overlap(target_tokens, record["tokens"]) * 18
    score += _prefix_overlap(target_tokens, record["tokens"]) * 5

    record_token_set = set(record["tokens"])
    for variant in _service_variants(service_name):
        variant_tokens = _tokenize(variant)
        if variant_tokens and all(
            token in record_token_set for token in variant_tokens
        ):
            score += 24

    if record.get("name") and (
        record["name"] in service_name or service_name in record["name"]
    ):
        score += 24
    return score


def build_bruteforce_candidate_overrides(
    unresolved_services: list[tuple[str, str]],
    admin_privileges: list[str],
    *,
    oauth_privileges: dict[str, dict[str, Any]] | None = None,
    max_single_candidates: int = 8,
) -> dict[str, list[str | list[str]]]:
    available_lookup = _available_key_lookup(admin_privileges)
    candidate_records = _candidate_records(
        admin_privileges,
        oauth_privileges=oauth_privileges,
    )
    rules_by_module: dict[str, list[tuple[str, tuple[str, ...]]]] = {}
    for rule in SERVICE_PRIVILEGE_RULES:
        if not rule.privileges:
            continue
        rules_by_module.setdefault(rule.module, []).append(
            (rule.service, tuple(rule.privileges))
        )

    overrides: dict[str, list[str | list[str]]] = {}
    for module_name, service_name in unresolved_services:
        service_key = f"{module_name}/{service_name}"
        scores: dict[str, int] = {}
        ordered_candidates: list[str | list[str]] = []

        manual_candidates = MANUAL_SERVICE_CANDIDATES.get(service_key, [])
        for item in manual_candidates:
            if isinstance(item, str):
                resolved = _resolve_candidate_key(available_lookup, item)
                _add_candidate_score(scores, resolved, 200)
            elif isinstance(item, list):
                combo = [
                    resolved
                    for resolved in (
                        _resolve_candidate_key(available_lookup, part) for part in item
                    )
                    if resolved
                ]
                if len(combo) == len(item):
                    ordered_candidates.append(combo)

        for candidate_name in _candidate_keys(module_name, service_name):
            resolved = _resolve_candidate_key(available_lookup, candidate_name)
            _add_candidate_score(scores, resolved, 160)

        for known_service, privileges in rules_by_module.get(module_name, []):
            similarity = _service_similarity(service_name, known_service)
            if similarity <= 0:
                continue
            for privilege in privileges:
                resolved = _resolve_candidate_key(available_lookup, privilege)
                _add_candidate_score(scores, resolved, 80 + similarity)

        for record in candidate_records:
            score = _service_metadata_score(module_name, service_name, record)
            _add_candidate_score(scores, record["raw"], score)

        ranked_singles = sorted(
            scores.items(),
            key=lambda item: (-item[1], item[0]),
        )
        ordered_candidates.extend(
            candidate for candidate, _score in ranked_singles[:max_single_candidates]
        )

        ordered_candidates = _unique_ordered(ordered_candidates)
        if ordered_candidates:
            overrides[service_key] = ordered_candidates

    return overrides


def _available_key_lookup(admin_privileges: list[str]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for raw in admin_privileges:
        normalized = normalize_effective_privilege(raw)
        lookup.setdefault(raw, raw)
        lookup.setdefault(normalized["name"], raw)
    return lookup


def _resolve_candidate_key(
    available_lookup: dict[str, str], candidate_name: str
) -> str | None:
    return available_lookup.get(candidate_name.strip())


def _add_candidate_score(
    scores: dict[str, int],
    resolved_key: str | None,
    score: int,
) -> None:
    if not resolved_key or score <= 0:
        return
    scores[resolved_key] = max(scores.get(resolved_key, 0), score)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build disciplined ClearPass privilege brute-force candidates."
    )
    parser.add_argument(
        "--planned-features-file",
        default=DEFAULT_PLANNED_FEATURES_FILE,
        help=(
            "Markdown file containing the unresolved retained services "
            f"(default: .\\{DEFAULT_PLANNED_FEATURES_FILE})"
        ),
    )
    parser.add_argument(
        "--admin-privileges-file",
        required=True,
        help=(
            "Path to the admin privilege dump, or '-' to read it from stdin. "
            "The input may be raw lines or the JSON payload from "
            "'netloom apioperations privileges get'."
        ),
    )
    parser.add_argument(
        "--out",
        default=DEFAULT_OUT_FILE,
        help=f"Output JSON path (default: .\\{DEFAULT_OUT_FILE})",
    )
    parser.add_argument(
        "--oauth-privileges-file",
        default=None,
        help=(
            "Optional JSON file containing '/api/oauth/all-privileges' output. "
            "Both 'format=list' and 'format=tree' are supported, but "
            "'format=list' is recommended because it is flatter."
        ),
    )
    parser.add_argument(
        "--max-single-candidates",
        type=int,
        default=8,
        help="Maximum number of single-key candidates per service.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    unresolved_text = Path(args.planned_features_file).read_text(encoding="utf-8")
    admin_text = _read_text(args.admin_privileges_file)
    oauth_text = (
        _read_text(args.oauth_privileges_file) if args.oauth_privileges_file else ""
    )
    unresolved_services = parse_unresolved_services(unresolved_text)
    admin_privileges = parse_admin_privileges(admin_text)
    oauth_privileges = parse_oauth_privileges(oauth_text) if oauth_text else {}
    overrides = build_bruteforce_candidate_overrides(
        unresolved_services,
        admin_privileges,
        oauth_privileges=oauth_privileges,
        max_single_candidates=max(args.max_single_candidates, 1),
    )

    out_path = Path(args.out)
    out_path.write_text(json.dumps(overrides, indent=2), encoding="utf-8")
    print(
        "Wrote"
        f" {len(overrides)} service candidate sets using"
        f" {len(admin_privileges)} admin privilege keys"
        f" and {len(oauth_privileges)} OAuth privilege metadata entries"
        f" to {out_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
