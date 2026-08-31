from __future__ import annotations

import re
from dataclasses import dataclass

from netloom.contracts import HttpResponse

_TEXT_CONTENT_MARKERS = (
    "json",
    "xml",
    "javascript",
    "yaml",
    "html",
    "csv",
    "x-www-form-urlencoded",
)


@dataclass(frozen=True)
class ResponseMetadata:
    content_type: str = ""
    filename: str | None = None
    is_binary: bool = False


def parse_content_type(value: str | None) -> str:
    return (value or "").split(";", 1)[0].strip().lower()


def is_binary_content_type(content_type: str | None) -> bool:
    parsed = parse_content_type(content_type)
    if not parsed:
        return False
    if parsed.startswith("text/"):
        return False
    return not any(marker in parsed for marker in _TEXT_CONTENT_MARKERS)


def filename_from_content_disposition(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', value, re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip().strip('"')


def response_metadata(response: HttpResponse) -> ResponseMetadata:
    return ResponseMetadata(
        content_type=response.content_type,
        filename=response.filename,
        is_binary=response.is_binary,
    )


__all__ = [
    "ResponseMetadata",
    "filename_from_content_disposition",
    "is_binary_content_type",
    "parse_content_type",
    "response_metadata",
]
