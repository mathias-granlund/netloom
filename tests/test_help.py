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
