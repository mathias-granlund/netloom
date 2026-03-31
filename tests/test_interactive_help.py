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
    assert "Manage the local API catalog cache" in text
    assert "Select or inspect the active plugin" in text
    assert "Select or inspect the active profile" in text
    assert "identities" in text
    assert "Identity, endpoint, and account records" in text


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


def test_describe_context_lists_top_level_modules():
    text = helpmod.describe_context(
        ["--catalog-view=full"],
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
    )

    assert "cache" in text
    assert "load" in text
    assert "server" in text
    assert "identities" in text


def test_describe_context_lists_services_with_summaries():
    text = helpmod.describe_context(
        ["identities"],
        {
            "modules": {
                "identities": {
                    "endpoint": {
                        "summary": "Manage endpoints",
                        "actions": {
                            "list": {
                                "method": "GET",
                                "paths": ["/api/endpoint"],
                                "summary": "Get a list of endpoints",
                            },
                            "get": {
                                "method": "GET",
                                "paths": ["/api/endpoint/{id}"],
                                "summary": "Get one endpoint",
                            }
                        }
                    }
                }
            }
        },
    )

    assert "endpoint" in text
    assert "Manage endpoints" in text


def test_describe_context_lists_single_action_service_summary():
    text = helpmod.describe_context(
        ["policyelements"],
        {
            "modules": {
                "policyelements": {
                    "service-disable": {
                        "actions": {
                            "get": {
                                "method": "POST",
                                "paths": ["/api/service/disable/{id}"],
                                "summary": "Disable a Service",
                            }
                        }
                    }
                }
            }
        },
    )

    assert "service-disable" in text
    assert "Disable a Service" in text


def test_describe_context_uses_manage_fallback_from_list_summary():
    text = helpmod.describe_context(
        ["policyelements"],
        {
            "modules": {
                "policyelements": {
                    "network-device": {
                        "actions": {
                            "list": {
                                "method": "GET",
                                "paths": ["/api/network-device"],
                                "summary": "Get a list of network devices",
                            },
                            "get": {
                                "method": "GET",
                                "paths": ["/api/network-device/{id}"],
                                "summary": "Get a network device",
                            },
                            "add": {
                                "method": "POST",
                                "paths": ["/api/network-device"],
                                "summary": "Create a new network device",
                            },
                        }
                    }
                }
            }
        },
    )

    assert "network-device" in text
    assert "Manage network devices" in text


def test_describe_context_hides_full_only_services_for_module_help():
    text = helpmod.describe_context(
        ["certificateauthority"],
        {
            "modules": {
                "certificateauthority": {
                    "certificate": {
                        "summary": "Manage Onboard certificates",
                        "actions": {
                            "list": {
                                "method": "GET",
                                "paths": ["/api/certificate"],
                            }
                        },
                    }
                }
            },
            "full_modules": {
                "certificateauthority": {
                    "certificate": {
                        "summary": "Manage Onboard certificates",
                        "actions": {
                            "list": {
                                "method": "GET",
                                "paths": ["/api/certificate"],
                            }
                        },
                    },
                    "certificate-chain": {
                        "summary": "Get a certificate and its trust chain",
                        "actions": {},
                    },
                }
            },
        },
    )

    assert "certificate" in text
    assert "certificate-chain" not in text


def test_describe_context_hides_short_alias_when_canonical_service_exists():
    text = helpmod.describe_context(
        ["certificateauthority"],
        {
            "modules": {
                "certificateauthority": {
                    "chain": {
                        "actions": {
                            "get": {
                                "method": "GET",
                                "paths": ["/api/certificate/chain/{id}"],
                                "summary": "Get a certificate and its trust chain",
                            }
                        }
                    },
                    "device": {
                        "actions": {
                            "list": {
                                "method": "GET",
                                "paths": ["/api/device"],
                                "summary": "Get a list of devices",
                            }
                        }
                    },
                }
            },
            "full_modules": {
                "certificateauthority": {
                    "certificate-chain": {
                        "summary": "Get a certificate and its trust chain",
                        "actions": {},
                    },
                    "onboard-device": {
                        "summary": "Manage Onboard devices",
                        "actions": {},
                    },
                }
            },
        },
    )

    assert "certificate-chain" in text
    assert "onboard-device" in text
    assert "  chain " not in text
    assert "  device " not in text


