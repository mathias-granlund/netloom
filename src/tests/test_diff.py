import json
import re
import types
from pathlib import Path
from uuid import uuid4

import pytest
import requests

import netloom.cli.copy as copymod
import netloom.cli.diff as diffmod
from netloom.core.config import AppPaths, Settings
from netloom.plugins.clearpass.copy_hooks import (
    normalize_diff_item as normalize_clearpass,
)


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
                "role": {
                    "actions": {
                        "list": {
                            "method": "GET",
                            "paths": ["/api/role"],
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
                            "paths": ["/api/role/{id}", "/api/role/name/{name}"],
                            "params": ["id", "name"],
                        },
                    }
                }
            }
        }
    }


def _plugin(build_client, catalog):
    def get_api_catalog(
        cp, token, settings, force_refresh=False, catalog_view="visible"
    ):
        del cp, token, settings, force_refresh, catalog_view
        return catalog

    def normalize_diff_item(module, service, item):
        del module, service
        if isinstance(item, dict):
            return {
                key: normalize_diff_item("", "", value)
                for key, value in item.items()
                if key not in {"id", "_links", "updated_at"}
            }
        if isinstance(item, list):
            return [normalize_diff_item("", "", value) for value in item]
        return item

    return types.SimpleNamespace(
        build_client=build_client,
        resolve_auth_token=lambda cp, settings: f"{settings.server}-token",
        get_api_catalog=get_api_catalog,
        normalize_diff_item=normalize_diff_item,
    )


class _CollectionCP:
    last_response_meta = None

    def __init__(self, catalog, items):
        self.catalog = catalog
        self.items = items

    def get_action_definition(self, api_catalog, module, service, action):
        return self.catalog["modules"][module][service]["actions"][action]

    def list(self, api_catalog, token, args, *, params=None):
        del api_catalog, token, params
        items = list(self.items)
        raw_filter = args.get("filter")
        if raw_filter:
            parsed = json.loads(raw_filter)
            if isinstance(parsed, dict) and isinstance(parsed.get("name"), str):
                items = [item for item in items if item.get("name") == parsed["name"]]
        return {"_embedded": {"items": items}, "count": len(items)}

    def get(self, api_catalog, token, args, *, params=None):
        del api_catalog, token, params
        if args.get("id") not in (None, ""):
            for item in self.items:
                if str(item.get("id")) == str(args["id"]):
                    return item
        if args.get("name") not in (None, ""):
            for item in self.items:
                if item.get("name") == args["name"]:
                    return item
        response = types.SimpleNamespace(status_code=404)
        raise requests.HTTPError("item not found", response=response)


def _setup_profiles(monkeypatch, tmp_path):
    monkeypatch.setattr(copymod, "list_profiles", lambda: ["lab", "prod"])
    monkeypatch.setattr(
        diffmod,
        "load_settings_for_profile",
        lambda profile: _make_settings(tmp_path, profile),
    )


def _build_client_for(source_cp, target_cp):
    def build_client(settings, *, mask_secrets=True):
        del mask_secrets
        return source_cp if settings.server == "lab" else target_cp

    return build_client


def _temp_root_dir() -> Path:
    path = Path(".tmp_diff_tests") / uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_handle_diff_command_all_is_symmetric_and_normalized(monkeypatch, capsys):
    catalog = _catalog()
    source_cp = _CollectionCP(
        catalog,
        [
            {"id": 1, "name": "alpha", "description": "same", "_links": {"self": "a"}},
            {"id": 2, "name": "beta", "description": "source-only"},
            {"id": 3, "name": "gamma", "description": "old"},
        ],
    )
    target_cp = _CollectionCP(
        catalog,
        [
            {"id": 99, "name": "alpha", "description": "same", "updated_at": "now"},
            {"id": 5, "name": "gamma", "description": "new"},
            {"id": 6, "name": "delta", "description": "target-only"},
        ],
    )

    temp_root = _temp_root_dir()
    _setup_profiles(monkeypatch, temp_root)
    settings = _make_settings(temp_root, "prod")
    report = diffmod.handle_diff_command(
        {
            "module": "policyelements",
            "service": "role",
            "action": "diff",
            "from": "lab",
            "to": "prod",
            "all": True,
        },
        settings=settings,
        plugin=_plugin(_build_client_for(source_cp, target_cp), catalog),
    )

    assert report["summary"] == {
        "compared": 2,
        "only_in_source": 1,
        "only_in_target": 1,
        "different": 1,
        "same": 1,
        "ambiguous_match": 0,
    }
    assert report["field_filters"] == {"fields": [], "ignore_fields": []}

    different = next(item for item in report["items"] if item["status"] == "different")
    assert different["label"] == "gamma"
    assert different["changed_fields"] == ["description"]
    assert different["changed_values"]["description"] == {
        "source": "old",
        "target": "new",
    }
    same = next(item for item in report["items"] if item["status"] == "same")
    assert same["label"] == "alpha"

    out = capsys.readouterr().out
    assert "Different:" in out
    assert 'description: "old" -> "new"' in out
    assert "Ambiguous matches: 0" in out

    report_path = Path(report["artifacts"]["report"])
    assert report_path.parent == settings.paths.response_dir
    assert re.fullmatch(
        r"policyelements_role_lab_to_prod_\d{8}-\d{6}-\d{6}_diff\.json",
        report_path.name,
    )
    saved = json.loads(report_path.read_text(encoding="utf-8"))
    assert saved["summary"]["different"] == 1


