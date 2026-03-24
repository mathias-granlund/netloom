import json

from netloom.core.config import AppPaths, Settings
from netloom.plugins.clearpass.catalog import (
    ApiEndpointCache,
    _filter_catalog_by_effective_privileges,
    _visible_catalog_modules,
    build_catalog_index,
    clear_api_cache,
    get_index_file_path,
    load_cached_index,
    project_catalog_view,
)


class FakeCP:
    server = "example:443"
    https_prefix = "https://"
    verify_ssl = False
    timeout = 5


def test_process_swagger_subdoc_captures_body_and_response_metadata(tmp_path):
    settings = Settings(
        paths=AppPaths(
            cache_dir=tmp_path / "cache",
            state_dir=tmp_path / "state",
            response_dir=tmp_path / "responses",
            app_log_dir=tmp_path / "logs",
        ).ensure()
    )
    cache = ApiEndpointCache(FakeCP(), token="tok", settings=settings)
    module_services = {}
    subdoc = {
        "resourcePath": "/example",
        "produces": ["application/x-pkcs12"],
        "models": {
            "ExampleCreate": {
                "required": ["name"],
                "properties": {
                    "name": {"type": "string", "description": "Object name"},
                    "enabled": {"type": "boolean", "description": "Toggle flag"},
                },
            }
        },
        "apis": [
            {
                "path": "/example",
                "operations": [
                    {
                        "method": "POST",
                        "summary": "Create example",
                        "notes": "Creates one example object",
                        "parameters": [
                            {
                                "paramType": "body",
                                "name": "body",
                                "type": "ExampleCreate",
                                "description": "Create payload",
                            }
                        ],
                        "responseMessages": [
                            {"code": 201, "message": "Created"},
                            {"code": 422, "message": "Validation failed"},
                        ],
                    }
                ],
            }
        ],
    }

    cache._process_swagger_subdoc(module_services, subdoc)

    action = module_services["example"]["actions"]["add"]
    assert action["summary"] == "Create example"
    assert "201 Created" in action["response_codes"]
    assert action["response_content_types"] == ["application/x-pkcs12"]
    assert action["body_required"] == ["name"]
    assert action["body_fields"][0]["name"] == "name"
    assert action["body_example"]["enabled"] is True


def test_process_swagger_subdoc_strips_html_from_notes(tmp_path):
    settings = Settings(
        paths=AppPaths(
            cache_dir=tmp_path / "cache",
            state_dir=tmp_path / "state",
            response_dir=tmp_path / "responses",
            app_log_dir=tmp_path / "logs",
        ).ensure()
    )
    cache = ApiEndpointCache(FakeCP(), token="tok", settings=settings)
    module_services = {}
    subdoc = {
        "resourcePath": "/enforcement-policy",
        "apis": [
            {
                "path": "/enforcement-policy",
                "operations": [
                    {
                        "method": "GET",
                        "summary": "Get a list of enforcement policies",
                        "notes": (
                            "Get a list of enforcement policies. <div>"
                            '<a href="#">More about JSON filter expressions</a>'
                            "<div><p>A filter is specified as a JSON object, "
                            "where the properties of the object specify the type "
                            "of query to be performed.</p><table><tr>"
                            "<th>Description</th>"
                            "<th>JSON Filter Syntax</th></tr><tr><td>Field is equal to "
                            '"value"</td><td class="code">{'
                            '"<i>fieldName</i>":"<i>value</i>"}'
                            "</td></tr></table></div></div>"
                        ),
                        "parameters": [
                            {"name": "filter"},
                            {"name": "limit"},
                        ],
                    }
                ],
            }
        ],
    }

    cache._process_swagger_subdoc(module_services, subdoc)

    action = module_services["enforcement-policy"]["actions"]["list"]
    assert action["notes"] == [
        (
            "Get a list of enforcement policies.\n"
            "More about JSON filter expressions\n"
            "A filter is specified as a JSON object, where the properties of "
            "the object specify the type of query to be performed.\n"
            "Description | JSON Filter Syntax\n"
            'Field is equal to "value" | {"fieldName":"value"}'
        )
    ]


def test_filter_catalog_by_effective_privileges_filters_known_services():
    catalog = {
        "modules": {
            "identities": {
                "endpoint": {
                    "actions": {
                        "list": {"method": "GET"},
                        "get": {"method": "GET"},
                        "add": {"method": "POST"},
                    }
                },
                "local-user": {
                    "actions": {
                        "list": {"method": "GET"},
                        "add": {"method": "POST"},
                    }
                },
            },
            "policyelements": {
                "network-device": {
                    "actions": {
                        "list": {"method": "GET"},
                        "add": {"method": "POST"},
                    }
                }
            },
        }
    }

    filtered, metadata = _filter_catalog_by_effective_privileges(
        catalog,
        [
            {"name": "cppm_endpoints", "access": "full", "raw": "cppm_endpoints"},
            {
                "name": "cppm_local_users",
                "access": "read-only",
                "raw": "#cppm_local_users",
            },
        ],
    )

    assert "endpoint" in filtered["identities"]
    assert "add" in filtered["identities"]["endpoint"]["actions"]
    assert "local-user" in filtered["identities"]
    assert "add" not in filtered["identities"]["local-user"]["actions"]
    assert "network-device" not in filtered.get("policyelements", {})
    assert metadata["filter_applied"] is True
    assert metadata["filtered_service_count"] == 1


