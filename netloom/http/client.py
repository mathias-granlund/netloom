from __future__ import annotations

from typing import Any

import requests

from netloom.contracts import HttpRequest, HttpResponse
from netloom.http.metadata import (
    filename_from_content_disposition,
    is_binary_content_type,
    parse_content_type,
)


def _normalized_headers(headers: Any) -> dict[str, str]:
    try:
        items = headers.items()
    except AttributeError:
        return {}
    return {str(key).lower(): str(value) for key, value in items}


def _content_bytes(response) -> bytes:
    content = getattr(response, "content", b"")
    if content is None:
        return b""
    if isinstance(content, bytes):
        return content
    return str(content).encode("utf-8")


class RequestsHttpClient:
    """Generic HTTP transport backed by requests.

    This class intentionally knows nothing about Netloom modules, services,
    actions, catalogs, plugins, or CLI arguments.
    """

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()

    def execute(self, request: HttpRequest) -> HttpResponse:
        if request.body is not None and request.json_body is not None:
            raise ValueError("HttpRequest cannot set both body and json_body")

        response = self.session.request(
            method=request.method,
            url=request.url,
            params=request.params or None,
            json=request.json_body,
            data=request.body,
            headers=request.headers or None,
            verify=True if request.verify_ssl is None else request.verify_ssl,
            timeout=request.timeout,
        )
        headers = _normalized_headers(getattr(response, "headers", {}))
        content_type = parse_content_type(headers.get("content-type"))
        return HttpResponse(
            status_code=int(getattr(response, "status_code", 0)),
            reason=str(getattr(response, "reason", "")),
            headers=headers,
            body=_content_bytes(response),
            url=str(getattr(response, "url", None) or request.url),
            request=request,
            content_type=content_type,
            filename=filename_from_content_disposition(
                headers.get("content-disposition")
            ),
            is_binary=is_binary_content_type(content_type),
        )


__all__ = [
    "RequestsHttpClient",
]
