from __future__ import annotations

from pathlib import Path

from netloom.cli import runtime
from netloom.core.config import AppPaths, Settings


def _settings() -> Settings:
    paths = AppPaths(
        cache_dir=Path("cache"),
        state_dir=Path("state"),
        response_dir=Path("responses"),
        app_log_dir=Path("logs"),
    )
    return Settings(paths=paths)


def test_settings_with_cli_overrides_updates_token_fields():
    settings = _settings()

    updated = runtime.settings_with_cli_overrides(
        settings,
        {"token": "abc123", "api_token_file": Path("token.txt")},
    )

    assert updated.api_token == "abc123"
    assert updated.api_token_file == Path("token.txt")


def test_run_cli_version_uses_injected_deps_and_skips_runtime_work(capsys):
    class _Deps:
        def get_version(self):
            return "7.7.7"

        def load_settings(self):
            raise AssertionError("should not load settings")

        def configure_logging(self, *args, **kwargs):
            raise AssertionError("should not configure logging")

    runtime.run_cli({"version": True}, deps=_Deps())

    assert capsys.readouterr().out.strip() == "7.7.7"
