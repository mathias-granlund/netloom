import pytest
import requests

import arapy.core.client as clearpass

MISSING = object()


class FakeResp:
    def __init__(
        self,
        *,
        status_code=200,
        reason="OK",
        url="https://server/api/x",
        headers=None,
        text='{"ok":true}',
        content=b'{"ok":true}',
        json_value=None,
        raise_http=False,
    ):
        self.status_code = status_code
        self.reason = reason
        self.url = url
        self.headers = headers or {"content-type": "application/json"}
        self.text = text
        self.content = content
        self._json_value = {"ok": True} if json_value is MISSING else json_value
        self._raise_http = raise_http

    def raise_for_status(self):
        if self._raise_http:
            err = requests.HTTPError(self.text)
            err.response = self
            raise err

    def json(self):
        if self._json_value is None:
            raise ValueError("not json")
        return self._json_value


class FakeLogger:
    def __init__(self):
        self.error_calls = []
        self.debug_calls = []

    def error(self, *args, **kwargs):
        self.error_calls.append((args, kwargs))

    def debug(self, msg, *args, **kwargs):
        if args:
            msg = msg % args
        self.debug_calls.append(msg)


def test_request_success_json(monkeypatch):
    cp = clearpass.ClearPassClient(
        "server:443", https_prefix="https://", verify_ssl=False
    )
    monkeypatch.setattr(
        cp.session,
        "request",
        lambda **kw: FakeResp(json_value={"ok": True}, content=b'{"ok":true}'),
    )
    out = cp.request({"endpoint": "/api/endpoint"}, "GET", "endpoint", token="t")
    assert out == {"ok": True}


def test_request_204_returns_none(monkeypatch):
    cp = clearpass.ClearPassClient(
        "server:443", https_prefix="https://", verify_ssl=False
    )
    monkeypatch.setattr(
        cp.session, "request", lambda **kw: FakeResp(status_code=204, content=b"")
    )
    assert cp.request({"x": "/api/x"}, "GET", "x") is None


def test_request_non_json_returns_text(monkeypatch):
    cp = clearpass.ClearPassClient(
        "server:443", https_prefix="https://", verify_ssl=False
    )
    monkeypatch.setattr(
        cp.session,
        "request",
        lambda **kw: FakeResp(
            headers={"content-type": "text/plain"},
            text="hi",
            content=b"hi",
            json_value=None,
        ),
    )
    assert cp.request({"x": "/api/x"}, "GET", "x") == "hi"


def test_request_binary_returns_bytes_and_metadata(monkeypatch):
    cp = clearpass.ClearPassClient(
        "server:443", https_prefix="https://", verify_ssl=False
    )
    monkeypatch.setattr(
        cp.session,
        "request",
        lambda **kw: FakeResp(
            headers={
                "content-type": "application/x-pkcs12",
                "content-disposition": 'attachment; filename="cert-export.p12"',
            },
            text="",
            content=b"\x01\x02\x03",
            json_value=None,
        ),
    )

    out = cp.request({"x": "/api/x"}, "GET", "x")
    assert out == b"\x01\x02\x03"
    assert cp.last_response_meta.is_binary is True
    assert cp.last_response_meta.filename == "cert-export.p12"


def test_request_http_error_masks_secrets_and_reraises(monkeypatch):
    cp = clearpass.ClearPassClient(
        "server:443", https_prefix="https://", verify_ssl=False
    )
    fake_log = FakeLogger()
    monkeypatch.setattr(clearpass, "log", fake_log)

    resp = FakeResp(
        status_code=401,
        reason="Unauthorized",
        url="https://server/api/oauth",
        headers={"content-type": "application/json"},
        text='{"error":"bad"}',
        content=b'{"error":"bad"}',
        raise_http=True,
    )
    monkeypatch.setattr(cp.session, "request", lambda **kw: resp)

    payload = {"client_id": "x", "client_secret": "SUPERSECRET"}
    with pytest.raises(requests.HTTPError):
        cp.request(
            {"oauth": "/api/oauth"}, "POST", "oauth", token="t", json_body=payload
        )

    assert fake_log.error_calls
    joined = "\n".join(fake_log.debug_calls)
    assert "***" in joined
    assert "SUPERSECRET" not in joined