def test_handle_diff_command_name_is_source_scoped(monkeypatch):
    catalog = _catalog()
    source_cp = _CollectionCP(catalog, [{"id": 2, "name": "beta", "description": "x"}])
    target_cp = _CollectionCP(catalog, [{"id": 6, "name": "delta", "description": "y"}])

    temp_root = _temp_root_dir()
    _setup_profiles(monkeypatch, temp_root)
    report = diffmod.handle_diff_command(
        {
            "module": "policyelements",
            "service": "role",
            "action": "diff",
            "from": "lab",
            "to": "prod",
            "name": "beta",
        },
        settings=_make_settings(temp_root, "prod"),
        plugin=_plugin(_build_client_for(source_cp, target_cp), catalog),
    )

    assert report["summary"] == {
        "compared": 0,
        "only_in_source": 1,
        "only_in_target": 0,
        "different": 0,
        "same": 0,
        "ambiguous_match": 0,
    }
    assert report["items"][0]["status"] == "only_in_source"
    assert "no target object matched" in report["items"][0]["match_reason"]


def test_handle_diff_command_filter_is_symmetric_with_filtered_target(monkeypatch):
    catalog = _catalog()
    source_cp = _CollectionCP(
        catalog,
        [
            {"id": 1, "name": "Guest", "description": "same"},
            {"id": 2, "name": "Admin", "description": "skip"},
        ],
    )
    target_cp = _CollectionCP(
        catalog,
        [
            {"id": 9, "name": "Guest", "description": "same"},
            {"id": 8, "name": "TargetOnly", "description": "skip"},
        ],
    )

    temp_root = _temp_root_dir()
    _setup_profiles(monkeypatch, temp_root)
    report = diffmod.handle_diff_command(
        {
            "module": "policyelements",
            "service": "role",
            "action": "diff",
            "from": "lab",
            "to": "prod",
            "filter": json.dumps({"name": "Guest"}),
        },
        settings=_make_settings(temp_root, "prod"),
        plugin=_plugin(_build_client_for(source_cp, target_cp), catalog),
    )

    assert report["summary"] == {
        "compared": 1,
        "only_in_source": 0,
        "only_in_target": 0,
        "different": 0,
        "same": 1,
        "ambiguous_match": 0,
    }


def test_handle_diff_command_match_by_id_uses_id_resolution(monkeypatch):
    catalog = _catalog()
    source_cp = _CollectionCP(
        catalog, [{"id": 7, "name": "old-name", "description": "x"}]
    )
    target_cp = _CollectionCP(
        catalog, [{"id": 7, "name": "new-name", "description": "x"}]
    )

    temp_root = _temp_root_dir()
    _setup_profiles(monkeypatch, temp_root)
    report = diffmod.handle_diff_command(
        {
            "module": "policyelements",
            "service": "role",
            "action": "diff",
            "from": "lab",
            "to": "prod",
            "id": "7",
            "match_by": "id",
        },
        settings=_make_settings(temp_root, "prod"),
        plugin=_plugin(_build_client_for(source_cp, target_cp), catalog),
    )

    assert report["summary"]["different"] == 1
    assert report["items"][0]["match_by"] == "id"
    assert report["items"][0]["changed_fields"] == ["name"]


