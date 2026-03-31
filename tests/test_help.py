import types

import netloom.cli.help as helpmod
from netloom.plugins.clearpass.help import build_help_context


def test_render_action_block_includes_dynamic_body_metadata():
    text = helpmod.render_action_block(
        "add",
        {
            "method": "POST",
            "paths": ["/api/example"],
            "summary": "Create an example object",
            "response_codes": ["201 Created", "422 Unprocessable Entity"],
            "response_content_types": ["application/json"],
            "body_description": "Example payload",
            "body_required": ["name"],
            "body_fields": [
                {
                    "name": "name",
                    "type": "string",
                    "required": True,
                    "description": "Unique object name",
                }
            ],
            "body_example": {"name": "demo"},
        },
    )

    assert "summary: Create an example object" in text
    assert "response codes:" in text
    assert "body required:" in text
    assert '"name": "demo"' in text


def test_render_action_block_hides_params_when_body_fields_exist():
    text = helpmod.render_action_block(
        "add",
        {
            "method": "POST",
            "paths": ["/api/example"],
            "params": ["name", "description"],
            "body_fields": [
                {"name": "name", "type": "string", "required": True},
            ],
        },
    )

    assert "body fields:" in text
    assert "params:" not in text


def test_render_action_block_keeps_params_without_body_fields():
    text = helpmod.render_action_block(
        "list",
        {
            "method": "GET",
            "paths": ["/api/example"],
            "params": ["limit", "offset"],
        },
    )

    assert "params:" in text
    assert "limit" in text


def test_render_action_block_indents_multiline_notes():
    text = helpmod.render_action_block(
        "list",
        {
            "method": "GET",
            "paths": ["/api/example"],
            "notes": ["Line one\nLine two\nLine three"],
        },
    )

    assert "  notes:" in text
    assert "    - Line one" in text
    assert "      Line two" in text
    assert "      Line three" in text


def test_render_action_block_replaces_verbose_filter_notes_with_compact_help():
    text = helpmod.render_action_block(
        "list",
        {
            "method": "GET",
            "paths": ["/api/example"],
            "params": ["filter", "limit", "offset"],
            "notes": [
                (
                    "Get a list of objects.\n"
                    "More about JSON filter expressions\n"
                    "A filter is specified as a JSON object, where the properties "
                    "of the object specify the type of query to be performed."
                )
            ],
        },
    )

    assert "  filter:" in text
    assert "shorthand: --filter=name:equals:TEST" in text
    assert '--filter=\'{"name":{"$contains":"TEST"}}\'' in text
    assert "More about JSON filter expressions" not in text
    assert "A filter is specified as a JSON object" not in text
    assert "    - limit" in text
    assert "    - offset" in text
    assert "    - filter" not in text


def test_render_help_includes_server_builtin(monkeypatch):
    monkeypatch.setattr(helpmod, "list_profiles", lambda: ["dev", "prod"])
    monkeypatch.setattr(helpmod, "profiles_env_path", lambda: "/tmp/profiles.env")
    monkeypatch.setattr(helpmod, "credentials_env_path", lambda: "/tmp/credentials.env")

    text = helpmod.render_help({}, {"module": "server"}, version="1.6.0")

    assert "netloom server use <profile>" in text
    assert "Configured profiles:" in text
    assert "  - dev" in text
    assert "  - prod" in text
    assert "Examples:" not in text
    assert "Common options:" not in text
    assert "Common flags:" not in text


def test_render_help_without_catalog_lists_builtin_modules():
    text = helpmod.render_help({}, {}, version="1.4.7")

    assert "Available modules:" in text
    assert "cache" in text
    assert "Manage the local API catalog cache" in text
    assert "server" in text
    assert "Select or inspect the active profile" in text


