from netloom.plugins.clearpass.privilege_bruteforce import (
    build_bruteforce_candidate_overrides,
    parse_admin_privileges,
    parse_oauth_privileges,
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


def test_parse_oauth_privileges_supports_list_and_tree_formats():
    list_payload = """
{
  "privileges": {
    "cppm_config": {
      "type": "domain",
      "name": "Policy Manager",
      "desc": "Select operator permissions for Policy Manager"
    },
    "cppm_nat_pool": {
      "type": "rwd",
      "domain": "cppm_config",
      "name": "Enforcement Profile - NAT Pool",
      "desc": "Manage Enforcement Profile NAT Pools"
    }
  }
}
"""
    tree_payload = """
{
  "privileges": {
    "cppm_config": {
      "type": "domain",
      "name": "Policy Manager",
      "desc": "Select operator permissions for Policy Manager",
      "features": {
        "cppm_nat_pool": {
          "type": "rwd",
          "domain": "cppm_config",
          "name": "Enforcement Profile - NAT Pool",
          "desc": "Manage Enforcement Profile NAT Pools"
        }
      }
    }
  }
}
"""

    list_result = parse_oauth_privileges(list_payload)
    tree_result = parse_oauth_privileges(tree_payload)

    assert list_result["cppm_nat_pool"]["domain_name"] == "Policy Manager"
    assert tree_result["cppm_nat_pool"]["domain_name"] == "Policy Manager"
    assert (
        tree_result["cppm_nat_pool"]["desc"] == "Manage Enforcement Profile NAT Pools"
    )


def test_build_bruteforce_candidate_overrides_uses_oauth_metadata():
    unresolved_services = [
        ("enforcementprofile", "nat-pool"),
        ("enforcementprofile", "dur-class"),
    ]
    admin_privileges = [
        "cppm_nat_pool",
        "cppm_dur_class",
        "cppm_certificates",
    ]
    oauth_privileges = parse_oauth_privileges(
        """
{
  "privileges": {
    "cppm_config": {
      "type": "domain",
      "name": "Policy Manager",
      "desc": "Select operator permissions for Policy Manager"
    },
    "cppm_nat_pool": {
      "type": "rwd",
      "domain": "cppm_config",
      "name": "Enforcement Profile - NAT Pool",
      "desc": "Manage Enforcement Profile NAT Pools"
    },
    "cppm_dur_class": {
      "type": "rwd",
      "domain": "cppm_config",
      "name": "Enforcement Profile - DUR Class",
      "desc": "Manage Enforcement Profile DUR Classes"
    }
  }
}
"""
    )

    result = build_bruteforce_candidate_overrides(
        unresolved_services,
        admin_privileges,
        oauth_privileges=oauth_privileges,
        max_single_candidates=3,
    )

    assert result["enforcementprofile/nat-pool"][0] == "cppm_nat_pool"
    assert result["enforcementprofile/dur-class"][0] == "cppm_dur_class"


def test_build_bruteforce_candidate_overrides_prefers_cppm_policy_for_policy_name():
    unresolved_services = [
        ("enforcementprofile", "policy-name"),
    ]
    admin_privileges = [
        "cppm_policy",
        "cppm_enforcement_policy",
        "cppm_enforcement_profile",
    ]

    result = build_bruteforce_candidate_overrides(
        unresolved_services,
        admin_privileges,
        max_single_candidates=3,
    )

    assert result["enforcementprofile/policy-name"][0] == "cppm_policy"
