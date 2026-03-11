from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

APP_NAME = "arapy"
DEFAULT_TIMEOUT = 15
DEFAULT_FORMAT = "json"
DEFAULT_HTTPS_PREFIX = "https://"
DEFAULT_LOG_LEVEL = "INFO"
SECRET_FIELDS = (
    "client_secret",
    "radius_secret",
    "tacacs_secret",
    "password",
    "enable_password",
)
RESERVED_ARGS = {
    "help",
    "version",
    "verbose",
    "debug",
    "console",
    "module",
    "service",
    "action",
    "out",
    "file",
    "csv_fieldnames",
    "data_format",
    "log_level",
    "all",
    "filter",
    "sort",
    "offset",
    "limit",
    "calculate_count",
    "encrypt",
    "decrypt",
    "api_token",
    "token_file",
    "api_token_file",
    "_complete",
    "_cword",
    "_cur",
}


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on", "enabled", "enable"}


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _xdg_cache_home() -> Path:
    return Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache"))


def _xdg_state_home() -> Path:
    return Path(os.getenv("XDG_STATE_HOME", Path.home() / ".local" / "state"))


@dataclass(frozen=True)
class AppPaths:
    cache_dir: Path
    state_dir: Path
    response_dir: Path
    app_log_dir: Path

    def ensure(self) -> "AppPaths":
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.response_dir.mkdir(parents=True, exist_ok=True)
        self.app_log_dir.mkdir(parents=True, exist_ok=True)
        return self


@dataclass(frozen=True)
class Settings:
    server: str | None = None
    https_prefix: str = DEFAULT_HTTPS_PREFIX
    verify_ssl: bool = False
    timeout: int = DEFAULT_TIMEOUT
    console: bool = False
    encrypt_secrets: bool = True
    default_format: str = DEFAULT_FORMAT
    default_csv_fieldnames: list[str] | None = None
    log_level: str = DEFAULT_LOG_LEVEL
    log_file: Path | None = None
    log_to_file: bool = False
    grant_type: str = "client_credentials"
    client_id: str | None = None
    client_secret: str | None = None
    api_token: str | None = None
    api_token_file: Path | None = None
    paths: AppPaths = field(default_factory=lambda: default_paths().ensure())

    @property
    def credentials(self) -> dict[str, str]:
        missing: list[str] = []
        if not self.client_id:
            missing.append("ARAPY_CLIENT_ID")
        if not self.client_secret:
            missing.append("ARAPY_CLIENT_SECRET")
        if missing:
            missing_text = ", ".join(missing)
            raise ValueError(
                f"Missing required credentials in environment: {missing_text}"
            )
        return {
            "grant_type": self.grant_type,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }


def default_paths() -> AppPaths:
    cache_override = os.getenv("ARAPY_CACHE_DIR")
    state_override = os.getenv("ARAPY_STATE_DIR")
    response_override = os.getenv("ARAPY_OUT_DIR")
    app_log_override = os.getenv("ARAPY_APP_LOG_DIR")

    cache_dir = Path(cache_override) if cache_override else _xdg_cache_home() / APP_NAME
    state_dir = Path(state_override) if state_override else _xdg_state_home() / APP_NAME
    response_dir = (
        Path(response_override) if response_override else state_dir / "responses"
    )
    app_log_dir = Path(app_log_override) if app_log_override else state_dir / "logs"
    return AppPaths(
        cache_dir=cache_dir,
        state_dir=state_dir,
        response_dir=response_dir,
        app_log_dir=app_log_dir,
    )


def load_settings() -> Settings:
    paths = default_paths().ensure()
    log_file_raw = os.getenv("ARAPY_LOG_FILE")
    log_file = Path(log_file_raw) if log_file_raw else paths.app_log_dir / "arapy.log"
    log_to_file = _bool_env("ARAPY_LOG_TO_FILE", False) or bool(log_file_raw)

    csv_fieldnames_raw = os.getenv("ARAPY_CSV_FIELDNAMES")
    csv_fieldnames = None
    if csv_fieldnames_raw:
        csv_fieldnames = [
            value.strip() for value in csv_fieldnames_raw.split(",") if value.strip()
        ]

    return Settings(
        server=os.getenv("ARAPY_SERVER"),
        https_prefix=os.getenv("ARAPY_HTTPS_PREFIX", DEFAULT_HTTPS_PREFIX),
        verify_ssl=_bool_env("ARAPY_VERIFY_SSL", False),
        timeout=_int_env("ARAPY_TIMEOUT", DEFAULT_TIMEOUT),
        console=_bool_env("ARAPY_CONSOLE", False),
        encrypt_secrets=_bool_env("ARAPY_ENCRYPT_SECRETS", True),
        default_format=os.getenv("ARAPY_DATA_FORMAT", DEFAULT_FORMAT),
        default_csv_fieldnames=csv_fieldnames,
        log_level=os.getenv("ARAPY_LOG_LEVEL", DEFAULT_LOG_LEVEL).upper(),
        log_file=log_file,
        log_to_file=log_to_file,
        grant_type=os.getenv("ARAPY_GRANT_TYPE", "client_credentials"),
        client_id=os.getenv("ARAPY_CLIENT_ID") or os.getenv("ARAPY_USERNAME"),
        client_secret=os.getenv("ARAPY_CLIENT_SECRET") or os.getenv("ARAPY_PASSWORD"),
        api_token=os.getenv("ARAPY_API_TOKEN") or os.getenv("ARAPY_TOKEN"),
        api_token_file=(
            Path(
                os.getenv("ARAPY_API_TOKEN_FILE") or os.getenv("ARAPY_TOKEN_FILE", "")
            )
            if os.getenv("ARAPY_API_TOKEN_FILE") or os.getenv("ARAPY_TOKEN_FILE")
            else None
        ),
        paths=paths,
    )
