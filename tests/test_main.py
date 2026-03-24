import types
from pathlib import Path

import pytest

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
        load_cached_index=lambda settings=None, catalog_view="visible": catalog,
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
    assert "copy" not in out


def test_complete_honors_full_catalog_view_flag(capsys, monkeypatch):
    plugin = types.SimpleNamespace(
        load_cached_catalog=lambda settings=None, catalog_view="visible": (
            TEST_CATALOG
            if catalog_view == "visible"
            else {
                "modules": {
                    **TEST_CATALOG["modules"],
                    "policyelements": {
                        "network-device": {
                            "actions": {
                                "list": {
                                    "method": "GET",
                                    "paths": ["/api/network-device"],
                                }
                            }
                        }
                    },
                }
            }
        )
    )
    monkeypatch.setattr(main, "get_plugin", lambda *args, **kwargs: plugin)
    main.complete(["--catalog-view=full", "--_cur="], settings=_settings())
    out = capsys.readouterr().out.strip().splitlines()
    assert "identities" in out
    assert "policyelements" in out


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
    assert "diff" in out
    assert "list" in out
    assert "get" in out
    assert "copy" in out


def test_complete_prefers_cached_index(capsys, monkeypatch):
    plugin = types.SimpleNamespace(
        load_cached_index=lambda settings=None, catalog_view="visible": TEST_CATALOG,
        load_cached_catalog=lambda settings=None, catalog_view="visible": (
            _ for _ in ()
        ).throw(AssertionError("should not load full cache")),
    )
    monkeypatch.setattr(main, "get_plugin", lambda *args, **kwargs: plugin)

    main.complete(["--_cur="], settings=_settings())

    out = capsys.readouterr().out.strip().splitlines()
    assert "identities" in out


def test_complete_outputs_server_profiles_for_use(capsys, monkeypatch):
    plugin = _catalog_plugin(TEST_CATALOG)
    monkeypatch.setattr(main, "get_plugin", lambda *args, **kwargs: plugin)
    monkeypatch.setattr(completion, "list_profiles", lambda: ["dev", "prod"])
    main.complete(["server", "use"], settings=_settings())
    out = capsys.readouterr().out.strip().splitlines()
    assert "dev" in out
    assert "prod" in out


def test_complete_load_builtin_does_not_touch_plugin_or_settings(capsys, monkeypatch):
    monkeypatch.setattr(
        main,
        "load_settings",
        lambda: (_ for _ in ()).throw(AssertionError("should not load settings")),
    )
    monkeypatch.setattr(
        main,
        "get_plugin",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("should not load plugin")
        ),
    )
    monkeypatch.setattr(completion, "list_plugins", lambda: ["clearpass"])

    main.complete(["load"], settings=None)

    out = capsys.readouterr().out.strip().splitlines()
    assert "clearpass" in out


def test_complete_server_builtin_does_not_touch_plugin_or_settings(capsys, monkeypatch):
    monkeypatch.setattr(
        main,
        "load_settings",
        lambda: (_ for _ in ()).throw(AssertionError("should not load settings")),
    )
    monkeypatch.setattr(
        main,
        "get_plugin",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("should not load plugin")
        ),
    )

    main.complete(["server"], settings=None)

    out = capsys.readouterr().out.strip().splitlines()
    assert "use" in out


def test_print_help_prefers_cached_index_for_compact_help(monkeypatch, capsys):
    plugin = types.SimpleNamespace(
        load_cached_index=lambda settings=None, catalog_view="visible": TEST_CATALOG,
        load_cached_catalog=lambda settings=None, catalog_view="visible": (
            _ for _ in ()
        ).throw(AssertionError("should not load full cache")),
    )
    monkeypatch.setattr(main, "get_plugin", lambda *args, **kwargs: plugin)
    monkeypatch.setattr(main, "get_version", lambda: "1.9.6")

    main.print_help({"module": "identities"}, settings=_settings())

    out = capsys.readouterr().out
    assert "Module: identities" in out
    assert "Available services:" in out


