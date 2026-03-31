from __future__ import annotations

from netloom.core.help_shared import (
    display_services_for_module,
    resolve_service_entry,
    service_cli_actions,
)


def list_profiles() -> list[str]:
    from netloom.core.interactive import list_profiles as impl

    return impl()


def list_plugins() -> list[str]:
    from netloom.core.interactive import list_plugins as impl

    return impl()


def completion_candidates(words: list[str], catalog: dict | None) -> list[str]:
    modules = (catalog or {}).get("modules") or {}

    current = ""
    for word in words:
        if word.startswith("--_cur="):
            current = word.split("=", 1)[1]

    positionals = [word for word in words if not word.startswith("-")]

    if len(positionals) == 0:
        return ["cache", "load", "server", *sorted(modules.keys())]

    module = positionals[0]
    if module == "cache":
        if len(positionals) == 1:
            return ["clear", "update"]
        return []

    if module == "load":
        if len(positionals) == 1:
            return ["list", "show", *list_plugins()]
        return list_plugins()

    if module == "server":
        if len(positionals) == 1:
            return ["list", "show", "use"]
        service = positionals[1]
        if service == "use" and len(positionals) == 2:
            return list_profiles()
        if service in {"list", "show"}:
            return []
        return ["list", "show", "use"]

    if module not in modules:
        return ["cache", "load", "server", *sorted(modules.keys())]

    services = display_services_for_module(catalog, module)
    if len(positionals) == 1 or (len(positionals) == 2 and current != ""):
        return sorted(services.keys())

    service = positionals[1]
    service_entry = resolve_service_entry(catalog, module, service)
    if not isinstance(service_entry, dict):
        return sorted(services.keys())

    if len(positionals) == 2:
        return service_cli_actions(service_entry)

    return []


def print_completions(words: list[str], catalog: dict | None) -> None:
    print("\n".join(completion_candidates(words, catalog)))
