import json
import re
from pathlib import Path

import pytest

import netloom.cli.commands as commands
from netloom.core.config import AppPaths, Settings
from netloom.plugins.clearpass.client import ResponseMetadata


@pytest.fixture
def api_catalog():
    return {
        "modules": {
            "identities": {
                "endpoint": {
                    "actions": {
                        "list": {
                            "method": "GET",
                            "paths": ["/api/endpoint"],
                            "params": [
                                "filter",
                                "sort",
                                "offset",
                                "limit",
                                "calculate_count",
                            ],
                        },
                        "get": {
                            "method": "GET",
                            "paths": [
                                "/api/endpoint/{id}",
                                "/api/endpoint/name/{name}",
                            ],
                            "params": ["id", "name"],
                        },
                        "delete": {
                            "method": "DELETE",
                            "paths": [
                                "/api/endpoint/{id}",
                                "/api/endpoint/name/{name}",
                            ],
                            "params": ["id", "name"],
                        },
                        "add": {
                            "method": "POST",
                            "paths": ["/api/endpoint"],
                            "params": ["name", "description", "foo"],
                        },
                    }
                }
            },
            "toolsandutilities": {
                "random-password": {
                    "actions": {
                        "add": {
                            "method": "POST",
                            "paths": ["/api/random-password"],
                            "params": ["random_password_method", "length"],
                        }
                    }
                }
            },
        }
    }


@pytest.fixture
def settings(tmp_path):
    paths = AppPaths(
        cache_dir=tmp_path / "cache",
        state_dir=tmp_path / "state",
        response_dir=tmp_path / "responses",
        app_log_dir=tmp_path / "logs",
    ).ensure()
    return Settings(paths=paths)


def test_resolve_out_path_uses_out_arg(tmp_path, settings):
    args = {"out": str(tmp_path / "custom.json")}
    assert commands.resolve_out_path(args, "svc", "list", "json", settings) == str(
        tmp_path / "custom.json"
    )


def test_resolve_out_path_default_uses_response_dir_and_normalizes_service(settings):
    args = {}
    out = commands.resolve_out_path(
        args, "network-device", "list", "json", settings=settings
    )
    path = Path(out)
    assert path.parent == settings.paths.response_dir
    assert re.fullmatch(
        r"network_device_list_\d{8}-\d{6}-\d{6}\.json",
        path.name,
    )


def test_payload_from_args_strips_reserved():
    args = {"name": "x", "id": "1", "console": True, "module": "m", "foo": "bar"}
    payload = commands.payload_from_cli_args(args, {"console", "module"})
    assert payload == {"name": "x", "id": "1", "foo": "bar"}


def test_payload_from_args_normalizes_random_password_method_shorthand():
    args = {
        "module": "toolsandutilities",
        "service": "random-password",
        "action": "add",
        "random_password_method": "6",
        "length": "20",
        "console": True,
    }

    payload = commands.payload_from_cli_args(
        args, {"console", "module", "service", "action"}
    )

    assert payload == {
        "random_password_method": "nwa_complex_password",
        "length": "20",
    }


def test_list_handler_validates_limit_range(api_catalog, settings):
    class CP:
        last_response_meta = None

        def get_action_definition(self, api_catalog, module, service, action):
            return api_catalog["modules"][module][service]["actions"][action]

        def list(self, *args, **kwargs):
            return {}

    with pytest.raises(ValueError, match="--limit must be between 1 and 1000"):
        commands.list_handler(
            CP(),
            "t",
            api_catalog,
            {
                "module": "identities",
                "service": "endpoint",
                "action": "list",
                "limit": "0",
            },
            settings=settings,
        )


