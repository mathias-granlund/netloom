import sys

import arapy.cli.main as main
from arapy.core import config
from arapy.core.config import AppPaths, load_settings


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
    monkeypatch.setenv("ARAPY_CONFIG_DIR", str(config_dir))
    monkeypatch.setenv("ARAPY_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("ARAPY_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.delenv("ARAPY_SERVER", raising=False)
    monkeypatch.delenv("ARAPY_CLIENT_ID", raising=False)
    monkeypatch.delenv("ARAPY_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("ARAPY_ACTIVE_PROFILE", raising=False)
    return config_dir


def _write_profiles(config_dir):
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "profiles.env").write_text(
        "\n".join(
            [
                "ARAPY_ACTIVE_PROFILE=prod",
                "ARAPY_SERVER_PROD=prod.clearpass.example:443",
                "ARAPY_SERVER_DEV=dev.clearpass.example:443",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (config_dir / "credentials.env").write_text(
        "\n".join(
            [
                "ARAPY_CLIENT_ID_PROD=prod-client",
                "ARAPY_CLIENT_SECRET_PROD=prod-secret",
                "ARAPY_CLIENT_ID_DEV=dev-client",
                "ARAPY_CLIENT_SECRET_DEV=dev-secret",
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
    assert settings.server == "prod.clearpass.example:443"
    assert settings.client_id == "prod-client"
    assert settings.client_secret == "prod-secret"


def test_load_settings_prefers_process_environment(monkeypatch, tmp_path):
    config_dir = _configure_runtime(monkeypatch, tmp_path)
    _write_profiles(config_dir)
    monkeypatch.setenv("ARAPY_SERVER", "override.example:443")
    monkeypatch.setenv("ARAPY_CLIENT_ID", "override-client")

    settings = load_settings()

    assert settings.server == "override.example:443"
    assert settings.client_id == "override-client"
    assert settings.client_secret == "prod-secret"


def test_load_settings_uses_out_dir_from_profile_files(monkeypatch, tmp_path):
    config_dir = _configure_runtime(monkeypatch, tmp_path)
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "profiles.env").write_text(
        "\n".join(
            [
                "ARAPY_ACTIVE_PROFILE=prod",
                "ARAPY_SERVER_PROD=prod.clearpass.example:443",
                "ARAPY_OUT_DIR_PROD=~/custom-responses",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (config_dir / "credentials.env").write_text(
        "\n".join(
            [
                "ARAPY_CLIENT_ID_PROD=prod-client",
                "ARAPY_CLIENT_SECRET_PROD=prod-secret",
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

    assert target == config_dir / "profiles.env"
    profiles_text = target.read_text(encoding="utf-8")
    assert "ARAPY_ACTIVE_PROFILE=dev" in profiles_text


def test_hyphenated_profile_names_round_trip(monkeypatch, tmp_path):
    config_dir = _configure_runtime(monkeypatch, tmp_path)
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "profiles.env").write_text(
        "\n".join(
            [
                "ARAPY_ACTIVE_PROFILE=qa-edge",
                "ARAPY_SERVER_QA_EDGE=qa.clearpass.example:443",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (config_dir / "credentials.env").write_text(
        "\n".join(
            [
                "ARAPY_CLIENT_ID_QA_EDGE=qa-client",
                "ARAPY_CLIENT_SECRET_QA_EDGE=qa-secret",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    settings = load_settings()

    assert settings.active_profile == "qa-edge"
    assert settings.server == "qa.clearpass.example:443"
    assert config.list_profiles() == ["qa-edge"]

    target = config.set_active_profile("qa-edge")

    assert "ARAPY_ACTIVE_PROFILE=qa-edge" in target.read_text(encoding="utf-8")


def test_main_server_use_switches_profile(monkeypatch, capsys, tmp_path):
    config_dir = _configure_runtime(monkeypatch, tmp_path)
    _write_profiles(config_dir)
    monkeypatch.setattr(
        main,
        "configure_logging",
        lambda settings, root_name: _FakeLogMgr(),
    )
    monkeypatch.setattr(main, "load_settings", lambda: _make_settings(tmp_path))
    monkeypatch.setattr(
        main,
        "ClearPassClient",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("server commands should not create a client")
        ),
    )

    monkeypatch.setattr(sys, "argv", ["arapy", "server", "use", "dev"])
    main.main()

    out = capsys.readouterr().out
    assert "Active profile set to dev." in out
    assert "Server: dev.clearpass.example:443" in out
    assert "ARAPY_ACTIVE_PROFILE=dev" in (
        config_dir / "profiles.env"
    ).read_text(encoding="utf-8")


def test_main_server_show_prints_profile_status(monkeypatch, capsys, tmp_path):
    config_dir = _configure_runtime(monkeypatch, tmp_path)
    _write_profiles(config_dir)
    monkeypatch.setattr(
        main,
        "configure_logging",
        lambda settings, root_name: _FakeLogMgr(),
    )
    monkeypatch.setattr(main, "load_settings", lambda: _make_settings(tmp_path))

    monkeypatch.setattr(sys, "argv", ["arapy", "server", "show"])
    main.main()

    out = capsys.readouterr().out
    assert "Active profile: prod" in out
    assert "Server: prod.clearpass.example:443" in out
    assert f"Profiles file: {config_dir / 'profiles.env'}" in out
