import sys
import types

import netloom.cli.main as main
from netloom.core.config import AppPaths, Settings


class FakeLogger:
    def __init__(self):
        self.debugs = []
        self.infos = []
        self.errors = []

    def debug(self, msg, *args, **kwargs):
        if args:
            msg = msg % args
        self.debugs.append(msg)

    def info(self, msg, *args, **kwargs):
        if args:
            msg = msg % args
        self.infos.append(msg)

    def error(self, msg, *args, **kwargs):
        if args:
            msg = msg % args
        self.errors.append(msg)


class FakeLogMgr:
    def __init__(self):
        self.root = types.SimpleNamespace(level=None, handlers=[])
        self.logger = FakeLogger()
        self.levels = []

    def get_logger(self, name):
        return self.logger

    def set_level(self, level):
        self.levels.append(level)


def make_settings(tmp_path):
    paths = AppPaths(
        cache_dir=tmp_path / "cache",
        state_dir=tmp_path / "state",
        response_dir=tmp_path / "responses",
        app_log_dir=tmp_path / "logs",
    ).ensure()
    return Settings(
        plugin="clearpass",
        server="example:443",
        https_prefix="https://",
        verify_ssl=False,
        timeout=1,
        client_id="x",
        client_secret="y",
        paths=paths,
    )


def _plugin_with_catalog(catalog):
    return types.SimpleNamespace(
        name="clearpass",
        build_client=lambda settings, mask_secrets=True: None,
        resolve_auth_token=lambda cp, settings: "TOKEN",
        get_api_catalog=lambda cp, token, settings=None, force_refresh=False: catalog,
        load_cached_catalog=lambda settings=None: catalog,
        clear_api_cache=lambda settings=None: True,
    )


def test_main_end_to_end_calls_login_and_action(monkeypatch, tmp_path):
    calls = {}
    mgr = FakeLogMgr()
    settings = make_settings(tmp_path)
    monkeypatch.setattr(main, "configure_logging", lambda settings, root_name: mgr)
    monkeypatch.setattr(main, "load_settings", lambda: settings)

    class FakeCP:
        pass

    def build_client(settings, mask_secrets=True):
        calls["cp_init"] = dict(
            server=settings.server,
            https_prefix=settings.https_prefix,
            verify_ssl=settings.verify_ssl,
            timeout=settings.timeout,
            mask_secrets=mask_secrets,
        )
        return FakeCP()

    def resolve_auth_token(cp, settings):
        calls["login"] = dict(
            credentials=settings.credentials,
            server=settings.server,
        )
        return "TOKEN"

    plugin = types.SimpleNamespace(
        name="clearpass",
        build_client=build_client,
        resolve_auth_token=resolve_auth_token,
        get_api_catalog=lambda cp, token, settings=None, force_refresh=False: {
            "modules": {}
        },
        load_cached_catalog=lambda settings=None: {"modules": {}},
        clear_api_cache=lambda settings=None: True,
    )
    monkeypatch.setattr(main, "get_plugin", lambda *args, **kwargs: plugin)

    def fake_action(cp, token, api_paths, args, settings=None):
        calls["action"] = dict(
            cp=cp, token=token, api_paths=api_paths, args=args, settings=settings
        )

    monkeypatch.setitem(main.ACTIONS, "list", fake_action)

    monkeypatch.setattr(
        sys,
        "argv",
        ["netloom", "identities", "endpoint", "list", "--limit=1", "--console"],
    )
    main.main()

    assert calls["cp_init"]["server"] == "example:443"
    assert calls["login"]["credentials"]["client_id"] == "x"
    assert calls["action"]["token"] == "TOKEN"
    assert calls["action"]["args"]["module"] == "identities"
    assert calls["action"]["args"]["service"] == "endpoint"
    assert calls["action"]["args"]["action"] == "list"
    assert calls["action"]["args"]["limit"] == "1"
    assert all("TOKEN" not in message for message in mgr.logger.debugs)


def test_main_invalid_log_level_exits_early(monkeypatch, tmp_path):
    mgr = FakeLogMgr()
    settings = make_settings(tmp_path)
    monkeypatch.setattr(main, "configure_logging", lambda settings, root_name: mgr)
    monkeypatch.setattr(main, "load_settings", lambda: settings)
    monkeypatch.setattr(
        main,
        "get_plugin",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("should not resolve plugin")
        ),
    )

    monkeypatch.setattr(
        sys,
        "argv",
        ["netloom", "identities", "endpoint", "list", "--log_level=nope"],
    )
    main.main()

    assert mgr.logger.errors
    assert "Invalid log level" in mgr.logger.errors[0]


