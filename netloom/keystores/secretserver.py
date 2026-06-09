from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

import requests

from netloom.core.config import DEFAULT_TIMEOUT, config_dir
from netloom.io.files import load_api_token_file
from netloom.io.secrets import SecretLookupError, load_keychain_secret

KEYSTORE_DIR_NAME = "keystores"
SECRET_SERVER_DIR_NAME = "secretserver"
DEFAULT_RADIUS_FIELD_SLUG = "radius_secret"
DEFAULT_TACACS_FIELD_SLUG = "tacacs_secret"
SECRETSERVER_ENV_PREFIX = "NETLOOM_SECRETSERVER_"


def _normalize_profile_name(name: str | None) -> str | None:
    if name in (None, ""):
        return None
    normalized = str(name).strip().lower()
    return normalized or None


def _bool_value(raw: str | None, default: bool) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on", "enabled", "enable"}


def _int_value(raw: str | None, default: int) -> int:
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    data: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        data[key] = value
    return data


def _keystore_root() -> Path:
    return config_dir() / KEYSTORE_DIR_NAME / SECRET_SERVER_DIR_NAME


def _defaults_path() -> Path:
    return _keystore_root() / "defaults.env"


def _profile_path(profile: str | None) -> Path | None:
    normalized = _normalize_profile_name(profile)
    if normalized is None:
        return None
    return _keystore_root() / "profiles" / f"{normalized}.env"


def _credentials_path(profile: str | None) -> Path | None:
    normalized = _normalize_profile_name(profile)
    if normalized is None:
        return None
    return _keystore_root() / "credentials" / f"{normalized}.env"


def _default_api_url(base_url: str | None) -> str | None:
    if not base_url:
        return None
    return f"{base_url.rstrip('/')}/api"


def _default_token_url(base_url: str | None) -> str | None:
    if not base_url:
        return None
    return f"{base_url.rstrip('/')}/oauth2/token"


@dataclass(frozen=True)
class SecretServerReference:
    profile: str
    secret_path: str
    field_slug: str


@dataclass(frozen=True)
class SecretServerSettings:
    profile: str | None
    base_url: str | None
    api_url: str | None
    token_url: str | None
    verify_ssl: bool
    timeout: int
    username: str | None
    password: str | None
    password_ref: str | None
    api_token: str | None
    api_token_file: Path | None
    network_device_path_template: str | None = None
    radius_field_slug: str = DEFAULT_RADIUS_FIELD_SLUG
    tacacs_field_slug: str = DEFAULT_TACACS_FIELD_SLUG

    def validate(self) -> None:
        if not self.api_url:
            raise SecretLookupError(
                "NETLOOM_SECRETSERVER_API_URL is not configured. Set "
                "NETLOOM_SECRETSERVER_URL or NETLOOM_SECRETSERVER_API_URL."
            )
        if not self.token_url and not self.api_token and not self.api_token_file:
            raise SecretLookupError(
                "NETLOOM_SECRETSERVER_TOKEN_URL is not configured. Set "
                "NETLOOM_SECRETSERVER_URL or NETLOOM_SECRETSERVER_TOKEN_URL."
            )

    def resolve_password(self) -> str:
        if self.password_ref:
            try:
                return load_keychain_secret(
                    plugin="secretserver", secret_ref=self.password_ref
                )
            except SecretLookupError as exc:
                if self.password:
                    return self.password
                raise SecretLookupError(str(exc)) from exc
        if self.password:
            return self.password
        raise SecretLookupError(
            "NETLOOM_SECRETSERVER_PASSWORD_REF or NETLOOM_SECRETSERVER_PASSWORD "
            "must be configured when using OAuth login."
        )


def parse_secretserver_reference(secret_ref: str) -> SecretServerReference:
    parsed = urlparse(secret_ref.strip())
    if parsed.scheme.lower() != "secretserver":
        raise SecretLookupError(
            "Secret Server references must use the secretserver:// scheme."
        )

    profile = unquote(parsed.netloc).strip()
    secret_path = unquote(parsed.path or "").strip()
    field_slug = unquote(parse_qs(parsed.query).get("field", [""])[0]).strip()

    if not profile:
        raise SecretLookupError(
            "Secret Server references must include a profile: "
            "secretserver://<profile>/<secret-path>?field=<slug>"
        )
    if not secret_path:
        raise SecretLookupError("Secret Server references must include a secret path.")
    if not field_slug:
        raise SecretLookupError("Secret Server references must include ?field=<slug>.")

    return SecretServerReference(
        profile=profile,
        secret_path=secret_path,
        field_slug=field_slug,
    )


