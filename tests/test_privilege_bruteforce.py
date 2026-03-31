from netloom.plugins.clearpass.privilege_bruteforce import (
    build_bruteforce_candidate_overrides,
    parse_admin_privileges,
    parse_unresolved_services,
)


def test_parse_admin_privileges_reads_json_payload_with_log_prefix():
    raw = """
2026-03-30 16:08:35 | INFO | netloom.cli.main | Connecting
{
  "privileges": [
    "#mdps_view_certificate",
    "cppm_nat_pool",
    "guestmanager"
  ]
}
"""

    assert parse_admin_privileges(raw) == [
        "#mdps_view_certificate",
        "cppm_nat_pool",
        "guestmanager",
    ]


def test_parse_unresolved_services_reads_planned_features_section():
    raw = """
## Current Priorities

Current unmapped retained services by module:

#### `endpointvisibility` (`2`)
- `windows-hotfix`
- `settings`

#### `guestconfiguration` (`1`)
- `pass`

## Something Else
"""

    assert parse_unresolved_services(raw) == [
        ("endpointvisibility", "windows-hotfix"),
        ("endpointvisibility", "settings"),
        ("guestconfiguration", "pass"),
    ]


def test_build_bruteforce_candidate_overrides_prefers_disciplined_service_guesses():
    unresolved_services = [
        ("enforcementprofile", "nat-pool"),
        ("endpointvisibility", "windows-hotfix"),
        ("guestconfiguration", "pass"),
        ("globalserverconfiguration", "messaging-setup"),
        ("sessioncontrol", "active-session"),
    ]
    admin_privileges = [
        "cppm_nat_pool",
        "cppm_windows_hotfix",
        "pass_index",
        "pass_config",
        "pass_template",
        "cppm_messaging_setup",
        "smtp_config",
        "sms_setup",
        "smtp_send",
        "cppm_mac_active_session",
    ]

    result = build_bruteforce_candidate_overrides(
        unresolved_services,
        admin_privileges,
        max_single_candidates=5,
    )

    assert result["enforcementprofile/nat-pool"][0] == "cppm_nat_pool"
    assert result["endpointvisibility/windows-hotfix"][0] == "cppm_windows_hotfix"
    assert result["guestconfiguration/pass"][:3] == [
        ["pass_index", "pass_config"],
        ["pass_index", "pass_template"],
        ["pass_config", "pass_template"],
    ]
    assert "pass_index" in result["guestconfiguration/pass"]
    assert result["globalserverconfiguration/messaging-setup"][:3] == [
        ["cppm_messaging_setup", "smtp_config"],
        ["cppm_messaging_setup", "sms_setup"],
        ["smtp_config", "sms_setup"],
    ]
    assert "cppm_messaging_setup" in result["globalserverconfiguration/messaging-setup"]
    assert result["sessioncontrol/active-session"][0] == "cppm_mac_active_session"
