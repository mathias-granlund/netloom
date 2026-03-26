import builtins
import importlib
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


def _settings(*, plugin=None):
    paths = AppPaths(
        cache_dir=Path("cache"),
        state_dir=Path("state"),
        response_dir=Path("responses"),
        app_log_dir=Path("logs"),
    )
    return Settings(plugin=plugin, paths=paths)


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


def test_complete_uses_direct_cached_index_without_get_plugin(capsys, monkeypatch):
    monkeypatch.setattr(
        main,
        "load_cached_catalog_for_plugin",
        lambda name, **kwargs: TEST_CATALOG,
    )
    monkeypatch.setattr(
        main,
        "get_plugin",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("should not load plugin")
        ),
    )

    main.complete(["--_cur="], settings=_settings(plugin="clearpass"))

    out = capsys.readouterr().out.strip().splitlines()
    assert "identities" in out


def test_complete_fast_path_does_not_import_plugin_layer(capsys, monkeypatch):
    monkeypatch.setattr(main, "_import_cache_layer", lambda: None)
    monkeypatch.setattr(main, "_import_interactive_layer", lambda: None)
    monkeypatch.setattr(
        main,
        "_import_plugin_layer",
        lambda: (_ for _ in ()).throw(AssertionError("should not import plugin layer")),
    )
    monkeypatch.setattr(
        main,
        "load_cached_catalog_for_plugin",
        lambda name, **kwargs: TEST_CATALOG,
    )

    main.complete(["--_cur="], settings=_settings(plugin="clearpass"))

    out = capsys.readouterr().out.strip().splitlines()
    assert "identities" in out


def test_complete_falls_back_to_get_plugin_when_direct_index_missing(
    capsys, monkeypatch
):
    plugin = _catalog_plugin(TEST_CATALOG)
    monkeypatch.setattr(
        main,
        "load_cached_catalog_for_plugin",
        lambda name, **kwargs: None,
    )
    monkeypatch.setattr(main, "get_plugin", lambda *args, **kwargs: plugin)

    main.complete(["--_cur="], settings=_settings(plugin="clearpass"))

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


def test_print_help_server_builtin_does_not_touch_plugin_or_cache(monkeypatch, capsys):
    monkeypatch.setattr(main, "render_help", lambda *args, **kwargs: "server help")
    monkeypatch.setattr(
        main,
        "load_cached_catalog_for_plugin",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("should not load cache")
        ),
    )
    monkeypatch.setattr(
        main,
        "get_plugin",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("should not load plugin")
        ),
    )
    monkeypatch.setattr(main, "get_version", lambda: "1.9.6")

    main.print_help({"module": "server"}, settings=_settings(plugin="clearpass"))

    out = capsys.readouterr().out
    assert "server help" in out


def test_print_help_top_level_uses_direct_cached_index_without_get_plugin(
    monkeypatch, capsys
):
    monkeypatch.setattr(
        main,
        "load_cached_catalog_for_plugin",
        lambda name, **kwargs: TEST_CATALOG,
    )
    monkeypatch.setattr(
        main,
        "get_plugin",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("should not load plugin")
        ),
    )
    monkeypatch.setattr(main, "get_version", lambda: "1.9.6")

    main.print_help({}, settings=_settings(plugin="clearpass"))

    out = capsys.readouterr().out
    assert "Available modules:" in out
    assert "Examples:" not in out


def test_print_help_uses_direct_cached_index_without_get_plugin(monkeypatch, capsys):
    monkeypatch.setattr(
        main,
        "load_cached_catalog_for_plugin",
        lambda name, **kwargs: TEST_CATALOG,
    )
    monkeypatch.setattr(
        main,
        "get_plugin",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("should not load plugin")
        ),
    )
    monkeypatch.setattr(main, "get_version", lambda: "1.9.6")

    main.print_help({"module": "identities"}, settings=_settings(plugin="clearpass"))

    out = capsys.readouterr().out
    assert "Module: identities" in out
    assert "Available services:" in out


def test_print_help_fast_path_does_not_import_plugin_layer(monkeypatch, capsys):
    monkeypatch.setattr(main, "_import_cache_layer", lambda: None)
    monkeypatch.setattr(main, "_import_interactive_layer", lambda: None)
    monkeypatch.setattr(
        main,
        "_import_plugin_layer",
        lambda: (_ for _ in ()).throw(AssertionError("should not import plugin layer")),
    )
    monkeypatch.setattr(
        main,
        "load_cached_catalog_for_plugin",
        lambda name, **kwargs: TEST_CATALOG,
    )
    monkeypatch.setattr(main, "get_version", lambda: "1.9.6")

    main.print_help({"module": "identities"}, settings=_settings(plugin="clearpass"))

    out = capsys.readouterr().out
    assert "Module: identities" in out
    assert "Available services:" in out


def test_print_help_falls_back_to_get_plugin_when_direct_index_missing(
    monkeypatch, capsys
):
    plugin = _catalog_plugin(TEST_CATALOG)
    monkeypatch.setattr(
        main,
        "load_cached_catalog_for_plugin",
        lambda name, **kwargs: None,
    )
    monkeypatch.setattr(main, "get_plugin", lambda *args, **kwargs: plugin)
    monkeypatch.setattr(main, "get_version", lambda: "1.9.6")

    main.print_help({"module": "identities"}, settings=_settings(plugin="clearpass"))

    out = capsys.readouterr().out
    assert "Module: identities" in out
    assert "Available services:" in out


