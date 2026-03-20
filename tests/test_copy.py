import json
import re
import types
from pathlib import Path

import pytest
import requests

import netloom.cli.copy as copymod
from netloom.core.config import AppPaths, Settings


def _make_settings(tmp_path, profile: str):
    paths = AppPaths(
        cache_dir=tmp_path / profile / "cache",
        state_dir=tmp_path / profile / "state",
        response_dir=tmp_path / profile / "responses",
        app_log_dir=tmp_path / profile / "logs",
    ).ensure()
    return Settings(
        server=profile,
        https_prefix="https://",
        verify_ssl=False,
        timeout=1,
        client_id=f"{profile}-client",
        client_secret=f"{profile}-secret",
        active_profile=profile,
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
                            "params": [
                                "filter",
                                "sort",
                                "offset",
                                "limit",
                                "calculate_count",
                            ],
                        },
                        "get": {
                            "method": "GET",
                            "paths": [
                                "/api/network-device/{id}",
                                "/api/network-device/name/{name}",
                            ],
                            "params": ["id", "name"],
                        },
                        "add": {
                            "method": "POST",
                            "paths": ["/api/network-device"],
                            "params": ["name", "ip_address", "radius_secret"],
                        },
                        "update": {
                            "method": "PATCH",
                            "paths": ["/api/network-device/{id}"],
                            "params": ["id", "name", "ip_address", "radius_secret"],
                        },
                        "replace": {
                            "method": "PUT",
                            "paths": ["/api/network-device/{id}"],
                            "params": ["id", "name", "ip_address", "radius_secret"],
                        },
                    }
                }
            }
        }
    }


def _plugin(build_client, catalog, *, get_api_catalog=None):
    return types.SimpleNamespace(
        build_client=build_client,
        resolve_auth_token=lambda cp, settings: f"{settings.server}-token",
        get_api_catalog=(
            get_api_catalog
            or (lambda cp, token, settings, force_refresh=False: catalog)
        ),
        normalize_copy_payload=lambda cp, api_catalog, action_args, action, item: {
            key: value
            for key, value in item.items()
            if key != "id" and value not in (None, "")
        },
        restore_secret_fields=lambda response, payload, mask_secrets=True: {
            **response,
            **{
                key: value
                for key, value in payload.items()
                if key.endswith("_secret") and value not in (None, "")
            },
        },
        preflight_error_for_payload=lambda module, service, action, payload: (
            "network device did not include usable RADIUS, TACACS+, or SNMP credentials"
            if action == "create"
            and service == "network-device"
            and payload is not None
            and not any(
                payload.get(name)
                for name in ("radius_secret", "tacacs_secret", "snmpv2_read")
            )
            else None
        ),
    )


class _BaseCP:
    last_response_meta = None

    def __init__(self, catalog):
        self.catalog = catalog

    def get_action_definition(self, api_catalog, module, service, action):
        return self.catalog["modules"][module][service]["actions"][action]

    def resolve_action(self, api_catalog, module, service, action, args):
        action_def = self.get_action_definition(api_catalog, module, service, action)
        paths = action_def["paths"]
        if action in {"update", "replace"}:
            return action_def, paths[0].replace("{id}", str(args["id"])), ["id"]
        if action == "get" and args.get("name"):
            return action_def, paths[1].replace("{name}", str(args["name"])), ["name"]
        if action == "get" and args.get("id"):
            return action_def, paths[0].replace("{id}", str(args["id"])), ["id"]
        return action_def, paths[0], []


class _SourceCP(_BaseCP):
    def __init__(self, catalog, items):
        super().__init__(catalog)
        self.items = items

    def list(self, api_catalog, token, args, *, params=None):
        return {"_embedded": {"items": self.items}}

    def get(self, api_catalog, token, args, *, params=None):
        if args.get("name"):
            for item in self.items:
                if item.get("name") == args["name"]:
                    return item
        if args.get("id"):
            for item in self.items:
                if item.get("id") == args["id"]:
                    return item
        err = requests.HTTPError("not found")
        err.response = type("Resp", (), {"status_code": 404})()
        raise err


