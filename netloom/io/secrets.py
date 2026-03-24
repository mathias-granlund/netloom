from __future__ import annotations

from importlib import import_module

KEYCHAIN_SERVICE_PREFIX = "netloom"


class SecretLookupError(RuntimeError):
    """Raised when a referenced secret cannot be resolved."""


def keychain_service_name(plugin: str | None) -> str:
    plugin_name = (plugin or "default").strip().lower().replace("-", "_")
    return f"{KEYCHAIN_SERVICE_PREFIX}/{plugin_name}"


def load_keychain_secret(*, plugin: str | None, secret_ref: str) -> str:
    service_name = keychain_service_name(plugin)
    ref = secret_ref.strip()
    if not ref:
        raise SecretLookupError("NETLOOM_CLIENT_SECRET_REF must not be empty.")

    try:
        keyring = import_module("keyring")
    except ModuleNotFoundError as exc:
        raise SecretLookupError(
            "NETLOOM_CLIENT_SECRET_REF is configured, but the Python `keyring` "
            "package is not installed. Install `keyring` or set "
            "NETLOOM_CLIENT_SECRET."
        ) from exc

    errors = getattr(keyring, "errors", None)
    no_keyring_error = getattr(errors, "NoKeyringError", ())
    keyring_error = getattr(errors, "KeyringError", ())

    try:
        secret = keyring.get_password(service_name, ref)
    except no_keyring_error as exc:
        raise SecretLookupError(
            "NETLOOM_CLIENT_SECRET_REF is configured, but no usable OS keychain "
            f"backend is available for service '{service_name}'. Configure a "
            "supported backend or set NETLOOM_CLIENT_SECRET."
        ) from exc
    except keyring_error as exc:
        raise SecretLookupError(
            "NETLOOM_CLIENT_SECRET_REF lookup failed for "
            f"service '{service_name}' and username '{ref}': {exc}"
        ) from exc

    if not secret:
        raise SecretLookupError(
            "NETLOOM_CLIENT_SECRET_REF is configured, but no keychain entry was "
            f"found for service '{service_name}' and username '{ref}'. Configure "
            "that entry or set NETLOOM_CLIENT_SECRET."
        )

    return secret