def test_list_handler_calls_cp_and_logs(monkeypatch, api_catalog, settings):
    calls = {}

    class CP:
        last_response_meta = None

        def get_action_definition(self, api_catalog, module, service, action):
            return api_catalog["modules"][module][service]["actions"][action]

        def list(self, api_catalog, token, args, *, params=None):
            calls["api_catalog"] = api_catalog
            calls["token"] = token
            calls["args"] = args
            calls["params"] = params
            return {"_embedded": {"items": [{"id": 1}]}, "count": 1}

    def fake_log_to_file(thing, filename, **kwargs):
        calls["logged"] = {"thing": thing, "filename": str(filename), "kwargs": kwargs}
        return thing

    monkeypatch.setattr(commands, "log_to_file", fake_log_to_file)

    args = {
        "module": "identities",
        "service": "endpoint",
        "action": "list",
        "offset": "10",
        "limit": "25",
        "sort": "-id",
        "filter": '{"name":"x"}',
        "calculate_count": True,
        "data_format": "json",
        "console": False,
    }

    commands.list_handler(CP(), "tok", api_catalog, args, settings=settings)

    assert calls["params"] == {
        "offset": 10,
        "limit": 25,
        "sort": "-id",
        "filter": '{"name":"x"}',
        "calculate_count": "true",
    }
    assert calls["logged"]["thing"]["count"] == 1
    assert re.search(
        r"endpoint_list_\d{8}-\d{6}-\d{6}\.json$",
        calls["logged"]["filename"],
    )


def test_query_params_for_action_normalizes_filter_shorthand_eq(api_catalog):
    class CP:
        def get_action_definition(self, api_catalog, module, service, action):
            return api_catalog["modules"][module][service]["actions"][action]

    params = commands.query_params_for_action(
        CP(),
        api_catalog,
        {
            "module": "identities",
            "service": "endpoint",
            "action": "list",
            "filter": "name:equals:TEST",
        },
        "list",
    )

    assert json.loads(params["filter"]) == {"name": {"$eq": "TEST"}}


def test_query_params_for_action_normalizes_filter_shorthand_with_colons(api_catalog):
    class CP:
        def get_action_definition(self, api_catalog, module, service, action):
            return api_catalog["modules"][module][service]["actions"][action]

    params = commands.query_params_for_action(
        CP(),
        api_catalog,
        {
            "module": "identities",
            "service": "endpoint",
            "action": "list",
            "filter": "url:equals:https://example.com/a:b",
        },
        "list",
    )

    assert json.loads(params["filter"]) == {"url": {"$eq": "https://example.com/a:b"}}


def test_query_params_for_action_normalizes_filter_shorthand_in_and_exists(api_catalog):
    class CP:
        def get_action_definition(self, api_catalog, module, service, action):
            return api_catalog["modules"][module][service]["actions"][action]

    in_params = commands.query_params_for_action(
        CP(),
        api_catalog,
        {
            "module": "identities",
            "service": "endpoint",
            "action": "list",
            "filter": "id:in:1,2,3",
        },
        "list",
    )
    exists_params = commands.query_params_for_action(
        CP(),
        api_catalog,
        {
            "module": "identities",
            "service": "endpoint",
            "action": "list",
            "filter": "enabled:exists:true",
        },
        "list",
    )

    assert json.loads(in_params["filter"]) == {"id": {"$in": [1, 2, 3]}}
    assert json.loads(exists_params["filter"]) == {"enabled": {"$exists": True}}


def test_query_params_for_action_rejects_invalid_filter_shorthand(api_catalog):
    class CP:
        def get_action_definition(self, api_catalog, module, service, action):
            return api_catalog["modules"][module][service]["actions"][action]

    with pytest.raises(ValueError, match="Unsupported --filter syntax"):
        commands.query_params_for_action(
            CP(),
            api_catalog,
            {
                "module": "identities",
                "service": "endpoint",
                "action": "list",
                "filter": "name:equals",
            },
            "list",
        )


def test_list_handler_fetches_all_pages(monkeypatch, api_catalog, settings):
    calls = []
    import netloom.core.pagination as pagination

    monkeypatch.setattr(pagination, "DEFAULT_PAGE_SIZE", 2)

    class CP:
        last_response_meta = None

        def get_action_definition(self, api_catalog, module, service, action):
            return api_catalog["modules"][module][service]["actions"][action]

        def list(self, api_catalog, token, args, *, params=None):
            calls.append(dict(params or {}))
            offset = int((params or {}).get("offset", 0))
            limit = int((params or {}).get("limit", 25))
            items = [
                {"id": item_id}
                for item_id in range(offset + 1, min(offset + limit, 5) + 1)
            ]
            response = {"_embedded": {"items": items}}
            if offset == 0:
                response["count"] = 5
            return response

    logged = {}
    monkeypatch.setattr(
        commands,
        "log_to_file",
        lambda thing, filename, **kwargs: logged.update(
            {"thing": thing, "filename": str(filename)}
        ),
    )

    commands.list_handler(
        CP(),
        "tok",
        api_catalog,
        {
            "module": "identities",
            "service": "endpoint",
            "action": "list",
            "calculate_count": True,
        },
        settings=settings,
    )

    assert calls == [
        {"limit": 2, "offset": 0, "sort": None, "calculate_count": "true"},
        {"limit": 2, "offset": 2, "sort": None, "calculate_count": "false"},
        {"limit": 2, "offset": 4, "sort": None, "calculate_count": "false"},
    ]
    assert [item["id"] for item in logged["thing"]["_embedded"]["items"]] == [
        1,
        2,
        3,
        4,
        5,
    ]
    assert logged["thing"]["count"] == 5


