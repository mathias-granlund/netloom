from __future__ import annotations


def build_help_context() -> dict[str, list[str]]:
    return {
        "notes": [
            (
                'Filter syntax: --filter=\'{"key":{"$eq":"value"}}\' or '
                "--filter=key:equals:value"
            ),
            (
                "Shorthand operators: equals, not-equals, contains, in, not-in, "
                "gt, gte, lt, lte, exists"
            ),
            (
                "Credential lookup: set "
                "NETLOOM_CLIENT_SECRET_REF=prod/client-secret to resolve the "
                "secret from the OS keychain service netloom/clearpass. "
                "NETLOOM_CLIENT_SECRET remains the plaintext fallback."
            ),
        ],
    }
