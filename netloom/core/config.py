from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

APP_NAME = "netloom"
ACTIVE_PROFILE_ENV = "NETLOOM_ACTIVE_PROFILE"
ACTIVE_PLUGIN_ENV = "NETLOOM_ACTIVE_PLUGIN"
CONFIG_DIR_ENV = "NETLOOM_CONFIG_DIR"
CONFIG_FILE_NAME = "config.env"
PLUGINS_DIR_NAME = "plugins"
DEFAULTS_FILE_NAME = "defaults.env"
PROFILES_DIR_NAME = "profiles"
CREDENTIALS_DIR_NAME = "credentials"
DEFAULT_TIMEOUT = 15
DEFAULT_FORMAT = "json"
DEFAULT_HTTPS_PREFIX = "https://"
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_PLUGIN = None
PROFILE_SCOPED_ENV_KEYS = (
    "NETLOOM_SERVER",
    "NETLOOM_HTTPS_PREFIX",
    "NETLOOM_VERIFY_SSL",
    "NETLOOM_TIMEOUT",
    "NETLOOM_CONSOLE",
    "NETLOOM_ENCRYPT_SECRETS",
    "NETLOOM_DATA_FORMAT",
    "NETLOOM_CSV_FIELDNAMES",
    "NETLOOM_LOG_LEVEL",
    "NETLOOM_API_TOKEN",
    "NETLOOM_API_TOKEN_FILE",
    "NETLOOM_TOKEN",
    "NETLOOM_TOKEN_FILE",
    "NETLOOM_GRANT_TYPE",
    "NETLOOM_CLIENT_ID",
    "NETLOOM_CLIENT_SECRET",
    "NETLOOM_USERNAME",
    "NETLOOM_PASSWORD",
    "NETLOOM_CACHE_DIR",
    "NETLOOM_STATE_DIR",
    "NETLOOM_OUT_DIR",
    "NETLOOM_APP_LOG_DIR",
)
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
    "fields",
    "ignore_fields",
    "sort",
    "offset",
    "limit",
    "calculate_count",
    "encrypt",
    "decrypt",
    "api_token",
    "token_file",
    "api_token_file",
    "catalog_view",
    "_complete",
    "_cword",
    "_cur",
}


def _bool_value(raw: str | None, default: bool) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on", "enabled", "enable"}


def _int_value(raw: str | None, default: int) -> int:
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _xdg_cache_home() -> Path:
    return Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache"))


def _xdg_config_home() -> Path:
    return Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config"))


def _xdg_state_home() -> Path:
    return Path(os.getenv("XDG_STATE_HOME", Path.home() / ".local" / "state"))


def config_dir() -> Path:
    override = os.getenv(CONFIG_DIR_ENV)
    if override:
        return Path(override)
    return _xdg_config_home() / APP_NAME


def config_env_path() -> Path:
    return config_dir() / CONFIG_FILE_NAME


def plugins_config_dir() -> Path:
    return config_dir() / PLUGINS_DIR_NAME


def _load_global_config_values() -> dict[str, str]:
    return _read_env_file(config_env_path())


def plugin_config_dir(
    plugin: str | None = None,
    *,
    config_values: Mapping[str, str] | None = None,
) -> Path | None:
    plugin_name = resolve_active_plugin(config_values) if plugin is None else plugin
    if plugin_name is None:
        return None
    return plugins_config_dir() / _normalize_plugin_name(plugin_name)


def defaults_env_path(
    plugin: str | None = None,
    *,
    config_values: Mapping[str, str] | None = None,
) -> Path | None:
    plugin_dir = plugin_config_dir(plugin, config_values=config_values)
    if plugin_dir is None:
        return None
    return plugin_dir / DEFAULTS_FILE_NAME


