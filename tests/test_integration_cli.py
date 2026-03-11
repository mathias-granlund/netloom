import sys
import types

import arapy.cli.main as main
from arapy.core.config import AppPaths, Settings


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
        server="example:443",
        https_prefix="https://",
        verify_ssl=False,
        timeout=1,
        client_id="x",
        client_secret="y",
        paths=paths,
    )


def test_main_end_to_end_calls_login_and_action(monkeypatch, tmp_path):
    calls = {}
    mgr = FakeLogMgr()
    settings = make_settings(tmp_path)
    monkeypatch.setattr(main, "configure_logging", lambda settings, root_name: mgr)
    monkeypatch.setattr(main, "load_settings", lambda: settings)

    class FakeCP:
        def __init__(self, server, https_prefix, verify_ssl, timeout):
            calls["cp_init"] = dict(
                server=server,
                https_prefix=https_prefix,
                verify_ssl=verify_ssl,
                timeout=timeout,
            )

        def login(self, api_paths, credentials):
            calls["login"] = dict(api_paths=api_paths, credentials=credentials)
            return {"access_token": "TOKEN"}

    monkeypatch.setattr(main, "ClearPassClient", FakeCP)
    monkeypatch.setattr(
        main, "get_api_catalog", lambda cp, token, settings: {"modules": {}}
    )

    def fake_action(cp, token, api_paths, args, settings=None):
        calls["action"] = dict(
            cp=cp, token=token, api_paths=api_paths, args=args, settings=settings
        )

    monkeypatch.setitem(main.ACTIONS, "list", fake_action)

    monkeypatch.setattr(
        sys,
        "argv",
        ["arapy", "identities", "endpoint", "list", "--limit=1", "--console"],
    )
    main.main()

    assert calls["cp_init"]["server"] == "example:443"
    assert calls["login"]["credentials"]["client_id"] == "x"
    assert calls["action"]["token"] == "TOKEN"
    assert calls["action"]["args"]["module"] == "identities"
    assert calls["action"]["args"]["service"] == "endpoint"
    assert calls["action"]["args"]["action"] == "list"
    assert calls["action"]["args"]["limit"] == "1"


def test_main_invalid_log_level_exits_early(monkeypatch, tmp_path):
    mgr = FakeLogMgr()
    settings = make_settings(tmp_path)
    monkeypatch.setattr(main, "configure_logging", lambda settings, root_name: mgr)
    monkeypatch.setattr(main, "load_settings", lambda: settings)
    monkeypatch.setattr(
        main,
        "ClearPassClient",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("should not create client")
        ),
    )

    monkeypatch.setattr(
        sys,
        "argv",
        ["arapy", "identities", "endpoint", "list", "--log_level=nope"],
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

    monkeypatch.setattr(sys, "argv", ["arapy", "--version"])
    main.main()

    assert capsys.readouterr().out.strip() == "9.9.9"


def test_main_help_prints_and_exits(monkeypatch, capsys, tmp_path):
    mgr = FakeLogMgr()
    settings = make_settings(tmp_path)
    monkeypatch.setattr(main, "configure_logging", lambda settings, root_name: mgr)
    monkeypatch.setattr(main, "load_settings", lambda: settings)
    monkeypatch.setattr(
        main, "print_help", lambda args=None: print("Usage:\n  arapy ...")
    )

    monkeypatch.setattr(sys, "argv", ["arapy", "--help"])
    main.main()
    out = capsys.readouterr().out
    assert "Usage:" in out


def test_main_unknown_action_prints_help_and_message(monkeypatch, capsys, tmp_path):
    mgr = FakeLogMgr()
    settings = make_settings(tmp_path)
    monkeypatch.setattr(main, "configure_logging", lambda settings, root_name: mgr)
    monkeypatch.setattr(main, "load_settings", lambda: settings)
    monkeypatch.setattr(
        main, "print_help", lambda args=None: print("Usage:\n  arapy ...")
    )

    if "doesnotexist" in main.ACTIONS:
        monkeypatch.delitem(main.ACTIONS, "doesnotexist", raising=False)

    monkeypatch.setattr(
        sys,
        "argv",
        ["arapy", "identities", "endpoint", "doesnotexist"],
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
        "ClearPassClient",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("should not create client")
        ),
    )
    monkeypatch.setattr(
        main,
        "load_cached_catalog",
        lambda settings=None: {"modules": {"identities": {}}},
    )

    monkeypatch.setattr(sys, "argv", ["arapy", "--_complete", "--_cur="])
    main.main()
    out = capsys.readouterr().out
    assert "identities" in out


def test_main_uses_direct_api_token_without_login(monkeypatch, tmp_path):
    calls = {}
    mgr = FakeLogMgr()
    settings = make_settings(tmp_path)
    monkeypatch.setattr(main, "configure_logging", lambda settings, root_name: mgr)
    monkeypatch.setattr(main, "load_settings", lambda: settings)

    class FakeCP:
        def __init__(self, server, https_prefix, verify_ssl, timeout):
            calls["cp_init"] = dict(
                server=server,
                https_prefix=https_prefix,
                verify_ssl=verify_ssl,
                timeout=timeout,
            )

        def login(self, api_paths, credentials):
            raise AssertionError("login should not be called when --api-token is set")

    monkeypatch.setattr(main, "ClearPassClient", FakeCP)
    monkeypatch.setattr(
        main, "get_api_catalog", lambda cp, token, settings: {"modules": {}}
    )

    def fake_action(cp, token, api_paths, args, settings=None):
        calls["action"] = {"token": token, "args": args, "settings": settings}

    monkeypatch.setitem(main.ACTIONS, "list", fake_action)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "arapy",
            "identities",
            "endpoint",
            "list",
            "--api-token=CLI-TOKEN",
        ],
    )

    main.main()

    assert calls["action"]["token"] == "CLI-TOKEN"
