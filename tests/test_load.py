import netloom.cli.load as loadmod


def test_handle_load_list_marks_config_only_plugin(monkeypatch, capsys):
    monkeypatch.setattr(loadmod, "list_plugins", lambda: ["arubacentral", "clearpass"])
    monkeypatch.setattr(
        loadmod,
        "has_runtime_plugin",
        lambda name: name == "clearpass",
    )

    handled = loadmod.handle_load_command({"module": "load", "service": "list"})

    assert handled is True
    out = capsys.readouterr().out
    assert "- clearpass" in out
    assert "- arubacentral (config only)" in out


def test_handle_load_rejects_config_only_plugin(monkeypatch, capsys):
    monkeypatch.setattr(loadmod, "list_plugins", lambda: ["arubacentral", "clearpass"])
    monkeypatch.setattr(loadmod, "has_runtime_plugin", lambda name: False)

    handled = loadmod.handle_load_command(
        {"module": "load", "service": "arubacentral"}
    )

    assert handled is True
    out = capsys.readouterr().out
    assert "has configuration files but no runtime implementation is installed" in out


def test_handle_load_can_clear_active_plugin(monkeypatch, capsys):
    calls = {}
    monkeypatch.setattr(
        loadmod,
        "set_active_plugin",
        lambda value: calls.update({"value": value}),
    )

    handled = loadmod.handle_load_command({"module": "load", "service": "none"})

    assert handled is True
    assert calls["value"] is None
    assert "Active plugin cleared." in capsys.readouterr().out
