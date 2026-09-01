from __future__ import annotations

import types
from pathlib import Path

import pytest

from netloom.core.config import AppPaths, Settings
from netloom.core.show import handle_show_command, render_running_config


def _settings(tmp_path: Path) -> Settings:
    paths = AppPaths(
        cache_dir=tmp_path / "cache",
        state_dir=tmp_path / "state",
        response_dir=tmp_path / "responses",
        app_log_dir=tmp_path / "logs",
    ).ensure()
    return Settings(
        server="clearpass.example",
        active_profile="lab",
        plugin="clearpass",
        paths=paths,
    )


def _catalog():
    return {
        "modules": {
            "policyelements": {
                "network-device": {
                    "actions": {
                        "list": {
                            "method": "GET",
                            "paths": ["/api/network-device"],
                            "params": ["limit", "offset", "sort"],
                        },
                        "get": {
                            "method": "GET",
                            "paths": ["/api/network-device/{id}"],
                            "params": ["id"],
                        },
                        "add": {
                            "method": "POST",
                            "paths": ["/api/network-device"],
                            "params": ["name", "ip_address", "radius_secret"],
                            "body_fields": [
                                {"name": "name", "required": True},
                                {"name": "ip_address", "required": False},
                                {"name": "radius_secret", "required": False},
                                {"name": "attributes", "required": False},
                            ],
                        },
                    }
                },
                "read-only": {
                    "actions": {
                        "list": {
                            "method": "GET",
                            "paths": ["/api/read-only"],
                        }
                    }
                },
            },
            "endpointvisibility": {
                "profiler-subnet-mapping-network": {
                    "actions": {
                        "get": {
                            "method": "GET",
                            "paths": [
                                "/api/profiler-subnet-mapping/{scan_type}/{network}"
                            ],
                            "params": ["scan_type", "network"],
                        },
                        "add": {
                            "method": "POST",
                            "paths": ["/api/profiler-subnet-mapping"],
                            "body_fields": [
                                {"name": "scan_type", "required": True},
                                {"name": "network", "required": True},
                            ],
                        },
                    }
                }
            },
        },
    }


class _CP:
    last_response_meta = None

    def __init__(self, catalog):
        self.catalog = catalog
        self.get_calls: list[dict] = []

    def get_action_definition(self, api_catalog, module, service, action):
        return api_catalog["modules"][module][service]["actions"][action]

    def list(self, api_catalog, token, args, *, params=None):
        assert token == "token"
        assert args["module"] == "policyelements"
        assert args["service"] == "network-device"
        assert params == {"limit": 1000, "offset": 0, "sort": None}
        return {
            "_embedded": {
                "items": [
                    {
                        "id": 7,
                        "name": "switch-a",
                        "ip_address": "192.0.2.10",
                        "radius_secret": "top-secret",
                        "attributes": {"role": "edge"},
                    }
                ]
            },
            "count": 1,
        }

    def get(self, api_catalog, token, args, *, params=None):
        assert token == "token"
        assert args["id"] == 7
        assert params == {"id": 7}
        self.get_calls.append(dict(args))
        return {
            "id": 7,
            "name": "switch-a",
            "description": "hydrated detail",
            "ip_address": "192.0.2.10",
            "radius_secret": "top-secret",
            "attributes": {"role": "edge"},
            "_links": {"self": {"href": "/api/network-device/7"}},
        }


class _SummaryCP(_CP):
    def list(self, api_catalog, token, args, *, params=None):
        del api_catalog
        assert token == "token"
        assert args["module"] == "policyelements"
        assert args["service"] == "network-device"
        assert params == {"limit": 1000, "offset": 0, "sort": None}
        return {"_embedded": {"items": [{"id": 7}]}, "count": 1}


class _FailingListCP(_CP):
    def list(self, api_catalog, token, args, *, params=None):
        del api_catalog, token, args, params
        raise RuntimeError("list failed")


class _ScopedCP(_CP):
    def list(self, api_catalog, token, args, *, params=None):
        del params
        if args["module"] == "logs":
            return {
                "_embedded": {
                    "items": [
                        {"source": "system", "description": "event"},
                    ]
                }
            }
        if (
            args["module"] == "globalserverconfiguration"
            and args["service"] == "messaging-setup"
        ):
            return {
                "_embedded": {
                    "items": [
                        {"server_name": "smtp.example", "password": "******"},
                    ]
                }
            }
        return super().list(api_catalog, token, args)


class _Log:
    def __init__(self):
        self.info_messages: list[str] = []
        self.debug_messages: list[str] = []

    def info(self, message, *args):
        self.info_messages.append(message % args if args else message)

    def debug(self, message, *args):
        self.debug_messages.append(message % args if args else message)


