from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from netloom.contracts import ExecutionOptions, NetloomRequest, NetloomResult
from netloom.core import runtime
from netloom.core.config import AppPaths, Settings


def _settings() -> Settings:
    paths = AppPaths(
        cache_dir=Path("cache"),
        state_dir=Path("state"),
        response_dir=Path("responses"),
        app_log_dir=Path("logs"),
    )
    return Settings(plugin="clearpass", paths=paths)


class _Log:
    def __init__(self):
        self.errors: list[tuple] = []

    def error(self, *args):
        self.errors.append(args)

    def info(self, *args):
        return None


class _LogManager:
    def __init__(self):
        self.log = _Log()
        self.levels: list[int] = []

    def get_logger(self, name):
        return self.log

    def set_level(self, level):
        self.levels.append(level)


def test_run_request_orchestrates_plugin_action_through_core():
    calls: dict[str, object] = {}
    settings = _settings()
    catalog = {"modules": {}}
    cp = object()

    def build_client(active_settings, mask_secrets=True):
        calls["client"] = (active_settings, mask_secrets)
        return cp

    def resolve_auth_token(client, active_settings):
        calls["token"] = (client, active_settings.api_token)
        return "token"

    plugin = SimpleNamespace(
        name="clearpass",
        display_name="ClearPass",
        build_client=build_client,
        resolve_auth_token=resolve_auth_token,
    )

    def action(client, token, api_catalog, args, *, settings):
        calls["action"] = {
            "client": client,
            "token": token,
            "catalog": api_catalog,
            "args": args,
            "settings": settings,
        }
        return {"items": []}

    log_manager = _LogManager()

    class Deps:
        def load_settings(self):
            return settings

        def configure_logging(self, active_settings, *, root_name):
            calls["logging"] = (active_settings, root_name)
            return log_manager

        def _log_levels(self):
            return {"INFO": 20, "DEBUG": 10}

        def get_plugin(self, name, *, settings):
            calls["plugin"] = (name, settings.api_token)
            return plugin

        def should_mask_secrets(self, args, active_settings):
            calls["mask_args"] = dict(args)
            return False

        def _get_catalog_for_cli(self, selected_plugin, client, **kwargs):
            calls["catalog"] = (selected_plugin, client, kwargs)
            return catalog

        def _actions(self):
            return {"list": action}

        def handle_import_command(self, *args, **kwargs):
            raise AssertionError("should not handle import")

        def handle_show_command(self, *args, **kwargs):
            raise AssertionError("should not handle show")

    request = NetloomRequest.from_mapping(
        {
            "module": "identities",
            "service": "endpoint",
            "action": "list",
            "catalog_view": "full",
            "token": "abc123",
        }
    )

    result = runtime.run_request(
        request,
        runtime.execution_options_from_mapping(request.to_mapping()),
        deps=Deps(),
    )

    assert result == NetloomResult(
        data={"items": []},
        metadata={
            "module": "identities",
            "service": "endpoint",
            "action": "list",
            "plugin": "clearpass",
        },
    )
    assert calls["plugin"] == (None, "abc123")
    assert calls["client"][1] is False
    assert calls["catalog"][2]["catalog_view"] == "full"
    assert calls["action"]["args"]["catalog_view"] == "full"


def test_run_request_returns_help_result_for_unknown_action():
    settings = _settings()

    class Deps:
        def load_settings(self):
            return settings

        def configure_logging(self, active_settings, *, root_name):
            return _LogManager()

        def _log_levels(self):
            return {"INFO": 20}

        def get_plugin(self, name, *, settings):
            return SimpleNamespace(name="clearpass")

        def _actions(self):
            return {}

        def handle_import_command(self, *args, **kwargs):
            return False

        def handle_show_command(self, *args, **kwargs):
            return False

    result = runtime.run_request(
        NetloomRequest(module="identities", service="endpoint", action="missing"),
        ExecutionOptions(),
        deps=Deps(),
    )

    assert result.status == "help"
    assert result.message == "Unknown command: identities endpoint missing"
    assert result.metadata["settings"].plugin == "clearpass"


def test_cli_run_cli_delegates_plugin_backed_requests_to_core_runtime(monkeypatch):
    from netloom.cli import runtime as cli_runtime

    captured: dict[str, object] = {}

    def fake_run_request(request, options, *, deps):
        captured["request"] = request
        captured["options"] = options
        captured["deps"] = deps
        return NetloomResult()

    monkeypatch.setattr(cli_runtime.core_runtime, "run_request", fake_run_request)

    deps = SimpleNamespace(
        get_version=lambda: "1.0.0",
        print_help=lambda *args, **kwargs: None,
    )
    args = {
        "module": "identities",
        "service": "endpoint",
        "action": "list",
        "console": True,
    }

    cli_runtime.run_cli(args, deps=deps)

    assert captured["request"].module == "identities"
    assert captured["request"].service == "endpoint"
    assert captured["request"].action == "list"
    assert captured["options"].console is True
    assert captured["deps"] is deps
