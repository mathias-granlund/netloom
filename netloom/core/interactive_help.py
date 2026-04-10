from __future__ import annotations

from pathlib import Path

from netloom.core.help_shared import (
    BUILTIN_MODULE_SUMMARIES,
    BUILTIN_MODULES,
    NETLOOM_BANNER,
    PLUGIN_SELECTION_HINT,
    display_services_for_module,
    module_display_summary,
    resolve_service_entry,
    service_cli_actions,
    service_display_summary,
    visible_catalog_modules,
)
from netloom.core.interactive import (
    credentials_env_path,
    list_plugins,
    list_profiles,
    profiles_env_path,
)

# This module is the fast-path help renderer used by cached interactive help.
# Keep its user-visible output aligned with `netloom.cli.help.render_help`
# for the cached compact-help cases, and rely on parity tests to catch drift.

_DESCRIBE_CACHE_COMMANDS = [
    ("clear", "Remove the cached API catalog"),
    ("update", "Refresh the cached API catalog"),
]
_DESCRIBE_LOAD_COMMANDS = [
    ("list", "List available plugins"),
    ("show", "Show the active plugin"),
]
_DESCRIBE_SERVER_COMMANDS = [
    ("list", "List configured profiles"),
    ("show", "Show the active profile"),
    ("use", "Select the active profile"),
]
_DESCRIBE_ACTION_SUMMARIES = {
    "list": "List matching resources",
    "get": "Get one resource or use --all",
    "add": "Create a resource",
    "update": "Patch an existing resource",
    "replace": "Replace an existing resource",
    "delete": "Delete a resource",
    "copy": "Copy matching resources between profiles",
    "diff": "Compare matching resources between profiles",
}


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
        "sort": "--sort=+FIELD|-FIELD",
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


def _path_tokens(path: str) -> list[str]:
    tokens: list[str] = []
    for segment in path.split("/"):
        if segment.startswith("{") and segment.endswith("}") and len(segment) > 2:
            tokens.append(segment[1:-1])
    return tokens


def _selector_usage_groups_from_paths(paths: list[str]) -> list[str]:
    groups: list[str] = []
    for path in paths:
        tokens = _path_tokens(path)
        if not tokens:
            continue
        groups.append(" ".join(_compact_param_flag(token) for token in tokens))
    return _dedupe_lines(groups)


def _selector_flags_from_paths(paths: list[str]) -> list[str]:
    selectors: list[str] = []
    for path in paths:
        for token in _path_tokens(path):
            selectors.append(_compact_param_flag(token))
    return selectors


def _body_field_names(action_def: dict) -> tuple[list[str], list[str]]:
    body_fields = action_def.get("body_fields") or []
    required_names = list(action_def.get("body_required") or [])
    optional_names: list[str] = []

    for field in body_fields:
        if not isinstance(field, dict):
            continue
        name = field.get("name")
        if not name:
            continue
        if field.get("required"):
            required_names.append(str(name))
        else:
            optional_names.append(str(name))

    required_names = _dedupe_lines(required_names)
    optional_names = [
        name for name in _dedupe_lines(optional_names) if name not in required_names
    ]
    return required_names, optional_names


def _field_usage_suffix(field: dict) -> str:
    details: list[str] = []
    field_type = field.get("type")
    if isinstance(field_type, str) and field_type:
        details.append(field_type)
    enum_values = field.get("enum")
    normalized_type = field_type.strip().lower() if isinstance(field_type, str) else ""
    suppress_enum = normalized_type in {
        "int",
        "integer",
        "long",
        "number",
        "float",
        "double",
    }
    if isinstance(enum_values, list) and enum_values and not suppress_enum:
        rendered = " | ".join(str(item) for item in enum_values if item is not None)
        if rendered:
            details.append(f"[{rendered}]")
    if not details:
        return ""
    return " ".join(details)


def _field_usage_row(field: dict) -> tuple[str, str | None] | None:
    name = field.get("name")
    if not isinstance(name, str) or not name:
        return None
    detail = _field_usage_suffix(field)
    description = field.get("description")
    if isinstance(description, str) and description:
        detail = f"{detail}  {description}" if detail else description
    return name, detail or None