class _TargetCP(_BaseCP):
    def __init__(self, catalog, matches=None):
        super().__init__(catalog)
        self.matches = matches or {}
        self.add_calls = []
        self.update_calls = []
        self.replace_calls = []

    def list(self, api_catalog, token, args, *, params=None):
        if args.get("filter"):
            return {"_embedded": {"items": list(self.matches.values())[:1]}}
        return {"_embedded": {"items": list(self.matches.values())}}

    def get(self, api_catalog, token, args, *, params=None):
        if args.get("name") and args["name"] in self.matches:
            return self.matches[args["name"]]
        if args.get("id"):
            for item in self.matches.values():
                if item.get("id") == args["id"]:
                    return item
        err = requests.HTTPError("not found")
        err.response = type("Resp", (), {"status_code": 404})()
        raise err

    def add(self, api_catalog, token, args, payload):
        self.add_calls.append({"args": args, "payload": payload})
        return {"id": 3001, **payload}

    def update(self, api_catalog, token, args, payload):
        self.update_calls.append({"args": args, "payload": payload})
        return {"id": args["id"], "name": payload["name"], "radius_secret": ""}

    def replace(self, api_catalog, token, args, payload):
        self.replace_calls.append({"args": args, "payload": payload})
        return {"id": args["id"], **payload}


class _PagedSourceCP(_SourceCP):
    def __init__(self, catalog, items):
        super().__init__(catalog, items)
        self.list_calls = []

    def list(self, api_catalog, token, args, *, params=None):
        self.list_calls.append(dict(params or {}))
        offset = int((params or {}).get("offset", 0))
        limit = int((params or {}).get("limit", 25))
        items = self.items[offset : offset + limit]
        response = {"_embedded": {"items": items}}
        if offset == 0:
            response["count"] = len(self.items)
        return response


def test_handle_copy_command_dry_run_create(monkeypatch, tmp_path, capsys):
    catalog = _catalog()
    source_cp = _SourceCP(
        catalog,
        [
            {
                "id": 1,
                "name": "switch-a",
                "ip_address": "10.0.0.1",
                "radius_secret": "abc123",
            }
        ],
    )
    target_cp = _TargetCP(catalog, {})

    monkeypatch.setattr(copymod, "list_profiles", lambda: ["dev", "prod"])
    monkeypatch.setattr(
        copymod,
        "load_settings_for_profile",
        lambda profile: _make_settings(tmp_path, profile),
    )

    def build_client(settings, *, mask_secrets=True):
        return source_cp if settings.server == "dev" else target_cp

    report = copymod.handle_copy_command(
        {
            "module": "copy",
            "copy_module": "policyelements",
            "copy_service": "network-device",
            "from": "dev",
            "to": "prod",
            "all": True,
            "dry_run": True,
        },
        settings=_make_settings(tmp_path, "prod"),
        plugin=_plugin(build_client, catalog),
    )

    out = capsys.readouterr().out
    assert "Dry run" in out
    assert report["summary"]["created"] == 1
    assert report["items"][0]["action"] == "create"
    assert report["items"][0]["status"] == "planned"


def test_handle_copy_command_fetches_all_source_pages(monkeypatch, tmp_path):
    import netloom.core.pagination as pagination

    monkeypatch.setattr(pagination, "DEFAULT_PAGE_SIZE", 2)
    catalog = _catalog()
    source_cp = _PagedSourceCP(
        catalog,
        [
            {
                "id": 1,
                "name": "switch-a",
                "ip_address": "10.0.0.1",
                "radius_secret": "one",
            },
            {
                "id": 2,
                "name": "switch-b",
                "ip_address": "10.0.0.2",
                "radius_secret": "two",
            },
            {
                "id": 3,
                "name": "switch-c",
                "ip_address": "10.0.0.3",
                "radius_secret": "three",
            },
        ],
    )
    target_cp = _TargetCP(catalog, {})

    monkeypatch.setattr(copymod, "list_profiles", lambda: ["dev", "prod"])
    monkeypatch.setattr(
        copymod,
        "load_settings_for_profile",
        lambda profile: _make_settings(tmp_path, profile),
    )

    def build_client(settings, *, mask_secrets=True):
        return source_cp if settings.server == "dev" else target_cp

    report = copymod.handle_copy_command(
        {
            "module": "copy",
            "copy_module": "policyelements",
            "copy_service": "network-device",
            "from": "dev",
            "to": "prod",
            "all": True,
            "dry_run": True,
        },
        settings=_make_settings(tmp_path, "prod"),
        plugin=_plugin(build_client, catalog),
    )

    assert report["summary"]["selected"] == 3
    assert report["summary"]["created"] == 3
    assert source_cp.list_calls == [
        {"limit": 2, "offset": 0, "sort": None},
        {"limit": 2, "offset": 2, "sort": None},
    ]


