import types
import sys
import pytest

import arapy.main as main
import arapy.config as config


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


def test_main_end_to_end_calls_login_and_action(monkeypatch):
    calls = {}

    # --- patch logging manager ---
    mgr = FakeLogMgr()
    monkeypatch.setattr(main, "build_logger_from_env", lambda root_name: mgr)

    # --- patch ClearPass client ---
    class FakeCP:
        def __init__(self, server, https_prefix, verify_ssl, timeout):
            calls["cp_init"] = dict(server=server, https_prefix=https_prefix, verify_ssl=verify_ssl, timeout=timeout)
        def login(self, api_paths, credentials):
            calls["login"] = dict(api_paths=api_paths, credentials=credentials)
            return {"access_token": "TOKEN"}

    monkeypatch.setattr(main, "ClearPassClient", FakeCP)

    # --- patch config secrets to avoid using real ones ---
    monkeypatch.setattr(config, "SERVER", "example:443", raising=False)
    monkeypatch.setattr(config, "HTTPS", "https://", raising=False)
    monkeypatch.setattr(config, "VERIFY_SSL", False, raising=False)
    monkeypatch.setattr(config, "DEFAULT_TIMEOUT", 1, raising=False)
    monkeypatch.setattr(config, "CREDENTIALS", {"client_id": "x", "client_secret": "y"}, raising=False)

    # --- patch action dispatch ---
    def fake_action(cp, token, api_paths, args):
        calls["action"] = dict(cp=cp, token=token, api_paths=api_paths, args=args)

    monkeypatch.setitem(main.commands.ACTIONS, "list", fake_action)

    monkeypatch.setattr(sys, "argv", ["arapy", "identities", "endpoint", "list", "--limit=1", "--console"])
    main.main()

    assert calls["cp_init"]["server"] == "example:443"
    assert calls["login"]["credentials"] == {"client_id": "x", "client_secret": "y"}
    assert calls["action"]["token"] == "TOKEN"
    assert calls["action"]["args"]["module"] == "identities"
    assert calls["action"]["args"]["service"] == "endpoint"
    assert calls["action"]["args"]["action"] == "list"
    assert calls["action"]["args"]["limit"] == "1"


def test_main_invalid_log_level_exits_early(monkeypatch, capsys):
    mgr = FakeLogMgr()
    monkeypatch.setattr(main, "build_logger_from_env", lambda root_name: mgr)
    # if it tries to create CP, fail loudly
    monkeypatch.setattr(main, "ClearPassClient", lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not create client")))

    monkeypatch.setattr(sys, "argv", ["arapy", "identities", "endpoint", "list", "--log_level=nope"])
    main.main()

    assert mgr.logger.errors, "expected an error log for invalid log_level"
    assert "Invalid log level" in mgr.logger.errors[0]


def test_main_version_prints_and_exits(monkeypatch, capsys):
    mgr = FakeLogMgr()
    monkeypatch.setattr(main, "build_logger_from_env", lambda root_name: mgr)
    monkeypatch.setattr(main, "get_version", lambda: "9.9.9")

    monkeypatch.setattr(sys, "argv", ["arapy", "--version"])
    main.main()

    assert capsys.readouterr().out.strip() == "9.9.9"


def test_main_help_prints_and_exits(monkeypatch, capsys):
    mgr = FakeLogMgr()
    monkeypatch.setattr(main, "build_logger_from_env", lambda root_name: mgr)

    # If it tries to connect, fail
    monkeypatch.setattr(main, "ClearPassClient", lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not create client")))

    monkeypatch.setattr(sys, "argv", ["arapy", "--help"])
    main.main()
    out = capsys.readouterr().out
    assert "Usage:" in out


def test_main_unknown_action_prints_help_and_message(monkeypatch, capsys):
    mgr = FakeLogMgr()
    monkeypatch.setattr(main, "build_logger_from_env", lambda root_name: mgr)

    # ensure action isn't in ACTIONS for this test
    if "doesnotexist" in main.commands.ACTIONS:
        monkeypatch.delitem(main.commands.ACTIONS, "doesnotexist", raising=False)

    # prevent network
    monkeypatch.setattr(main, "ClearPassClient", lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not create client")))

    monkeypatch.setattr(sys, "argv", ["arapy", "identities", "endpoint", "doesnotexist"])
    main.main()

    out = capsys.readouterr().out
    assert "Unknown command:" in out


def test_main_complete_mode_outputs_and_exits(monkeypatch, capsys):
    # should not create a logger or client in completion mode
    monkeypatch.setattr(main, "build_logger_from_env", lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not build logger")))
    monkeypatch.setattr(main, "ClearPassClient", lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not create client")))

    monkeypatch.setattr(sys, "argv", ["arapy", "--_complete", "--_cur="])
    main.main()
    out = capsys.readouterr().out
    assert "identities" in out
