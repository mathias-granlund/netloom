from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

APP_NAME = "netloom"
ACTIVE_PROFILE_ENV = "NETLOOM_ACTIVE_PROFILE"
ACTIVE_PLUGIN_ENV = "NETLOOM_ACTIVE_PLUGIN"
CONFIG_DIR_ENV = "NETLOOM_CONFIG_DIR"
CLI_TIMING_ENV = "NETLOOM_CLI_TIMING"
CONFIG_FILE_NAME = "config.env"
PLUGINS_DIR_NAME = "plugins"
DEFAULTS_FILE_NAME = "defaults.env"
PROFILES_DIR_NAME = "profiles"
CREDENTIALS_DIR_NAME = "credentials"
DEFAULT_PLUGIN = None
_RUNTIME_PLUGIN_NAMES = ("clearpass",)

# This module intentionally mirrors only the small subset of config behavior
# needed by cached help/completion fast paths. Keep it lightweight, and keep
# its observable path/plugin/profile behavior aligned with `netloom.core.config`.


def _bool_value(raw: str | None, default: bool) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on", "enabled", "enable"}


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


def _resolve_active_profile(config_values: Mapping[str, str]) -> str | None:
    raw = os.getenv(ACTIVE_PROFILE_ENV)
    if raw is None:
        raw = config_values.get(ACTIVE_PROFILE_ENV)
    if raw is None or raw.strip() == "":
        return None
    return _normalize_profile_name(raw)


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
class InteractivePaths:
    cache_dir: Path
    state_dir: Path
    response_dir: Path
    app_log_dir: Path

    def ensure(self) -> "InteractivePaths":
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.response_dir.mkdir(parents=True, exist_ok=True)
        self.app_log_dir.mkdir(parents=True, exist_ok=True)
        return self


@dataclass(frozen=True)
class InteractiveSettings:
    plugin: str | None = None
    active_profile: str | None = None
    cli_timing: bool = False
    profiles_path: Path | None = None
    credentials_path: Path | None = None
    paths: InteractivePaths = field(default_factory=lambda: default_paths().ensure())


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
) -> InteractivePaths:
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
    return InteractivePaths(
        cache_dir=cache_dir,
        state_dir=state_dir,
        response_dir=response_dir,
        app_log_dir=app_log_dir,
    )


def load_interactive_settings() -> InteractiveSettings:
    active_plugin = resolve_active_plugin(_load_global_config_values())
    values = _load_config_values(active_plugin)
    active_profile = _resolve_active_profile(values)
    cli_timing_raw = _resolve_value(
        CLI_TIMING_ENV, values, active_profile=active_profile
    )
    return InteractiveSettings(
        plugin=active_plugin,
        active_profile=active_profile,
        cli_timing=_bool_value(cli_timing_raw, False),
        profiles_path=profiles_env_path(active_plugin, profile=active_profile),
        credentials_path=credentials_env_path(active_plugin, profile=active_profile),
        paths=default_paths(values, active_profile=active_profile).ensure(),
    )


def list_runtime_plugins() -> list[str]:
    return sorted(_RUNTIME_PLUGIN_NAMES)


def list_configured_plugins() -> list[str]:
    plugins_dir = plugins_config_dir()
    try:
        entries = plugins_dir.iterdir()
    except FileNotFoundError:
        return []

    configured: list[str] = []
    for entry in entries:
        if entry.is_dir():
            configured.append(entry.name)
    return sorted(configured)


def list_plugins() -> list[str]:
    return sorted(set(list_runtime_plugins()) | set(list_configured_plugins()))


__all__ = [
    "CLI_TIMING_ENV",
    "InteractivePaths",
    "InteractiveSettings",
    "credentials_env_path",
    "default_paths",
    "list_plugins",
    "list_profiles",
    "load_interactive_settings",
    "plugins_config_dir",
    "profiles_env_path",
    "resolve_active_plugin",
]
