import pytest

import netloom.cli.help as cli_help
import netloom.core.interactive_help as helpmod


def test_render_help_includes_server_builtin_from_lightweight_layer(monkeypatch):
    monkeypatch.setattr(helpmod, "list_profiles", lambda: ["dev", "prod"])
    monkeypatch.setattr(helpmod, "profiles_env_path", lambda: "/tmp/profiles.env")
    monkeypatch.setattr(
        helpmod,
        "credentials_env_path",
        lambda: "/tmp/credentials.env",
    )

    text = helpmod.render_help({}, {"module": "server"}, version="1.9.8")

    assert "netloom server use <profile>" in text
    assert "Configured profiles:" in text
    assert "  - dev" in text
    assert "  - prod" in text


def test_render_help_lists_builtin_and_catalog_modules_from_lightweight_layer():
    text = helpmod.render_help(
        {
            "modules": {
                "identities": {
                    "endpoint": {
                        "actions": {
                            "list": {"method": "GET", "paths": ["/api/endpoint"]}
                        }
                    }
                }
            }
        },
        {},
        version="1.9.8",
    )

    assert "Available modules:" in text
    assert "  - cache" in text
    assert "  - load" in text
    assert "  - server" in text
    assert "  - identities" in text


@pytest.mark.parametrize(
    ("catalog", "args"),
    [
        ({}, {}),
        (
            {
                "modules": {
                    "identities": {
                        "endpoint": {
                            "actions": {
                                "list": {
                                    "method": "GET",
                                    "paths": ["/api/endpoint"],
                                    "params": ["limit", "offset", "filter"],
                                },
                                "get": {
                                    "method": "GET",
                                    "paths": ["/api/endpoint/{id}"],
                                },
                            }
                        }
                    }
                }
            },
            {"module": "identities"},
        ),
        (
            {
                "modules": {
                    "identities": {
                        "endpoint": {
                            "actions": {
                                "list": {
                                    "method": "GET",
                                    "paths": ["/api/endpoint"],
                                    "params": ["limit", "offset", "filter"],
                                },
                                "get": {
                                    "method": "GET",
                                    "paths": ["/api/endpoint/{id}"],
                                },
                            }
                        }
                    }
                }
            },
            {"module": "identities", "service": "endpoint"},
        ),
        (
            {
                "modules": {
                    "identities": {
                        "endpoint": {
                            "actions": {
                                "list": {
                                    "method": "GET",
                                    "paths": ["/api/endpoint"],
                                    "params": ["limit", "offset", "filter"],
                                },
                                "get": {
                                    "method": "GET",
                                    "paths": ["/api/endpoint/{id}"],
                                },
                            }
                        }
                    }
                }
            },
            {"module": "identities", "service": "endpoint", "action": "list"},
        ),
        (
            {
                "modules": {
                    "globalserverconfiguration": {
                        "attribute-name": {
                            "actions": {
                                "list": {
                                    "method": "GET",
                                    "paths": ["/api/attribute"],
                                    "params": [
                                        "limit",
                                        "offset",
                                        "filter",
                                        "sort",
                                        "calculate_count",
                                    ],
                                },
                                "get": {
                                    "method": "GET",
                                    "paths": [
                                        "/api/attribute/{entity_name}/name/{name}"
                                    ],
                                },
                            }
                        }
                    }
                }
            },
            {
                "module": "globalserverconfiguration",
                "service": "attribute-name",
                "action": "get",
            },
        ),
    ],
)
def test_lightweight_help_matches_cli_help_for_cached_compact_cases(
    monkeypatch, catalog, args
):
    monkeypatch.setattr(helpmod, "list_profiles", lambda: ["dev", "prod"])
    monkeypatch.setattr(helpmod, "profiles_env_path", lambda: "/tmp/profiles.env")
    monkeypatch.setattr(
        helpmod,
        "credentials_env_path",
        lambda: "/tmp/credentials.env",
    )
    monkeypatch.setattr(helpmod, "list_plugins", lambda: ["clearpass"])

    monkeypatch.setattr(cli_help, "list_profiles", lambda: ["dev", "prod"])
    monkeypatch.setattr(cli_help, "profiles_env_path", lambda: "/tmp/profiles.env")
    monkeypatch.setattr(
        cli_help,
        "credentials_env_path",
        lambda: "/tmp/credentials.env",
    )
    monkeypatch.setattr(cli_help, "list_plugins", lambda: ["clearpass"])

    light = helpmod.render_help(catalog, args, version="1.9.8")
    full = cli_help.render_help(catalog, args, version="1.9.8")

    assert light == full
