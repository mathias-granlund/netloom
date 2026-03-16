import types
from pathlib import Path

import netloom.cli.completion as completion
import netloom.cli.main as main
from netloom.core.config import AppPaths, Settings

TEST_CATALOG = {
    "modules": {
        "identities": {
            "endpoint": {
                "actions": {
                    "list": {"method": "GET", "paths": ["/api/endpoint"]},
                    "get": {"method": "GET", "paths": ["/api/endpoint/{id}"]},
                    "add": {"method": "POST", "paths": ["/api/endpoint"]},
                }
            }
        }
    }
}


def _catalog_plugin(catalog):
    return types.SimpleNamespace(
        load_cached_catalog=lambda settings=None: catalog,
    )


def _settings():
    paths = AppPaths(
        cache_dir=Path("cache"),
        state_dir=Path("state"),
        response_dir=Path("responses"),
        app_log_dir=Path("logs"),
    )
    return Settings(paths=paths)


def test_parse_cli_basic():
    argv = [
        "netloom",
        "identities",
        "endpoint",
        "list",
        "--limit=10",
        "--console",
        "--log_level=debug",
    ]
    args = main.parse_cli(argv)
    assert args["module"] == "identities"
    assert args["service"] == "endpoint"
    assert args["action"] == "list"
    assert args["limit"] == "10"
    assert args["console"] is True
    assert args["log_level"] == "debug"


def test_parse_cli_ignores_unknown_flags_in_completion_mode():
    argv = ["netloom", "--_complete", "--_cur=ep", "-x", "identities"]
    args = main.parse_cli(argv)
    assert args["_complete"] is True


def test_complete_outputs_modules(capsys, monkeypatch):
    plugin = _catalog_plugin(TEST_CATALOG)
    monkeypatch.setattr(main, "get_plugin", lambda *args, **kwargs: plugin)
    main.complete(["--_cur="], settings=_settings())
    out = capsys.readouterr().out.strip().splitlines()
    assert "identities" in out
    assert "copy" in out


def test_complete_outputs_services_for_module(capsys, monkeypatch):
    plugin = _catalog_plugin(TEST_CATALOG)
    monkeypatch.setattr(main, "get_plugin", lambda *args, **kwargs: plugin)
    main.complete(["identities", "--_cur="], settings=_settings())
    out = capsys.readouterr().out.strip().splitlines()
    assert "endpoint" in out


def test_complete_outputs_actions_for_service(capsys, monkeypatch):
    plugin = _catalog_plugin(TEST_CATALOG)
    monkeypatch.setattr(main, "get_plugin", lambda *args, **kwargs: plugin)
    main.complete(["identities", "endpoint"], settings=_settings())
    out = capsys.readouterr().out.strip().splitlines()
    assert "list" in out
    assert "get" in out
    assert "copy" in out


def test_complete_outputs_server_profiles_for_use(capsys, monkeypatch):
    plugin = _catalog_plugin(TEST_CATALOG)
    monkeypatch.setattr(main, "get_plugin", lambda *args, **kwargs: plugin)
    monkeypatch.setattr(completion, "list_profiles", lambda: ["dev", "prod"])
    main.complete(["server", "use"], settings=_settings())
    out = capsys.readouterr().out.strip().splitlines()
    assert "dev" in out
    assert "prod" in out


def test_complete_outputs_services_for_copy_module(capsys, monkeypatch):
    plugin = _catalog_plugin(TEST_CATALOG)
    monkeypatch.setattr(main, "get_plugin", lambda *args, **kwargs: plugin)
    main.complete(["copy", "identities"], settings=_settings())
    out = capsys.readouterr().out.strip().splitlines()
    assert "endpoint" in out


def test_parse_cli_encrypt_disable_and_separator():
    argv = [
        "netloom",
        "policyelements",
        "network-device",
        "list",
        "--console",
        "--",
        "--encrypt=disable",
    ]
    args = main.parse_cli(argv)
    assert args["encrypt"] == "disable"
    assert args["console"] is True


def test_parse_cli_decrypt_flag():
    argv = ["netloom", "policyelements", "network-device", "list", "--decrypt"]
    args = main.parse_cli(argv)
    assert args["decrypt"] is True


def test_parse_cli_copy_command():
    argv = [
        "netloom",
        "policyelements",
        "network-device",
        "copy",
        "--from=dev",
        "--to=prod",
        "--all",
        "--dry-run",
    ]
    args = main.parse_cli(argv)
    assert args["module"] == "policyelements"
    assert args["service"] == "network-device"
    assert args["action"] == "copy"
    assert args["copy_module"] == "policyelements"
    assert args["copy_service"] == "network-device"
    assert args["from"] == "dev"
    assert args["to"] == "prod"
    assert args["all"] is True
    assert args["dry_run"] is True


def test_parse_cli_legacy_copy_alias():
    argv = [
        "netloom",
        "copy",
        "policyelements",
        "network-device",
        "--from=dev",
        "--to=prod",
    ]
    args = main.parse_cli(argv)
    assert args["module"] == "copy"
    assert args["copy_module"] == "policyelements"
    assert args["copy_service"] == "network-device"
    assert args["legacy_copy_syntax"] is True