def test_describe_context_hides_aliases_when_both_forms_exist_in_full_modules():
    text = helpmod.describe_context(
        ["certificateauthority"],
        {
            "modules": {
                "certificateauthority": {
                    "certificate-chain": {
                        "summary": "Get a certificate and its trust chain",
                        "actions": {},
                    },
                    "chain": {
                        "summary": "Get a certificate and its trust chain",
                        "actions": {"get": {"method": "GET"}},
                    },
                }
            },
            "full_modules": {
                "certificateauthority": {
                    "certificate-chain": {
                        "summary": "Get a certificate and its trust chain",
                        "actions": {},
                    },
                    "chain": {
                        "summary": "Get a certificate and its trust chain",
                        "actions": {"get": {"method": "GET"}},
                    },
                }
            },
        },
    )

    assert "certificate-chain" in text
    assert "  chain " not in text


def test_describe_context_hides_request_alias_when_summary_picks_one_match():
    text = helpmod.describe_context(
        ["certificateauthority"],
        {
            "modules": {
                "certificateauthority": {
                    "request": {
                        "summary": "Import a certificate signing request",
                        "actions": {"add": {"method": "POST"}},
                    }
                }
            },
            "full_modules": {
                "certificateauthority": {
                    "certificate-request": {
                        "summary": "Import a certificate signing request",
                        "actions": {},
                    },
                    "certificate-sign-request": {
                        "summary": "Sign a certificate signing request",
                        "actions": {},
                    },
                    "request": {
                        "summary": "Import a certificate signing request",
                        "actions": {"add": {"method": "POST"}},
                    },
                }
            },
        },
    )

    assert "certificate-request" in text
    assert "certificate-sign-request" not in text
    assert "  request " not in text


def test_render_help_accepts_canonical_service_name_from_full_modules():
    text = helpmod.render_help(
        {
            "modules": {
                "certificateauthority": {
                    "chain": {
                        "summary": "Get a certificate and its trust chain",
                        "actions": {
                            "get": {
                                "method": "GET",
                                "paths": ["/api/certificate/chain/{id}"],
                                "summary": "Get a certificate and its trust chain",
                            }
                        }
                    },
                }
            },
            "full_modules": {
                "certificateauthority": {
                    "certificate-chain": {
                        "summary": "Get a certificate and its trust chain",
                        "actions": {
                            "get": {
                                "method": "GET",
                                "paths": ["/api/certificate/chain/{id}"],
                                "summary": "Get a certificate and its trust chain",
                            }
                        },
                    }
                }
            },
        },
        {"module": "certificateauthority", "service": "certificate-chain"},
        version="1.9.15",
    )

    assert "Unknown service" not in text
    assert "Service: certificate-chain" in text
    assert "Available actions:" in text
    assert "get" in text


def test_render_help_hides_full_only_service_without_visible_alias():
    text = helpmod.render_help(
        {
            "modules": {
                "certificateauthority": {
                    "certificate": {
                        "actions": {
                            "list": {"method": "GET", "paths": ["/api/certificate"]}
                        }
                    }
                }
            },
            "full_modules": {
                "certificateauthority": {
                    "certificate-chain": {
                        "summary": "Get a certificate and its trust chain",
                        "actions": {
                            "get": {
                                "method": "GET",
                                "paths": ["/api/certificate/chain/{id}"],
                            }
                        },
                    }
                }
            },
        },
        {"module": "certificateauthority"},
        version="1.9.15",
    )

    assert "certificate-chain" not in text


def test_describe_context_lists_actions_with_summaries():
    text = helpmod.describe_context(
        ["identities", "endpoint"],
        {
            "modules": {
                "identities": {
                    "endpoint": {
                        "actions": {
                            "list": {
                                "method": "GET",
                                "paths": ["/api/endpoint"],
                                "summary": "Get a list of endpoints",
                            },
                            "get": {
                                "method": "GET",
                                "paths": ["/api/endpoint/{id}"],
                                "summary": "Get one endpoint",
                            },
                        }
                    }
                }
            }
        },
    )

    assert "list" in text
    assert "Get a list of endpoints" in text
    assert "get" in text
    assert "Get one endpoint" in text
    assert "copy" in text
    assert "diff" in text


def test_describe_context_for_action_reuses_compact_help():
    text = helpmod.describe_context(
        ["identities", "endpoint", "list"],
        {
            "modules": {
                "identities": {
                    "endpoint": {
                        "actions": {
                            "list": {
                                "method": "GET",
                                "paths": ["/api/endpoint"],
                                "params": ["limit", "offset", "filter"],
                            }
                        }
                    }
                }
            }
        },
    )

    assert "list (identities endpoint):" in text
    assert "usage: netloom <module> <service> list [options]" in text


def test_describe_context_for_server_use_lists_profiles(monkeypatch):
    monkeypatch.setattr(helpmod, "list_profiles", lambda: ["dev", "prod"])

    text = helpmod.describe_context(["server", "use"])

    assert "dev" in text
    assert "prod" in text
