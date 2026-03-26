import json
from contextlib import contextmanager
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

from netloom.core.cache import (
    load_cached_interactive_catalog,
    project_catalog_view,
    supports_interactive_catalog,
)
from netloom.core.config import AppPaths, Settings


@contextmanager
def _workspace_root():
    root = Path(".tmp_cache_tests") / uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    try:
        yield root
    finally:
        rmtree(root, ignore_errors=True)


def _settings(root: Path) -> Settings:
    return Settings(
        plugin="clearpass",
        paths=AppPaths(
            cache_dir=root / "cache",
            state_dir=root / "state",
            response_dir=root / "responses",
            app_log_dir=root / "logs",
        ).ensure(),
    )


def test_project_catalog_view_can_switch_to_full_modules():
    catalog = {
        "version": 5,
        "modules": {
            "identities": {
                "endpoint": {"actions": {"list": {"method": "GET"}}},
            }
        },
        "full_modules": {
            "identities": {
                "endpoint": {"actions": {"list": {"method": "GET"}}},
                "guest": {"actions": {"list": {"method": "GET"}}},
            }
        },
    }

    projected = project_catalog_view(catalog, catalog_view="full")

    assert projected["catalog_view"] == "full"
    assert "endpoint" in projected["modules"]["identities"]
    assert "guest" in projected["modules"]["identities"]


def test_load_cached_interactive_catalog_reads_index_first():
    with _workspace_root() as root:
        settings = _settings(root)
        (settings.paths.cache_dir / "api_endpoints_index.json").write_text(
            json.dumps(
                {
                    "version": 5,
                    "index_version": 1,
                    "modules": {
                        "identities": {
                            "endpoint": {"actions": {"list": {"method": "GET"}}}
                        }
                    },
                    "full_modules": {
                        "identities": {
                            "endpoint": {"actions": {"list": {"method": "GET"}}},
                            "guest": {"actions": {"list": {"method": "GET"}}},
                        }
                    },
                }
            ),
            encoding="utf-8",
        )

        visible = load_cached_interactive_catalog(
            "clearpass",
            settings=settings,
            prefer_index=True,
        )
        full = load_cached_interactive_catalog(
            "clearpass",
            settings=settings,
            catalog_view="full",
            prefer_index=True,
        )

    assert "endpoint" in visible["modules"]["identities"]
    assert "guest" not in visible["modules"]["identities"]
    assert "guest" in full["modules"]["identities"]


def test_load_cached_interactive_catalog_falls_back_to_full_cache():
    with _workspace_root() as root:
        settings = _settings(root)
        (settings.paths.cache_dir / "api_endpoints_cache.json").write_text(
            json.dumps(
                {
                    "version": 5,
                    "modules": {
                        "identities": {
                            "endpoint": {"actions": {"list": {"method": "GET"}}}
                        }
                    },
                    "full_modules": {
                        "identities": {
                            "endpoint": {"actions": {"list": {"method": "GET"}}},
                            "guest": {"actions": {"list": {"method": "GET"}}},
                        }
                    },
                }
            ),
            encoding="utf-8",
        )

        full = load_cached_interactive_catalog(
            "clearpass",
            settings=settings,
            catalog_view="full",
            prefer_index=True,
        )

    assert "guest" in full["modules"]["identities"]
    assert full["catalog_view"] == "full"


def test_load_cached_interactive_catalog_rejects_invalid_index():
    with _workspace_root() as root:
        settings = _settings(root)
        (settings.paths.cache_dir / "api_endpoints_index.json").write_text(
            json.dumps(
                {
                    "version": 5,
                    "index_version": 999,
                    "modules": {"identities": {}},
                }
            ),
            encoding="utf-8",
        )

        assert (
            load_cached_interactive_catalog(
                "clearpass",
                settings=settings,
                prefer_index=True,
            )
            is None
        )


def test_load_cached_interactive_catalog_returns_none_for_unknown_plugin():
    with _workspace_root() as root:
        settings = _settings(root)

        assert supports_interactive_catalog("clearpass") is True
        assert supports_interactive_catalog("unknown") is False
        assert (
            load_cached_interactive_catalog(
                "unknown",
                settings=settings,
                prefer_index=True,
            )
            is None
        )