def test_complete_emits_timing_when_enabled(capsys, monkeypatch):
    plugin = _catalog_plugin(TEST_CATALOG)
    monkeypatch.setattr(main, "get_plugin", lambda *args, **kwargs: plugin)
    monkeypatch.setenv("NETLOOM_CLI_TIMING", "1")

    main.complete(["--_cur="], settings=_settings())

    captured = capsys.readouterr()
    assert "identities" in captured.out
    assert "[netloom timing] complete total=" in captured.err


def test_complete_emits_timing_when_enabled_from_settings(capsys, monkeypatch):
    plugin = _catalog_plugin(TEST_CATALOG)
    monkeypatch.setattr(main, "get_plugin", lambda *args, **kwargs: plugin)
    monkeypatch.delenv("NETLOOM_CLI_TIMING", raising=False)

    settings = Settings(paths=_settings().paths, cli_timing=True)
    main.complete(["--_cur="], settings=settings)

    captured = capsys.readouterr()
    assert "identities" in captured.out
    assert "[netloom timing] complete total=" in captured.err


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


def test_parse_cli_catalog_view_flag():
    argv = [
        "netloom",
        "identities",
        "endpoint",
        "list",
        "--catalog-view=full",
    ]
    args = main.parse_cli(argv)
    assert args["catalog_view"] == "full"


def test_parse_cli_global_flags_before_dynamic_command():
    argv = [
        "netloom",
        "--catalog-view=full",
        "--log-level=debug",
        "identities",
        "endpoint",
        "list",
    ]
    args = main.parse_cli(argv)
    assert args["catalog_view"] == "full"
    assert args["log_level"] == "debug"
    assert args["module"] == "identities"
    assert args["service"] == "endpoint"
    assert args["action"] == "list"


def test_parse_cli_decrypt_flag():
    argv = ["netloom", "policyelements", "network-device", "list", "--decrypt"]
    args = main.parse_cli(argv)
    assert args["decrypt"] is True


def test_parse_cli_question_mark_sets_help_context():
    argv = ["netloom", "identities", "endpoint", "?"]
    args = main.parse_cli(argv)
    assert args["module"] == "identities"
    assert args["service"] == "endpoint"
    assert args["help"] is True


def test_parse_cli_server_builtin_uses_argparse_shape():
    argv = ["netloom", "--log-level=debug", "server", "use", "prod"]
    args = main.parse_cli(argv)
    assert args["module"] == "server"
    assert args["service"] == "use"
    assert args["action"] == "prod"
    assert args["log_level"] == "debug"


def test_parse_cli_cache_builtin_accepts_global_flag():
    argv = ["netloom", "--catalog-view=full", "cache", "update"]
    args = main.parse_cli(argv)
    assert args["module"] == "cache"
    assert args["service"] == "update"
    assert args["catalog_view"] == "full"


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


def test_parse_cli_diff_console_expansion_flags():
    argv = [
        "netloom",
        "policyelements",
        "network-device",
        "diff",
        "--from=dev",
        "--to=prod",
        "--all",
        "--show-all",
        "--max-items=25",
    ]
    args = main.parse_cli(argv)
    assert args["action"] == "diff"
    assert args["show_all"] is True
    assert args["max_items"] == "25"


def test_parse_cli_removed_legacy_copy_alias_is_not_special_cased():
    argv = ["netloom", "copy", "policyelements", "network-device", "--from=dev"]
    args = main.parse_cli(argv)
    assert args["module"] == "copy"
    assert args["service"] == "policyelements"
    assert args["action"] == "network-device"
    assert "copy_module" not in args
    assert "legacy_copy_syntax" not in args


def test_parse_cli_rejects_invalid_builtin_shape():
    argv = ["netloom", "load", "clearpass", "extra"]
    with pytest.raises(main.CliParseError, match="unrecognized arguments: extra"):
        main.parse_cli(argv)