def test_main_version_prints_and_exits(monkeypatch, capsys, tmp_path):
    mgr = FakeLogMgr()
    settings = make_settings(tmp_path)
    monkeypatch.setattr(main, "configure_logging", lambda settings, root_name: mgr)
    monkeypatch.setattr(main, "load_settings", lambda: settings)
    monkeypatch.setattr(main, "get_version", lambda: "9.9.9")

    monkeypatch.setattr(sys, "argv", ["netloom", "--version"])
    main.main()

    assert capsys.readouterr().out.strip() == "9.9.9"


def test_main_help_prints_and_exits(monkeypatch, capsys, tmp_path):
    mgr = FakeLogMgr()
    settings = make_settings(tmp_path)
    monkeypatch.setattr(main, "configure_logging", lambda settings, root_name: mgr)
    monkeypatch.setattr(main, "load_settings", lambda: settings)
    monkeypatch.setattr(
        main, "print_help", lambda args=None, **kwargs: print("Usage:\n  netloom ...")
    )

    monkeypatch.setattr(sys, "argv", ["netloom", "--help"])
    main.main()
    out = capsys.readouterr().out
    assert "Usage:" in out


def test_main_unknown_action_prints_help_and_message(monkeypatch, capsys, tmp_path):
    mgr = FakeLogMgr()
    settings = make_settings(tmp_path)
    plugin = _plugin_with_catalog({"modules": {}})
    monkeypatch.setattr(main, "configure_logging", lambda settings, root_name: mgr)
    monkeypatch.setattr(main, "load_settings", lambda: settings)
    monkeypatch.setattr(
        main, "print_help", lambda args=None, **kwargs: print("Usage:\n  netloom ...")
    )
    monkeypatch.setattr(main, "get_plugin", lambda *args, **kwargs: plugin)

    if "doesnotexist" in main.ACTIONS:
        monkeypatch.delitem(main.ACTIONS, "doesnotexist", raising=False)

    monkeypatch.setattr(
        sys,
        "argv",
        ["netloom", "identities", "endpoint", "doesnotexist"],
    )
    main.main()

    out = capsys.readouterr().out
    assert "Unknown command:" in out


def test_main_complete_mode_outputs_and_exits(monkeypatch, capsys, tmp_path):
    settings = make_settings(tmp_path)
    monkeypatch.setattr(main, "load_settings", lambda: settings)
    monkeypatch.setattr(
        main,
        "configure_logging",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("should not build logger")
        ),
    )
    monkeypatch.setattr(
        main,
        "get_plugin",
        lambda *args, **kwargs: _plugin_with_catalog({"modules": {"identities": {}}}),
    )

    monkeypatch.setattr(sys, "argv", ["netloom", "--_complete", "--_cur="])
    main.main()
    out = capsys.readouterr().out
    assert "identities" in out


def test_main_complete_mode_without_plugin_still_outputs_builtins(
    monkeypatch, capsys, tmp_path
):
    settings = make_settings(tmp_path)
    settings = types.SimpleNamespace(**{**settings.__dict__, "plugin": None})
    monkeypatch.setattr(main, "load_settings", lambda: settings)
    monkeypatch.setattr(
        main,
        "configure_logging",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("should not build logger")
        ),
    )
    monkeypatch.setattr(
        main,
        "get_plugin",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("no plugin")),
    )

    monkeypatch.setattr(sys, "argv", ["netloom", "--_complete", "--_cur="])
    main.main()
    out = capsys.readouterr().out
    assert "load" in out
    assert "server" in out


def test_main_complete_server_builtin_skips_runtime_setup(monkeypatch, capsys):
    monkeypatch.setattr(
        main,
        "load_settings",
        lambda: (_ for _ in ()).throw(AssertionError("should not load settings")),
    )
    monkeypatch.setattr(
        main,
        "configure_logging",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("should not build logger")
        ),
    )
    monkeypatch.setattr(
        main,
        "get_plugin",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("should not load plugin")
        ),
    )

    monkeypatch.setattr(sys, "argv", ["netloom", "--_complete", "server", "--_cur="])
    main.main()
    out = capsys.readouterr().out
    assert "use" in out