def test_handle_copy_command_honors_explicit_limit(monkeypatch, tmp_path):
    catalog = _catalog()
    source_cp = _PagedSourceCP(
        catalog,
        [
            {
                "id": 1,
                "name": "switch-a",
                "ip_address": "10.0.0.1",
                "radius_secret": "one",
            },
            {
                "id": 2,
                "name": "switch-b",
                "ip_address": "10.0.0.2",
                "radius_secret": "two",
            },
        ],
    )
    target_cp = _TargetCP(catalog, {})

    monkeypatch.setattr(copymod, "list_profiles", lambda: ["dev", "prod"])
    monkeypatch.setattr(
        copymod,
        "load_settings_for_profile",
        lambda profile: _make_settings(tmp_path, profile),
    )

    def build_client(settings, *, mask_secrets=True):
        return source_cp if settings.server == "dev" else target_cp

    report = copymod.handle_copy_command(
        {
            "module": "copy",
            "copy_module": "policyelements",
            "copy_service": "network-device",
            "from": "dev",
            "to": "prod",
            "all": True,
            "limit": "1",
            "dry_run": True,
        },
        settings=_make_settings(tmp_path, "prod"),
        plugin=_plugin(build_client, catalog),
    )

    assert report["summary"]["selected"] == 1
    assert report["summary"]["created"] == 1
    assert source_cp.list_calls == [{"limit": 1, "offset": 0, "sort": None}]


def test_handle_copy_command_updates_existing_match_and_restores_secret(
    monkeypatch, tmp_path
):
    catalog = _catalog()
    source_cp = _SourceCP(
        catalog,
        [
            {
                "id": 1,
                "name": "switch-a",
                "ip_address": "10.0.0.1",
                "radius_secret": "abc123",
            }
        ],
    )
    target_cp = _TargetCP(catalog, {"switch-a": {"id": 42, "name": "switch-a"}})

    monkeypatch.setattr(copymod, "list_profiles", lambda: ["dev", "prod"])
    monkeypatch.setattr(
        copymod,
        "load_settings_for_profile",
        lambda profile: _make_settings(tmp_path, profile),
    )

    def build_client(settings, *, mask_secrets=True):
        return source_cp if settings.server == "dev" else target_cp

    report = copymod.handle_copy_command(
        {
            "module": "copy",
            "copy_module": "policyelements",
            "copy_service": "network-device",
            "from": "dev",
            "to": "prod",
            "all": True,
            "on_conflict": "update",
            "decrypt": True,
        },
        settings=_make_settings(tmp_path, "prod"),
        plugin=_plugin(build_client, catalog),
    )

    assert target_cp.update_calls
    assert target_cp.update_calls[0]["args"]["id"] == 42
    assert target_cp.update_calls[0]["payload"] == {
        "name": "switch-a",
        "ip_address": "10.0.0.1",
        "radius_secret": "abc123",
    }
    assert report["summary"]["updated"] == 1
    assert report["items"][0]["response"]["radius_secret"] == "abc123"


def test_handle_copy_command_uses_cached_catalog_by_default(monkeypatch, tmp_path):
    catalog = _catalog()
    source_cp = _SourceCP(
        catalog,
        [{"id": 1, "name": "switch-a", "ip_address": "10.0.0.1"}],
    )
    target_cp = _TargetCP(catalog, {})
    catalog_calls = []

    monkeypatch.setattr(copymod, "list_profiles", lambda: ["dev", "prod"])
    monkeypatch.setattr(
        copymod,
        "load_settings_for_profile",
        lambda profile: _make_settings(tmp_path, profile),
    )

    def build_client(settings, *, mask_secrets=True):
        return source_cp if settings.server == "dev" else target_cp

    def get_api_catalog(cp, token, settings, force_refresh=False):
        catalog_calls.append(
            {
                "server": settings.server,
                "token": token,
                "force_refresh": force_refresh,
            }
        )
        return catalog

    copymod.handle_copy_command(
        {
            "module": "copy",
            "copy_module": "policyelements",
            "copy_service": "network-device",
            "from": "dev",
            "to": "prod",
            "all": True,
            "dry_run": True,
        },
        settings=_make_settings(tmp_path, "prod"),
        plugin=_plugin(build_client, catalog, get_api_catalog=get_api_catalog),
    )

    assert len(catalog_calls) == 2
    assert catalog_calls[0]["server"] == "dev"
    assert catalog_calls[1]["server"] == "prod"
    assert catalog_calls[0]["force_refresh"] is False
    assert catalog_calls[1]["force_refresh"] is False


