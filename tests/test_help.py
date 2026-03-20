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


def test_render_help_without_catalog_lists_builtin_modules():
    text = helpmod.render_help({}, {}, version="1.4.7")

    assert "Available modules:" in text
    assert "  - cache" in text
    assert "  - copy" in text
    assert "  - server" in text


def test_render_help_includes_copy_builtin():
    text = helpmod.render_help({}, {"module": "copy"}, version="1.6.0")

    assert "Built-in module: copy" in text
    assert "--from=SOURCE_PROFILE" in text
    assert "--on-conflict=fail|skip|update|replace" in text
    assert "copied across all matching paged results" in text
    assert "NETLOOM_OUT_DIR/<generated>_source.json" in text


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
    assert "legacy alias: netloom copy <module> <service>" in text


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
    assert "  notes:" in text
    assert (
        "broad selectors report: same, different, only_in_source, only_in_target"
        in text
    )
    assert "changed_fields uses nested dotted paths when possible" in text
    assert "ambiguous matches are reported explicitly" in text
    assert "only_in_source" in text


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

    assert "list/get --all keep paging until all matching rows are fetched" in text
    assert "fetches every matching page, not just the first 1000 results" in text


def test_render_help_mentions_catalog_view_option():
    text = helpmod.render_help({}, {}, version="1.8.2")

    assert "Catalog options:" in text
    assert "--catalog-view=visible|full" in text


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

    assert "netloom <module> <service> copy --from=SOURCE --to=TARGET" in text
    assert "netloom copy <module> <service> --from=SOURCE --to=TARGET" in text
    assert "--api-token=TOKEN" in text
    assert "--token-file=PATH" in text


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

    assert "netloom load clearpass" in text
    assert "netloom identities endpoint list --limit=10" in text
    assert "Plugin-specific note" in text


def test_clearpass_help_mentions_filter_shorthand():
    plugin = types.SimpleNamespace(help_context=build_help_context)

    text = helpmod.render_help({}, {}, version="1.7.6", plugin=plugin)

    assert "--filter=JSON|FIELD:OP:VALUE" in text
    assert "--filter=key:equals:value" in text


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
