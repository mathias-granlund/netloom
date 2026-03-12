import arapy.cli.help as helpmod


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


def test_render_help_includes_server_builtin(monkeypatch):
    monkeypatch.setattr(helpmod, "list_profiles", lambda: ["dev", "prod"])
    monkeypatch.setattr(helpmod, "profiles_env_path", lambda: "/tmp/profiles.env")
    monkeypatch.setattr(
        helpmod, "credentials_env_path", lambda: "/tmp/credentials.env"
    )

    text = helpmod.render_help({}, {"module": "server"}, version="1.4.7")

    assert "arapy server use <profile>" in text
    assert "Configured profiles:" in text
    assert "  - dev" in text
    assert "  - prod" in text


def test_render_help_without_catalog_lists_builtin_modules():
    text = helpmod.render_help({}, {}, version="1.4.7")

    assert "Available modules:" in text
    assert "  - cache" in text
    assert "  - server" in text