def _body_field_usage_rows(
    action_def: dict, *, required: bool
) -> list[tuple[str, str | None]]:
    rows: list[tuple[str, str | None]] = []
    seen: set[tuple[str, str | None]] = set()
    for field in action_def.get("body_fields") or []:
        if not isinstance(field, dict):
            continue
        if bool(field.get("required")) != required:
            continue
        row = _field_usage_row(field)
        if row is None or row in seen:
            continue
        seen.add(row)
        rows.append(row)
    return rows


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


def _describe_lines(rows: list[tuple[str, str | None]]) -> str:
    visible_rows = [(name, summary) for name, summary in rows if name]
    if not visible_rows:
        return ""

    width = max(len(name) for name, _ in visible_rows) + 2
    lines: list[str] = []
    for name, summary in visible_rows:
        if summary:
            lines.append(f"  {name.ljust(width)} {summary}")
        else:
            lines.append(f"  {name}")
    return "\n".join(lines)


def _format_named_rows(rows: list[tuple[str, str | None]]) -> str:
    return _describe_lines(rows)


def _format_aligned_rows(
    rows: list[tuple[str, str | None]], *, width: int | None = None
) -> list[str]:
    visible_rows = [(name, detail) for name, detail in rows if name]
    if not visible_rows:
        return []

    if width is None:
        width = max(len(name) for name, _ in visible_rows) + 2
    lines: list[str] = []
    for name, detail in visible_rows:
        if detail:
            lines.append(f"  {name.ljust(width)} {detail}")
        else:
            lines.append(f"  {name}")
    return lines


def _service_summary(service_entry: dict) -> str | None:
    summary = service_display_summary(service_entry)
    if summary:
        return summary
    action_map = service_entry.get("actions") or {}
    cli_actions = service_cli_actions(service_entry)
    catalog_actions = [action for action in cli_actions if action in action_map]
    if len(catalog_actions) > 1:
        return "Actions: " + ", ".join(cli_actions)
    for action in catalog_actions:
        summary = (action_map.get(action) or {}).get("summary")
        if isinstance(summary, str) and summary.strip():
            return summary.strip()
    return None


def _action_summary(action: str, action_def: dict | None = None) -> str | None:
    summary = (action_def or {}).get("summary")
    if isinstance(summary, str) and summary.strip():
        return summary.strip()
    return _DESCRIBE_ACTION_SUMMARIES.get(action)


def _describe_builtin_context(module: str) -> str:
    if module == "cache":
        return _describe_lines(_DESCRIBE_CACHE_COMMANDS)
    if module == "load":
        plugin_rows = [(name, "Activate this plugin") for name in list_plugins()]
        return _describe_lines([*_DESCRIBE_LOAD_COMMANDS, *plugin_rows])
    if module == "server":
        return _describe_lines(_DESCRIBE_SERVER_COMMANDS)
    return ""