def test_filter_catalog_by_effective_privileges_supports_all_of_rules():
    catalog = {
        "modules": {
            "identities": {
                "device": {
                    "actions": {
                        "list": {"method": "GET"},
                        "add": {"method": "POST"},
                    }
                }
            }
        }
    }

    filtered_missing, _ = _filter_catalog_by_effective_privileges(
        catalog,
        [
            {"name": "mac", "access": "full", "raw": "mac"},
        ],
    )
    assert "device" not in filtered_missing.get("identities", {})

    filtered_present, _ = _filter_catalog_by_effective_privileges(
        catalog,
        [
            {"name": "mac", "access": "full", "raw": "mac"},
            {"name": "guest_users", "access": "full", "raw": "guest_users"},
        ],
    )
    assert "device" in filtered_present["identities"]
    assert filtered_present["identities"]["device"]["privilege_match"] == "all"


def test_visible_catalog_modules_hide_unmapped_services_when_filter_applied():
    filtered_modules = {
        "identities": {
            "endpoint": {
                "actions": {"list": {"method": "GET"}},
                "required_privileges": ["cppm_endpoints"],
            },
            "guest": {
                "actions": {"list": {"method": "GET"}},
            },
        }
    }

    visible_modules, metadata = _visible_catalog_modules(
        filtered_modules,
        {
            "filter_applied": True,
            "effective_privileges": [
                {
                    "name": "cppm_endpoints",
                    "access": "full",
                    "raw": "cppm_endpoints",
                }
            ],
        },
    )

    assert "endpoint" in visible_modules["identities"]
    assert "guest" not in visible_modules["identities"]
    assert metadata["view_applied"] is True
    assert metadata["hidden_service_count"] == 1


def test_project_catalog_view_can_switch_to_full_modules():
    catalog = {
        "version": 5,
        "modules": {
            "identities": {
                "endpoint": {"actions": {"list": {"method": "GET"}}},
            }
        },
        "full_modules": {
            "identities": {
                "endpoint": {"actions": {"list": {"method": "GET"}}},
                "guest": {"actions": {"list": {"method": "GET"}}},
            }
        },
    }

    projected = project_catalog_view(catalog, catalog_view="full")

    assert projected["catalog_view"] == "full"
    assert "endpoint" in projected["modules"]["identities"]
    assert "guest" in projected["modules"]["identities"]


def test_build_catalog_index_trims_heavy_action_metadata():
    catalog = {
        "version": 5,
        "modules": {
            "policyelements": {
                "network-device": {
                    "actions": {
                        "add": {
                            "method": "POST",
                            "paths": ["/api/network-device"],
                            "summary": "Create a network device",
                            "response_codes": ["201 Created"],
                            "response_content_types": ["application/json"],
                            "body_required": ["name"],
                            "body_fields": [
                                {
                                    "name": "name",
                                    "required": True,
                                    "type": "string",
                                    "description": "Device name",
                                },
                                {
                                    "name": "description",
                                    "required": False,
                                    "type": "string",
                                },
                            ],
                            "body_example": {"name": "switch-a"},
                        }
                    }
                }
            }
        },
        "full_modules": {
            "policyelements": {
                "network-device": {
                    "actions": {
                        "add": {
                            "method": "POST",
                            "paths": ["/api/network-device"],
                        }
                    }
                }
            }
        },
    }

    index = build_catalog_index(catalog)
    action = index["modules"]["policyelements"]["network-device"]["actions"]["add"]

    assert index["index_version"] == 1
    assert "full_modules" in index
    assert action["method"] == "POST"
    assert action["paths"] == ["/api/network-device"]
    assert action["body_required"] == ["name"]
    assert action["body_fields"] == [
        {"name": "name", "required": True},
        {"name": "description"},
    ]
    assert "response_codes" not in action
    assert "response_content_types" not in action
    assert "body_example" not in action


def test_load_cached_index_projects_full_modules(tmp_path):
    settings = Settings(
        paths=AppPaths(
            cache_dir=tmp_path / "cache",
            state_dir=tmp_path / "state",
            response_dir=tmp_path / "responses",
            app_log_dir=tmp_path / "logs",
        ).ensure()
    )
    path = get_index_file_path(settings=settings)
    path.write_text(
        json.dumps(
            {
                "version": 5,
                "index_version": 1,
                "modules": {
                    "identities": {"endpoint": {"actions": {"list": {"method": "GET"}}}}
                },
                "full_modules": {
                    "identities": {
                        "endpoint": {"actions": {"list": {"method": "GET"}}},
                        "guest": {"actions": {"list": {"method": "GET"}}},
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    visible = load_cached_index(settings=settings)
    full = load_cached_index(settings=settings, catalog_view="full")

    assert "endpoint" in visible["modules"]["identities"]
    assert "guest" not in visible["modules"]["identities"]
    assert "guest" in full["modules"]["identities"]
    assert full["catalog_view"] == "full"


def test_clear_api_cache_removes_full_cache_and_index(tmp_path):
    settings = Settings(
        paths=AppPaths(
            cache_dir=tmp_path / "cache",
            state_dir=tmp_path / "state",
            response_dir=tmp_path / "responses",
            app_log_dir=tmp_path / "logs",
        ).ensure()
    )
    cache = ApiEndpointCache(FakeCP(), token="tok", settings=settings)
    cache.cache_path.write_text('{"version":5,"modules":{}}', encoding="utf-8")
    cache.index_path.write_text(
        '{"version":5,"index_version":1,"modules":{}}',
        encoding="utf-8",
    )

    removed = clear_api_cache(settings=settings)

    assert removed is True
    assert cache.cache_path.exists() is False
    assert cache.index_path.exists() is False