def test_main_uses_direct_api_token_without_login(monkeypatch, tmp_path):
    calls = {}
    mgr = FakeLogMgr()
    settings = make_settings(tmp_path)
    monkeypatch.setattr(main, "configure_logging", lambda settings, root_name: mgr)
    monkeypatch.setattr(main, "load_settings", lambda: settings)

    class FakeCP:
        pass

    def build_client(settings, mask_secrets=True):
        calls["cp_init"] = dict(
            server=settings.server,
            https_prefix=settings.https_prefix,
            verify_ssl=settings.verify_ssl,
            timeout=settings.timeout,
            mask_secrets=mask_secrets,
        )
        return FakeCP()

    def resolve_auth_token(cp, settings):
        calls["token"] = settings.api_token
        return settings.api_token

    plugin = types.SimpleNamespace(
        name="clearpass",
        build_client=build_client,
        resolve_auth_token=resolve_auth_token,
        get_api_catalog=lambda cp, token, settings=None, force_refresh=False: {
            "modules": {}
        },
        load_cached_catalog=lambda settings=None: {"modules": {}},
        clear_api_cache=lambda settings=None: True,
    )
    monkeypatch.setattr(main, "get_plugin", lambda *args, **kwargs: plugin)

    def fake_action(cp, token, api_paths, args, settings=None):
        calls["action"] = {"token": token, "args": args, "settings": settings}

    monkeypatch.setitem(main.ACTIONS, "list", fake_action)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "netloom",
            "identities",
            "endpoint",
            "list",
            "--api-token=CLI-TOKEN",
        ],
    )

    main.main()

    assert calls["action"]["token"] == "CLI-TOKEN"


def test_main_plugin_backed_command_without_plugin_prints_message(
    monkeypatch, capsys, tmp_path
):
    mgr = FakeLogMgr()
    settings = make_settings(tmp_path)
    settings = types.SimpleNamespace(**{**settings.__dict__, "plugin": None})
    monkeypatch.setattr(main, "configure_logging", lambda settings, root_name: mgr)
    monkeypatch.setattr(main, "load_settings", lambda: settings)
    message = (
        "No active plugin selected. Use `netloom load <plugin>` before running "
        "plugin-backed commands."
    )
    monkeypatch.setattr(
        main,
        "get_plugin",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError(message)),
    )

    monkeypatch.setattr(
        sys,
        "argv",
        ["netloom", "identities", "endpoint", "list"],
    )
    main.main()

    out = capsys.readouterr().out
    assert "No active plugin selected." in out


def test_main_copy_invokes_copy_handler(monkeypatch, tmp_path):
    calls = {}
    mgr = FakeLogMgr()
    settings = make_settings(tmp_path)
    plugin = _plugin_with_catalog({"modules": {}})
    monkeypatch.setattr(main, "configure_logging", lambda settings, root_name: mgr)
    monkeypatch.setattr(main, "load_settings", lambda: settings)
    monkeypatch.setattr(
        main,
        "handle_copy_command",
        lambda args, **kwargs: calls.update({"args": args, "kwargs": kwargs}),
    )
    monkeypatch.setattr(main, "get_plugin", lambda *args, **kwargs: plugin)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "netloom",
            "policyelements",
            "network-device",
            "copy",
            "--from=dev",
            "--to=prod",
            "--all",
        ],
    )

    main.main()

    assert calls["args"]["module"] == "policyelements"
    assert calls["args"]["service"] == "network-device"
    assert calls["args"]["action"] == "copy"
    assert calls["args"]["copy_module"] == "policyelements"
    assert calls["args"]["copy_service"] == "network-device"
    assert calls["kwargs"]["settings"] == settings


def test_main_diff_invokes_diff_handler(monkeypatch, tmp_path):
    calls = {}
    mgr = FakeLogMgr()
    settings = make_settings(tmp_path)
    plugin = _plugin_with_catalog({"modules": {}})
    monkeypatch.setattr(main, "configure_logging", lambda settings, root_name: mgr)
    monkeypatch.setattr(main, "load_settings", lambda: settings)
    monkeypatch.setattr(
        main,
        "handle_diff_command",
        lambda args, **kwargs: calls.update({"args": args, "kwargs": kwargs}),
    )
    monkeypatch.setattr(main, "get_plugin", lambda *args, **kwargs: plugin)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "netloom",
            "policyelements",
            "network-device",
            "diff",
            "--from=dev",
            "--to=prod",
            "--all",
        ],
    )

    main.main()

    assert calls["args"]["module"] == "policyelements"
    assert calls["args"]["service"] == "network-device"
    assert calls["args"]["action"] == "diff"
    assert calls["kwargs"]["settings"] == settings


def test_main_legacy_copy_alias_prints_default_help(monkeypatch, capsys, tmp_path):
    mgr = FakeLogMgr()
    settings = make_settings(tmp_path)
    monkeypatch.setattr(main, "configure_logging", lambda settings, root_name: mgr)
    monkeypatch.setattr(main, "load_settings", lambda: settings)
    monkeypatch.setattr(
        main,
        "print_help",
        lambda args=None, **kwargs: print("Usage:\n  netloom ..."),
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "netloom",
            "copy",
            "policyelements",
            "network-device",
            "--from=dev",
            "--to=prod",
        ],
    )

    main.main()

    out = capsys.readouterr().out
    assert "Usage:" in out
    assert "Legacy command removed" not in out
