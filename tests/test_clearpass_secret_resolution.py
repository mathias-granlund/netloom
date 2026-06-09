from __future__ import annotations

import netloom.plugins.clearpass.copy_hooks as hooks
from netloom.core.config import Settings


def test_prepare_write_payload_resolves_network_device_secrets(monkeypatch):
    monkeypatch.setattr(
        hooks,
        "resolve_network_device_secret_values",
        lambda **kwargs: {
            "radius_secret": "radius-from-delinea",
            "tacacs_secret": "tacacs-from-delinea",
        },
    )

    payload = hooks.prepare_write_payload(
        None,
        {},
        {"module": "policyelements", "service": "network-device", "action": "add"},
        "add",
        {
            "name": "switch-a",
            "radius_secret": "",
            "tacacs_secret": "********",
        },
        token="tok",
        settings=Settings(active_profile="prod"),
    )

    assert payload["radius_secret"] == "radius-from-delinea"
    assert payload["tacacs_secret"] == "tacacs-from-delinea"


def test_prepare_write_payload_fetches_name_for_id_based_update(monkeypatch):
    monkeypatch.setattr(
        hooks, "query_params_for_action", lambda *args, **kwargs: {"id": 42}
    )
    monkeypatch.setattr(
        hooks,
        "resolve_network_device_secret_values",
        lambda **kwargs: {"radius_secret": "radius-from-delinea"},
    )

    class CP:
        def get(self, api_catalog, token, args, *, params=None):
            assert params == {"id": 42}
            return {"id": 42, "name": "switch-a"}

    payload = hooks.prepare_write_payload(
        CP(),
        {},
        {
            "module": "policyelements",
            "service": "network-device",
            "action": "update",
            "id": 42,
        },
        "update",
        {"ip_address": "10.0.0.1", "radius_secret": ""},
        token="tok",
        settings=Settings(active_profile="prod"),
    )

    assert payload["radius_secret"] == "radius-from-delinea"


def test_prepare_write_payload_leaves_non_network_device_payloads_unchanged():
    payload = {"name": "alice", "password": ""}

    result = hooks.prepare_write_payload(
        None,
        {},
        {"module": "identities", "service": "endpoint", "action": "add"},
        "add",
        payload,
        token="tok",
        settings=Settings(active_profile="prod"),
    )

    assert result == payload