def _plugin(cp):
    def normalize_copy_payload(cp, api_catalog, action_args, action, item):
        del cp, api_catalog, action_args, action
        return {
            key: value
            for key, value in item.items()
            if key not in {"id", "_links"} and value not in (None, "")
        }

    return types.SimpleNamespace(
        name="clearpass",
        build_client=lambda settings, mask_secrets=True: cp,
        resolve_auth_token=lambda cp, settings: "token",
        normalize_copy_payload=normalize_copy_payload,
    )


def test_render_running_config_auto_uses_renderable_list_items(tmp_path):
    settings = _settings(tmp_path)
    catalog = _catalog()
    cp = _CP(catalog)

    text = render_running_config(
        _plugin(cp),
        cp,
        "token",
        catalog,
        settings=settings,
        catalog_view="visible",
        include={("policyelements", "network-device")},
        mask_secrets=True,
    )

    assert cp.get_calls == []
    assert "# profile: lab" in text
    assert "# hydrate: auto" in text
    assert "# policyelements network-device" in text
    assert "# source-id: 7" in text
    assert "netloom policyelements network-device add --payload-json=" in text
    assert '"id":7' not in text
    assert '"name":"switch-a"' in text
    assert '"ip_address":"192.0.2.10"' in text
    assert '"attributes":{"role":"edge"}' in text
    assert '"radius_secret":""' in text
    assert "hydrated detail" not in text
    assert "top-secret" not in text


def test_render_running_config_hydrate_always_gets_item_detail(tmp_path):
    settings = _settings(tmp_path)
    catalog = _catalog()
    cp = _CP(catalog)

    text = render_running_config(
        _plugin(cp),
        cp,
        "token",
        catalog,
        settings=settings,
        catalog_view="visible",
        include={("policyelements", "network-device")},
        mask_secrets=True,
        hydrate_mode="always",
    )

    assert cp.get_calls == [
        {
            "module": "policyelements",
            "service": "network-device",
            "action": "get",
            "id": 7,
        }
    ]
    assert "# hydrate: always" in text
    assert '"description":"hydrated detail"' in text


def test_render_running_config_auto_hydrates_unrenderable_list_item(tmp_path):
    settings = _settings(tmp_path)
    catalog = _catalog()
    cp = _SummaryCP(catalog)

    text = render_running_config(
        _plugin(cp),
        cp,
        "token",
        catalog,
        settings=settings,
        catalog_view="visible",
        include={("policyelements", "network-device")},
        mask_secrets=True,
    )

    assert cp.get_calls
    assert "# source-id: 7" in text
    assert '"name":"switch-a"' in text
    assert '"description":"hydrated detail"' in text


def test_render_running_config_hydrate_never_does_not_hydrate_unrenderable_item(
    tmp_path,
):
    settings = _settings(tmp_path)
    catalog = _catalog()
    cp = _SummaryCP(catalog)

    text = render_running_config(
        _plugin(cp),
        cp,
        "token",
        catalog,
        settings=settings,
        catalog_view="visible",
        include={("policyelements", "network-device")},
        mask_secrets=True,
        hydrate_mode="never",
    )

    assert cp.get_calls == []
    assert "# hydrate: never" in text
    assert "# skipped policyelements network-device: no renderable items" in text


def test_render_running_config_skips_parameterized_get_without_list(tmp_path):
    settings = _settings(tmp_path)
    catalog = _catalog()
    cp = _CP(catalog)

    text = render_running_config(
        _plugin(cp),
        cp,
        "token",
        catalog,
        settings=settings,
        catalog_view="visible",
        include={("endpointvisibility", "profiler-subnet-mapping-network")},
        mask_secrets=True,
    )

    assert cp.get_calls == []
    assert (
        "# skipped endpointvisibility profiler-subnet-mapping-network: "
        "get requires selectors (--scan-type=... --network=...)"
    ) in text


def test_render_running_config_writes_source_id_before_command(tmp_path):
    settings = _settings(tmp_path)
    catalog = _catalog()
    cp = _CP(catalog)

    text = render_running_config(
        _plugin(cp),
        cp,
        "token",
        catalog,
        settings=settings,
        catalog_view="visible",
        include={("policyelements", "network-device")},
        mask_secrets=True,
    )

    lines = text.splitlines()
    source_index = lines.index("# source-id: 7")
    command_index = next(
        index
        for index, line in enumerate(lines)
        if line.startswith("netloom policyelements network-device add ")
    )
    assert source_index + 1 == command_index