def test_handle_copy_command_omits_blank_secrets_on_update(monkeypatch, tmp_path):
    catalog = _catalog()
    source_cp = _SourceCP(
        catalog,
        [
            {
                "id": 1,
                "name": "switch-a",
                "ip_address": "10.0.0.1",
                "radius_secret": "",
                "tacacs_secret": "",
            }
        ],
    )
    target_cp = _TargetCP(catalog, {"switch-a": {"id": 42, "name": "switch-a"}})

    monkeypatch.setattr(copymod, "list_profiles", lambda: ["dev", "prod"])
    monkeypatch.setattr(
        copymod,
        "load_settings_for_profile",
        lambda profile: _make_settings(tmp_path, profile),
    )

    def build_client(settings, *, mask_secrets=True):
        return source_cp if settings.server == "dev" else target_cp

    report = copymod.handle_copy_command(
        {
            "module": "copy",
            "copy_module": "policyelements",
            "copy_service": "network-device",
            "from": "dev",
            "to": "prod",
            "all": True,
            "on_conflict": "update",
        },
        settings=_make_settings(tmp_path, "prod"),
        plugin=_plugin(build_client, catalog),
    )

    assert report["summary"]["updated"] == 1
    assert target_cp.update_calls[0]["payload"] == {
        "name": "switch-a",
        "ip_address": "10.0.0.1",
    }


def test_handle_copy_command_fails_early_for_network_device_create_without_credentials(
    monkeypatch, tmp_path, capsys
):
    catalog = _catalog()
    source_cp = _SourceCP(
        catalog,
        [
            {
                "id": 1,
                "name": "switch-a",
                "ip_address": "10.0.0.1",
                "radius_secret": "",
                "tacacs_secret": "",
            }
        ],
    )
    target_cp = _TargetCP(catalog, {})

    monkeypatch.setattr(copymod, "list_profiles", lambda: ["dev", "prod"])
    monkeypatch.setattr(
        copymod,
        "load_settings_for_profile",
        lambda profile: _make_settings(tmp_path, profile),
    )

    def build_client(settings, *, mask_secrets=True):
        return source_cp if settings.server == "dev" else target_cp

    report = copymod.handle_copy_command(
        {
            "module": "copy",
            "copy_module": "policyelements",
            "copy_service": "network-device",
            "from": "dev",
            "to": "prod",
            "all": True,
            "dry_run": True,
        },
        settings=_make_settings(tmp_path, "prod"),
        plugin=_plugin(build_client, catalog),
    )

    out = capsys.readouterr().out
    assert report["summary"]["created"] == 0
    assert report["summary"]["failed"] == 1
    assert report["items"][0]["status"] == "failed"
    assert (
        "did not include usable RADIUS, TACACS+, or SNMP credentials"
        in report["items"][0]["reason"]
    )
    assert "Failure reasons:" in out
    assert "did not include usable RADIUS, TACACS+, or SNMP credentials" in out
    assert not target_cp.add_calls


def test_handle_copy_command_console_masks_secrets_by_default(
    monkeypatch, tmp_path, capsys
):
    catalog = _catalog()
    source_cp = _SourceCP(
        catalog,
        [
            {
                "id": 1,
                "name": "switch-a",
                "ip_address": "10.0.0.1",
                "radius_secret": "abc123",
            }
        ],
    )
    target_cp = _TargetCP(catalog, {})

    monkeypatch.setattr(copymod, "list_profiles", lambda: ["dev", "prod"])
    monkeypatch.setattr(
        copymod,
        "load_settings_for_profile",
        lambda profile: _make_settings(tmp_path, profile),
    )

    def build_client(settings, *, mask_secrets=True):
        return source_cp if settings.server == "dev" else target_cp

    copymod.handle_copy_command(
        {
            "module": "copy",
            "copy_module": "policyelements",
            "copy_service": "network-device",
            "from": "dev",
            "to": "prod",
            "all": True,
            "dry_run": True,
            "console": True,
        },
        settings=_make_settings(tmp_path, "prod"),
        plugin=_plugin(build_client, catalog),
    )

    out = capsys.readouterr().out
    assert "abc123" not in out
    assert '"radius_secret": ""' in out


