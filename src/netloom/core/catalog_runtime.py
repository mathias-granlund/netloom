from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from netloom.core.config import Settings


def catalog_view_from_args(args: dict | None) -> str:
    value = (args or {}).get("catalog_view")
    if isinstance(value, str) and value.strip().lower() == "full":
        return "full"
    return "visible"


def get_catalog_for_runtime(
    plugin,
    cp,
    *,
    token: str,
    settings: Settings | None,
    force_refresh: bool = False,
    catalog_view: str,
    timing_sink=None,
    progress_sink=None,
) -> dict:
    kwargs = {
        "token": token,
        "force_refresh": force_refresh,
        "settings": settings,
        "catalog_view": catalog_view,
    }
    if timing_sink is not None:
        kwargs["timing_sink"] = timing_sink
    if progress_sink is not None:
        kwargs["progress_sink"] = progress_sink

    while True:
        try:
            return plugin.get_api_catalog(cp, **kwargs)
        except TypeError as exc:
            message = str(exc)
            if "progress_sink" in message and "progress_sink" in kwargs:
                kwargs.pop("progress_sink", None)
                continue
            if "timing_sink" in message and "timing_sink" in kwargs:
                kwargs.pop("timing_sink", None)
                continue
            if "catalog_view" in message and "catalog_view" in kwargs:
                kwargs.pop("catalog_view", None)
                continue
            raise


__all__ = ["catalog_view_from_args", "get_catalog_for_runtime"]