def test_render_running_config_excludes_non_restorable_scopes(tmp_path):
    settings = _settings(tmp_path)
    catalog = _catalog()
    catalog["modules"]["logs"] = {
        "system-event": {
            "actions": {
                "list": {"method": "GET", "paths": ["/api/system-event"]},
                "add": {
                    "method": "POST",
                    "paths": ["/api/system-event"],
                    "body_fields": [
                        {"name": "source", "required": True},
                        {"name": "description", "required": False},
                    ],
                },
            }
        }
    }
    catalog["modules"]["globalserverconfiguration"] = {
        "messaging-setup": {
            "actions": {
                "list": {"method": "GET", "paths": ["/api/messaging-setup"]},
                "add": {
                    "method": "POST",
                    "paths": ["/api/messaging-setup"],
                    "body_fields": [
                        {"name": "server_name", "required": True},
                        {"name": "password", "required": False},
                    ],
                },
            }
        }
    }
    cp = _CP(catalog)

    text = render_running_config(
        _plugin(cp),
        cp,
        "token",
        catalog,
        settings=settings,
        catalog_view="visible",
        include={
            ("logs", "system-event"),
            ("globalserverconfiguration", "messaging-setup"),
            ("policyelements", "network-device"),
        },
        mask_secrets=True,
    )

    assert "# logs system-event" not in text
    assert "netloom logs system-event" not in text
    assert "# globalserverconfiguration messaging-setup" not in text
    assert "netloom globalserverconfiguration messaging-setup" not in text
    assert "# policyelements network-device" in text


def test_render_running_config_explicit_exclude_replaces_settings(tmp_path):
    settings = _settings(tmp_path)
    catalog = _catalog()
    catalog["modules"]["logs"] = {
        "system-event": {
            "actions": {
                "list": {"method": "GET", "paths": ["/api/system-event"]},
                "add": {
                    "method": "POST",
                    "paths": ["/api/system-event"],
                    "body_fields": [
                        {"name": "source", "required": True},
                        {"name": "description", "required": False},
                    ],
                },
            }
        }
    }
    catalog["modules"]["globalserverconfiguration"] = {
        "messaging-setup": {
            "actions": {
                "list": {"method": "GET", "paths": ["/api/messaging-setup"]},
                "add": {
                    "method": "POST",
                    "paths": ["/api/messaging-setup"],
                    "body_fields": [
                        {"name": "server_name", "required": True},
                        {"name": "password", "required": False},
                    ],
                },
            }
        }
    }
    cp = _ScopedCP(catalog)

    text = render_running_config(
        _plugin(cp),
        cp,
        "token",
        catalog,
        settings=settings,
        catalog_view="visible",
        include={
            ("logs", "system-event"),
            ("globalserverconfiguration", "messaging-setup"),
        },
        exclude=set(),
        mask_secrets=True,
    )

    assert "netloom logs system-event" in text
    assert "netloom globalserverconfiguration messaging-setup" in text


def test_handle_show_command_writes_default_running_config_file(tmp_path, capsys):
    settings = _settings(tmp_path)
    catalog = _catalog()
    cp = _CP(catalog)
    plugin = _plugin(cp)

    deps = types.SimpleNamespace(
        _catalog_view_from_args=lambda args: "visible",
        _get_catalog_for_cli=lambda plugin, cp, **kwargs: catalog,
    )

    handled = handle_show_command(
        {
            "module": "show",
            "service": "running-config",
            "include": "policyelements/network-device",
        },
        plugin=plugin,
        settings=settings,
        deps=deps,
    )

    out = capsys.readouterr().out
    path = settings.paths.response_dir / "running-config.txt"
    assert handled is True
    assert path.read_text(encoding="utf-8") == out
    assert "netloom policyelements network-device add" in out


def test_handle_show_command_streams_partial_output_on_error(tmp_path, capsys):
    settings = _settings(tmp_path)
    catalog = _catalog()
    cp = _FailingListCP(catalog)
    plugin = _plugin(cp)

    deps = types.SimpleNamespace(
        _catalog_view_from_args=lambda args: "visible",
        _get_catalog_for_cli=lambda plugin, cp, **kwargs: catalog,
    )

    with pytest.raises(RuntimeError, match="list failed"):
        handle_show_command(
            {
                "module": "show",
                "service": "running-config",
                "include": "policyelements/network-device",
            },
            plugin=plugin,
            settings=settings,
            deps=deps,
        )

    out = capsys.readouterr().out
    path = settings.paths.response_dir / "running-config.txt"
    assert path.read_text(encoding="utf-8") == out
    assert "# netloom running-config" in out
    assert "# policyelements network-device" in out
    assert "# aborted: list failed" in out


def test_render_running_config_emits_progress_and_debug_messages(tmp_path):
    settings = _settings(tmp_path)
    catalog = _catalog()
    cp = _CP(catalog)
    log = _Log()

    render_running_config(
        _plugin(cp),
        cp,
        "token",
        catalog,
        settings=settings,
        catalog_view="visible",
        include={("policyelements", "network-device")},
        mask_secrets=True,
        hydrate_mode="always",
        log=log,
    )

    assert any("selected 1 services" in item for item in log.info_messages)
    assert any(
        "list policyelements network-device" in item for item in log.info_messages
    )
    assert any(
        "GET via netloom policyelements network-device get --id=7" in item
        for item in log.debug_messages
    )
