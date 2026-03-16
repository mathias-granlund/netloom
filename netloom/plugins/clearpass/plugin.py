from __future__ import annotations

from netloom.core.config import Settings
from netloom.core.plugin import PluginDefinition
from netloom.io.files import load_api_token_file
from netloom.plugins.clearpass import catalog
from netloom.plugins.clearpass.client import ClearPassClient
from netloom.plugins.clearpass.copy_hooks import (
    normalize_copy_payload,
    preflight_error_for_payload,
    restore_secret_fields,
)


def build_client(settings: Settings, *, mask_secrets: bool = True) -> ClearPassClient:
    if not settings.server:
        raise ValueError(
            "NETLOOM_SERVER is not configured. Set it in the environment "
            "before running network actions."
        )
    try:
        return ClearPassClient(
            server=settings.server,
            https_prefix=settings.https_prefix,
            verify_ssl=settings.verify_ssl,
            timeout=settings.timeout,
            mask_secrets=mask_secrets,
        )
    except TypeError as exc:
        if "mask_secrets" not in str(exc):
            raise
        cp = ClearPassClient(
            server=settings.server,
            https_prefix=settings.https_prefix,
            verify_ssl=settings.verify_ssl,
            timeout=settings.timeout,
        )
        setattr(cp, "mask_secrets", mask_secrets)
        return cp


def resolve_auth_token(cp: ClearPassClient, settings: Settings) -> str:
    if settings.api_token:
        return settings.api_token
    if settings.api_token_file:
        return load_api_token_file(settings.api_token_file)
    return cp.login(catalog.OAUTH_ENDPOINTS, settings.credentials)["access_token"]


PLUGIN = PluginDefinition(
    name="clearpass",
    display_name="HPE Aruba ClearPass",
    build_client=build_client,
    resolve_auth_token=resolve_auth_token,
    get_api_catalog=catalog.get_api_catalog,
    load_cached_catalog=catalog.load_cached_catalog,
    clear_api_cache=catalog.clear_api_cache,
    normalize_copy_payload=normalize_copy_payload,
    restore_secret_fields=restore_secret_fields,
    preflight_error_for_payload=preflight_error_for_payload,
)