def profiles_dir(
    plugin: str | None = None,
    *,
    config_values: Mapping[str, str] | None = None,
) -> Path | None:
    plugin_dir = plugin_config_dir(plugin, config_values=config_values)
    if plugin_dir is None:
        return None
    return plugin_dir / PROFILES_DIR_NAME


def credentials_dir(
    plugin: str | None = None,
    *,
    config_values: Mapping[str, str] | None = None,
) -> Path | None:
    plugin_dir = plugin_config_dir(plugin, config_values=config_values)
    if plugin_dir is None:
        return None
    return plugin_dir / CREDENTIALS_DIR_NAME


def _profile_file_name(profile: str) -> str:
    normalized = _normalize_profile_name(profile)
    if not normalized:
        raise ValueError("Profile name must not be empty.")
    return f"{normalized}.env"


def profiles_env_path(
    plugin: str | None = None,
    *,
    config_values: Mapping[str, str] | None = None,
    profile: str | None = None,
) -> Path | None:
    target_dir = profiles_dir(plugin, config_values=config_values)
    if target_dir is None:
        return None
    effective_profile = profile
    if effective_profile in (None, ""):
        effective_profile = _resolve_active_profile(
            dict(config_values or _load_config_values(plugin))
        )
    if effective_profile is None:
        return target_dir
    return target_dir / _profile_file_name(effective_profile)


def credentials_env_path(
    plugin: str | None = None,
    *,
    config_values: Mapping[str, str] | None = None,
    profile: str | None = None,
) -> Path | None:
    target_dir = credentials_dir(plugin, config_values=config_values)
    if target_dir is None:
        return None
    effective_profile = profile
    if effective_profile in (None, ""):
        effective_profile = _resolve_active_profile(
            dict(config_values or _load_config_values(plugin))
        )
    if effective_profile is None:
        return target_dir
    return target_dir / _profile_file_name(effective_profile)


def _normalize_profile_name(name: str) -> str:
    return name.strip().lower()


def _normalize_plugin_name(name: str) -> str:
    normalized = name.strip().lower().replace("-", "_")
    if not normalized:
        raise ValueError("Plugin name must not be empty.")
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789_")
    invalid = {char for char in normalized if char not in allowed}
    if invalid:
        raise ValueError(
            "Plugin names may contain only letters, digits, hyphens, and underscores."
        )
    return normalized


def _plugin_is_unset(value: str | None) -> bool:
    if value is None:
        return True
    return value.strip().lower() in {"", "none", "unset"}


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