def test_handle_diff_command_reports_nested_paths_and_field_filters(
    monkeypatch, capsys
):
    catalog = _catalog()
    source_cp = _CollectionCP(
        catalog,
        [
            {
                "id": 1,
                "name": "alpha",
                "description": "same",
                "attributes": {"role": "guest", "meta": {"weight": 1}},
            }
        ],
    )
    target_cp = _CollectionCP(
        catalog,
        [
            {
                "id": 9,
                "name": "alpha",
                "description": "same",
                "attributes": {"role": "staff", "meta": {"weight": 99}},
            }
        ],
    )

    temp_root = _temp_root_dir()
    _setup_profiles(monkeypatch, temp_root)
    report = diffmod.handle_diff_command(
        {
            "module": "policyelements",
            "service": "role",
            "action": "diff",
            "from": "lab",
            "to": "prod",
            "name": "alpha",
            "fields": "attributes.role,attributes.meta.weight",
            "ignore_fields": "attributes.meta.weight",
        },
        settings=_make_settings(temp_root, "prod"),
        plugin=_plugin(_build_client_for(source_cp, target_cp), catalog),
    )

    item = report["items"][0]
    assert item["status"] == "different"
    assert item["changed_fields"] == ["attributes.role"]
    assert item["changed_values"]["attributes.role"] == {
        "source": "guest",
        "target": "staff",
    }
    assert report["field_filters"] == {
        "fields": ["attributes.role", "attributes.meta.weight"],
        "ignore_fields": ["attributes.meta.weight"],
    }

    out = capsys.readouterr().out
    assert 'attributes.role: "guest" -> "staff"' in out
    assert "attributes.meta.weight" not in out


def test_handle_diff_command_max_items_limits_console_preview(monkeypatch, capsys):
    catalog = _catalog()
    source_cp = _CollectionCP(
        catalog,
        [
            {"id": 1, "name": "alpha", "description": "old-a"},
            {"id": 2, "name": "beta", "description": "old-b"},
            {"id": 3, "name": "gamma", "description": "old-c"},
        ],
    )
    target_cp = _CollectionCP(
        catalog,
        [
            {"id": 11, "name": "alpha", "description": "new-a"},
            {"id": 12, "name": "beta", "description": "new-b"},
            {"id": 13, "name": "gamma", "description": "new-c"},
        ],
    )

    temp_root = _temp_root_dir()
    _setup_profiles(monkeypatch, temp_root)
    report = diffmod.handle_diff_command(
        {
            "module": "policyelements",
            "service": "role",
            "action": "diff",
            "from": "lab",
            "to": "prod",
            "all": True,
            "max_items": "2",
        },
        settings=_make_settings(temp_root, "prod"),
        plugin=_plugin(_build_client_for(source_cp, target_cp), catalog),
    )

    assert report["summary"]["different"] == 3

    out = capsys.readouterr().out
    assert "- alpha" in out
    assert "- beta" in out
    assert "- gamma" not in out
    assert "... 1 more changed items" in out


def test_handle_diff_command_show_all_disables_console_truncation(monkeypatch, capsys):
    catalog = _catalog()
    source_cp = _CollectionCP(
        catalog,
        [
            {
                "id": 1,
                "name": "alpha",
                "field1": "a",
                "field2": "b",
                "field3": "c",
                "field4": "d",
                "field5": "e",
                "field6": "f",
            },
            {"id": 2, "name": "beta", "description": "old-b"},
            {"id": 3, "name": "gamma", "description": "old-c"},
        ],
    )
    target_cp = _CollectionCP(
        catalog,
        [
            {
                "id": 11,
                "name": "alpha",
                "field1": "A",
                "field2": "B",
                "field3": "C",
                "field4": "D",
                "field5": "E",
                "field6": "F",
            },
            {"id": 12, "name": "beta", "description": "new-b"},
            {"id": 13, "name": "gamma", "description": "new-c"},
        ],
    )

    temp_root = _temp_root_dir()
    _setup_profiles(monkeypatch, temp_root)
    report = diffmod.handle_diff_command(
        {
            "module": "policyelements",
            "service": "role",
            "action": "diff",
            "from": "lab",
            "to": "prod",
            "all": True,
            "show_all": True,
            "max_items": "1",
        },
        settings=_make_settings(temp_root, "prod"),
        plugin=_plugin(_build_client_for(source_cp, target_cp), catalog),
    )

    assert report["summary"]["different"] == 3

    out = capsys.readouterr().out
    assert "- alpha" in out
    assert "- beta" in out
    assert "- gamma" in out
    assert 'field6: "f" -> "F"' in out
    assert "more changed items" not in out
    assert "more changed fields" not in out