def load_secretserver_settings(profile: str | None) -> SecretServerSettings:
    normalized = _normalize_profile_name(profile)
    values = _read_env_file(_defaults_path())

    profile_path = _profile_path(normalized)
    if profile_path is not None and profile_path.is_file():
        values.update(_read_env_file(profile_path))

    credentials_path = _credentials_path(normalized)
    if credentials_path is not None and credentials_path.is_file():
        values.update(_read_env_file(credentials_path))

    for key, value in os.environ.items():
        if key.startswith(SECRETSERVER_ENV_PREFIX):
            values[key] = value

    base_url = values.get("NETLOOM_SECRETSERVER_URL")
    api_url = values.get("NETLOOM_SECRETSERVER_API_URL") or _default_api_url(base_url)
    token_url = values.get("NETLOOM_SECRETSERVER_TOKEN_URL") or _default_token_url(
        base_url
    )
    api_token_file_raw = values.get("NETLOOM_SECRETSERVER_API_TOKEN_FILE")

    return SecretServerSettings(
        profile=normalized,
        base_url=base_url,
        api_url=api_url,
        token_url=token_url,
        verify_ssl=_bool_value(values.get("NETLOOM_SECRETSERVER_VERIFY_SSL"), True),
        timeout=_int_value(values.get("NETLOOM_SECRETSERVER_TIMEOUT"), DEFAULT_TIMEOUT),
        username=values.get("NETLOOM_SECRETSERVER_USERNAME"),
        password=values.get("NETLOOM_SECRETSERVER_PASSWORD"),
        password_ref=values.get("NETLOOM_SECRETSERVER_PASSWORD_REF"),
        api_token=values.get("NETLOOM_SECRETSERVER_API_TOKEN"),
        api_token_file=Path(api_token_file_raw) if api_token_file_raw else None,
        network_device_path_template=values.get(
            "NETLOOM_SECRETSERVER_NETWORK_DEVICE_PATH_TEMPLATE"
        ),
        radius_field_slug=(
            values.get("NETLOOM_SECRETSERVER_RADIUS_FIELD_SLUG")
            or DEFAULT_RADIUS_FIELD_SLUG
        ),
        tacacs_field_slug=(
            values.get("NETLOOM_SECRETSERVER_TACACS_FIELD_SLUG")
            or DEFAULT_TACACS_FIELD_SLUG
        ),
    )


