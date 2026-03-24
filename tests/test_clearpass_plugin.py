from pathlib import Path

import netloom.core.config as config
import netloom.plugins.clearpass.plugin as pluginmod
from netloom.core.config import AppPaths, Settings


class _FakeClearPassClient:
    def __init__(self):
        self.login_calls = []

    def login(self, endpoints, credentials):
        self.login_calls.append({"endpoints": endpoints, "credentials": credentials})
        return {"access_token": "LOGIN-TOKEN"}


def _settings(tmp_path, **overrides):
    paths = AppPaths(
        cache_dir=tmp_path / "cache",
        state_dir=tmp_path / "state",
        response_dir=tmp_path / "responses",
        app_log_dir=tmp_path / "logs",
    ).ensure()
    values = {
        "plugin": "clearpass",
        "client_id": "prod-client",
        "client_secret": "plaintext-secret",
        "paths": paths,
    }
    values.update(overrides)
    return Settings(**values)


def test_resolve_auth_token_uses_resolved_secret_for_login(monkeypatch, tmp_path):
    client = _FakeClearPassClient()
    settings = _settings(
        tmp_path,
        client_secret=None,
        client_secret_ref="prod/client-secret",
    )
    monkeypatch.setattr(
        config,
        "load_keychain_secret",
        lambda *, plugin, secret_ref: "resolved-secret",
    )

    token = pluginmod.resolve_auth_token(client, settings)

    assert token == "LOGIN-TOKEN"
    assert client.login_calls[0]["credentials"]["client_secret"] == "resolved-secret"


def test_resolve_auth_token_bypasses_login_with_api_token(tmp_path):
    client = _FakeClearPassClient()
    settings = _settings(tmp_path, api_token="DIRECT-TOKEN")

    token = pluginmod.resolve_auth_token(client, settings)

    assert token == "DIRECT-TOKEN"
    assert client.login_calls == []


def test_resolve_auth_token_bypasses_login_with_api_token_file(monkeypatch, tmp_path):
    client = _FakeClearPassClient()
    token_file = tmp_path / "token.json"
    settings = _settings(tmp_path, api_token_file=Path(token_file))
    monkeypatch.setattr(pluginmod, "load_api_token_file", lambda path: "FILE-TOKEN")

    token = pluginmod.resolve_auth_token(client, settings)

    assert token == "FILE-TOKEN"
    assert client.login_calls == []