def test_complete_emits_timing_when_enabled(capsys, monkeypatch):
    plugin = _catalog_plugin(TEST_CATALOG)
    monkeypatch.setattr(main, "get_plugin", lambda *args, **kwargs: plugin)
    monkeypatch.setenv("NETLOOM_COMPLETION_TIMING", "1")

    main.complete(["--_cur="], settings=_settings())

    captured = capsys.readouterr()
    assert "identities" in captured.out
    assert "[netloom timing] complete total=" in captured.err


def test_complete_timing_splits_import_bucket_from_completion_work(capsys, monkeypatch):
    monkeypatch.setattr(main, "_import_interactive_layer", lambda: None)
    monkeypatch.setattr(main, "_import_cache_layer", lambda: None)
    monkeypatch.setattr(main, "_import_completion_layer", lambda: None)
    monkeypatch.setattr(
        main,
        "load_cached_catalog_for_plugin",
        lambda name, **kwargs: TEST_CATALOG,
    )
    monkeypatch.setenv("NETLOOM_COMPLETION_TIMING", "1")

    main.complete(["--_cur="], settings=_settings(plugin="clearpass"))

    captured = capsys.readouterr()
    assert "identities" in captured.out
    assert "import_interactive_layer=" in captured.err
    assert "import_cache_layer=" in captured.err
    assert "load_core_cached_catalog=" in captured.err
    assert "import_completion_layer=" in captured.err
    assert "print_completions=" in captured.err


def test_complete_does_not_emit_timing_from_help_settings_flag(capsys, monkeypatch):
    plugin = _catalog_plugin(TEST_CATALOG)
    monkeypatch.setattr(main, "get_plugin", lambda *args, **kwargs: plugin)
    monkeypatch.delenv("NETLOOM_CLI_TIMING", raising=False)
    monkeypatch.delenv("NETLOOM_COMPLETION_TIMING", raising=False)

    settings = Settings(paths=_settings().paths, cli_timing=True)
    main.complete(["--_cur="], settings=settings)

    captured = capsys.readouterr()
    assert "identities" in captured.out
    assert "[netloom timing] complete total=" not in captured.err


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


def test_importing_main_does_not_eagerly_import_help_completion_or_plugin_layers(
    monkeypatch,
):
    real_import = builtins.__import__
    blocked = {
        "netloom.cli.completion",
        "netloom.core.compact_help",
        "netloom.core.cache",
        "netloom.core.interactive",
        "netloom.core.interactive_cache",
        "netloom.core.interactive_help",
        "netloom.core.config",
        "netloom.core.plugin",
    }

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name in blocked:
            raise AssertionError(f"should not import {name}")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    importlib.reload(main)


def test_main_version_skips_settings_and_logging(monkeypatch, capsys):
    monkeypatch.setattr(
        main,
        "load_settings",
        lambda: (_ for _ in ()).throw(AssertionError("should not load settings")),
    )
    monkeypatch.setattr(
        main,
        "configure_logging",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("should not configure logging")
        ),
    )
    monkeypatch.setattr(main, "get_version", lambda: "9.9.9")
    monkeypatch.setattr(main.sys, "argv", ["netloom", "--version"])

    main.main()

    assert capsys.readouterr().out.strip() == "9.9.9"


def test_main_help_skips_eager_settings_and_logging(monkeypatch, capsys):
    monkeypatch.setattr(
        main,
        "load_settings",
        lambda: (_ for _ in ()).throw(AssertionError("should not load settings")),
    )
    monkeypatch.setattr(
        main,
        "configure_logging",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("should not configure logging")
        ),
    )
    monkeypatch.setattr(
        main, "print_help", lambda args=None, **kwargs: print("Usage:\n  netloom ...")
    )
    monkeypatch.setattr(main.sys, "argv", ["netloom", "--help"])

    main.main()

    assert "Usage:" in capsys.readouterr().out


def test_print_help_timing_splits_import_buckets_from_render_and_cache_work(
    monkeypatch, capsys
):
    monkeypatch.setattr(main, "_import_interactive_layer", lambda: None)
    monkeypatch.setattr(main, "_import_cache_layer", lambda: None)
    monkeypatch.setattr(main, "_import_help_layer", lambda: None)
    monkeypatch.setattr(
        main,
        "load_cached_catalog_for_plugin",
        lambda name, **kwargs: TEST_CATALOG,
    )
    monkeypatch.setattr(main, "render_help", lambda *args, **kwargs: "help text")
    monkeypatch.setattr(main, "get_version", lambda: "1.9.8")
    monkeypatch.setenv("NETLOOM_CLI_TIMING", "1")

    main.print_help({"module": "identities"}, settings=_settings(plugin="clearpass"))

    captured = capsys.readouterr()
    assert "help text" in captured.out
    assert "import_interactive_layer=" in captured.err
    assert "import_cache_layer=" in captured.err
    assert "load_core_cached_catalog=" in captured.err
    assert "import_help_layer=" in captured.err
    assert "render_help=" in captured.err
