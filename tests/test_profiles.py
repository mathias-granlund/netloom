import sys

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


def _write_profiles(config_dir, plugin="clearpass"):
    _write_global_config(config_dir, plugin=plugin)
    plugin_dir = _plugin_dir(config_dir, plugin)
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "profiles.env").write_text(
        "\n".join(
            [
                "NETLOOM_ACTIVE_PROFILE=prod",
                "NETLOOM_SERVER_PROD=prod.clearpass.example:443",
                "NETLOOM_SERVER_DEV=dev.clearpass.example:443",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (plugin_dir / "credentials.env").write_text(
        "\n".join(
            [
                "NETLOOM_CLIENT_ID_PROD=prod-client",
                "NETLOOM_CLIENT_SECRET_PROD=prod-secret",
                "NETLOOM_CLIENT_ID_DEV=dev-client",
                "NETLOOM_CLIENT_SECRET_DEV=dev-secret",
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


def test_load_settings_uses_out_dir_from_profile_files(monkeypatch, tmp_path):
    config_dir = _configure_runtime(monkeypatch, tmp_path)
    _write_global_config(config_dir)
    plugin_dir = _plugin_dir(config_dir)
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "profiles.env").write_text(
        "\n".join(
            [
                "NETLOOM_ACTIVE_PROFILE=prod",
                "NETLOOM_SERVER_PROD=prod.clearpass.example:443",
                "NETLOOM_OUT_DIR_PROD=~/custom-responses",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (plugin_dir / "credentials.env").write_text(
        "\n".join(
            [
                "NETLOOM_CLIENT_ID_PROD=prod-client",
                "NETLOOM_CLIENT_SECRET_PROD=prod-secret",
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


def test_list_profiles_and_set_active_profile(monkeypatch, tmp_path):
    config_dir = _configure_runtime(monkeypatch, tmp_path)
    _write_profiles(config_dir)

    assert config.list_profiles() == ["dev", "prod"]

    target = config.set_active_profile("dev")

    assert target == config_dir / "plugins" / "clearpass" / "profiles.env"
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
    (plugin_dir / "profiles.env").write_text(
        "\n".join(
            [
                "NETLOOM_ACTIVE_PROFILE=qa-edge",
                "NETLOOM_SERVER_QA_EDGE=qa.clearpass.example:443",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (plugin_dir / "credentials.env").write_text(
        "\n".join(
            [
                "NETLOOM_CLIENT_ID_QA_EDGE=qa-client",
                "NETLOOM_CLIENT_SECRET_QA_EDGE=qa-secret",
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
    profiles_path = config_dir / "plugins" / "clearpass" / "profiles.env"
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
    assert (
        f"Profiles file: {config_dir / 'plugins' / 'clearpass' / 'profiles.env'}"
        in out
    )
    assert (
        "Credentials file: "
        f"{config_dir / 'plugins' / 'clearpass' / 'credentials.env'}"
    ) in out
