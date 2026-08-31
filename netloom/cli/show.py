from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from netloom.core.config import Settings
from netloom.core.running_config import (
    _default_out_path,
    _parse_scope,
    render_netloom_format,
    render_running_config,
)
from netloom.io.files import ensure_parent_dir
from netloom.io.output import should_mask_secrets


def handle_show_command(
    args: dict[str, Any],
    *,
    plugin,
    settings: Settings,
    deps,
    log=None,
) -> bool:
    if args.get("module") != "show":
        return False
    if args.get("service") != "running-config" or args.get("action"):
        return False

    mask_secrets = should_mask_secrets(args, settings)
    cp = plugin.build_client(settings, mask_secrets=mask_secrets)
    if log is not None:
        log.info(
            "Exporting running config via plugin '%s' from server: %s",
            plugin.name,
            settings.server,
        )
    token = plugin.resolve_auth_token(cp, settings)
    catalog_view = deps._catalog_view_from_args(args)
    api_catalog = deps._get_catalog_for_cli(
        plugin,
        cp,
        token=token,
        settings=settings,
        catalog_view=catalog_view,
    )
    out_path = Path(args.get("out") or _default_out_path(settings))
    ensure_parent_dir(out_path)

    with out_path.open("w", encoding="utf-8") as output_file:

        def stream_line(line: str) -> None:
            rendered = f"{line}\n"
            output_file.write(rendered)
            output_file.flush()
            sys.stdout.write(rendered)
            sys.stdout.flush()

        try:
            render_running_config(
                plugin,
                cp,
                token,
                api_catalog,
                settings=settings,
                catalog_view=catalog_view,
                include=_parse_scope(args.get("include")),
                exclude=(
                    _parse_scope(args.get("exclude"))
                    if args.get("exclude") is not None
                    else None
                ),
                continue_on_error=bool(args.get("continue_on_error")),
                mask_secrets=mask_secrets,
                hydrate_mode=args.get("hydrate") or "auto",
                line_sink=stream_line,
                log=log,
            )
        except KeyboardInterrupt:
            stream_line(
                "# interrupted: running-config export stopped before completion"
            )
            raise
        except Exception as exc:
            stream_line(f"# aborted: {exc}")
            raise
    return True


__all__ = [
    "_parse_scope",
    "handle_show_command",
    "render_netloom_format",
    "render_running_config",
]
