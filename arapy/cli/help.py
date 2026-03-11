from __future__ import annotations

CLI_ACTION_ORDER = ["get", "add", "delete", "update", "replace"]


def service_cli_actions(service_entry: dict) -> list[str]:
    actions = service_entry.get("actions") or {}
    cli_actions: list[str] = []
    if "get" in actions or "list" in actions:
        cli_actions.append("get")
    #if "list" in actions:
    #    cli_actions.append("list")
    for action in CLI_ACTION_ORDER[1:]:
        if action in actions:
            cli_actions.append(action)
    return cli_actions


def render_action_block(title: str, action_def: dict) -> str:
    lines = [f"{title}:", f"  method: {action_def.get('method', '<unknown>')}"]
    paths = action_def.get("paths") or []
    if paths:
        lines.append("  paths:")
        lines.extend(f"    - {path}" for path in paths)
    params = action_def.get("params") or []
    if params:
        lines.append("  params:")
        lines.extend(f"    - {param}" for param in params)
    return "\n".join(lines)


def render_help(
    api_catalog: dict | None = None,
    args: dict | None = None,
    *,
    version: str = "0.0.0",
) -> str:
    args = args or {}
    module = args.get("module")
    service = args.get("service")
    action = args.get("action")

    header = f"ClearPass API tool v{version}\n"
    usage = (
        "Usage:\n"
        "  arapy <module> <service> <action> [options] [flags]\n\n"
        "Examples:\n"
        "  arapy <module> <service> "
        "[add|delete|get|list|update|replace] "
        "[--key=value] "
        "[--log-level=debug|info|warning|error|critical] [--console]\n"
        "  arapy cache [clear | update]\n"
        "  arapy [--help | ?]\n"
        "  arapy --version\n\n"
        "Common options:\n"
        "  --file=PATH                        Path to JSON/CSV bulk payload input.\n"
        "  --out=PATH                         Override the output file path.\n"
        "  --data-format=json|csv|raw         Output format (default: json).\n"
        "  --csv-fieldnames=a,b,c             Fields and order for CSV output.\n"
        "  --log-level=LEVEL                 Select log level.\n\n"
        "Common flags:\n"
        "  --help                             Print help message (same as -h and ?).\n"
        "  --console                          Also print output to terminal.\n"
        "  --decrypt                          Include secrets in output.\n\n"
        "Notes:\n"
        "  Action 'list' is the same as 'get --all'.\n"
    )

    modules = (api_catalog or {}).get("modules") or {}
    if not modules:
        return (
            header
            + usage
            + "\nNo API catalog cache found.\n"
            + "Run `arapy cache update` to build the cache from ClearPass /api-docs."
        )

    if not module:
        available_modules = "\n".join(f"  - {name}" for name in sorted(modules.keys()))
        return header + usage + "\nAvailable modules:\n" + available_modules

    if module not in modules:
        available = ", ".join(sorted(modules.keys()))
        return header + f"Unknown module '{module}'. Available modules: {available}"

    services = modules[module]
    if not service:
        available_services = "\n".join(
            f"  - {name}" for name in sorted(services.keys())
        )
        return (
            header
            + usage
            + f"\nModule: {module}\nAvailable services:\n{available_services}"
        )

    if service not in services:
        available = ", ".join(sorted(services.keys()))
        return (
            header
            + f"Unknown service '{service}' under module '{module}'. "
            + f"Available services: {available}"
        )

    service_entry = services[service]
    cli_actions = service_cli_actions(service_entry)
    action_map = service_entry.get("actions") or {}

    if not action:
        return (
            header
            + usage
            + f"\nModule: {module}\n"
            + f"Service: {service}\n"
            + "Available actions: "
            + ", ".join(cli_actions)
        )

    valid_actions = set(cli_actions)
    if "list" in action_map:
        valid_actions.add("list")

    if action not in valid_actions:
        shown_actions = list(cli_actions)
        if "list" in action_map:
            shown_actions.append("list")
        return (
            header
            + f"Unknown action '{action}' for {module} {service}.\n"
            + f"Available actions: {', '.join(shown_actions)}"
        )

    blocks: list[str] = []
    if action == "get":
        if "list" in action_map:
            blocks.append(
                render_action_block("list (used by `get --all`)", action_map["list"])
            )
        if "get" in action_map:
            blocks.append(render_action_block("get", action_map["get"]))
    elif action == "list":
        blocks.append(
            render_action_block("list (alias for `get --all`)", action_map["list"])
        )
    else:
        blocks.append(render_action_block(action, action_map[action]))

    return "\n\n".join(blocks)
