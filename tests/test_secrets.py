import types

import pytest

import netloom.core.config as config
import netloom.io.secrets as secretsmod
from netloom.core.config import Settings
from netloom.io.secrets import SecretLookupError


def test_load_keychain_secret_uses_plugin_service_namespace(monkeypatch):
    calls = {}
    fake_keyring = types.SimpleNamespace(
        errors=types.SimpleNamespace(
            NoKeyringError=RuntimeError,
            KeyringError=RuntimeError,
        ),
        get_password=lambda service, username: calls.update(
            {"service": service, "username": username}
        )
        or "resolved-secret",
    )
    monkeypatch.setattr(secretsmod, "import_module", lambda name: fake_keyring)

    secret = secretsmod.load_keychain_secret(
        plugin="clearpass", secret_ref="prod/client-secret"
    )

    assert secret == "resolved-secret"
    assert calls == {
        "service": "netloom/clearpass",
        "username": "prod/client-secret",
    }


def test_load_keychain_secret_errors_when_keyring_package_missing(monkeypatch):
    def fake_import_module(name):
        raise ModuleNotFoundError("No module named 'keyring'")

    monkeypatch.setattr(secretsmod, "import_module", fake_import_module)

    with pytest.raises(SecretLookupError, match="keyring"):
        secretsmod.load_keychain_secret(
            plugin="clearpass", secret_ref="prod/client-secret"
        )


def test_load_keychain_secret_errors_when_backend_missing(monkeypatch):
    class FakeNoKeyringError(Exception):
        pass

    def fake_get_password(service, username):
        raise FakeNoKeyringError("no backend")

    fake_keyring = types.SimpleNamespace(
        errors=types.SimpleNamespace(
            NoKeyringError=FakeNoKeyringError,
            KeyringError=Exception,
        ),
        get_password=fake_get_password,
    )
    monkeypatch.setattr(secretsmod, "import_module", lambda name: fake_keyring)

    with pytest.raises(SecretLookupError, match="no usable OS keychain backend"):
        secretsmod.load_keychain_secret(
            plugin="clearpass", secret_ref="prod/client-secret"
        )


def test_load_keychain_secret_errors_when_entry_missing(monkeypatch):
    fake_keyring = types.SimpleNamespace(
        errors=types.SimpleNamespace(
            NoKeyringError=RuntimeError,
            KeyringError=RuntimeError,
        ),
        get_password=lambda service, username: None,
    )
    monkeypatch.setattr(secretsmod, "import_module", lambda name: fake_keyring)

    with pytest.raises(SecretLookupError, match="no keychain entry was found"):
        secretsmod.load_keychain_secret(
            plugin="clearpass", secret_ref="prod/client-secret"
        )


def test_settings_credentials_prefers_keychain_secret(monkeypatch):
    monkeypatch.setattr(
        config,
        "load_keychain_secret",
        lambda *, plugin, secret_ref: "resolved-secret",
    )
    settings = Settings(
        plugin="clearpass",
        client_id="prod-client",
        client_secret_ref="prod/client-secret",
    )

    assert settings.credentials["client_secret"] == "resolved-secret"


def test_settings_credentials_falls_back_to_plaintext_when_keychain_lookup_fails(
    monkeypatch,
):
    def fake_load_keychain_secret(*, plugin, secret_ref):
        raise SecretLookupError("keychain backend unavailable")

    monkeypatch.setattr(config, "load_keychain_secret", fake_load_keychain_secret)
    settings = Settings(
        plugin="clearpass",
        client_id="prod-client",
        client_secret_ref="prod/client-secret",
        client_secret="plaintext-secret",
    )

    assert settings.credentials["client_secret"] == "plaintext-secret"


def test_settings_credentials_raises_when_keychain_lookup_fails_without_fallback(
    monkeypatch,
):
    def fake_load_keychain_secret(*, plugin, secret_ref):
        raise SecretLookupError("keychain backend unavailable")

    monkeypatch.setattr(config, "load_keychain_secret", fake_load_keychain_secret)
    settings = Settings(
        plugin="clearpass",
        client_id="prod-client",
        client_secret_ref="prod/client-secret",
    )

    with pytest.raises(ValueError, match="keychain backend unavailable"):
        _ = settings.credentials
