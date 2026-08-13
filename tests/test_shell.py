from pathlib import Path
from types import SimpleNamespace

import netloom.cli.main as main
from netloom.cli.shell import NetloomShell
from netloom.core.config import AppPaths, Settings

TEST_CATALOG = {
    "modules": {
        "policyelements": {
            "network-device": {
                "actions": {
                    "list": {"method": "GET", "paths": ["/api/network-device"]},
                    "get": {"method": "GET", "paths": ["/api/network-device/{id}"]},
                }
            },
            "service-template": {
                "actions": {
                    "list": {"method": "GET", "paths": ["/api/service-template"]},
                }
            },
        }
    }
}


def _settings(profile: str = "dev", plugin: str | None = "clearpass") -> Settings:
    return Settings(
        plugin=plugin,
        active_profile=profile,
        paths=AppPaths(
            cache_dir=Path("cache"),
            state_dir=Path("state"),
            response_dir=Path("responses"),
            app_log_dir=Path("logs"),
        ),
    )


class FakeDeps:
    def __init__(self) -> None:
        self.settings = _settings()
        self.catalog = TEST_CATALOG
        self.executed: list[dict] = []
        self.help_calls: list[dict] = []

    def load_settings(self) -> Settings:
        return self.settings

    def get_plugin(self, name, *, settings=None):
        return SimpleNamespace(name=(settings.plugin if settings else "clearpass"))

    def load_cached_catalog_for_plugin(self, name, **kwargs):
        return self.catalog if name else None

    def parse_cli(self, argv: list[str]) -> dict:
        return main.parse_cli(argv)

    def run_cli(self, args: dict) -> None:
        self.executed.append(dict(args))
        if args.get("module") == "server" and args.get("service") == "use":
            self.settings = _settings(profile=str(args.get("action")))

    def render_help(self, api_catalog, args, *, version, plugin=None) -> str:
        self.help_calls.append(dict(args))
        return f"HELP {args}"

    def get_version(self) -> str:
        return "1.11.1"


def test_shell_executes_relative_command_from_service_context(capsys):
    deps = FakeDeps()
    prompts: list[str] = []
    commands = iter(
        [
            "policyelements",
            "network-device",
            "list --limit=10",
            "quit",
        ]
    )

    def fake_input(prompt: str) -> str:
        prompts.append(prompt)
        return next(commands)

    NetloomShell(deps=deps, input_func=fake_input).run()

    assert prompts[0] == "dev:netloom# "
    assert prompts[1] == "dev:netloom/policyelements# "
    assert prompts[2] == "dev:netloom/policyelements/network-device# "
    assert deps.executed == [
        {
            "module": "policyelements",
            "service": "network-device",
            "action": "list",
            "limit": "10",
        }
    ]
    assert "Entering netloom shell" in capsys.readouterr().out


def test_shell_updates_prompt_after_server_use():
    deps = FakeDeps()
    prompts: list[str] = []
    commands = iter(["server use prod", "quit"])

    def fake_input(prompt: str) -> str:
        prompts.append(prompt)
        return next(commands)

    NetloomShell(deps=deps, input_func=fake_input).run()

    assert prompts[0] == "dev:netloom# "
    assert prompts[1] == "prod:netloom# "


def test_shell_show_running_config_uses_module_context():
    deps = FakeDeps()
    commands = iter(
        [
            "policyelements",
            "show running-config --continue-on-error",
            "quit",
        ]
    )

    def fake_input(prompt: str) -> str:
        return next(commands)

    NetloomShell(deps=deps, input_func=fake_input).run()

    assert deps.executed == [
        {
            "module": "show",
            "service": "running-config",
            "include": "policyelements",
            "continue_on_error": True,
        }
    ]


def test_shell_show_running_config_uses_service_context():
    deps = FakeDeps()
    commands = iter(
        [
            "policyelements",
            "network-device",
            "show running-config --log-level=debug",
            "quit",
        ]
    )

    def fake_input(prompt: str) -> str:
        return next(commands)

    NetloomShell(deps=deps, input_func=fake_input).run()

    assert deps.executed == [
        {
            "module": "show",
            "service": "running-config",
            "include": "policyelements/network-device",
            "log_level": "debug",
        }
    ]


def test_shell_show_running_config_preserves_explicit_include():
    deps = FakeDeps()
    commands = iter(
        [
            "policyelements",
            "show running-config --include=policyelements/network-device",
            "quit",
        ]
    )

    def fake_input(prompt: str) -> str:
        return next(commands)

    NetloomShell(deps=deps, input_func=fake_input).run()

    assert deps.executed == [
        {
            "module": "show",
            "service": "running-config",
            "include": "policyelements/network-device",
        }
    ]


def test_shell_do_show_running_config_uses_root_context():
    deps = FakeDeps()
    commands = iter(
        [
            "policyelements",
            "do show running-config",
            "quit",
        ]
    )

    def fake_input(prompt: str) -> str:
        return next(commands)

    NetloomShell(deps=deps, input_func=fake_input).run()

    assert deps.executed == [
        {
            "module": "show",
            "service": "running-config",
        }
    ]


def test_shell_help_uses_current_context(capsys):
    deps = FakeDeps()
    commands = iter(["policyelements", "network-device", "?", "quit"])

    def fake_input(prompt: str) -> str:
        return next(commands)

    NetloomShell(deps=deps, input_func=fake_input).run()

    assert deps.help_calls[-1] == {
        "module": "policyelements",
        "service": "network-device",
    }
    assert "HELP" in capsys.readouterr().out


def test_shell_exit_moves_up_one_level(capsys):
    deps = FakeDeps()
    prompts: list[str] = []
    commands = iter(["policyelements", "network-device", "exit", "quit"])

    def fake_input(prompt: str) -> str:
        prompts.append(prompt)
        return next(commands)

    NetloomShell(deps=deps, input_func=fake_input).run()

    capsys.readouterr()
    assert prompts[-1] == "dev:netloom/policyelements# "


def test_shell_completion_candidates_follow_current_context():
    deps = FakeDeps()
    shell = NetloomShell(deps=deps, input_func=lambda prompt: "quit")

    assert "policyelements" in shell.completion_candidates("")
    assert "show" in shell.completion_candidates("")
    assert "running-config" in shell.completion_candidates("show ")
    assert shell.completion_candidates("cache ") == ["clear", "update"]

    shell.context = shell.context.__class__(module="policyelements")
    assert "network-device" in shell.completion_candidates("")
    assert "service-template" in shell.completion_candidates("")
    assert "top" in shell.completion_candidates("")

    shell.context = shell.context.__class__(
        module="policyelements",
        service="network-device",
    )
    assert "list" in shell.completion_candidates("")
    assert "get" in shell.completion_candidates("")
    assert "top" in shell.completion_candidates("")


def test_shell_do_completion_uses_root_context():
    deps = FakeDeps()
    shell = NetloomShell(
        deps=deps,
        input_func=lambda prompt: "quit",
    )
    shell.context = shell.context.__class__(module="policyelements")

    candidates = shell.completion_candidates("do ser")

    assert "server" in candidates


def test_shell_help_text_for_buffer_uses_context_without_staircase_formatting():
    deps = FakeDeps()
    shell = NetloomShell(deps=deps, input_func=lambda prompt: "quit")
    shell.context = shell.context.__class__(module="policyelements")

    text = shell.help_text_for_buffer("")

    assert "\r\n" not in text
    assert "HELP {'module': 'policyelements'}" == text
