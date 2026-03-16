from netloom.core.config import AppPaths, Settings
from netloom.plugins.clearpass.catalog import ApiEndpointCache


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
