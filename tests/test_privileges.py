from netloom.plugins.clearpass.privileges import (
    normalize_effective_privileges,
    parse_privilege_definitions,
    service_privilege_rule_index,
    suggest_catalog_mappings,
)

PRIVILEGE_TEXT = """
API Services
Select operator permissions for API access and management.
Allow API Access No Access Allow Access
Operators with this privilege are permitted to make API calls.
Manage API Clients No Access Read Only Full
Operators with this privilege may view and manage API clients.

Policy Manager
Select operator permissions for Policy Manager
Identity - Endpoints No Access Read Read, Write Read, Write, Delete
Operators with this privilege can manage endpoints
Network - Devices No Access Read Read, Write Read, Write, Delete
Operators with this privilege can manage network devices
"""


def test_parse_privilege_definitions_from_pasted_text():
    parsed = parse_privilege_definitions(PRIVILEGE_TEXT)

    assert parsed["source_type"] == "clearpass-privilege-definitions"
    assert parsed["sections"][0]["name"] == "API Services"
    assert parsed["sections"][1]["name"] == "Policy Manager"
    assert parsed["privileges"][0]["name"] == "Allow API Access"
    assert parsed["privileges"][0]["levels"] == ["No Access", "Allow Access"]
    assert parsed["privileges"][2]["name"] == "Identity - Endpoints"
    assert parsed["privileges"][2]["levels"] == [
        "No Access",
        "Read",
        "Read, Write",
        "Read, Write, Delete",
    ]


def test_parse_privilege_definitions_handles_read_only_and_select_descriptions():
    parsed = parse_privilege_definitions(
        """
Administrator
Select operator permissions for system administration and management tasks.
Application Log No Access Read Only
Operators with the Application Log privilege can view logged messages and events.

Operator Logins
Select permissions for managing local operator logins.
External Operator Logins No Access Read Only Full
Select permissions for managing external operator logins.
Manage Operator Logins No Access Read Only Full
Operators with the Manage Operator Logins privilege can view, create and remove operator logins for this web application.
"""
    )

    assert parsed["sections"][0]["name"] == "Administrator"
    assert parsed["privileges"][0]["name"] == "Application Log"
    assert parsed["privileges"][0]["levels"] == ["No Access", "Read Only"]
    assert "Application Log privilege can view logged messages" in (
        parsed["privileges"][0]["description"] or ""
    )
    assert parsed["privileges"][1]["section"] == "Operator Logins"
    assert (
        parsed["privileges"][1]["description"]
        == "Select permissions for managing external operator logins."
    )


def test_suggest_catalog_mappings_prefers_matching_services():
    definitions = parse_privilege_definitions(PRIVILEGE_TEXT)
    catalog = {
        "modules": {
            "identities": {
                "endpoint": {"actions": {"list": {"paths": ["/api/endpoint"]}}},
            },
            "policyelements": {
                "network-device": {
                    "actions": {"list": {"paths": ["/api/network-device"]}}
                }
            },
        }
    }

    suggested = suggest_catalog_mappings(definitions, catalog, limit=1)
    matches = {item["name"]: item["matches"] for item in suggested["privileges"]}

    assert matches["Identity - Endpoints"][0]["module"] == "identities"
    assert matches["Identity - Endpoints"][0]["service"] == "endpoint"
    assert matches["Network - Devices"][0]["service"] == "network-device"


def test_normalize_effective_privileges_tracks_prefix_access_levels():
    normalized = normalize_effective_privileges(
        ["#support_index", "?api_index", "cppm_endpoints"]
    )

    assert normalized == [
        {"raw": "#support_index", "name": "support_index", "access": "read-only"},
        {"raw": "?api_index", "name": "api_index", "access": "allowed"},
        {"raw": "cppm_endpoints", "name": "cppm_endpoints", "access": "full"},
    ]


def test_service_privilege_rule_index_includes_verified_live_mappings():
    rules = service_privilege_rule_index()

    assert rules[("enforcementprofile", "enforcement-profile")].privileges == (
        "cppm_enforcement_profile",
    )
    assert rules[("globalserverconfiguration", "application-license")].privileges == (
        "cppm_licenses",
    )
    assert rules[("globalserverconfiguration", "admin-user")].privileges == (
        "cppm_admin_users",
    )
    assert rules[("identities", "api-client")].privileges == ("api_clients",)
    assert rules[("identities", "endpoint")].privileges == ("cppm_endpoints",)
    assert rules[("identities", "guest")].privileges == ("guest_users",)
    assert rules[("localserverconfiguration", "server")].privileges == ("platform",)
    assert rules[("identities", "local-user")].privileges == ("cppm_local_users",)
    assert rules[("logs", "system-event")].privileges == ("cppm_system_events",)
    assert rules[("policyelements", "application-dictionary")].privileges == (
        "cppm_application_dict",
    )
    assert rules[("policyelements", "network-device")].privileges == (
        "cppm_network_devices",
    )
    assert rules[
        ("policyelements", "radius-dynamic-authorization-template")
    ].privileges == ("cppm_radius_dyn_autz_template",)
    assert rules[("policyelements", "role-mapping")].privileges == (
        "cppm_role_mapping",
    )
