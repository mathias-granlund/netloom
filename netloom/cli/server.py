from __future__ import annotations

from netloom.core.config import ProfileState, describe_profile_state, set_active_profile
from netloom.core.help import format_path_or_hint


def _format_profile_list(state: ProfileState) -> str:
    if not state.available_profiles:
        return (
            "No server profiles found.\n"
            "Expected profile definitions in "
            f"{format_path_or_hint(state.profiles_path)} and "
            f"{format_path_or_hint(state.credentials_path)}."
        )

    lines = ["Configured server profiles:"]
    for profile in state.available_profiles:
        marker = "*" if profile == state.active_profile else " "
        server = state.profile_servers.get(profile)
        plugin = state.profile_plugins.get(profile)
        suffix = []
        if server:
            suffix.append(server)
        if plugin:
            suffix.append(f"plugin={plugin}")
        suffix_text = f" ({', '.join(suffix)})" if suffix else ""
        lines.append(f"{marker} {profile}{suffix_text}")
    return "\n".join(lines)


def _format_profile_show(state: ProfileState) -> str:
    lines = [
        f"Active profile: {state.active_profile or '<unset>'}",
        f"Active plugin: {state.active_plugin or '<unset>'}",
        f"Server: {state.server or '<unset>'}",
        f"Client ID: {state.client_id or '<unset>'}",
        f"Client secret: {state.client_secret_status}",
        f"Profiles file: {format_path_or_hint(state.profiles_path)}",
        f"Credentials file: {format_path_or_hint(state.credentials_path)}",
    ]
    if state.client_secret_ref:
        lines.insert(5, f"Client secret ref: {state.client_secret_ref}")
    return "\n".join(lines)


def handle_server_command(args: dict) -> bool:
    service = args.get("service")
    action = args.get("action")

    if service == "list" and not action:
        print(_format_profile_list(describe_profile_state()))
        return True

    if service == "show" and not action:
        print(_format_profile_show(describe_profile_state()))
        return True

    if service == "use" and action:
        try:
            set_active_profile(str(action))
        except ValueError as exc:
            print(str(exc))
            return True
        state = describe_profile_state()
        print(f"Active profile set to {state.active_profile}.")
        if state.server:
            print(f"Server: {state.server}")
        if state.active_plugin:
            print(f"Plugin: {state.active_plugin}")
        return True

    return False
