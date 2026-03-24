from __future__ import annotations

import json
from pathlib import Path

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


def render_copy_action_help(module: str, service: str) -> str:
    return (
        f"copy ({module} {service}):\n"
        "  usage: netloom <module> <service> copy --from=SOURCE_PROFILE "
        "--to=TARGET_PROFILE [options]\n"
        "  selectors:\n"
        "    - --id=VALUE\n"
        "    - --name=VALUE\n"
        "    - --filter=JSON\n"
        "    - --all\n"
        "  behavior:\n"
        "    - --on-conflict=fail|skip|update|replace\n"
        "    - --match-by=auto|name|id\n"
        "    - --dry-run\n"
        "    - --continue-on-error\n"
        "    - --decrypt\n"
        "  artifacts:\n"
        "    - --out=PATH\n"
        "    - --save-source=PATH  (default: NETLOOM_OUT_DIR/<generated>_source.json)\n"
        "    - --save-payload=PATH "
        "(default: NETLOOM_OUT_DIR/<generated>_payload.json)\n"
        "    - --save-plan=PATH    (default: NETLOOM_OUT_DIR/<generated>_plan.json)"
    )


def render_diff_action_help(module: str, service: str) -> str:
    return (
        f"diff ({module} {service}):\n"
        "  usage: netloom <module> <service> diff --from=SOURCE_PROFILE "
        "--to=TARGET_PROFILE [options]\n"
        "  selectors:\n"
        "    - --id=VALUE\n"
        "    - --name=VALUE\n"
        "    - --filter=JSON\n"
        "    - --all\n"
        "  behavior:\n"
        "    - --match-by=auto|name|id\n"
        "    - --fields=path1,path2\n"
        "    - --ignore-fields=path1,path2\n"
        "    - --show-all\n"
        "    - --max-items=N\n"
        "  notes:\n"
        "    broad selectors report: same, different, only_in_source, only_in_target\n"
        "    narrow selectors stay source-scoped\n"
        "    changed_fields uses nested dotted paths when possible\n"
        "    ambiguous matches are reported explicitly\n"
        "    console previews are capped by default; use --show-all or "
        "--max-items=N to expand them\n"
        "  output:\n"
        "    - --out=PATH (default: NETLOOM_OUT_DIR/<generated>_diff.json)"
    )


def _compact_param_flag(param: str) -> str:
    mapping = {
        "sort": "--sort=FIELD[:asc|desc]",
        "offset": "--offset=N",
        "limit": "--limit=N",
        "calculate_count": "--calculate-count=true|false",
    }
    return mapping.get(param, f"--{param.replace('_', '-')}=VALUE")


def _dedupe_lines(lines: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for line in lines:
        if line in seen:
            continue
        seen.add(line)
        deduped.append(line)
    return deduped


def _supports_path_token(paths: list[str], token: str) -> bool:
    marker = "{" + token + "}"
    return any(marker in path for path in paths)


def render_list_action_help(module: str, service: str, action_def: dict) -> str:
    params = action_def.get("params") or []
    selectors: list[str] = []
    options: list[str] = []

    if "filter" in params:
        selectors.append("--filter=JSON|FIELD:OP:VALUE")

    for param in params:
        if param == "filter":
            continue
        options.append(_compact_param_flag(param))

    options.extend(["--console", "--out=PATH"])
    options = _dedupe_lines(options)

    lines = [
        f"list ({module} {service}):",
        "  usage: netloom <module> <service> list [options]",
    ]
    if selectors:
        lines.append("  selectors:")
        lines.extend(f"    - {selector}" for selector in selectors)
    if options:
        lines.append("  options:")
        lines.extend(f"    - {option}" for option in options)
    return "\n".join(lines)


def render_get_action_help(module: str, service: str, service_entry: dict) -> str:
    action_map = service_entry.get("actions") or {}
    get_def = action_map.get("get") or {}
    list_def = action_map.get("list") or {}
    get_paths = get_def.get("paths") or []
    list_params = list_def.get("params") or []

    selector_usage: list[str] = []
    selectors: list[str] = []
    options: list[str] = []

    if _supports_path_token(get_paths, "id"):
        selector_usage.append("--id=VALUE")
        selectors.append("--id=VALUE")
    if _supports_path_token(get_paths, "name"):
        selector_usage.append("--name=VALUE")
        selectors.append("--name=VALUE")
    if list_def:
        selector_usage.append("--all")
        selectors.append("--all")
    if "filter" in list_params:
        selectors.append("--filter=JSON|FIELD:OP:VALUE")

    for param in list_params:
        if param == "filter":
            continue
        options.append(_compact_param_flag(param))

    options.extend(["--console", "--out=PATH"])
    selectors = _dedupe_lines(selectors)
    options = _dedupe_lines(options)

    usage = "  usage: netloom <module> <service> get [options]"
    if selector_usage:
        usage = (
            "  usage: netloom <module> <service> get "
            f"[{' | '.join(selector_usage)}] [options]"
        )

    lines = [f"get ({module} {service}):", usage]
    if selectors:
        lines.append("  selectors:")
        lines.extend(f"    - {selector}" for selector in selectors)
    if options:
        lines.append("  options:")
        lines.extend(f"    - {option}" for option in options)
    return "\n".join(lines)


def _is_filter_reference_note(note: str) -> bool:
    text = note.lower()
    return (
        "more about json filter expressions" in text
        or "a filter is specified as a json object" in text
    )


def _filter_help_lines() -> list[str]:
    return [
        "  filter:",
        "    shorthand: --filter=name:equals:TEST",
        '    json: --filter=\'{"name":{"$contains":"TEST"}}\'',
        (
            "    operators: equals, not-equals, contains, in, not-in, gt, "
            "gte, lt, lte, exists"
        ),
        "    use full JSON for advanced expressions like $and, $or, and regex",
    ]


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
    notes = action_def.get("notes") or []
    filter_supported = "filter" in params
    visible_notes = [
        note
        for note in notes
        if not (filter_supported and _is_filter_reference_note(str(note)))
    ]
    if filter_supported:
        lines.extend(_filter_help_lines())
    if visible_notes:
        lines.append("  notes:")
        for note in visible_notes:
            note_lines = [line for line in str(note).splitlines() if line.strip()]
            if not note_lines:
                continue
            lines.append(f"    - {note_lines[0]}")
            lines.extend(f"      {line}" for line in note_lines[1:])
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
    if params and not body_fields:
        visible_params = [
            param for param in params if not (filter_supported and param == "filter")
        ]
        if visible_params:
            lines.append("  params:")
            lines.extend(f"    - {param}" for param in visible_params)
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
            for line in json.dumps(
                body_example, indent=2, ensure_ascii=False
            ).splitlines()
        )
    return "\n".join(lines)


