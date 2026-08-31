import pytest

from netloom.contracts import HttpRequest
from netloom.http.client import RequestsHttpClient
from netloom.http.metadata import (
    filename_from_content_disposition,
    is_binary_content_type,
    parse_content_type,
)


class _FakeResponse:
    status_code = 200
    reason = "OK"
    url = "https://example.test/api/items"
    headers = {"Content-Type": "application/json; charset=utf-8"}
    content = b'{"ok":true}'


class _FakeSession:
    def __init__(self, response=None):
        self.response = response or _FakeResponse()
        self.calls = []

    def request(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def test_requests_http_client_executes_generic_request():
    session = _FakeSession()
    client = RequestsHttpClient(session)
    request = HttpRequest(
        method="post",
        url="https://example.test/api/items",
        headers={"Authorization": "Bearer token"},
        params={"limit": 25},
        json_body={"name": "demo"},
        verify_ssl=False,
        timeout=10,
    )

    response = client.execute(request)

    assert session.calls == [
        {
            "method": "POST",
            "url": "https://example.test/api/items",
            "params": {"limit": 25},
            "json": {"name": "demo"},
            "data": None,
            "headers": {"Authorization": "Bearer token"},
            "verify": False,
            "timeout": 10,
        }
    ]
    assert response.status_code == 200
    assert response.content_type == "application/json"
    assert response.is_binary is False
    assert response.json() == {"ok": True}


def test_requests_http_client_normalizes_binary_response_metadata():
    class BinaryResponse:
        status_code = 200
        reason = "OK"
        url = "https://example.test/api/cert"
        headers = {
            "Content-Type": "application/x-pkcs12",
            "Content-Disposition": 'attachment; filename="cert-export.p12"',
        }
        content = b"\x01\x02\x03"

    response = RequestsHttpClient(_FakeSession(BinaryResponse())).execute(
        HttpRequest(method="GET", url="https://example.test/api/cert")
    )

    assert response.content == b"\x01\x02\x03"
    assert response.content_type == "application/x-pkcs12"
    assert response.filename == "cert-export.p12"
    assert response.is_binary is True


def test_requests_http_client_rejects_ambiguous_body():
    client = RequestsHttpClient(_FakeSession())
    request = HttpRequest(
        method="POST",
        url="https://example.test/api/items",
        json_body={"name": "demo"},
        body="raw",
    )

    with pytest.raises(ValueError, match="body and json_body"):
        client.execute(request)


def test_content_type_helpers():
    assert parse_content_type("Application/JSON; charset=utf-8") == "application/json"
    assert is_binary_content_type("application/json") is False
    assert is_binary_content_type("text/plain") is False
    assert is_binary_content_type("application/octet-stream") is True
    assert (
        filename_from_content_disposition(
            "attachment; filename*=UTF-8''clearpass-export.zip"
        )
        == "clearpass-export.zip"
    )