def test_get_handler_calls_cp_and_logs(monkeypatch, api_catalog, settings):
    logged = {}

    class CP:
        last_response_meta = None

        def get_action_definition(self, api_catalog, module, service, action):
            return api_catalog["modules"][module][service]["actions"][action]

        def get(self, api_catalog, token, args, *, params=None):
            logged["call"] = {
                "api_catalog": api_catalog,
                "token": token,
                "args": args,
                "params": params,
            }
            return {"name": "bob", "id": 2}

    def fake_log_to_file(thing, filename, **kwargs):
        logged["thing"] = thing
        logged["filename"] = str(filename)

    monkeypatch.setattr(commands, "log_to_file", fake_log_to_file)

    commands.get_handler(
        CP(),
        "tok",
        api_catalog,
        {"module": "identities", "service": "endpoint", "action": "get", "name": "bob"},
        settings=settings,
    )
    assert logged["call"]["params"] == {"name": "bob"}
    assert logged["thing"]["id"] == 2
    assert re.search(
        r"endpoint_get_\d{8}-\d{6}-\d{6}\.json$",
        logged["filename"],
    )


def test_get_handler_all_fetches_all_pages_without_count(
    monkeypatch, api_catalog, settings
):
    calls = []
    import netloom.core.pagination as pagination

    monkeypatch.setattr(pagination, "DEFAULT_PAGE_SIZE", 2)

    class CP:
        last_response_meta = None

        def get_action_definition(self, api_catalog, module, service, action):
            return api_catalog["modules"][module][service]["actions"][action]

        def list(self, api_catalog, token, args, *, params=None):
            calls.append(dict(params or {}))
            offset = int((params or {}).get("offset", 0))
            limit = int((params or {}).get("limit", 25))
            items = [
                {"id": item_id}
                for item_id in range(offset + 1, min(offset + limit, 5) + 1)
            ]
            return {"_embedded": {"items": items}}

    logged = {}
    monkeypatch.setattr(
        commands,
        "log_to_file",
        lambda thing, filename, **kwargs: logged.update(
            {"thing": thing, "filename": str(filename)}
        ),
    )

    commands.get_handler(
        CP(),
        "tok",
        api_catalog,
        {
            "module": "identities",
            "service": "endpoint",
            "action": "get",
            "all": True,
        },
        settings=settings,
    )

    assert calls == [
        {"limit": 2, "offset": 0, "sort": None},
        {"limit": 2, "offset": 2, "sort": None},
        {"limit": 2, "offset": 4, "sort": None},
    ]
    assert [item["id"] for item in logged["thing"]["_embedded"]["items"]] == [
        1,
        2,
        3,
        4,
        5,
    ]


def test_list_handler_honors_explicit_limit(monkeypatch, api_catalog, settings):
    calls = []
    logged = {}

    class CP:
        last_response_meta = None

        def get_action_definition(self, api_catalog, module, service, action):
            return api_catalog["modules"][module][service]["actions"][action]

        def list(self, api_catalog, token, args, *, params=None):
            calls.append(dict(params or {}))
            return {"_embedded": {"items": [{"id": 1}]}, "count": 4}

    monkeypatch.setattr(
        commands,
        "log_to_file",
        lambda thing, filename, **kwargs: logged.update(
            {"thing": thing, "filename": str(filename)}
        ),
    )

    commands.list_handler(
        CP(),
        "tok",
        api_catalog,
        {
            "module": "identities",
            "service": "endpoint",
            "action": "list",
            "limit": "1",
        },
        settings=settings,
    )

    assert calls == [{"limit": 1, "offset": 0, "sort": None}]
    assert [item["id"] for item in logged["thing"]["_embedded"]["items"]] == [1]


