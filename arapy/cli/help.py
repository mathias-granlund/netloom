from __future__ import annotations

import json

CLI_ACTION_ORDER = ["list", "get", "add", "delete", "update", "replace"]


def service_cli_actions(service_entry: dict) -> list[str]:
    actions = service_entry.get("actions") or {}
    cli_actions: list[str] = []
    if "list" in actions:
        cli_actions.append("list")
    if "get" in actions:
        cli_actions.append("get")
    for action in CLI_ACTION_ORDER[2:]:
        if action in actions:
            cli_actions.append(action)
    return cli_actions


def render_action_block(title: str, action_def: dict) -> str:
    lines = [f"{title}:"]
    summary = action_def.get("summary")
    if summary:
        lines.append(f"  summary: {summary}")
    lines.append(f"  method: {action_def.get('method', '<unknown>')}")
    paths = action_def.get("paths") or []
    if paths:
        lines.append("  paths:")
        lines.extend(f"    - {path}" for path in paths)
    params = action_def.get("params") or []
    if params:
        lines.append("  params:")
        lines.extend(f"    - {param}" for param in params)
    notes = action_def.get("notes") or []
    if notes:
        lines.append("  notes:")
        lines.extend(f"    - {note}" for note in notes)
    response_codes = action_def.get("response_codes") or []
    if response_codes:
        lines.append("  response codes:")
        lines.extend(f"    - {code}" for code in response_codes)
    response_types = action_def.get("response_content_types") or []
    if response_types:
        lines.append("  response content types:")
        lines.extend(f"    - {content_type}" for content_type in response_types)
    body_description = action_def.get("body_description")
    if body_description:
        lines.append(f"  body: {body_description}")
    body_required = action_def.get("body_required") or []
    if body_required:
        lines.append("  body required:")
        lines.extend(f"    - {name}" for name in body_required)
    body_fields = action_def.get("body_fields") or []
    if body_fields:
        lines.append("  body fields:")
        for field in body_fields:
            if not isinstance(field, dict):
                continue
            requirement = "required" if field.get("required") else "optional"
            field_type = field.get("type") or "object"
            description = field.get("description")
            line = f"    - {field.get('name')}: {field_type} ({requirement})"
            if description:
                line += f" - {description}"
            lines.append(line)
    body_example = action_def.get("body_example")
    if body_example not in (None, {}, []):
        lines.append("  body example:")
        lines.extend(
            f"    {line}"
            for line in json.dumps(body_example, indent=2, ensure_ascii=False).splitlines()
        )
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
