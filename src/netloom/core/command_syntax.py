from __future__ import annotations

BOOLEAN_FLAGS = {
    "verbose",
    "version",
    "debug",
    "console",
    "all",
    "show_all",
    "decrypt",
    "dry_run",
    "continue_on_error",
    "help",
}

VALUE_FLAG_ALIASES = {
    "format": "data_format",
}


def normalize_flag_name(key: str) -> str:
    normalized = key.replace("-", "_")
    return VALUE_FLAG_ALIASES.get(normalized, normalized)


__all__ = ["BOOLEAN_FLAGS", "VALUE_FLAG_ALIASES", "normalize_flag_name"]
