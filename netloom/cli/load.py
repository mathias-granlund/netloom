from __future__ import annotations

from netloom.core.config import describe_profile_state, set_active_plugin
from netloom.core.plugin import has_runtime_plugin, list_plugins


def handle_load_command(args: dict) -> bool:
    service = args.get("service")
    action = args.get("action")

    if service in (None, "") and action in (None, ""):
        print("Usage: netloom load <plugin>")
        return True

    if service == "list" and not action:
        print("Available plugins:")
        for plugin in list_plugins():
            suffix = "" if has_runtime_plugin(plugin) else " (config only)"
            print(f"- {plugin}{suffix}")
        return True

    if service == "show" and not action:
        state = describe_profile_state()
        print(f"Active plugin: {state.active_plugin or '<unset>'}")
        return True

    if action:
        print("Usage: netloom load <plugin>")
        return True

    plugin = str(service)
    if plugin.lower() in {"none", "unset"}:
        set_active_plugin(None)
        print("Active plugin cleared.")
        return True
    available = list_plugins()
    if plugin not in available:
        print(f"Unknown plugin '{plugin}'. Available plugins: {', '.join(available)}")
        return True
    if not has_runtime_plugin(plugin):
        print(
            f"Plugin '{plugin}' has configuration files but no runtime "
            "implementation is installed."
        )
        return True

    set_active_plugin(plugin)
    print(f"Active plugin set to {plugin}.")
    return True
