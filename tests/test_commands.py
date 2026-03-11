from pathlib import Path

import pytest

import arapy.cli.commands as commands
from arapy.core.client import ResponseMetadata
from arapy.core.config import AppPaths, Settings


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
            }
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
    assert out == str(Path(settings.paths.response_dir) / "network_device_list.json")


def test_payload_from_args_strips_reserved():
    args = {"name": "x", "id": "1", "console": True, "module": "m", "foo": "bar"}
    payload = commands.payload_from_cli_args(args, {"console", "module"})
    assert payload == {"name": "x", "id": "1", "foo": "bar"}


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
        "calculate_count": True,
    }
    assert calls["logged"]["thing"]["count"] == 1
    assert calls["logged"]["filename"].endswith("endpoint_list.json")


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
    assert logged["filename"].endswith("endpoint_get.json")


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
    assert logged["filename"].endswith("endpoint_delete.json")


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
