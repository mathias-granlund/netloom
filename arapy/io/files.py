from __future__ import annotations

import csv
import json
from pathlib import Path


def ensure_parent_dir(path: str | Path) -> None:
    Path(path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


def _strip_response_links(value):
    if isinstance(value, dict):
        return {
            key: _strip_response_links(item)
            for key, item in value.items()
            if key != "_links"
        }
    if isinstance(value, list):
        return [_strip_response_links(item) for item in value]
    return value


def _normalize_json_payload(data):
    if isinstance(data, dict):
        embedded = data.get("_embedded")
        if isinstance(embedded, dict):
            items = embedded.get("items")
            if isinstance(items, list) and all(
                isinstance(item, dict) for item in items
            ):
                return _strip_response_links(items)
        return _strip_response_links(data)

    if isinstance(data, list) and all(isinstance(item, dict) for item in data):
        return _strip_response_links(data)

    raise ValueError(
        "JSON must contain a dict, a list of dicts, or a ClearPass list response."
    )


def load_api_token_file(filename: str | Path) -> str:
    path = Path(filename)
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("Token file is empty.")

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return text

    if isinstance(data, str) and data.strip():
        return data.strip()

    if isinstance(data, dict):
        for key in ("access_token", "api_token", "token"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        raise ValueError(
            "Token JSON must contain one of: access_token, api_token, token"
        )

    raise ValueError("Token file must contain a raw token string or token JSON object.")


def load_payload_file(filename: str | Path):
    path = Path(filename)
    extension = path.suffix.lower()

    if extension == ".json":
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return _normalize_json_payload(data)

    if extension == ".csv":
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    raise ValueError("Unsupported file type. Use .json or .csv")
