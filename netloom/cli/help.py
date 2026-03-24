from __future__ import annotations

from netloom.core.config import credentials_env_path, list_profiles, profiles_env_path
from netloom.core.help import (
    NETLOOM_BANNER,
    render_action_block,
    render_cache_help,
    render_catalog_help,
    render_load_help,
    render_server_help,
    service_cli_actions,
)
from netloom.core.plugin import list_plugins

__all__ = ["render_action_block", "render_help", "service_cli_actions"]


def _plugin_help_context(plugin=None) -> dict:
    provider = getattr(plugin, "help_context", None)
    if callable(provider):
        return provider() or {}
    return {}


def _with_indent(lines: list[str], prefix: str = "  ") -> list[str]:
    return [line if line.startswith(prefix) else f"{prefix}{line}" for line in lines]


def _render_usage(plugin=None) -> str:
    plugin_help = _plugin_help_context(plugin)
    usage_lines = [
        "Usage:",
        "  netloom load [list | show | <plugin>]",
        "  netloom server [list | show | use <profile>]",
        "  netloom cache [clear | update]",
        "  netloom <module> <service> <action> [options] [flags]",
        "  netloom <module> <service> copy --from=SOURCE --to=TARGET [options] [flags]",
        "  netloom <module> <service> diff --from=SOURCE --to=TARGET [options] [flags]",
        "  netloom [--help | ?]",
        "  netloom --version",
    ]
    examples = plugin_help.get("examples") or []
    option_lines = _with_indent(plugin_help.get("common_options") or [])
    flag_lines = _with_indent(plugin_help.get("common_flags") or [])
    note_lines = _with_indent(plugin_help.get("notes") or [])

    if examples:
        usage_lines.extend(["", "Examples:", *[f"  {line}" for line in examples]])
    usage_lines.extend(
        [
            "",
            "Catalog options:",
            "  --catalog-view=visible|full       "
            "Use the filtered catalog or the full discovered catalog "
            "(default: visible).",
        ]
    )
    if option_lines:
        usage_lines.extend(["", "Common options:", *option_lines])
    if flag_lines:
        usage_lines.extend(["", "Common flags:", *flag_lines])
    if note_lines:
        usage_lines.extend(["", "Notes:", *note_lines])
    return "\n".join(usage_lines) + "\n"


def render_help(
    api_catalog: dict | None = None,
    args: dict | None = None,
    *,
    version: str = "0.0.0",
    plugin=None,
) -> str:
    args = args or {}
    module = args.get("module")
    header = f"{NETLOOM_BANNER}\nnetloom v{version}\n"
    usage = _render_usage(plugin)

    if module == "cache":
        return render_cache_help(header, usage)

    if module == "server":
        return render_server_help(
            header,
            usage,
            profiles=list_profiles(),
            profiles_path=profiles_env_path(),
            credentials_path=credentials_env_path(),
        )

    if module == "load":
        return render_load_help(header, usage, list_plugins())

    return render_catalog_help(
        header,
        usage,
        api_catalog=api_catalog,
        module=module,
        service=args.get("service"),
        action=args.get("action"),
        has_plugin=plugin is not None,
    )