def test_delete_handler_calls_delete(monkeypatch, api_catalog, settings):
    logged = {}

    class CP:
        last_response_meta = None

        def get_action_definition(self, api_catalog, module, service, action):
            return api_catalog["modules"][module][service]["actions"][action]

        def delete(self, api_catalog, token, args, *, params=None):
            logged["delete_call"] = {
                "api_catalog": api_catalog,
                "token": token,
                "args": args,
                "params": params,
            }
            return {"deleted": args["id"]}

    def fake_log_to_file(thing, filename, **kwargs):
        logged["thing"] = thing
        logged["filename"] = str(filename)

    monkeypatch.setattr(commands, "log_to_file", fake_log_to_file)

    commands.delete_handler(
        CP(),
        "tok",
        api_catalog,
        {
            "module": "identities",
            "service": "endpoint",
            "action": "delete",
            "id": "123",
        },
        settings=settings,
    )
    assert logged["delete_call"]["params"] == {"id": "123"}
    assert logged["thing"]["deleted"] == "123"
    assert re.search(
        r"endpoint_delete_\d{8}-\d{6}-\d{6}\.json$",
        logged["filename"],
    )


def test_add_handler_builds_payload_from_args(monkeypatch, api_catalog, settings):
    logged = {}

    class CP:
        last_response_meta = None

        def get_action_definition(self, api_catalog, module, service, action):
            return api_catalog["modules"][module][service]["actions"][action]

        def resolve_action(self, api_catalog, module, service, action, args):
            return (
                api_catalog["modules"][module][service]["actions"][action],
                "/api/endpoint",
                [],
            )

        def add(self, api_catalog, token, args, payload):
            logged["add_call"] = {
                "api_catalog": api_catalog,
                "token": token,
                "args": args,
                "payload": payload,
            }
            return {"id": 7, **payload}

    monkeypatch.setattr(
        commands,
        "log_to_file",
        lambda thing, filename, **kwargs: logged.update(
            {"thing": thing, "filename": str(filename)}
        ),
    )

    commands.add_handler(
        CP(),
        "tok",
        api_catalog,
        {
            "module": "identities",
            "service": "endpoint",
            "action": "add",
            "name": "alice",
            "description": "demo",
            "foo": "bar",
            "console": False,
        },
        settings=settings,
    )

    assert logged["add_call"]["payload"] == {
        "name": "alice",
        "description": "demo",
        "foo": "bar",
    }
    assert logged["thing"]["id"] == 7


def test_add_handler_file_payload_filters_response_fields(
    monkeypatch, api_catalog, settings, tmp_path
):
    logged = {}
    payload_path = tmp_path / "payload.json"
    payload_path.write_text(
        (
            '[{"id": 7, "name": "alice", "description": "demo", '
            '"foo": "bar", "attributes": {}, "ignored": "x"}]'
        ),
        encoding="utf-8",
    )
    api_catalog["modules"]["identities"]["endpoint"]["actions"]["add"][
        "body_fields"
    ] = [
        {"name": "name", "required": True},
        {"name": "description", "required": False},
        {"name": "foo", "required": False},
        {"name": "attributes", "required": False},
    ]

    class CP:
        last_response_meta = None

        def get_action_definition(self, api_catalog, module, service, action):
            return api_catalog["modules"][module][service]["actions"][action]

        def resolve_action(self, api_catalog, module, service, action, args):
            return (
                api_catalog["modules"][module][service]["actions"][action],
                "/api/endpoint",
                [],
            )

        def add(self, api_catalog, token, args, payload):
            logged["add_call"] = {
                "api_catalog": api_catalog,
                "token": token,
                "args": args,
                "payload": payload,
            }
            return {"id": 7, **payload}

    monkeypatch.setattr(
        commands,
        "log_to_file",
        lambda thing, filename, **kwargs: logged.update(
            {"thing": thing, "filename": str(filename)}
        ),
    )

    commands.add_handler(
        CP(),
        "tok",
        api_catalog,
        {
            "module": "identities",
            "service": "endpoint",
            "action": "add",
            "file": str(payload_path),
            "console": False,
        },
        settings=settings,
    )

    assert logged["add_call"]["payload"] == {
        "name": "alice",
        "description": "demo",
        "foo": "bar",
    }


