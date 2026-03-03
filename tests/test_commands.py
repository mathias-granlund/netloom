import types
import pytest

import arapy.commands as commands
import arapy.config as config


def test_resolve_out_path_uses_out_arg(tmp_path, monkeypatch):
    args = {"out": str(tmp_path / "custom.json")}
    assert commands.resolve_out_path(args, "svc", "list", "json") == str(tmp_path / "custom.json")


def test_resolve_out_path_default_uses_log_dir_and_normalizes_service(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LOG_DIR", tmp_path)
    args = {}
    out = commands.resolve_out_path(args, "network-device", "list", "json")
    assert out == str(tmp_path / "network_device_list.json")


def test_build_payload_from_args_strips_reserved():
    args = {"name": "x", "id": "1", "console": True, "module": "m", "foo": "bar"}
    payload = commands.build_payload_from_args(args, {"console", "module"})
    assert payload == {"name": "x", "id": "1", "foo": "bar"}


def test_list_handler_validates_limit_range():
    cp = types.SimpleNamespace(_list=lambda *a, **k: {})
    with pytest.raises(ValueError, match="--limit must be between 1 and 1000"):
        commands.list_handler(cp, "t", {}, {"service": "endpoint", "action": "list", "limit": "0"})


def test_list_handler_calls_cp_and_logs(monkeypatch):
    calls = {}

    class CP:
        def _list(self, api_paths, token, args, *, offset, limit, sort, filter, calculate_count):
            calls["params"] = dict(offset=offset, limit=limit, sort=sort, filter=filter, calculate_count=calculate_count)
            return {"_embedded": {"items": [{"id": 1}]}, "count": 1}

    def fake_log_to_file(thing, filename, **kwargs):
        calls["logged"] = {"thing": thing, "filename": str(filename), "kwargs": kwargs}
        return thing

    monkeypatch.setattr(commands, "log_to_file", fake_log_to_file)

    args = {
        "service": "endpoint",
        "action": "list",
        "offset": "10",
        "limit": "25",
        "sort": "-id",
        "filter": '{"name":"x"}',
        "calculate_count": "true",
        "data_format": "json",
        "console": False,
    }

    commands.list_handler(CP(), "tok", {}, args)

    assert calls["params"] == {
        "offset": 10,
        "limit": 25,
        "sort": "-id",
        "filter": '{"name":"x"}',
        "calculate_count": True,
    }
    assert calls["logged"]["thing"]["count"] == 1
    assert calls["logged"]["filename"].endswith("endpoint_list.json")


def test_get_handler_requires_id_or_name():
    cp = types.SimpleNamespace(_get=lambda *a, **k: {})
    with pytest.raises(ValueError, match="requires --id=<id> or --name=<name>"):
        commands.get_handler(cp, "t", {}, {"service": "endpoint", "action": "get"})


def test_get_handler_name_fallback(monkeypatch):
    logged = {}

    class CP:
        def __init__(self):
            self.calls = []
        def _get(self, api_paths, token, args, entity):
            self.calls.append(entity)
            if entity == "bob":
                raise RuntimeError("not found on first attempt")
            return {"name": "bob", "id": 2}

    def fake_log_to_file(thing, filename, **kwargs):
        logged["thing"] = thing
        logged["filename"] = str(filename)

    monkeypatch.setattr(commands, "log_to_file", fake_log_to_file)

    cp = CP()
    commands.get_handler(cp, "tok", {}, {"service": "endpoint", "action": "get", "name": "bob"})
    assert cp.calls == ["bob", "name/bob"]
    assert logged["thing"]["id"] == 2
    assert logged["filename"].endswith("endpoint_get.json")


def test_delete_handler_requires_id_or_name():
    cp = types.SimpleNamespace(_delete=lambda *a, **k: None)
    with pytest.raises(ValueError, match="requires --id=<id> or --name=<name>"):
        commands.delete_handler(cp, "tok", {}, {"service": "endpoint", "action": "delete"})


def test_delete_handler_by_id_calls_delete(monkeypatch):
    logged = {}

    class CP:
        def __init__(self):
            self.deleted = []
        def _delete(self, api_paths, token, args, entity):
            self.deleted.append(entity)

    def fake_log_to_file(thing, filename, **kwargs):
        logged["thing"] = thing
        logged["filename"] = str(filename)

    monkeypatch.setattr(commands, "log_to_file", fake_log_to_file)

    cp = CP()
    commands.delete_handler(cp, "tok", {}, {"service": "endpoint", "action": "delete", "id": "123"})
    assert cp.deleted == ["123"]
    assert logged["thing"]["deleted"] == "123"
    assert logged["filename"].endswith("endpoint_delete.json")


def test_delete_handler_by_name_calls_delete(monkeypatch):
    class CP:
        def __init__(self):
            self.deleted = []
        def _delete(self, api_paths, token, args, entity):
            self.deleted.append(entity)

    monkeypatch.setattr(commands, "log_to_file", lambda *a, **k: None)
    cp = CP()
    commands.delete_handler(cp, "tok", {}, {"service": "endpoint", "action": "delete", "name": "alice"})
    assert cp.deleted == ["name/alice"]