class SecretServerClient:
    def __init__(self, settings: SecretServerSettings):
        self.settings = settings
        self.settings.validate()
        self.session = requests.Session()
        self._token: str | None = None
        self._secret_id_cache: dict[str, int] = {}

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        auth_required: bool = True,
    ) -> requests.Response:
        headers: dict[str, str] = {}
        if auth_required:
            headers["Authorization"] = f"Bearer {self.access_token}"
        response = self.session.request(
            method,
            f"{self.settings.api_url.rstrip('/')}/{path.lstrip('/')}",
            params=params,
            data=data,
            headers=headers,
            timeout=self.settings.timeout,
            verify=self.settings.verify_ssl,
        )
        if response.status_code >= 400:
            raise self._error_for_response(response)
        return response

    @property
    def access_token(self) -> str:
        if self._token:
            return self._token
        if self.settings.api_token:
            self._token = self.settings.api_token
            return self._token
        if self.settings.api_token_file:
            self._token = load_api_token_file(self.settings.api_token_file)
            return self._token

        if not self.settings.token_url:
            raise SecretLookupError("NETLOOM_SECRETSERVER_TOKEN_URL is not configured.")
        if not self.settings.username:
            raise SecretLookupError(
                "NETLOOM_SECRETSERVER_USERNAME must be configured when using "
                "OAuth login."
            )

        response = self.session.request(
            "POST",
            self.settings.token_url,
            data={
                "username": self.settings.username,
                "password": self.settings.resolve_password(),
                "grant_type": "password",
            },
            timeout=self.settings.timeout,
            verify=self.settings.verify_ssl,
        )
        if response.status_code >= 400:
            raise self._error_for_response(response, context="OAuth token request")

        try:
            payload = response.json()
        except ValueError as exc:
            raise SecretLookupError(
                "Secret Server OAuth token response was not valid JSON."
            ) from exc

        token = payload.get("access_token") if isinstance(payload, dict) else None
        if not isinstance(token, str) or not token.strip():
            raise SecretLookupError(
                "Secret Server OAuth token response did not include access_token."
            )
        self._token = token.strip()
        return self._token

    def _error_for_response(
        self, response: requests.Response, *, context: str | None = None
    ) -> SecretLookupError:
        message = f"Secret Server request failed with HTTP {response.status_code}"
        if context:
            message = f"{context} failed with HTTP {response.status_code}"
        try:
            payload = response.json()
        except ValueError:
            payload = None

        if isinstance(payload, dict):
            detail = (
                payload.get("message")
                or payload.get("error")
                or payload.get("error_description")
            )
            if isinstance(detail, str) and detail.strip():
                message = f"{message}: {detail.strip()}"
        elif response.text.strip():
            message = f"{message}: {response.text.strip()}"
        return SecretLookupError(message)

    def lookup_secret_id(self, secret_path: str) -> int:
        normalized_path = secret_path.strip()
        if normalized_path in self._secret_id_cache:
            return self._secret_id_cache[normalized_path]

        response = self._request(
            "GET",
            "/v1/secrets/lookup/0",
            params={"secretPath": normalized_path},
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise SecretLookupError(
                "Secret Server lookup response was not valid JSON."
            ) from exc

        secret_id = payload.get("id") if isinstance(payload, dict) else None
        if not isinstance(secret_id, int) or secret_id < 1:
            raise SecretLookupError(
                f"Secret Server lookup did not return a valid id for "
                f"secretPath '{normalized_path}'."
            )
        self._secret_id_cache[normalized_path] = secret_id
        return secret_id

    def get_secret_field(self, secret_path: str, field_slug: str) -> str:
        secret_id = self.lookup_secret_id(secret_path)
        response = self._request(
            "GET",
            f"/v1/secrets/{secret_id}/fields/{field_slug}",
        )
        content_type = (response.headers.get("content-type") or "").lower()
        if "application/json" in content_type:
            value = response.json()
        else:
            value = response.text

        if isinstance(value, dict):
            value = value.get("itemValue")
        if value is None:
            return ""
        if not isinstance(value, str):
            raise SecretLookupError(
                f"Secret Server field '{field_slug}' for '{secret_path}' returned "
                "an unsupported value type."
            )
        return value


@lru_cache(maxsize=16)
def _client_for_settings(settings: SecretServerSettings) -> SecretServerClient:
    return SecretServerClient(settings)


def resolve_secretserver_reference(secret_ref: str) -> str:
    ref = parse_secretserver_reference(secret_ref)
    settings = load_secretserver_settings(ref.profile)
    client = _client_for_settings(settings)
    return client.get_secret_field(ref.secret_path, ref.field_slug)


def resolve_network_device_secret_values(
    *,
    profile: str | None,
    device_name: str,
    requested_fields: tuple[str, ...],
) -> dict[str, str]:
    settings = load_secretserver_settings(profile)
    template = (settings.network_device_path_template or "").strip()
    if not template:
        return {}

    try:
        secret_path = template.format(name=device_name)
    except KeyError as exc:
        raise SecretLookupError(
            "NETLOOM_SECRETSERVER_NETWORK_DEVICE_PATH_TEMPLATE may only use the "
            "{name} placeholder."
        ) from exc

    field_slugs = {
        "radius_secret": settings.radius_field_slug,
        "tacacs_secret": settings.tacacs_field_slug,
    }
    client = _client_for_settings(settings)
    resolved: dict[str, str] = {}
    for field_name in requested_fields:
        slug = field_slugs.get(field_name)
        if not slug:
            continue
        try:
            value = client.get_secret_field(secret_path, slug)
        except SecretLookupError as exc:
            if "HTTP 404" in str(exc):
                continue
            raise
        if value not in (None, ""):
            resolved[field_name] = value
    return resolved
