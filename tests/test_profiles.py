import re
import sys
from pathlib import Path

import netloom.cli.main as main
from netloom.core import config
from netloom.core.config import AppPaths, load_settings


class _FakeLogMgr:
    def get_logger(self, name):
        return self

    def set_level(self, level):
        return None

    def info(self, msg, *args, **kwargs):
        return None

    def debug(self, msg, *args, **kwargs):
        return None

    def error(self, msg, *args, **kwargs):
        return None


def _configure_runtime(monkeypatch, tmp_path):
    config_dir = tmp_path / "config"
    monkeypatch.setenv("NETLOOM_CONFIG_DIR", str(config_dir))
    monkeypatch.setenv("NETLOOM_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("NETLOOM_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.delenv("NETLOOM_SERVER", raising=False)
    monkeypatch.delenv("NETLOOM_CLIENT_ID", raising=False)
    monkeypatch.delenv("NETLOOM_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("NETLOOM_CLIENT_SECRET_REF", raising=False)
    monkeypatch.delenv("NETLOOM_ACTIVE_PROFILE", raising=False)
    monkeypatch.delenv("NETLOOM_ACTIVE_PLUGIN", raising=False)
    return config_dir


def _write_global_config(config_dir, plugin="clearpass"):
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "config.env").write_text(
        f"NETLOOM_ACTIVE_PLUGIN={plugin}\n",
        encoding="utf-8",
    )


def _plugin_dir(config_dir, plugin="clearpass"):
    return config_dir / "plugins" / plugin


def _defaults_path(config_dir, plugin="clearpass"):
    return _plugin_dir(config_dir, plugin) / "defaults.env"


def _profiles_dir(config_dir, plugin="clearpass"):
    return _plugin_dir(config_dir, plugin) / "profiles"


def _credentials_dir(config_dir, plugin="clearpass"):
    return _plugin_dir(config_dir, plugin) / "credentials"


def _profile_path(config_dir, profile, plugin="clearpass"):
    return _profiles_dir(config_dir, plugin) / f"{profile}.env"


def _credential_path(config_dir, profile, plugin="clearpass"):
    return _credentials_dir(config_dir, plugin) / f"{profile}.env"


def _write_profiles(config_dir, plugin="clearpass"):
    _write_global_config(config_dir, plugin=plugin)
    plugin_dir = _plugin_dir(config_dir, plugin)
    plugin_dir.mkdir(parents=True, exist_ok=True)
    _profiles_dir(config_dir, plugin).mkdir(parents=True, exist_ok=True)
    _credentials_dir(config_dir, plugin).mkdir(parents=True, exist_ok=True)
    _defaults_path(config_dir, plugin).write_text(
        "NETLOOM_ACTIVE_PROFILE=prod\n",
        encoding="utf-8",
    )
    _profile_path(config_dir, "prod", plugin).write_text(
        "NETLOOM_SERVER=prod.clearpass.example:443\n",
        encoding="utf-8",
    )
    _profile_path(config_dir, "dev", plugin).write_text(
        "NETLOOM_SERVER=dev.clearpass.example:443\n",
        encoding="utf-8",
    )
    _credential_path(config_dir, "prod", plugin).write_text(
        "\n".join(
            [
                "NETLOOM_CLIENT_ID=prod-client",
                "NETLOOM_CLIENT_SECRET=prod-secret",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    _credential_path(config_dir, "dev", plugin).write_text(
        "\n".join(
            [
                "NETLOOM_CLIENT_ID=dev-client",
                "NETLOOM_CLIENT_SECRET=dev-secret",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _make_settings(tmp_path):
    paths = AppPaths(
        cache_dir=tmp_path / "cache",
        state_dir=tmp_path / "state",
        response_dir=tmp_path / "responses",
        app_log_dir=tmp_path / "logs",
    ).ensure()
    return config.Settings(paths=paths)


def test_load_settings_uses_active_profile_files(monkeypatch, tmp_path):
    config_dir = _configure_runtime(monkeypatch, tmp_path)
    _write_profiles(config_dir)

    settings = load_settings()

    assert settings.active_profile == "prod"
    assert settings.plugin == "clearpass"
    assert settings.server == "prod.clearpass.example:443"
    assert settings.client_id == "prod-client"
    assert settings.client_secret == "prod-secret"


def test_load_settings_uses_defaults_as_profile_fallback(monkeypatch, tmp_path):
    config_dir = _configure_runtime(monkeypatch, tmp_path)
    _write_global_config(config_dir)
    plugin_dir = _plugin_dir(config_dir)
    plugin_dir.mkdir(parents=True, exist_ok=True)
    _profiles_dir(config_dir).mkdir(parents=True, exist_ok=True)
    _credentials_dir(config_dir).mkdir(parents=True, exist_ok=True)
    _defaults_path(config_dir).write_text(
        "\n".join(
            [
                "NETLOOM_ACTIVE_PROFILE=prod",
                "NETLOOM_HTTPS_PREFIX=https://fallback/",
                "NETLOOM_VERIFY_SSL=true",
                "NETLOOM_TIMEOUT=42",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    _profile_path(config_dir, "prod").write_text(
        "NETLOOM_SERVER=prod.clearpass.example:443\n",
        encoding="utf-8",
    )
    _credential_path(config_dir, "prod").write_text(
        "\n".join(
            [
                "NETLOOM_CLIENT_ID=prod-client",
                "NETLOOM_CLIENT_SECRET=prod-secret",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    settings = load_settings()

    assert settings.server == "prod.clearpass.example:443"
    assert settings.https_prefix == "https://fallback/"
    assert settings.verify_ssl is True
    assert settings.timeout == 42


def test_load_settings_without_active_plugin(monkeypatch, tmp_path):
    _configure_runtime(monkeypatch, tmp_path)

    settings = load_settings()

    assert settings.plugin is None
    assert settings.active_profile is None
    assert settings.profiles_path is None
    assert settings.credentials_path is None


def test_load_settings_prefers_process_environment(monkeypatch, tmp_path):
    config_dir = _configure_runtime(monkeypatch, tmp_path)
    _write_profiles(config_dir)
    monkeypatch.setenv("NETLOOM_SERVER", "override.example:443")
    monkeypatch.setenv("NETLOOM_CLIENT_ID", "override-client")

    settings = load_settings()

    assert settings.server == "override.example:443"
    assert settings.client_id == "override-client"
    assert settings.client_secret == "prod-secret"


def test_load_settings_reads_cli_timing_from_global_config(monkeypatch, tmp_path):
    config_dir = _configure_runtime(monkeypatch, tmp_path)
    _write_profiles(config_dir)
    (config_dir / "config.env").write_text(
        "NETLOOM_ACTIVE_PLUGIN=clearpass\nNETLOOM_CLI_TIMING=1\n",
        encoding="utf-8",
    )

    settings = load_settings()

    assert settings.cli_timing is True


def test_load_settings_applies_client_secret_ref_precedence(monkeypatch, tmp_path):
    config_dir = _configure_runtime(monkeypatch, tmp_path)
    _write_global_config(config_dir)
    plugin_dir = _plugin_dir(config_dir)
    plugin_dir.mkdir(parents=True, exist_ok=True)
    _profiles_dir(config_dir).mkdir(parents=True, exist_ok=True)
    _credentials_dir(config_dir).mkdir(parents=True, exist_ok=True)
    _defaults_path(config_dir).write_text(
        "\n".join(
            [
                "NETLOOM_ACTIVE_PROFILE=prod",
                "NETLOOM_CLIENT_SECRET_REF=defaults/client-secret",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    _profile_path(config_dir, "prod").write_text(
        "\n".join(
            [
                "NETLOOM_SERVER=prod.clearpass.example:443",
                "NETLOOM_CLIENT_SECRET_REF=profile/client-secret",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    _credential_path(config_dir, "prod").write_text(
        "\n".join(
            [
                "NETLOOM_CLIENT_ID=prod-client",
                "NETLOOM_CLIENT_SECRET_REF=credentials/client-secret",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    settings = load_settings()
    assert settings.client_secret_ref == "credentials/client-secret"

    monkeypatch.setenv("NETLOOM_CLIENT_SECRET_REF", "env/client-secret")

    settings = load_settings()
    assert settings.client_secret_ref == "env/client-secret"


def test_load_settings_uses_out_dir_from_profile_files(monkeypatch, tmp_path):
    config_dir = _configure_runtime(monkeypatch, tmp_path)
    _write_global_config(config_dir)
    plugin_dir = _plugin_dir(config_dir)
    plugin_dir.mkdir(parents=True, exist_ok=True)
    _profiles_dir(config_dir).mkdir(parents=True, exist_ok=True)
    _credentials_dir(config_dir).mkdir(parents=True, exist_ok=True)
    _defaults_path(config_dir).write_text(
        "NETLOOM_ACTIVE_PROFILE=prod\n",
        encoding="utf-8",
    )
    _profile_path(config_dir, "prod").write_text(
        "\n".join(
            [
                "NETLOOM_SERVER=prod.clearpass.example:443",
                "NETLOOM_OUT_DIR=~/custom-responses",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    _credential_path(config_dir, "prod").write_text(
        "\n".join(
            [
                "NETLOOM_CLIENT_ID=prod-client",
                "NETLOOM_CLIENT_SECRET=prod-secret",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    home_dir = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setenv("USERPROFILE", str(home_dir))

    settings = load_settings()

    assert settings.paths.response_dir == home_dir / "custom-responses"


def test_load_settings_uses_timestamped_default_log_file(monkeypatch, tmp_path):
    _configure_runtime(monkeypatch, tmp_path)

    settings = load_settings()

    assert settings.log_file is not None
    assert settings.log_file.parent == tmp_path / "state" / "logs"
    assert re.fullmatch(
        r"netloom-\d{8}-\d{6}-\d{6}\.log",
        settings.log_file.name,
    )
    assert settings.log_to_file is False


def test_load_settings_preserves_explicit_log_file(monkeypatch, tmp_path):
    config_dir = _configure_runtime(monkeypatch, tmp_path)
    _write_global_config(config_dir)
    plugin_dir = _plugin_dir(config_dir)
    plugin_dir.mkdir(parents=True, exist_ok=True)
    _profiles_dir(config_dir).mkdir(parents=True, exist_ok=True)
    _credentials_dir(config_dir).mkdir(parents=True, exist_ok=True)
    _defaults_path(config_dir).write_text(
        "\n".join(
            [
                "NETLOOM_ACTIVE_PROFILE=prod",
                "NETLOOM_LOG_TO_FILE=true",
                "NETLOOM_LOG_FILE=custom-logs/session.log",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    _profile_path(config_dir, "prod").write_text(
        "NETLOOM_SERVER=prod.clearpass.example:443\n",
        encoding="utf-8",
    )
    _credential_path(config_dir, "prod").write_text(
        "\n".join(
            [
                "NETLOOM_CLIENT_ID=prod-client",
                "NETLOOM_CLIENT_SECRET=prod-secret",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    settings = load_settings()

    assert settings.log_file == Path("custom-logs/session.log")
    assert settings.log_to_file is True


def test_list_profiles_and_set_active_profile(monkeypatch, tmp_path):
    config_dir = _configure_runtime(monkeypatch, tmp_path)
    _write_profiles(config_dir)

    assert config.list_profiles() == ["dev", "prod"]

    target = config.set_active_profile("dev")

    assert target == config_dir / "plugins" / "clearpass" / "defaults.env"
    profiles_text = target.read_text(encoding="utf-8")
    assert "NETLOOM_ACTIVE_PROFILE=dev" in profiles_text


def test_set_active_plugin_writes_global_config(monkeypatch, tmp_path):
    config_dir = _configure_runtime(monkeypatch, tmp_path)

    target = config.set_active_plugin("clearpass")

    assert target == config_dir / "config.env"
    assert "NETLOOM_ACTIVE_PLUGIN=clearpass" in target.read_text(encoding="utf-8")


def test_set_active_plugin_can_clear_selection(monkeypatch, tmp_path):
    config_dir = _configure_runtime(monkeypatch, tmp_path)

    target = config.set_active_plugin(None)

    assert target == config_dir / "config.env"
    assert "NETLOOM_ACTIVE_PLUGIN=none" in target.read_text(encoding="utf-8")
    assert config.resolve_active_plugin() is None


def test_hyphenated_profile_names_round_trip(monkeypatch, tmp_path):
    config_dir = _configure_runtime(monkeypatch, tmp_path)
    _write_global_config(config_dir)
    plugin_dir = _plugin_dir(config_dir)
    plugin_dir.mkdir(parents=True, exist_ok=True)
    _profiles_dir(config_dir).mkdir(parents=True, exist_ok=True)
    _credentials_dir(config_dir).mkdir(parents=True, exist_ok=True)
    _defaults_path(config_dir).write_text(
        "NETLOOM_ACTIVE_PROFILE=qa-edge\n",
        encoding="utf-8",
    )
    _profile_path(config_dir, "qa-edge").write_text(
        "\n".join(
            [
                "NETLOOM_SERVER=qa.clearpass.example:443",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    _credential_path(config_dir, "qa-edge").write_text(
        "\n".join(
            [
                "NETLOOM_CLIENT_ID=qa-client",
                "NETLOOM_CLIENT_SECRET=qa-secret",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    settings = load_settings()

    assert settings.active_profile == "qa-edge"
    assert settings.plugin == "clearpass"
    assert settings.server == "qa.clearpass.example:443"
    assert config.list_profiles() == ["qa-edge"]

    target = config.set_active_profile("qa-edge")

    assert "NETLOOM_ACTIVE_PROFILE=qa-edge" in target.read_text(encoding="utf-8")


def test_main_server_use_switches_profile(monkeypatch, capsys, tmp_path):
    config_dir = _configure_runtime(monkeypatch, tmp_path)
    _write_profiles(config_dir)
    monkeypatch.setattr(
        main,
        "configure_logging",
        lambda settings, root_name: _FakeLogMgr(),
    )
    monkeypatch.setattr(main, "load_settings", lambda: _make_settings(tmp_path))

    monkeypatch.setattr(sys, "argv", ["netloom", "server", "use", "dev"])
    main.main()

    out = capsys.readouterr().out
    assert "Active profile set to dev." in out
    assert "Server: dev.clearpass.example:443" in out
    assert "Plugin: clearpass" in out
    profiles_path = config_dir / "plugins" / "clearpass" / "defaults.env"
    assert "NETLOOM_ACTIVE_PROFILE=dev" in profiles_path.read_text(encoding="utf-8")


def test_main_server_show_prints_profile_status(monkeypatch, capsys, tmp_path):
    config_dir = _configure_runtime(monkeypatch, tmp_path)
    _write_profiles(config_dir)
    monkeypatch.setattr(
        main,
        "configure_logging",
        lambda settings, root_name: _FakeLogMgr(),
    )
    monkeypatch.setattr(main, "load_settings", lambda: _make_settings(tmp_path))

    monkeypatch.setattr(sys, "argv", ["netloom", "server", "show"])
    main.main()

    out = capsys.readouterr().out
    assert "Active profile: prod" in out
    assert "Active plugin: clearpass" in out
    assert "Server: prod.clearpass.example:443" in out
    assert "Client ID: prod-client" in out
    assert "Client secret: plaintext configured" in out
    assert (
        "Profiles file: "
        f"{config_dir / 'plugins' / 'clearpass' / 'profiles' / 'prod.env'}" in out
    )
    assert (
        "Credentials file: "
        f"{config_dir / 'plugins' / 'clearpass' / 'credentials' / 'prod.env'}"
    ) in out


def test_main_server_show_reports_keychain_secret_ref(monkeypatch, capsys, tmp_path):
    config_dir = _configure_runtime(monkeypatch, tmp_path)
    _write_global_config(config_dir)
    plugin_dir = _plugin_dir(config_dir)
    plugin_dir.mkdir(parents=True, exist_ok=True)
    _profiles_dir(config_dir).mkdir(parents=True, exist_ok=True)
    _credentials_dir(config_dir).mkdir(parents=True, exist_ok=True)
    _defaults_path(config_dir).write_text(
        "NETLOOM_ACTIVE_PROFILE=prod\n",
        encoding="utf-8",
    )
    _profile_path(config_dir, "prod").write_text(
        "NETLOOM_SERVER=prod.clearpass.example:443\n",
        encoding="utf-8",
    )
    _credential_path(config_dir, "prod").write_text(
        "\n".join(
            [
                "NETLOOM_CLIENT_ID=prod-client",
                "NETLOOM_CLIENT_SECRET_REF=prod/client-secret",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        main,
        "configure_logging",
        lambda settings, root_name: _FakeLogMgr(),
    )
    monkeypatch.setattr(main, "load_settings", lambda: _make_settings(tmp_path))

    monkeypatch.setattr(sys, "argv", ["netloom", "server", "show"])
    main.main()

    out = capsys.readouterr().out
    assert "Client ID: prod-client" in out
    assert "Client secret: keychain ref configured" in out
    assert "Client secret ref: prod/client-secret" in out