def _write_env_value(path: Path, key: str, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    updated = False
    rendered = f"{key}={value}"
    new_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in line:
            existing_key = line.split("=", 1)[0].strip()
            if existing_key == key and not updated:
                new_lines.append(rendered)
                updated = True
                continue
        new_lines.append(line)

    if not updated:
        if new_lines and new_lines[-1].strip():
            new_lines.append("")
        new_lines.append(rendered)

    path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def _load_config_values(
    plugin: str | None = None, *, active_profile: str | None = None
) -> dict[str, str]:
    global_values = _load_global_config_values()
    values = dict(global_values)
    effective_plugin = (
        resolve_active_plugin(global_values) if plugin is None else plugin
    )
    defaults_path = defaults_env_path(effective_plugin, config_values=global_values)
    if defaults_path is not None:
        values.update(_read_env_file(defaults_path))

    effective_profile = (
        _normalize_profile_name(active_profile)
        if active_profile not in (None, "")
        else _resolve_active_profile(values)
    )
    profile_path = profiles_env_path(
        effective_plugin,
        config_values=values,
        profile=effective_profile,
    )
    credential_path = credentials_env_path(
        effective_plugin,
        config_values=values,
        profile=effective_profile,
    )
    if profile_path is not None and profile_path.is_file():
        values.update(_read_env_file(profile_path))
    if credential_path is not None and credential_path.is_file():
        values.update(_read_env_file(credential_path))
    return values


def _resolve_active_profile(config_values: Mapping[str, str]) -> str | None:
    raw = os.getenv(ACTIVE_PROFILE_ENV)
    if raw is None:
        raw = config_values.get(ACTIVE_PROFILE_ENV)
    if raw is None or raw.strip() == "":
        return None
    return _normalize_profile_name(raw)


def _resolve_value(
    name: str,
    config_values: Mapping[str, str],
    *,
    active_profile: str | None,
) -> str | None:
    del active_profile
    raw = os.getenv(name)
    if raw is not None:
        return raw

    raw = config_values.get(name)
    if raw is not None:
        return raw

    return None


def list_profiles(
    config_values: Mapping[str, str] | None = None,
    *,
    plugin: str | None = None,
) -> list[str]:
    profiles: set[str] = set()
    plugin_name = resolve_active_plugin(config_values) if plugin is None else plugin
    if plugin_name is None:
        return []

    for directory in (
        profiles_dir(plugin_name, config_values=config_values),
        credentials_dir(plugin_name, config_values=config_values),
    ):
        if directory is None or not directory.exists():
            continue
        for entry in directory.glob("*.env"):
            if entry.is_file():
                profiles.add(_normalize_profile_name(entry.stem))

    values = dict(config_values or _load_config_values(plugin_name))
    defaults_path = defaults_env_path(plugin_name, config_values=values)
    if defaults_path is not None:
        values.update(_read_env_file(defaults_path))
    active_profile = _resolve_active_profile(values)
    if active_profile:
        profiles.add(active_profile)

    return sorted(profiles)


@dataclass(frozen=True)
class ProfileState:
    active_profile: str | None
    active_plugin: str | None
    available_profiles: list[str]
    profiles_path: Path | None
    credentials_path: Path | None
    server: str | None = None
    has_client_id: bool = False
    has_client_secret: bool = False
    profile_servers: dict[str, str | None] = field(default_factory=dict)
    profile_plugins: dict[str, str | None] = field(default_factory=dict)


def describe_profile_state() -> ProfileState:
    global_values = _load_global_config_values()
    active_plugin = resolve_active_plugin(global_values)
    values = _load_config_values(active_plugin)
    active_profile = _resolve_active_profile(values)
    available_profiles = list_profiles(values) if active_plugin else []
    profile_servers = {}
    for profile in available_profiles:
        profile_settings = load_settings_for_profile(profile)
        profile_servers[profile] = profile_settings.server
    profile_plugins = {profile: active_plugin for profile in available_profiles}

    server = _resolve_value("NETLOOM_SERVER", values, active_profile=active_profile)
    client_id = _resolve_value(
        "NETLOOM_CLIENT_ID", values, active_profile=active_profile
    )
    client_secret = _resolve_value(
        "NETLOOM_CLIENT_SECRET", values, active_profile=active_profile
    )

    return ProfileState(
        active_profile=active_profile,
        active_plugin=active_plugin,
        available_profiles=available_profiles,
        profiles_path=profiles_env_path(active_plugin, profile=active_profile),
        credentials_path=credentials_env_path(active_plugin, profile=active_profile),
        server=server,
        has_client_id=bool(client_id),
        has_client_secret=bool(client_secret),
        profile_servers=profile_servers,
        profile_plugins=profile_plugins,
    )


def set_active_profile(profile: str) -> Path:
    normalized = _normalize_profile_name(profile)
    if not normalized:
        raise ValueError("Profile name must not be empty.")
    active_plugin = resolve_active_plugin(_load_global_config_values())
    if active_plugin is None:
        raise ValueError(
            "No active plugin selected. Use `netloom load <plugin>` before "
            "selecting a profile."
        )
    values = _load_config_values(active_plugin)
    available_profiles = list_profiles(values, plugin=active_plugin)
    profile_path = profiles_env_path(active_plugin, profile=normalized)
    credential_path = credentials_env_path(active_plugin, profile=normalized)
    if (
        normalized not in available_profiles
        and not (profile_path and profile_path.exists())
        and not (credential_path and credential_path.exists())
    ):
        available_text = (
            ", ".join(available_profiles) if available_profiles else "<none>"
        )
        raise ValueError(
            f"Unknown profile '{profile}'. Available profiles: {available_text}"
        )
    target = defaults_env_path(active_plugin)
    _write_env_value(target, ACTIVE_PROFILE_ENV, normalized)
    return target


def set_active_plugin(plugin: str | None) -> Path:
    normalized = (
        "none" if _plugin_is_unset(plugin) else _normalize_plugin_name(str(plugin))
    )
    target = config_env_path()
    _write_env_value(target, ACTIVE_PLUGIN_ENV, normalized)
    return target


def resolve_active_plugin(
    config_values: Mapping[str, str] | None = None,
    *,
    active_profile: str | None = None,
) -> str | None:
    del active_profile
    values = config_values or _load_global_config_values()
    raw = os.getenv(ACTIVE_PLUGIN_ENV)
    if raw is None:
        raw = values.get(ACTIVE_PLUGIN_ENV)
    if _plugin_is_unset(raw):
        return DEFAULT_PLUGIN
    return _normalize_plugin_name(str(raw))


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
    plugin: str | None = None
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
    active_profile: str | None = None
    profiles_path: Path | None = None
    credentials_path: Path | None = None
    paths: AppPaths = field(default_factory=lambda: default_paths().ensure())

    @property
    def credentials(self) -> dict[str, str]:
        missing: list[str] = []
        if not self.client_id:
            missing.append("NETLOOM_CLIENT_ID")
        if not self.client_secret:
            missing.append("NETLOOM_CLIENT_SECRET")
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


def _resolve_path_override(
    name: str,
    config_values: Mapping[str, str] | None = None,
    *,
    active_profile: str | None = None,
) -> Path | None:
    raw = _resolve_value(name, config_values or {}, active_profile=active_profile)
    if raw is None or raw.strip() == "":
        return None
    return Path(raw).expanduser()


def default_paths(
    config_values: Mapping[str, str] | None = None,
    *,
    active_profile: str | None = None,
) -> AppPaths:
    cache_override = _resolve_path_override(
        "NETLOOM_CACHE_DIR", config_values, active_profile=active_profile
    )
    state_override = _resolve_path_override(
        "NETLOOM_STATE_DIR", config_values, active_profile=active_profile
    )
    response_override = _resolve_path_override(
        "NETLOOM_OUT_DIR", config_values, active_profile=active_profile
    )
    app_log_override = _resolve_path_override(
        "NETLOOM_APP_LOG_DIR", config_values, active_profile=active_profile
    )

    cache_dir = cache_override or (_xdg_cache_home() / APP_NAME)
    state_dir = state_override or (_xdg_state_home() / APP_NAME)
    response_dir = response_override if response_override else state_dir / "responses"
    app_log_dir = app_log_override if app_log_override else state_dir / "logs"
    return AppPaths(
        cache_dir=cache_dir,
        state_dir=state_dir,
        response_dir=response_dir,
        app_log_dir=app_log_dir,
    )


def _default_log_file(
    paths: AppPaths,
    *,
    now: datetime | None = None,
) -> Path:
    timestamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S-%f")
    return paths.app_log_dir / f"{APP_NAME}-{timestamp}.log"


def _build_settings_from_values(
    values: Mapping[str, str], *, active_profile: str | None, active_plugin: str | None
) -> Settings:
    paths = default_paths(values, active_profile=active_profile).ensure()

    log_file_raw = _resolve_value(
        "NETLOOM_LOG_FILE", values, active_profile=active_profile
    )
    log_file = Path(log_file_raw) if log_file_raw else _default_log_file(paths)
    log_to_file = _bool_value(
        _resolve_value("NETLOOM_LOG_TO_FILE", values, active_profile=active_profile),
        False,
    ) or bool(log_file_raw)

    csv_fieldnames_raw = _resolve_value(
        "NETLOOM_CSV_FIELDNAMES", values, active_profile=active_profile
    )
    csv_fieldnames = None
    if csv_fieldnames_raw:
        csv_fieldnames = [
            value.strip() for value in csv_fieldnames_raw.split(",") if value.strip()
        ]

    api_token_file_raw = _resolve_value(
        "NETLOOM_API_TOKEN_FILE", values, active_profile=active_profile
    ) or _resolve_value("NETLOOM_TOKEN_FILE", values, active_profile=active_profile)

    return Settings(
        plugin=active_plugin,
        server=_resolve_value("NETLOOM_SERVER", values, active_profile=active_profile),
        https_prefix=_resolve_value(
            "NETLOOM_HTTPS_PREFIX", values, active_profile=active_profile
        )
        or DEFAULT_HTTPS_PREFIX,
        verify_ssl=_bool_value(
            _resolve_value("NETLOOM_VERIFY_SSL", values, active_profile=active_profile),
            False,
        ),
        timeout=_int_value(
            _resolve_value("NETLOOM_TIMEOUT", values, active_profile=active_profile),
            DEFAULT_TIMEOUT,
        ),
        console=_bool_value(
            _resolve_value("NETLOOM_CONSOLE", values, active_profile=active_profile),
            False,
        ),
        encrypt_secrets=_bool_value(
            _resolve_value(
                "NETLOOM_ENCRYPT_SECRETS", values, active_profile=active_profile
            ),
            True,
        ),
        default_format=_resolve_value(
            "NETLOOM_DATA_FORMAT", values, active_profile=active_profile
        )
        or DEFAULT_FORMAT,
        default_csv_fieldnames=csv_fieldnames,
        log_level=(
            _resolve_value("NETLOOM_LOG_LEVEL", values, active_profile=active_profile)
            or DEFAULT_LOG_LEVEL
        ).upper(),
        log_file=log_file,
        log_to_file=log_to_file,
        grant_type=_resolve_value(
            "NETLOOM_GRANT_TYPE", values, active_profile=active_profile
        )
        or "client_credentials",
        client_id=_resolve_value(
            "NETLOOM_CLIENT_ID", values, active_profile=active_profile
        )
        or _resolve_value("NETLOOM_USERNAME", values, active_profile=active_profile),
        client_secret=_resolve_value(
            "NETLOOM_CLIENT_SECRET", values, active_profile=active_profile
        )
        or _resolve_value("NETLOOM_PASSWORD", values, active_profile=active_profile),
        api_token=_resolve_value(
            "NETLOOM_API_TOKEN", values, active_profile=active_profile
        )
        or _resolve_value("NETLOOM_TOKEN", values, active_profile=active_profile),
        api_token_file=Path(api_token_file_raw) if api_token_file_raw else None,
        active_profile=active_profile,
        profiles_path=profiles_env_path(active_plugin, profile=active_profile),
        credentials_path=credentials_env_path(active_plugin, profile=active_profile),
        paths=paths,
    )


def load_settings() -> Settings:
    active_plugin = resolve_active_plugin(_load_global_config_values())
    values = _load_config_values(active_plugin)
    active_profile = _resolve_active_profile(values)
    return _build_settings_from_values(
        values, active_profile=active_profile, active_plugin=active_plugin
    )


def load_settings_for_profile(profile: str | None) -> Settings:
    active_plugin = resolve_active_plugin(_load_global_config_values())
    active_profile = (
        _normalize_profile_name(profile)
        if profile not in (None, "")
        else _resolve_active_profile(_load_config_values(active_plugin))
    )
    values = _load_config_values(active_plugin, active_profile=active_profile)
    return _build_settings_from_values(
        values, active_profile=active_profile, active_plugin=active_plugin
    )