def describe_context(words: list[str], api_catalog: dict | None = None) -> str:
    modules = visible_catalog_modules(api_catalog)
    positionals = [word for word in words if not word.startswith("-")]

    if not positionals:
        rows = [
            *[(name, BUILTIN_MODULE_SUMMARIES.get(name)) for name in BUILTIN_MODULES],
            *[
                (name, module_display_summary(name))
                for name in sorted(modules.keys())
                if name not in BUILTIN_MODULE_SUMMARIES
            ],
        ]
        return _describe_lines(rows)

    module = positionals[0]
    if module in BUILTIN_MODULE_SUMMARIES:
        if module == "server" and len(positionals) >= 2 and positionals[1] == "use":
            return _describe_lines(
                [(profile, "Configured profile") for profile in list_profiles()]
            )
        return _describe_builtin_context(module)

    if module not in modules:
        rows = [
            *[(name, BUILTIN_MODULE_SUMMARIES.get(name)) for name in BUILTIN_MODULES],
            *[
                (name, module_display_summary(name))
                for name in sorted(modules.keys())
                if name not in BUILTIN_MODULE_SUMMARIES
            ],
        ]
        return _describe_lines(rows)

    services = display_services_for_module(api_catalog, module)
    if len(positionals) == 1:
        return _describe_lines(
            [
                (name, _service_summary(entry))
                for name, entry in sorted(services.items())
            ]
        )

    service = positionals[1]
    if service not in services:
        return _describe_lines(
            [
                (name, _service_summary(entry))
                for name, entry in sorted(services.items())
            ]
        )

    service_entry = resolve_service_entry(api_catalog, module, service)
    if service_entry is None:
        return _describe_lines(
            [
                (name, _service_summary(entry))
                for name, entry in sorted(services.items())
            ]
        )
    action_map = service_entry.get("actions") or {}
    cli_actions = service_cli_actions(service_entry)

    if len(positionals) == 2:
        return _describe_lines(
            [
                (action, _action_summary(action, action_map.get(action)))
                for action in cli_actions
            ]
        )

    action = positionals[2]
    if action == "copy":
        return render_copy_action_help(module, service)
    if action == "diff":
        return render_diff_action_help(module, service)
    if action == "get":
        return render_get_action_help(module, service, service_entry)
    if action == "list" and action in action_map:
        return render_list_action_help(module, service, action_map[action])
    if action in {"add", "update", "replace"} and action in action_map:
        return render_write_action_help(module, service, action, action_map[action])
    if action == "delete" and action in action_map:
        return render_delete_action_help(module, service, action_map[action])

    return _describe_lines(
        [(name, _action_summary(name, action_map.get(name))) for name in cli_actions]
    )


def render_get_action_help(module: str, service: str, service_entry: dict) -> str:
    action_map = service_entry.get("actions") or {}
    get_def = action_map.get("get") or {}
    list_def = action_map.get("list") or {}
    get_paths = get_def.get("paths") or []
    list_params = list_def.get("params") or []

    selector_usage: list[str] = []
    selectors: list[str] = []
    options: list[str] = []

    selector_usage.extend(_selector_usage_groups_from_paths(get_paths))
    selectors.extend(_selector_flags_from_paths(get_paths))
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


def render_write_action_help(
    module: str, service: str, action: str, action_def: dict
) -> str:
    paths = action_def.get("paths") or []
    selectors = _selector_flags_from_paths(paths)
    required_fields, optional_fields = _body_field_names(action_def)
    required_field_rows = _body_field_usage_rows(action_def, required=True)
    optional_field_rows = _body_field_usage_rows(action_def, required=False)
    field_width = None
    all_field_rows = [*required_field_rows, *optional_field_rows]
    if all_field_rows:
        field_width = max(len(name) for name, _ in all_field_rows) + 2
    required_field_lines = _format_aligned_rows(required_field_rows, width=field_width)
    optional_field_lines = _format_aligned_rows(optional_field_rows, width=field_width)

    options = ["--file=PATH", "--console", "--out=PATH"]
    usage = (
        f"  usage: netloom <module> <service> {action} "
        "[--file=PATH | field=value ...] [options]"
    )

    if selectors:
        usage = (
            f"  usage: netloom <module> <service> {action} "
            f"[{' | '.join(selectors)}] [--file=PATH | field=value ...] [options]"
        )

    lines = [f"{action} ({module} {service}):", usage]
    if selectors:
        lines.append("  selectors:")
        lines.extend(f"    - {selector}" for selector in selectors)
    if required_fields:
        lines.append("  required fields:")
        lines.extend(required_field_lines or [f"    - {field}" for field in required_fields])
    if optional_fields:
        lines.append("  optional fields:")
        lines.extend(optional_field_lines or [f"    - {field}" for field in optional_fields])
    lines.append("  options:")
    lines.extend(f"    - {option}" for option in options)
    return "\n".join(lines)


