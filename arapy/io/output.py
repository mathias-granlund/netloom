from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any, Iterable

from arapy.core.config import SECRET_FIELDS, Settings
from arapy.io.files import ensure_parent_dir

log = logging.getLogger(__name__)


def should_mask_secrets(args: dict | None, settings: Settings) -> bool:
    if not args:
        return settings.encrypt_secrets

    if args.get("decrypt"):
        return False

    encrypt = args.get("encrypt")
    if encrypt is None:
        return settings.encrypt_secrets

    value = str(encrypt).strip().lower()
    if value in {"enable", "enabled", "true", "1", "yes", "on"}:
        return True
    if value in {"disable", "disabled", "false", "0", "no", "off"}:
        return False
    raise ValueError("--encrypt must be enable or disable")


def sanitize_secrets(value: Any, *, mask_secrets: bool = True):
    if not mask_secrets:
        return value

    if isinstance(value, dict):
        sanitized = {}
        for key, item in value.items():
            if key in SECRET_FIELDS:
                sanitized[key] = ""
            else:
                sanitized[key] = sanitize_secrets(item, mask_secrets=mask_secrets)
        return sanitized

    if isinstance(value, list):
        return [sanitize_secrets(item, mask_secrets=mask_secrets) for item in value]

    return value


def _extract_by_path(data: Any, path: Iterable[str | int]):
    current = data
    for step in path:
        try:
            current = current[step]
        except (KeyError, IndexError, TypeError):
            return None
    return current


def _console_text_for_raw_bytes(value: bytes) -> str:
    try:
        decoded = value.decode("utf-8")
    except UnicodeDecodeError:
        return f"<binary data: {len(value)} bytes>"

    # Avoid spewing binary blobs into the terminal when the bytes are not readable text.
    if any(ord(char) < 32 and char not in "\r\n\t" for char in decoded):
        return f"<binary data: {len(value)} bytes>"

    if decoded and not any(
        char.isprintable() and not char.isspace() for char in decoded
    ):
        return f"<binary data: {len(value)} bytes>"

    return decoded


def write_value_to_file(
    value: Any,
    path: str | Path,
    *,
    mode: str = "w",
    data_format: str = "json",
    csv_fieldnames: list[str] | None = None,
    csv_include_header: bool = True,
    items_path: tuple[str | int, ...] = ("_embedded", "items"),
    also_console: bool = False,
    mask_secrets: bool = True,
) -> None:
    if mode not in {"a", "w"}:
        raise ValueError("mode must be 'a' or 'w'")
    if data_format not in {"json", "csv", "raw"}:
        raise ValueError("data_format must be 'json', 'csv', or 'raw'")

    path = Path(path)
    ensure_parent_dir(path)
    safe_value = sanitize_secrets(value, mask_secrets=mask_secrets)

    if data_format == "json":
        with path.open(mode, encoding="utf-8") as handle:
            if isinstance(safe_value, (dict, list)):
                json.dump(safe_value, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
            else:
                handle.write(f"{safe_value}\n")
        if also_console:
            if isinstance(safe_value, (dict, list)):
                print(json.dumps(safe_value, indent=2, ensure_ascii=False))
            else:
                print(safe_value)
    elif data_format == "raw":
        if isinstance(safe_value, bytes):
            binary_mode = "ab" if mode == "a" else "wb"
            with path.open(binary_mode) as handle:
                handle.write(safe_value)
            if also_console:
                print(_console_text_for_raw_bytes(safe_value))
        else:
            text = str(safe_value)
            with path.open(mode, encoding="utf-8") as handle:
                handle.write(text)
            if also_console:
                print(text)
    else:
        rows = None
        if isinstance(safe_value, dict):
            # Prefer ClearPass list payloads when exporting a single response object as CSV.
            extracted = _extract_by_path(safe_value, items_path)
            if isinstance(extracted, list):
                rows = extracted
        if rows is None and isinstance(safe_value, list):
            rows = safe_value
        if rows is None and isinstance(safe_value, dict):
            rows = [safe_value]
        if rows is None:
            rows = [{"value": safe_value}]
        if not rows:
            return

        append_mode = mode == "a"
        need_header = csv_include_header and (
            not append_mode
            or (append_mode and (not path.exists() or path.stat().st_size == 0))
        )

        with path.open(mode, encoding="utf-8", newline="") as handle:
            if isinstance(rows[0], dict):
                fieldnames = csv_fieldnames or list(rows[0].keys())
                writer = csv.DictWriter(
                    handle,
                    fieldnames=fieldnames,
                    lineterminator="\n",
                    extrasaction="ignore",
                )
                if need_header:
                    writer.writeheader()
                    if also_console:
                        print(",".join(fieldnames))
                for row in rows:
                    writer.writerow(row)
                    if also_console:
                        print(
                            ",".join(
                                "" if row.get(field) is None else str(row.get(field))
                                for field in fieldnames
                            )
                        )
            else:
                writer = csv.writer(handle, lineterminator="\n")
                if need_header:
                    writer.writerow(["value"])
                    if also_console:
                        print("value")
                for row in rows:
                    writer.writerow([row])
                    if also_console:
                        print(row)

    log.debug("Wrote file to %s", path)


def log_to_file(
    thing: Any,
    filename: str | Path | None = None,
    *args,
    also_console: bool = False,
    mode: str = "w",
    data_format: str = "json",
    csv_fieldnames: list[str] | None = None,
    csv_include_header: bool = True,
    items_path: tuple[str | int, ...] = ("_embedded", "items"),
    mask_secrets: bool = True,
    **kwargs,
):
    if filename is None:
        raise ValueError("filename must be provided")

    if callable(thing):
        result = thing(*args, **kwargs)
        if result is not None:
            write_value_to_file(
                result,
                filename,
                mode=mode,
                data_format=data_format,
                csv_fieldnames=csv_fieldnames,
                csv_include_header=csv_include_header,
                items_path=items_path,
                also_console=also_console,
                mask_secrets=mask_secrets,
            )
        return result

    write_value_to_file(
        thing,
        filename,
        mode=mode,
        data_format=data_format,
        csv_fieldnames=csv_fieldnames,
        csv_include_header=csv_include_header,
        items_path=items_path,
        also_console=also_console,
        mask_secrets=mask_secrets,
    )
    return thing
