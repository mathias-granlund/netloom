from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

from netloom.core.config import AppPaths, Settings
from netloom.plugins.clearpass import catalog


@contextmanager
def _workspace_root():
    root = Path(".tmp_clearpass_catalog_tests") / uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    try:
        yield root
    finally:
        rmtree(root, ignore_errors=True)


class _FakeResponse:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self) -> None:
        return None


class _FakeSession:
    def __init__(self):
        self.responses = {
            "/api-docs": ('{"apis":[{"path":"/api-docs/Identities-v1"}]}'),
            "/api/apigility/documentation/Identities-v1": (
                '{"apis":[{"path":"/endpoint/swagger"}]}'
            ),
            "/api/apigility/documentation/Identities-v1/endpoint/swagger": (
                '{"resourcePath":"/api/endpoint","apis":[{"path":"/api/endpoint",'
                '"operations":[{"method":"GET","parameters":[{"paramType":"query",'
                '"name":"limit"}]}]}]}'
            ),
        }

    def get(self, url, headers=None, verify=None, timeout=None):
        path = url.split(".example", 1)[1]
        return _FakeResponse(self.responses[path])


class _FakeClient:
    https_prefix = "https://"
    server = "clearpass.example"
    verify_ssl = True
    timeout = 30

    def __init__(self):
        self.session = _FakeSession()

    def request(self, endpoints, method, resource, token=None):
        return {"privileges": []}


def test_get_api_catalog_emits_cache_update_timing_buckets():
    with _workspace_root() as root:
        settings = Settings(
            plugin="clearpass",
            paths=AppPaths(
                cache_dir=root / "cache",
                state_dir=root / "state",
                response_dir=root / "responses",
                app_log_dir=root / "logs",
            ).ensure(),
        )
        records: list[tuple[str, float]] = []
        progress_events: list[tuple[str, dict[str, object]]] = []

        result = catalog.get_api_catalog(
            _FakeClient(),
            token="token",
            force_refresh=True,
            settings=settings,
            timing_sink=lambda name, duration: records.append((name, duration)),
            progress_sink=lambda event, **data: progress_events.append((event, data)),
        )

        assert "identities" in result["modules"]
        names = [name for name, _duration in records]
        progress_names = [name for name, _data in progress_events]
        assert "fetch_api_docs" in names
        assert "fetch_effective_privileges" in names
        assert "fetch_module_listings" in names
        assert "fetch_subdocuments" in names
        assert "build_catalog" in names
        assert "write_full_cache" in names
        assert "write_fast_index" in names
        assert "fetch_api_docs" in progress_names
        assert "fetch_effective_privileges" in progress_names
        assert "module_listing" in progress_names
        assert "subdocuments_start" in progress_names
        assert "subdocument" in progress_names
        assert "build_catalog" in progress_names
        assert "write_full_cache" in progress_names
        assert "write_fast_index" in progress_names
        assert (settings.paths.cache_dir / "api_endpoints_cache.json").is_file()
        assert (settings.paths.cache_dir / "api_endpoints_index.json").is_file()