def test_handle_diff_command_reports_ambiguous_target_matches(monkeypatch, capsys):
    catalog = _catalog()
    source_cp = _CollectionCP(catalog, [{"id": 1, "name": "alpha", "description": "x"}])
    target_cp = _CollectionCP(
        catalog,
        [
            {"id": 9, "name": "alpha", "description": "x"},
            {"id": 10, "name": "alpha", "description": "y"},
        ],
    )

    temp_root = _temp_root_dir()
    _setup_profiles(monkeypatch, temp_root)
    report = diffmod.handle_diff_command(
        {
            "module": "policyelements",
            "service": "role",
            "action": "diff",
            "from": "lab",
            "to": "prod",
            "name": "alpha",
        },
        settings=_make_settings(temp_root, "prod"),
        plugin=_plugin(_build_client_for(source_cp, target_cp), catalog),
    )

    assert report["summary"]["ambiguous_match"] == 1
    item = report["items"][0]
    assert item["status"] == "ambiguous_match"
    assert item["target_candidate_count"] == 2
    assert item["target_candidates"][0]["label"] == "alpha"

    out = capsys.readouterr().out
    assert "Ambiguous matches:" in out
    assert "multiple target objects matched by name" in out


def test_handle_diff_command_reports_symmetric_ambiguity(monkeypatch):
    catalog = _catalog()
    source_cp = _CollectionCP(catalog, [{"id": 1, "name": "alpha", "description": "x"}])
    target_cp = _CollectionCP(
        catalog,
        [
            {"id": 9, "name": "alpha", "description": "x"},
            {"id": 10, "name": "alpha", "description": "y"},
        ],
    )

    temp_root = _temp_root_dir()
    _setup_profiles(monkeypatch, temp_root)
    report = diffmod.handle_diff_command(
        {
            "module": "policyelements",
            "service": "role",
            "action": "diff",
            "from": "lab",
            "to": "prod",
            "all": True,
        },
        settings=_make_settings(temp_root, "prod"),
        plugin=_plugin(_build_client_for(source_cp, target_cp), catalog),
    )

    assert report["summary"] == {
        "compared": 0,
        "only_in_source": 0,
        "only_in_target": 0,
        "different": 0,
        "same": 0,
        "ambiguous_match": 1,
    }
    assert report["items"][0]["status"] == "ambiguous_match"
    assert report["items"][0]["match_reason"] == (
        "multiple target objects share name 'alpha'"
    )


def test_handle_diff_command_rejects_invalid_field_list(monkeypatch):
    temp_root = _temp_root_dir()
    _setup_profiles(monkeypatch, temp_root)
    with pytest.raises(ValueError, match="must not include empty field paths"):
        diffmod.handle_diff_command(
            {
                "module": "policyelements",
                "service": "role",
                "action": "diff",
                "from": "lab",
                "to": "prod",
                "all": True,
                "fields": "name,,description",
            },
            settings=_make_settings(temp_root, "prod"),
            plugin=types.SimpleNamespace(),
        )


def test_handle_diff_command_rejects_invalid_max_items(monkeypatch):
    temp_root = _temp_root_dir()
    _setup_profiles(monkeypatch, temp_root)
    with pytest.raises(ValueError, match="--max-items must be a positive integer"):
        diffmod.handle_diff_command(
            {
                "module": "policyelements",
                "service": "role",
                "action": "diff",
                "from": "lab",
                "to": "prod",
                "all": True,
                "max_items": "0",
            },
            settings=_make_settings(temp_root, "prod"),
            plugin=types.SimpleNamespace(),
        )


def test_clearpass_normalize_diff_item_drops_empty_and_masked_noise():
    normalized = normalize_clearpass(
        "policyelements",
        "network-device",
        {
            "id": 99,
            "name": "core-switch",
            "description": "core",
            "updated_at": "2026-03-20",
            "radius_secret": "top-secret",
            "shared_secret": "********",
            "metadata": {},
            "groups": [],
            "attributes": {"note": "keep"},
        },
    )

    assert normalized == {
        "name": "core-switch",
        "description": "core",
        "attributes": {"note": "keep"},
    }


def test_handle_diff_command_rejects_missing_selector(monkeypatch):
    temp_root = _temp_root_dir()
    _setup_profiles(monkeypatch, temp_root)
    with pytest.raises(ValueError, match="Use exactly one selector"):
        diffmod.handle_diff_command(
            {
                "module": "policyelements",
                "service": "role",
                "action": "diff",
                "from": "lab",
                "to": "prod",
            },
            settings=_make_settings(temp_root, "prod"),
            plugin=types.SimpleNamespace(),
        )
