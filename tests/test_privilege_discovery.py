import requests

from netloom.plugins.clearpass.privilege_discovery import (
    _build_write_probe_payload,
    _fetch_operator_profile,
    _iter_target_services,
    _operator_profile_item_path,
    _probe_action_for_service,
    _service_supports_reversible_write_probe,
    _update_operator_profile,
)


def test_fetch_operator_profile_falls_back_to_listing_on_name_404():
    profile = {
        "id": 12,
        "name": "netloom-privileges-discovery-profile",
        "_links": {
            "self": {"href": "https://clearpass.example/api/operator-profile/12"}
        },
    }

    class _AdminClient:
        def __init__(self):
            self.calls = []

        def request_path(self, method, path, token=None, json_body=None):
            self.calls.append((method, path, token, json_body))
            if path.startswith("/api/operator-profile/name/"):
                response = requests.Response()
                response.status_code = 404
                response.url = f"https://clearpass.example{path}"
                raise requests.HTTPError(response=response)
            return {"_embedded": {"items": [profile]}}

    client = _AdminClient()

    result = _fetch_operator_profile(
        client,
        "token",
        "netloom-privileges-discovery-profile",
    )

    assert result == profile
    assert client.calls[0][1] == (
        "/api/operator-profile/name/netloom-privileges-discovery-profile"
    )
    assert client.calls[1][1].startswith("/api/operator-profile?")


def test_update_operator_profile_prefers_item_identity_path():
    profile = {
        "id": 12,
        "name": "netloom-privileges-discovery-profile",
        "_links": {
            "self": {"href": "https://clearpass.example/api/operator-profile/12"}
        },
        "privileges": ["api_docs", "apigility"],
    }

    calls = []

    class _AdminClient:
        def request_path(self, method, path, token=None, json_body=None):
            calls.append((method, path, token, json_body))
            return {"ok": True}

    result = _update_operator_profile(
        _AdminClient(),
        "token",
        profile,
        ["api_docs", "apigility", "cppm_endpoints"],
    )

    assert result == {"ok": True}
    assert _operator_profile_item_path(profile) == "/api/operator-profile/12"
    assert calls[0][0] == "PATCH"
    assert calls[0][1] == "/api/operator-profile/12"
    assert calls[0][3]["privileges"] == [
        "api_docs",
        "apigility",
        "cppm_endpoints",
    ]


def test_probe_action_for_service_falls_back_to_get_when_list_is_missing():
    service_entry = {
        "actions": {
            "get": {
                "paths": ["/api/application-license/summary"],
                "params": None,
            }
        }
    }

    assert _probe_action_for_service(service_entry) == "get"


def test_iter_target_services_includes_safe_get_only_services():
    catalog = {
        "modules": {
            "globalserverconfiguration": {
                "application-license-summary": {
                    "actions": {
                        "get": {
                            "paths": ["/api/application-license/summary"],
                            "params": None,
                        }
                    }
                },
                "attribute-name": {
                    "actions": {
                        "get": {
                            "paths": ["/api/attribute/{entity_name}/name/{name}"],
                            "params": None,
                        }
                    }
                },
            }
        }
    }

    services = _iter_target_services(
        catalog,
        ("globalserverconfiguration",),
        include_mapped=True,
    )

    assert ("globalserverconfiguration", "application-license-summary") in services
    assert ("globalserverconfiguration", "attribute-name") not in services


def test_service_supports_reversible_write_probe_for_resource_style_service():
    service_entry = {
        "actions": {
            "add": {
                "paths": ["/api/template/pass"],
                "body_example": {"id": 0, "name": "", "description": ""},
                "body_required": [],
            },
            "delete": {"paths": ["/api/template/pass/{id}"]},
        }
    }

    assert _service_supports_reversible_write_probe(service_entry) is True


def test_service_supports_reversible_write_probe_rejects_unfilled_required_fields():
    service_entry = {
        "actions": {
            "add": {
                "paths": ["/api/weblogin"],
                "body_example": {"name": "", "vendor_preset": ""},
                "body_required": ["name", "vendor_preset"],
            },
            "delete": {"paths": ["/api/weblogin/{id}"]},
        }
    }

    assert _service_supports_reversible_write_probe(service_entry) is False


def test_build_write_probe_payload_populates_unique_name_fields():
    action_def = {
        "body_example": {"id": 0, "name": "", "page_name": "", "description": ""}
    }

    payload = _build_write_probe_payload("guestconfiguration", "pass", action_def)

    assert "id" not in payload
    assert payload["name"].startswith("netloom-privilege-probe-")
    assert payload["page_name"].startswith("netloom-privilege-probe-")
    assert payload["description"].startswith("netloom-privilege-probe-")


def test_service_supports_reversible_write_probe_with_synthesized_required_fields():
    service_entry = {
        "actions": {
            "add": {
                "paths": ["/api/messaging-setup"],
                "body_required": ["server_name", "default_from_address"],
                "body_fields": [
                    {"name": "server_name", "type": "string"},
                    {"name": "default_from_address", "type": "string"},
                    {"name": "port", "type": "int"},
                ],
                "body_example": {
                    "server_name": "",
                    "default_from_address": "",
                    "port": 0,
                },
            },
            "delete": {"paths": ["/api/messaging-setup"]},
        }
    }

    assert _service_supports_reversible_write_probe(service_entry) is True


def test_build_write_probe_payload_prefers_minimal_required_values():
    action_def = {
        "body_required": ["server_name", "default_from_address"],
        "body_fields": [
            {"name": "server_name", "type": "string"},
            {"name": "default_from_address", "type": "string"},
            {"name": "port", "type": "int"},
            {"name": "password", "type": "string"},
        ],
        "body_example": {
            "server_name": "",
            "default_from_address": "",
            "port": 0,
            "password": "",
        },
    }

    payload = _build_write_probe_payload(
        "globalserverconfiguration",
        "messaging-setup",
        action_def,
    )

    assert payload == {
        "server_name": "localhost",
        "default_from_address": "netloom@example.com",
    }
