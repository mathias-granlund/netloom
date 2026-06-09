from __future__ import annotations

import types
from pathlib import Path

import pytest

import netloom.keystores.secretserver as secretserver


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture(autouse=True)
def _clear_secretserver_cache():
    cache_clear = getattr(secretserver._client_for_settings, "cache_clear", None)
    if callable(cache_clear):
        cache_clear()
    yield
    cache_clear = getattr(secretserver._client_for_settings, "cache_clear", None)
    if callable(cache_clear):
        cache_clear()


def test_load_secretserver_settings_applies_profile_and_env_precedence(
    monkeypatch, tmp_path
):
    config_dir = tmp_path / "config"
    monkeypatch.setenv("NETLOOM_CONFIG_DIR", str(config_dir))
    _write(
        config_dir / "keystores" / "secretserver" / "defaults.env",
        "\n".join(
            [
                "NETLOOM_SECRETSERVER_URL=https://vault.example/SecretServer",
                "NETLOOM_SECRETSERVER_TIMEOUT=10",
                "NETLOOM_SECRETSERVER_USERNAME=default-user",
                "NETLOOM_SECRETSERVER_NETWORK_DEVICE_PATH_TEMPLATE=/Devices/{name}",
            ]
        )
        + "\n",
    )
    _write(
        config_dir / "keystores" / "secretserver" / "profiles" / "prod.env",
        "NETLOOM_SECRETSERVER_USERNAME=profile-user\n",
    )
    _write(
        config_dir / "keystores" / "secretserver" / "credentials" / "prod.env",
        "NETLOOM_SECRETSERVER_PASSWORD=profile-pass\n",
    )
    monkeypatch.setenv("NETLOOM_SECRETSERVER_TIMEOUT", "25")

    settings = secretserver.load_secretserver_settings("prod")

    assert settings.api_url == "https://vault.example/SecretServer/api"
    assert settings.token_url == "https://vault.example/SecretServer/oauth2/token"
    assert settings.timeout == 25
    assert settings.username == "profile-user"
    assert settings.password == "profile-pass"
    assert settings.network_device_path_template == "/Devices/{name}"


def test_resolve_secretserver_reference_uses_profile_settings(monkeypatch, tmp_path):
    config_dir = tmp_path / "config"
    monkeypatch.setenv("NETLOOM_CONFIG_DIR", str(config_dir))
    _write(
        config_dir / "keystores" / "secretserver" / "defaults.env",
        "NETLOOM_SECRETSERVER_URL=https://vault.example/SecretServer\n",
    )
    calls = {}

    def fake_get_secret_field(path, slug):
        calls["path"] = path
        calls["slug"] = slug
        return "resolved-value"

    monkeypatch.setattr(
        secretserver,
        "_client_for_settings",
        lambda settings: types.SimpleNamespace(get_secret_field=fake_get_secret_field),
    )

    value = secretserver.resolve_secretserver_reference(
        "secretserver://prod/Shared/ClearPass/API?field=password"
    )

    assert value == "resolved-value"
    assert calls == {"path": "/Shared/ClearPass/API", "slug": "password"}


def test_secretserver_client_uses_oauth_password_grant(monkeypatch):
    calls = []

    class _Response:
        status_code = 200
        headers = {"content-type": "application/json"}
        text = ""

        def json(self):
            return {"access_token": "ACCESS-TOKEN"}

    class _Session:
        def request(self, method, url, **kwargs):
            calls.append({"method": method, "url": url, **kwargs})
            return _Response()

    monkeypatch.setattr(secretserver.requests, "Session", lambda: _Session())
    settings = secretserver.SecretServerSettings(
        profile="prod",
        base_url="https://vault.example/SecretServer",
        api_url="https://vault.example/SecretServer/api",
        token_url="https://vault.example/SecretServer/oauth2/token",
        verify_ssl=True,
        timeout=15,
        username="svc-user",
        password="svc-pass",
        password_ref=None,
        api_token=None,
        api_token_file=None,
    )

    client = secretserver.SecretServerClient(settings)

    assert client.access_token == "ACCESS-TOKEN"
    assert calls[0]["method"] == "POST"
    assert calls[0]["url"] == "https://vault.example/SecretServer/oauth2/token"
    assert calls[0]["data"] == {
        "username": "svc-user",
        "password": "svc-pass",
        "grant_type": "password",
    }


def test_resolve_network_device_secret_values_formats_path(monkeypatch):
    calls = []
    settings = secretserver.SecretServerSettings(
        profile="prod",
        base_url="https://vault.example/SecretServer",
        api_url="https://vault.example/SecretServer/api",
        token_url="https://vault.example/SecretServer/oauth2/token",
        verify_ssl=True,
        timeout=15,
        username=None,
        password=None,
        password_ref=None,
        api_token="TOKEN",
        api_token_file=None,
        network_device_path_template="/Shared/Devices/{name}",
        radius_field_slug="radius_secret",
        tacacs_field_slug="tacacs_secret",
    )
    monkeypatch.setattr(
        secretserver, "load_secretserver_settings", lambda profile: settings
    )
    monkeypatch.setattr(
        secretserver,
        "_client_for_settings",
        lambda loaded_settings: types.SimpleNamespace(
            get_secret_field=lambda path, slug: (
                calls.append((path, slug))
                or {
                    "radius_secret": "radius-value",
                    "tacacs_secret": "tacacs-value",
                }[slug]
            )
        ),
    )

    resolved = secretserver.resolve_network_device_secret_values(
        profile="prod",
        device_name="switch-a",
        requested_fields=("radius_secret", "tacacs_secret"),
    )

    assert resolved == {
        "radius_secret": "radius-value",
        "tacacs_secret": "tacacs-value",
    }
    assert calls == [
        ("/Shared/Devices/switch-a", "radius_secret"),
        ("/Shared/Devices/switch-a", "tacacs_secret"),
    ]
