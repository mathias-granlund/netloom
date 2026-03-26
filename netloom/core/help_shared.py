from __future__ import annotations

CLI_ACTION_ORDER = [
    "list",
    "get",
    "add",
    "update",
    "replace",
    "delete",
    "diff",
    "copy",
]

NETLOOM_BANNER = r"""
 _   _      _   _
| \ | | ___| |_| | ___   ___  _ __ ___
|  \| |/ _ \ __| |/ _ \ / _ \| '_ ` _ \
| |\  |  __/ |_| | (_) | (_) | | | | | |
|_| \_|\___|\__|_|\___/ \___/|_| |_| |_|
""".strip("\n")

PLUGIN_SELECTION_HINT = "<select a plugin with `netloom load <plugin>`>"
BUILTIN_MODULES = ["cache", "load", "server"]


def service_cli_actions(service_entry: dict) -> list[str]:
    actions = service_entry.get("actions") or {}
    cli_actions: list[str] = []
    if "list" in actions:
        cli_actions.append("list")
    if "get" in actions:
        cli_actions.append("get")
    for action in CLI_ACTION_ORDER[2:]:
        if action in {"copy", "diff"}:
            cli_actions.append(action)
        elif action in actions:
            cli_actions.append(action)
    return cli_actions


__all__ = [
    "BUILTIN_MODULES",
    "CLI_ACTION_ORDER",
    "NETLOOM_BANNER",
    "PLUGIN_SELECTION_HINT",
    "service_cli_actions",
]
