import types
import pytest
import requests

import arapy.clearpass as clearpass
import arapy.config as config


class FakeResp:
    def __init__(self, *, status_code=200, reason="OK", url="https://x/api", headers=None, text="", content=b"{}", json_value=None, raise_http=False):
        self.status_code = status_code
        self.reason = reason
        self.url = url
        self.headers = headers or {"content-type": "application/json"}
        self.text = text
        self.content = content
        self._json_value = json_value
        self._raise_http = raise_http

    def raise_for_status(self):
        if self._raise_http:
            raise requests.HTTPError("boom")

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
        # emulate logging formatting behavior enough for tests
        if args:
            msg = msg % args
        self.debug_calls.append(msg)


def test_request_success_json(monkeypatch):
    cp = clearpass.ClearPassClient("server:443", https_prefix="https://", verify_ssl=False)

    def fake_request(**kwargs):
        return FakeResp(json_value={"ok": True}, content=b'{"ok":true}')

    monkeypatch.setattr(cp.session, "request", lambda **kw: fake_request(**kw))
    out = cp.request({"endpoint": "/api/endpoint"}, "GET", "endpoint", token="t")
    assert out == {"ok": True}


def test_request_204_returns_none(monkeypatch):
    cp = clearpass.ClearPassClient("server:443", https_prefix="https://", verify_ssl=False)
    monkeypatch.setattr(cp.session, "request", lambda **kw: FakeResp(status_code=204, content=b""))
    assert cp.request({"x": "/api/x"}, "GET", "x") is None


def test_request_non_json_returns_text(monkeypatch):
    cp = clearpass.ClearPassClient("server:443", https_prefix="https://", verify_ssl=False)
    monkeypatch.setattr(cp.session, "request", lambda **kw: FakeResp(headers={"content-type": "text/plain"}, text="hi", content=b"hi", json_value=None))
    assert cp.request({"x": "/api/x"}, "GET", "x") == "hi"


def test_request_http_error_masks_secrets_and_reraises(monkeypatch):
    cp = clearpass.ClearPassClient("server:443", https_prefix="https://", verify_ssl=False)

    fake_log = FakeLogger()
    monkeypatch.setattr(clearpass, "log", fake_log)

    # response body gets split into debug lines
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
        cp.request({"oauth": "/api/oauth"}, "POST", "oauth", token="t", json_body=payload)

    # one error summary
    assert fake_log.error_calls, "expected an error log"
    # debug should include masked secret
    joined = "\n".join(fake_log.debug_calls)
    assert "***" in joined
    assert "SUPERSECRET" not in joined