def render_delete_action_help(module: str, service: str, action_def: dict) -> str:
    paths = action_def.get("paths") or []
    selectors = _selector_flags_from_paths(paths)
    usage = "  usage: netloom <module> <service> delete [options]"
    if selectors:
        usage = (
            "  usage: netloom <module> <service> delete "
            f"[{' | '.join(selectors)}] [options]"
        )

    lines = [f"delete ({module} {service}):", usage]
    if selectors:
        lines.append("  selectors:")
        lines.extend(f"    - {selector}" for selector in selectors)
    lines.append("  options:")
    lines.extend(["    - --console", "    - --out=PATH"])
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
    modules = visible_catalog_modules(api_catalog)
    if not modules:
        builtin_modules = _format_named_rows(
            [(name, BUILTIN_MODULE_SUMMARIES.get(name)) for name in BUILTIN_MODULES]
        )
        text = header + usage + "\nAvailable modules:\n" + builtin_modules
        if not has_plugin:
            return text
        return (
            text
            + "\nNo API catalog cache found.\n"
            + "Run `netloom cache update` to build the cache from the active plugin."
        )

    if not module:
        available_modules = _format_named_rows(
            [
                *[
                    (name, BUILTIN_MODULE_SUMMARIES.get(name))
                    for name in BUILTIN_MODULES
                ],
                *[(name, module_display_summary(name)) for name in sorted(modules)],
            ]
        )
        return header + usage + "\nAvailable modules:\n" + available_modules

    if module not in modules:
        available = ", ".join([*BUILTIN_MODULES, *sorted(modules.keys())])
        return header + f"Unknown module '{module}'\nAvailable modules: {available}"

    services = display_services_for_module(api_catalog, module)
    if not service:
        available_services = "\n".join(
            f"  - {name}" for name in sorted(services.keys())
        )
        return (
            header
            + usage
            + f"\nModule: {module}\nAvailable services:\n{available_services}"
        )

    service_entry = resolve_service_entry(api_catalog, module, service)
    if service_entry is None:
        available = ", ".join(sorted(services.keys()))
        return (
            header
            + f"Unknown service '{service}' under module '{module}'. "
            + f"Available services: {available}"
        )
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
    elif action in {"add", "update", "replace"}:
        blocks.append(
            render_write_action_help(module, service, action, action_map[action])
        )
    elif action == "delete":
        blocks.append(render_delete_action_help(module, service, action_map["delete"]))

    return "\n\n".join(blocks)


def _render_usage(
    *,
    module: str | None = None,
    service: str | None = None,
    action: str | None = None,
) -> str:
    if module == "copy":
        module = None

    if module == "cache":
        return (
            "\n".join(
                [
                    "Usage:",
                    "  netloom cache [clear | update]",
                    "  netloom [--help | ?]",
                ]
            )
            + "\n"
        )

    if module == "server":
        return (
            "\n".join(
                [
                    "Usage:",
                    "  netloom server [list | show | use <profile>]",
                    "  netloom [--help | ?]",
                ]
            )
            + "\n"
        )

    if module == "load":
        return (
            "\n".join(
                [
                    "Usage:",
                    "  netloom load [list | show | <plugin>]",
                    "  netloom [--help | ?]",
                ]
            )
            + "\n"
        )

    if module and service and not action:
        return (
            "\n".join(
                [
                    "Usage:",
                    f"  netloom {module} {service} <action> [options] [flags]",
                    (
                        f"  netloom {module} {service} "
                        "{copy|diff} --from=SOURCE --to=TARGET "
                        "[options] [flags]"
                    ),
                    f"  netloom {module} {service} ?",
                ]
            )
            + "\n"
        )

    if module and not service:
        return (
            "\n".join(
                [
                    "Usage:",
                    f"  netloom {module} <service> <action> [options] [flags]",
                    (
                        f"  netloom {module} "
                        "<service> {copy|diff} --from=SOURCE --to=TARGET "
                        "[options] [flags]"
                    ),
                    f"  netloom {module} <service> ?",
                ]
            )
            + "\n"
        )

    usage_lines = [
        "Usage:",
        "  netloom load [list | show | <plugin>]",
        "  netloom server [list | show | use <profile>]",
        "  netloom cache [clear | update]",
        "  netloom <module> <service> <action> [options] [flags]",
        (
            "  netloom <module> <service> {copy|diff} --from=SOURCE --to=TARGET "
            "[options] [flags]"
        ),
        "  netloom [--help | ?]",
        "  netloom --version",
    ]
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
    usage = _render_usage(
        module=module,
        service=args.get("service"),
        action=args.get("action"),
    )

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


__all__ = ["describe_context", "render_help", "service_cli_actions"]
