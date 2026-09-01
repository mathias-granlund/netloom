import re

import pytest
from requests import HTTPError

from netloom.plugins.clearpass.catalog import load_cached_catalog


def _iter_list_endpoints(catalog: dict):
    modules = catalog.get("modules") or {}
    for module, services in modules.items():
        if not isinstance(services, dict):
            continue
        for service, entry in services.items():
            if not isinstance(entry, dict):
                continue
            actions = entry.get("actions") or {}
            list_action = actions.get("list")
            if not isinstance(list_action, dict):
                continue
            for path in list_action.get("paths") or []:
                if isinstance(path, str) and "{" not in path:
                    yield module, service, path, list_action


@pytest.fixture(scope="session")
def catalog():
    cat = load_cached_catalog()
    if not cat:
        pytest.skip("No api_endpoints_cache.json found. Run: netloom cache update")
    return cat


def _compile_denylist(pytestconfig):
    pats = list(pytestconfig.getoption("--netloom-deny-regex") or [])
    pats += [
        r"/activate-(online|offline)$",
        r"/export$",
        r"/reject$",
        r"/user-id$",
        r"/page-name$",
        r"/host-address$",
        r"/server-name$",
        r"/mac-address$",
        r"/username$",
        r"/global-settings$",
        r"/settings$",
        r"/login-audit$",
        r"/system-event$",
        r"/server-cert$",
        r"/time-range$",
        r"/ip-range$",
        r"/mac$",
        r"/ip$",
        r"^/api/oauth$",
        r"^/api/session-action$",
        r"^/api/device-profiler/device-fingerprint$",
        r"^/api/server/(access-control|service|snmp)$",
    ]
    return [re.compile(p) for p in pats]


def _is_denied(route: str, deny):
    return any(rx.search(route) for rx in deny)


def test_list_endpoints_smoke(
    clearpass_client, token, api_catalog, catalog, pytestconfig
):
    deny = _compile_denylist(pytestconfig)
    max_n = int(pytestconfig.getoption("--netloom-max-endpoints"))

    endpoints = []
    for module, service, route, action_def in _iter_list_endpoints(catalog):
        if _is_denied(route, deny):
            continue
        endpoints.append((module, service, route, action_def))

    endpoints.sort(key=lambda x: (x[0], x[1], x[2]))
    if max_n and len(endpoints) > max_n:
        endpoints = endpoints[:max_n]

    failures = []
    by_status = {}

    for module, service, route, action_def in endpoints:
        params = {}
        allowed = set(action_def.get("params") or [])
        if "offset" in allowed:
            params["offset"] = 0
        if "limit" in allowed:
            params["limit"] = 1

        args = {"module": module, "service": service, "action": "list"}
        try:
            clearpass_client.list(api_catalog, token, args, params=params or None)
        except HTTPError as e:
            code = getattr(e.response, "status_code", None)
            by_status[code] = by_status.get(code, 0) + 1
            failures.append((f"{module}:{service}", route, f"{code} {e}"))
        except Exception as e:
            by_status["other"] = by_status.get("other", 0) + 1
            failures.append((f"{module}:{service}", route, str(e)))

    if failures:
        status_summary = ", ".join(
            f"{k}:{v}" for k, v in sorted(by_status.items(), key=lambda kv: str(kv[0]))
        )
        msg = "\n".join(f"- {k} ({route}): {err}" for k, route, err in failures[:50])
        pytest.fail(
            f"{len(failures)} list endpoints failed "
            f"(status summary: {status_summary}). "
            f"First failures:\n{msg}"
        )