def test_render_help_for_legacy_copy_command():
    text = helpmod.render_help({}, {"module": "copy"}, version="1.6.0")

    assert "Usage:" in text
    assert "netloom <module> <service> {copy|diff} --from=SOURCE --to=TARGET" in text
    assert "netloom copy <service> <action> [options] [flags]" not in text


def test_render_help_includes_copy_as_service_action():
    text = helpmod.render_help(
        {
            "modules": {
                "policyelements": {
                    "network-device": {
                        "actions": {
                            "list": {"method": "GET", "paths": ["/api/network-device"]}
                        }
                    }
                }
            }
        },
        {"module": "policyelements", "service": "network-device"},
        version="1.7.1",
    )

    assert "Available actions:" in text
    assert "copy" in text
    assert "diff" in text
    assert "Examples:" not in text
    assert "Common options:" not in text
    assert "Common flags:" not in text


def test_render_help_for_copy_action():
    text = helpmod.render_help(
        {
            "modules": {
                "policyelements": {
                    "network-device": {
                        "actions": {
                            "list": {"method": "GET", "paths": ["/api/network-device"]}
                        }
                    }
                }
            }
        },
        {
            "module": "policyelements",
            "service": "network-device",
            "action": "copy",
        },
        version="1.7.1",
    )

    assert "usage: netloom <module> <service> copy" in text
    assert "legacy alias" not in text


def test_render_help_for_diff_action():
    text = helpmod.render_help(
        {
            "modules": {
                "policyelements": {
                    "network-device": {
                        "actions": {
                            "list": {"method": "GET", "paths": ["/api/network-device"]}
                        }
                    }
                }
            }
        },
        {
            "module": "policyelements",
            "service": "network-device",
            "action": "diff",
        },
        version="1.7.1",
    )

    assert "usage: netloom <module> <service> diff" in text
    assert "--match-by=auto|name|id" in text
    assert "--fields=path1,path2" in text
    assert "--ignore-fields=path1,path2" in text
    assert "--show-all" in text
    assert "--max-items=N" in text
    assert "  notes:" in text
    assert (
        "broad selectors report: same, different, only_in_source, only_in_target"
        in text
    )
    assert "changed_fields uses nested dotted paths when possible" in text
    assert "ambiguous matches are reported explicitly" in text
    assert "use --show-all or --max-items=N to expand them" in text
    assert "only_in_source" in text


def test_render_help_for_get_action_is_compact():
    text = helpmod.render_help(
        {
            "modules": {
                "policyelements": {
                    "network-device": {
                        "actions": {
                            "list": {
                                "method": "GET",
                                "paths": ["/api/network-device"],
                                "params": [
                                    "sort",
                                    "offset",
                                    "limit",
                                    "calculate_count",
                                    "filter",
                                ],
                                "response_codes": ["200 OK"],
                            },
                            "get": {
                                "method": "GET",
                                "paths": [
                                    "/api/network-device/{id}",
                                    "/api/network-device/name/{name}",
                                ],
                                "response_codes": ["200 OK"],
                            },
                        }
                    }
                }
            }
        },
        {
            "module": "policyelements",
            "service": "network-device",
            "action": "get",
        },
        version="1.9.5",
    )

    assert "get (policyelements network-device):" in text
    assert (
        "usage: netloom <module> <service> get [--id=VALUE | --name=VALUE | --all] "
        "[options]" in text
    )
    assert "  selectors:" in text
    assert "    - --id=VALUE" in text
    assert "    - --name=VALUE" in text
    assert "    - --all" in text
    assert "    - --filter=JSON|FIELD:OP:VALUE" in text
    assert "  options:" in text
    assert "    - --sort=+FIELD|-FIELD" in text
    assert "    - --limit=N" in text
    assert "    - --offset=N" in text
    assert "    - --calculate-count=true|false" in text
    assert "    - --console" in text
    assert "    - --out=PATH" in text
    assert "response codes:" not in text
    assert "response content types:" not in text
    assert "list (used by `get --all`)" not in text