def format_path_or_hint(path: Path | None) -> str:
    return str(path) if path is not None else PLUGIN_SELECTION_HINT


def render_cache_help(header: str, usage: str) -> str:
    return (
        header
        + usage
        + "\nBuilt-in module: cache\n"
        + "Commands:\n"
        + "  netloom cache clear\n"
        + "  netloom cache update"
    )


def render_server_help(
    header: str,
    usage: str,
    *,
    profiles: list[str],
    profiles_path: Path | None,
    credentials_path: Path | None,
) -> str:
    profile_lines = (
        "\n".join(f"  - {profile}" for profile in profiles)
        if profiles
        else "  <none found>"
    )
    return (
        header
        + usage
        + "\nBuilt-in module: server\n"
        + "Commands:\n"
        + "  netloom server list\n"
        + "  netloom server show\n"
        + "  netloom server use <profile>\n\n"
        + f"Profiles file: {format_path_or_hint(profiles_path)}\n"
        + f"Credentials file: {format_path_or_hint(credentials_path)}\n"
        + "Configured profiles:\n"
        + profile_lines
    )


def render_load_help(header: str, usage: str, plugins: list[str]) -> str:
    plugin_lines = "\n".join(f"  - {name}" for name in plugins)
    return (
        header
        + usage
        + "\nBuilt-in module: load\n"
        + "Commands:\n"
        + "  netloom load list\n"
        + "  netloom load show\n"
        + "  netloom load <plugin>\n\n"
        + "Available plugins:\n"
        + plugin_lines
    )


def render_catalog_help(
    header: str,
    usage: str,
    *,
    api_catalog: dict | None,
    module: str | None,
    service: str | None,
    action: str | None,
    has_plugin: bool,
) -> str:
    modules = (api_catalog or {}).get("modules") or {}
    if not modules:
        builtin_modules = "\n".join(f"  - {name}" for name in BUILTIN_MODULES)
        text = header + usage + "\nAvailable modules:\n" + builtin_modules
        if not has_plugin:
            return text
        return (
            text
            + "\nNo API catalog cache found.\n"
            + "Run `netloom cache update` to build the cache from the active plugin."
        )

    if not module:
        available_modules = "\n".join(
            [
                *[f"  - {name}" for name in BUILTIN_MODULES],
                *[f"  - {name}" for name in sorted(modules.keys())],
            ]
        )
        return header + usage + "\nAvailable modules:\n" + available_modules

    if module not in modules:
        available = ", ".join([*BUILTIN_MODULES, *sorted(modules.keys())])
        return header + f"Unknown module '{module}'\nAvailable modules: {available}"

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
    if action == "copy":
        blocks.append(render_copy_action_help(module, service))
    elif action == "diff":
        blocks.append(render_diff_action_help(module, service))
    elif action == "get":
        blocks.append(render_get_action_help(module, service, service_entry))
    elif action == "list":
        blocks.append(render_list_action_help(module, service, action_map["list"]))
    else:
        blocks.append(render_action_block(action, action_map[action]))

    return "\n\n".join(blocks)