def test_add_handler_normalizes_random_password_method_alias(
    monkeypatch, api_catalog, settings
):
    logged = {}

    class CP:
        last_response_meta = None

        def get_action_definition(self, api_catalog, module, service, action):
            return api_catalog["modules"][module][service]["actions"][action]

        def resolve_action(self, api_catalog, module, service, action, args):
            return (
                api_catalog["modules"][module][service]["actions"][action],
                "/api/random-password",
                [],
            )

        def add(self, api_catalog, token, args, payload):
            logged["add_call"] = {
                "api_catalog": api_catalog,
                "token": token,
                "args": args,
                "payload": payload,
            }
            return {"id": 7, **payload}

    monkeypatch.setattr(
        commands,
        "log_to_file",
        lambda thing, filename, **kwargs: logged.update(
            {"thing": thing, "filename": str(filename)}
        ),
    )

    commands.add_handler(
        CP(),
        "tok",
        api_catalog,
        {
            "module": "toolsandutilities",
            "service": "random-password",
            "action": "add",
            "random_password_method": "strong",
            "length": "24",
            "console": False,
        },
        settings=settings,
    )

    assert logged["add_call"]["payload"] == {
        "random_password_method": "nwa_strong_password",
        "length": "24",
    }


def test_update_handler_file_payload_uses_id_for_path_not_body(
    monkeypatch, api_catalog, settings, tmp_path
):
    logged = {}
    payload_path = tmp_path / "payload.json"
    payload_path.write_text(
        '{"id": "123", "name": "alice", "description": "demo", "ignored": "x"}',
        encoding="utf-8",
    )
    api_catalog["modules"]["identities"]["endpoint"]["actions"]["update"] = {
        "method": "PATCH",
        "paths": ["/api/endpoint/{id}"],
        "params": ["id", "name", "description"],
    }

    class CP:
        last_response_meta = None

        def get_action_definition(self, api_catalog, module, service, action):
            return api_catalog["modules"][module][service]["actions"][action]

        def resolve_action(self, api_catalog, module, service, action, args):
            return (
                api_catalog["modules"][module][service]["actions"][action],
                f"/api/endpoint/{args['id']}",
                ["id"],
            )

        def update(self, api_catalog, token, args, payload):
            logged["update_call"] = {
                "api_catalog": api_catalog,
                "token": token,
                "args": args,
                "payload": payload,
            }
            return {"id": args["id"], **payload}

    monkeypatch.setattr(
        commands,
        "log_to_file",
        lambda thing, filename, **kwargs: logged.update(
            {"thing": thing, "filename": str(filename)}
        ),
    )

    commands.update_handler(
        CP(),
        "tok",
        api_catalog,
        {
            "module": "identities",
            "service": "endpoint",
            "action": "update",
            "file": str(payload_path),
            "console": False,
        },
        settings=settings,
    )

    assert logged["update_call"]["args"]["id"] == "123"
    assert logged["update_call"]["payload"] == {
        "name": "alice",
        "description": "demo",
    }


def test_get_handler_binary_response_uses_raw_output_and_filename(
    monkeypatch, api_catalog, settings
):
    logged = {}
    api_catalog["modules"]["identities"]["endpoint"]["actions"]["get"][
        "response_content_types"
    ] = ["application/x-pkcs12"]

    class CP:
        last_response_meta = ResponseMetadata(
            content_type="application/x-pkcs12",
            filename="endpoint-export.p12",
            is_binary=True,
        )

        def get_action_definition(self, api_catalog, module, service, action):
            return api_catalog["modules"][module][service]["actions"][action]

        def get(self, api_catalog, token, args, *, params=None):
            return b"\x01\x02"

    def fake_log_to_file(thing, filename, **kwargs):
        logged["thing"] = thing
        logged["filename"] = str(filename)
        logged["kwargs"] = kwargs

    monkeypatch.setattr(commands, "log_to_file", fake_log_to_file)

    commands.get_handler(
        CP(),
        "tok",
        api_catalog,
        {"module": "identities", "service": "endpoint", "action": "get", "id": "1"},
        settings=settings,
    )

    assert logged["thing"] == b"\x01\x02"
    assert logged["kwargs"]["data_format"] == "raw"
    assert logged["filename"].endswith("endpoint-export.p12")