def test_render_help_for_get_action_with_multi_part_path_selector():
    text = helpmod.render_help(
        {
            "modules": {
                "globalserverconfiguration": {
                    "attribute-name": {
                        "actions": {
                            "list": {
                                "method": "GET",
                                "paths": ["/api/attribute"],
                                "params": [
                                    "sort",
                                    "offset",
                                    "limit",
                                    "calculate_count",
                                    "filter",
                                ],
                            },
                            "get": {
                                "method": "GET",
                                "paths": [
                                    "/api/attribute/{entity_name}/name/{name}",
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
        version="1.9.5",
    )

    assert "get (globalserverconfiguration attribute-name):" in text
    assert (
        "usage: netloom <module> <service> get "
        "[--entity-name=VALUE --name=VALUE | --all] [options]" in text
    )
    assert "  selectors:" in text
    assert "    - --entity-name=VALUE" in text
    assert "    - --name=VALUE" in text
    assert "    - --all" in text
    assert "    - --filter=JSON|FIELD:OP:VALUE" in text
    assert "  options:" in text
    assert "    - --sort=+FIELD|-FIELD" in text
    assert "    - --limit=N" in text
    assert "    - --offset=N" in text
    assert "    - --calculate-count=true|false" in text
    assert "    - --console" in text
    assert "    - --out=PATH" in text


def test_render_help_for_list_action_is_compact():
    text = helpmod.render_help(
        {
            "modules": {
                "logs": {
                    "system-event": {
                        "actions": {
                            "list": {
                                "method": "GET",
                                "paths": ["/api/system-event"],
                                "params": [
                                    "sort",
                                    "offset",
                                    "limit",
                                    "calculate_count",
                                    "filter",
                                ],
                                "response_codes": ["200 OK"],
                            }
                        }
                    }
                }
            }
        },
        {
            "module": "logs",
            "service": "system-event",
            "action": "list",
        },
        version="1.9.5",
    )

    assert "list (logs system-event):" in text
    assert "usage: netloom <module> <service> list [options]" in text
    assert "  selectors:" in text
    assert "    - --filter=JSON|FIELD:OP:VALUE" in text
    assert "  options:" in text
    assert "    - --sort=+FIELD|-FIELD" in text
    assert "    - --limit=N" in text
    assert "    - --offset=N" in text
    assert "    - --calculate-count=true|false" in text
    assert "    - --console" in text
    assert "    - --out=PATH" in text
    assert "response codes:" not in text
    assert "response content types:" not in text
    assert "alias for `get --all`" not in text


def test_render_help_for_add_action_is_compact_and_shows_required_fields():
    text = helpmod.render_help(
        {
            "modules": {
                "policyelements": {
                    "network-device": {
                        "actions": {
                            "add": {
                                "method": "POST",
                                "paths": ["/api/network-device"],
                                "body_required": ["name", "ip_address"],
                                "body_fields": [
                                    {"name": "name", "required": True},
                                    {"name": "ip_address", "required": True},
                                    {"name": "description", "required": False},
                                    {"name": "radius_secret", "required": False},
                                ],
                                "response_codes": ["201 Created"],
                            }
                        }
                    }
                }
            }
        },
        {
            "module": "policyelements",
            "service": "network-device",
            "action": "add",
        },
        version="1.9.5",
    )

    assert "add (policyelements network-device):" in text
    assert (
        "usage: netloom <module> <service> add [--file=PATH | field=value ...] "
        "[options]" in text
    )
    assert "  required fields:" in text
    assert "    - name" in text
    assert "    - ip_address" in text
    assert "  optional fields:" in text
    assert "    - description" in text
    assert "    - radius_secret" in text
    assert "  options:" in text
    assert "    - --file=PATH" in text
    assert "    - --console" in text
    assert "    - --out=PATH" in text
    assert "response codes:" not in text
    assert "body example:" not in text


def test_render_help_for_update_action_is_compact_and_shows_selectors():
    text = helpmod.render_help(
        {
            "modules": {
                "policyelements": {
                    "network-device": {
                        "actions": {
                            "update": {
                                "method": "PATCH",
                                "paths": [
                                    "/api/network-device/{id}",
                                    "/api/network-device/name/{name}",
                                ],
                                "body_fields": [
                                    {"name": "description", "required": False},
                                    {"name": "name", "required": False},
                                    {"name": "ip_address", "required": False},
                                ],
                                "response_codes": ["200 OK"],
                            }
                        }
                    }
                }
            }
        },
        {
            "module": "policyelements",
            "service": "network-device",
            "action": "update",
        },
        version="1.9.5",
    )

    assert "update (policyelements network-device):" in text
    assert (
        "usage: netloom <module> <service> update [--id=VALUE | --name=VALUE] "
        "[--file=PATH | field=value ...] [options]" in text
    )
    assert "  selectors:" in text
    assert "    - --id=VALUE" in text
    assert "    - --name=VALUE" in text
    assert "  optional fields:" in text
    assert "    - description" in text
    assert "    - name" in text
    assert "    - ip_address" in text
    assert "response codes:" not in text
    assert "body example:" not in text


def test_render_help_for_replace_action_is_compact_and_shows_required_fields():
    text = helpmod.render_help(
        {
            "modules": {
                "policyelements": {
                    "network-device": {
                        "actions": {
                            "replace": {
                                "method": "PUT",
                                "paths": [
                                    "/api/network-device/{id}",
                                    "/api/network-device/name/{name}",
                                ],
                                "body_required": ["name", "ip_address"],
                                "body_fields": [
                                    {"name": "name", "required": True},
                                    {"name": "ip_address", "required": True},
                                    {"name": "description", "required": False},
                                ],
                                "response_codes": ["200 OK"],
                            }
                        }
                    }
                }
            }
        },
        {
            "module": "policyelements",
            "service": "network-device",
            "action": "replace",
        },
        version="1.9.5",
    )

    assert "replace (policyelements network-device):" in text
    assert (
        "usage: netloom <module> <service> replace [--id=VALUE | --name=VALUE] "
        "[--file=PATH | field=value ...] [options]" in text
    )
    assert "  required fields:" in text
    assert "    - name" in text
    assert "    - ip_address" in text
    assert "  optional fields:" in text
    assert "    - description" in text
    assert "response codes:" not in text
    assert "body example:" not in text


def test_render_help_for_delete_action_is_compact_and_shows_selectors():
    text = helpmod.render_help(
        {
            "modules": {
                "policyelements": {
                    "network-device": {
                        "actions": {
                            "delete": {
                                "method": "DELETE",
                                "paths": [
                                    "/api/network-device/{id}",
                                    "/api/network-device/name/{name}",
                                ],
                                "response_codes": ["204 No Content"],
                            }
                        }
                    }
                }
            }
        },
        {
            "module": "policyelements",
            "service": "network-device",
            "action": "delete",
        },
        version="1.9.5",
    )

    assert "delete (policyelements network-device):" in text
    assert (
        "usage: netloom <module> <service> delete [--id=VALUE | --name=VALUE] "
        "[options]" in text
    )
    assert "  selectors:" in text
    assert "    - --id=VALUE" in text
    assert "    - --name=VALUE" in text
    assert "  options:" in text
    assert "    - --console" in text
    assert "    - --out=PATH" in text
    assert "response codes:" not in text
    assert "response content types:" not in text


def test_render_help_mentions_filter_paging_behavior():
    plugin = types.SimpleNamespace(
        help_context=lambda: {
            "notes": [
                "list/get --all keep paging until all matching rows are fetched.",
                "When --filter is used with list/get --all, netloom fetches every "
                "matching page, not just the first 1000 results.",
            ]
        }
    )
    text = helpmod.render_help({}, {}, version="1.6.0", plugin=plugin)

    assert "list/get --all keep paging until all matching rows are fetched" not in text
    assert "fetches every matching page, not just the first 1000 results" not in text


def test_render_help_mentions_token_and_copy_syntax():
    plugin = types.SimpleNamespace(
        help_context=lambda: {
            "common_options": [
                "--api-token=TOKEN                  Use an existing bearer token.",
                "--token-file=PATH                  Load a bearer token from a file.",
            ]
        }
    )
    text = helpmod.render_help({}, {}, version="1.7.1", plugin=plugin)

    assert "netloom <module> <service> {copy|diff} --from=SOURCE --to=TARGET" in text
    assert "netloom copy <module> <service> --from=SOURCE --to=TARGET" not in text
    assert "--api-token=TOKEN" not in text
    assert "--token-file=PATH" not in text


def test_render_help_uses_plugin_specific_examples():
    plugin = types.SimpleNamespace(
        help_context=lambda: {
            "examples": [
                "netloom load clearpass",
                "netloom identities endpoint list --limit=10",
            ],
            "notes": ["Plugin-specific note"],
        }
    )

    text = helpmod.render_help({}, {}, version="1.7.2", plugin=plugin)

    assert "netloom load clearpass" not in text
    assert "netloom identities endpoint list --limit=10" not in text
    assert "Plugin-specific note" not in text


def test_render_help_for_module_is_compact():
    text = helpmod.render_help(
        {
            "modules": {
                "policyelements": {
                    "network-device": {
                        "actions": {
                            "list": {"method": "GET", "paths": ["/api/network-device"]}
                        }
                    }
                }
            }
        },
        {"module": "policyelements"},
        version="1.9.5",
    )

    assert "Usage:" in text
    assert "netloom policyelements <service> <action> [options] [flags]" in text
    assert (
        "netloom policyelements <service> {copy|diff} --from=SOURCE --to=TARGET "
        "[options] [flags]" in text
    )
    assert "Examples:" not in text
    assert "Common options:" not in text
    assert "Common flags:" not in text


def test_render_help_for_service_is_compact():
    text = helpmod.render_help(
        {
            "modules": {
                "policyelements": {
                    "network-device": {
                        "actions": {
                            "list": {"method": "GET", "paths": ["/api/network-device"]}
                        }
                    }
                }
            }
        },
        {"module": "policyelements", "service": "network-device"},
        version="1.9.5",
    )

    assert "Usage:" in text
    assert "netloom policyelements network-device <action> [options] [flags]" in text
    assert (
        "netloom policyelements network-device {copy|diff} --from=SOURCE --to=TARGET "
        "[options] [flags]" in text
    )
    assert "Examples:" not in text
    assert "Common options:" not in text
    assert "Common flags:" not in text


def test_clearpass_help_mentions_filter_shorthand():
    plugin = types.SimpleNamespace(help_context=build_help_context)

    text = helpmod.render_help({}, {}, version="1.7.6", plugin=plugin)

    assert "--filter=JSON|FIELD:OP:VALUE" not in text
    assert "netloom identities endpoint list --filter=name:equals:TEST" not in text
    assert "Notes:" not in text
    assert "NETLOOM_CLIENT_SECRET_REF=prod/client-secret" not in text


def test_render_help_defaults_to_generic_examples_without_plugin():
    text = helpmod.render_help({}, {}, version="1.7.2")

    assert "Examples:" not in text
    assert "Common options:" not in text
    assert "Common flags:" not in text
    assert "Notes:" not in text
    assert "Usage:" in text
    assert "Available modules:" in text
    assert "No API catalog cache found." not in text


def test_render_help_includes_ascii_banner():
    text = helpmod.render_help({}, {}, version="1.6.2")

    assert "_   _      _   _" in text
    assert "netloom v1.6.2" in text
