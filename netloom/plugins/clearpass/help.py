from __future__ import annotations


def build_help_context() -> dict[str, list[str]]:
    return {
        "examples": [
            "netloom load clearpass",
            "netloom cache update",
            "netloom server use dev",
            "netloom identities endpoint list --limit=10",
            "netloom identities endpoint list --filter=name:equals:TEST",
            "netloom policyelements network-device get --id=1337 --console",
            (
                "netloom policyelements network-device copy "
                "--from=dev --to=prod --all --dry-run"
            ),
        ],
        "common_options": [
            ("--file=PATH                        Path to JSON/CSV bulk payload input."),
            "--out=PATH                         Override the output file path.",
            "--data-format=JSON|CSV|RAW         Output format (default: json).",
            "--csv-fieldnames=A,B,C             Fields and order for CSV output.",
            (
                "--filter=JSON|FIELD:OP:VALUE       Server-side filter applied "
                "across all matching pages."
            ),
            (
                "--limit=N                          Page size for list/get "
                "--all/copy requests."
            ),
            ("--calculate-count=true|false       Request total count metadata."),
            "--log-level=LEVEL                  Select log level (default: info).",
            "--api-token=TOKEN                  Use an existing bearer token.",
            "--token-file=PATH                  Load a bearer token from a file.",
            "--encrypt=enable|disable           Mask or show secret fields.",
        ],
        "notes": [
            (
                'Filter syntax: --filter=\'{"key":{"$eq":"value"}}\' or '
                "--filter=key:equals:value"
            ),
            (
                "Shorthand operators: equals, not-equals, contains, in, not-in, "
                "gt, gte, lt, lte, exists"
            ),
        ],
    }