def test_handle_copy_command_saves_default_artifacts_to_response_dir(
    monkeypatch, tmp_path
):
    catalog = _catalog()
    source_cp = _SourceCP(
        catalog,
        [
            {
                "id": 1,
                "name": "switch-a",
                "ip_address": "10.0.0.1",
                "radius_secret": "abc123",
            }
        ],
    )
    target_cp = _TargetCP(catalog, {})

    monkeypatch.setattr(copymod, "list_profiles", lambda: ["dev", "prod"])
    monkeypatch.setattr(
        copymod,
        "load_settings_for_profile",
        lambda profile: _make_settings(tmp_path, profile),
    )

    def build_client(settings, *, mask_secrets=True):
        return source_cp if settings.server == "dev" else target_cp

    settings = _make_settings(tmp_path, "prod")
    report = copymod.handle_copy_command(
        {
            "module": "copy",
            "copy_module": "policyelements",
            "copy_service": "network-device",
            "from": "dev",
            "to": "prod",
            "all": True,
            "dry_run": True,
        },
        settings=settings,
        plugin=_plugin(build_client, catalog),
    )

    base_dir = settings.paths.response_dir
    source_path = Path(report["artifacts"]["source"])
    payload_path = Path(report["artifacts"]["payload"])
    plan_path = Path(report["artifacts"]["plan"])

    assert source_path.parent == base_dir
    assert payload_path.parent == base_dir
    assert plan_path.parent == base_dir
    assert re.fullmatch(
        r"policyelements_network_device_dev_to_prod_\d{8}-\d{6}-\d{6}_source\.json",
        source_path.name,
    )
    assert re.fullmatch(
        r"policyelements_network_device_dev_to_prod_\d{8}-\d{6}-\d{6}_payload\.json",
        payload_path.name,
    )
    assert re.fullmatch(
        r"policyelements_network_device_dev_to_prod_\d{8}-\d{6}-\d{6}_plan\.json",
        plan_path.name,
    )
    assert json.loads(source_path.read_text(encoding="utf-8"))[0]["name"] == "switch-a"
    assert json.loads(payload_path.read_text(encoding="utf-8"))[0]["name"] == "switch-a"
    assert json.loads(plan_path.read_text(encoding="utf-8"))[0]["action"] == "create"


def test_handle_copy_command_honors_explicit_artifact_paths(monkeypatch, tmp_path):
    catalog = _catalog()
    source_cp = _SourceCP(
        catalog,
        [
            {
                "id": 1,
                "name": "switch-a",
                "ip_address": "10.0.0.1",
                "radius_secret": "abc123",
            }
        ],
    )
    target_cp = _TargetCP(catalog, {})

    monkeypatch.setattr(copymod, "list_profiles", lambda: ["dev", "prod"])
    monkeypatch.setattr(
        copymod,
        "load_settings_for_profile",
        lambda profile: _make_settings(tmp_path, profile),
    )

    def build_client(settings, *, mask_secrets=True):
        return source_cp if settings.server == "dev" else target_cp

    custom_dir = tmp_path / "artifacts"
    source_path = custom_dir / "source.json"
    payload_path = custom_dir / "payload.json"
    plan_path = custom_dir / "plan.json"

    report = copymod.handle_copy_command(
        {
            "module": "copy",
            "copy_module": "policyelements",
            "copy_service": "network-device",
            "from": "dev",
            "to": "prod",
            "all": True,
            "dry_run": True,
            "save_source": str(source_path),
            "save_payload": str(payload_path),
            "save_plan": str(plan_path),
        },
        settings=_make_settings(tmp_path, "prod"),
        plugin=_plugin(build_client, catalog),
    )

    assert report["artifacts"]["source"] == str(source_path)
    assert report["artifacts"]["payload"] == str(payload_path)
    assert report["artifacts"]["plan"] == str(plan_path)
    assert source_path.exists()
    assert payload_path.exists()
    assert plan_path.exists()


def test_handle_copy_command_rejects_missing_selector(monkeypatch, tmp_path):
    monkeypatch.setattr(copymod, "list_profiles", lambda: ["dev", "prod"])
    monkeypatch.setattr(
        copymod,
        "load_settings_for_profile",
        lambda profile: _make_settings(tmp_path, profile),
    )

    with pytest.raises(ValueError, match="Use exactly one selector"):
        copymod.handle_copy_command(
            {
                "module": "copy",
                "copy_module": "policyelements",
                "copy_service": "network-device",
                "from": "dev",
                "to": "prod",
            },
            settings=_make_settings(tmp_path, "prod"),
            plugin=_plugin(lambda settings, mask_secrets=True: None, _catalog()),
        )
