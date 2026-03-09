import re
from urllib.parse import quote

import requests

from . import config
from .logger import AppLogger

log = AppLogger().get_logger(__name__)

_PLACEHOLDER_RE = re.compile(r"\{([^}]+)\}")
CLI_ACTION_ORDER = ["get", "add", "delete", "update", "replace"]


class ClearPassClient:
    def __init__(self, server: str, *, https_prefix: str, verify_ssl: bool = False, timeout: int = 15):
        self.server = server
        self.https_prefix = https_prefix
        self.verify_ssl = verify_ssl
        self.timeout = timeout

        self.session = requests.Session()
        self.session.headers.update({"accept": "application/json"})

    # ------------------------------------------------------------------
    # Low-level HTTP helpers
    # ------------------------------------------------------------------
    def request(
        self,
        api_paths: dict,
        method: str,
        endpoint_key: str,
        token: str | None = None,
        *,
        path_suffix: str = "",
        params: dict | None = None,
        json_body: dict | None = None,
    ):
        path = api_paths.get(endpoint_key)
        if path is None and ":" in endpoint_key:
            path = api_paths.get(endpoint_key.split(":", 1)[1])
        if path is None:
            raise KeyError(endpoint_key)
        return self.request_path(
            method,
            path + (path_suffix or ""),
            token=token,
            params=params,
            json_body=json_body,
        )

    def request_path(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        params: dict | None = None,
        json_body: dict | None = None,
    ):
        base = self.https_prefix + self.server
        url = base + path

        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        resp = self.session.request(
            method=method.upper(),
            url=url,
            params=params,
            json=json_body,
            headers=headers if headers else None,
            verify=self.verify_ssl,
            timeout=self.timeout,
        )

        try:
            resp.raise_for_status()
        except requests.HTTPError:
            content_type = resp.headers.get("content-type", "")
            body = resp.text
            if len(body) > 4000:
                body = body[:4000] + "\n... (truncated)"

            request_json = json_body
            if isinstance(request_json, dict):
                masked = dict(request_json)
                for key in config.SECRETS:
                    if key in masked:
                        masked[key] = "***"
                request_json = masked

            debug_lines = [
                "HTTP ERROR (details below)",
                f"HTTP {resp.status_code} {resp.reason}",
                f"URL: {resp.url}",
                f"Method: {method.upper()}",
                f"Content-Type: {content_type}",
            ]
            if params:
                debug_lines.append(f"Query params: {params}")
            if request_json is not None:
                debug_lines.append(f"Request JSON: {request_json}")
            debug_lines.append("Response body:")
            debug_lines.extend(body.splitlines() or ["<empty>"])

            log.error("HTTP %s %s - %s", resp.status_code, resp.reason, resp.url)
            for line in debug_lines:
                if line.strip():
                    log.debug(line)
            raise

        if resp.status_code == 204 or not resp.content:
            return None

        try:
            return resp.json()
        except ValueError:
            return resp.text

    def login(self, api_paths: dict, credentials: dict) -> dict:
        payload = {
            "grant_type": credentials["grant_type"],
            "client_id": credentials["client_id"],
            "client_secret": credentials["client_secret"],
        }
        return self.request(api_paths, "POST", "oauth", json_body=payload)

    # ------------------------------------------------------------------
    # Catalog helpers
    # ------------------------------------------------------------------
    def _get_service_entry(self, api_catalog: dict, module: str, service: str) -> dict:
        modules = api_catalog.get("modules") or {}
        try:
            return modules[module][service]
        except KeyError as exc:
            raise KeyError(f"Unknown service '{service}' in module '{module}'") from exc

    def _get_action_definition(self, api_catalog: dict, module: str, service: str, action: str) -> dict:
        service_entry = self._get_service_entry(api_catalog, module, service)
        actions = service_entry.get("actions") or {}
        try:
            return actions[action]
        except KeyError as exc:
            raise KeyError(f"Action '{action}' is not available for {module} {service}") from exc

    def _extract_placeholders(self, path: str) -> list[str]:
        return _PLACEHOLDER_RE.findall(path)

    def _expand_path_template(self, path: str, args: dict) -> str:
        missing: list[str] = []

        def repl(match: re.Match[str]) -> str:
            key = match.group(1)
            if key in args and args[key] not in (None, ""):
                return quote(str(args[key]), safe="")
            missing.append(key)
            return match.group(0)

        expanded = _PLACEHOLDER_RE.sub(repl, path)
        if missing:
            joined = ", ".join(f"--{name}=..." for name in missing)
            raise ValueError(f"Missing required path variables: {joined}")
        return expanded

    def _resolve_action(self, api_catalog: dict, module: str, service: str, action: str, args: dict) -> tuple[dict, str, list[str]]:
        action_def = self._get_action_definition(api_catalog, module, service, action)
        paths = action_def.get("paths") or []
        if not paths:
            raise ValueError(f"No paths are defined for {module} {service} {action}")

        candidates: list[tuple[str, list[str]]] = []
        missing_sets: list[list[str]] = []

        for path in paths:
            placeholders = self._extract_placeholders(path)
            missing = [name for name in placeholders if args.get(name) in (None, "")]
            if not missing:
                candidates.append((path, placeholders))
            else:
                missing_sets.append(missing)

        if candidates:
            best_path, placeholders = sorted(candidates, key=lambda item: (-len(item[1]), len(item[0])))[0]
            return action_def, self._expand_path_template(best_path, args), placeholders

        if len(paths) == 1 and not self._extract_placeholders(paths[0]):
            return action_def, paths[0], []

        unique_missing = []
        for missing in missing_sets:
            text = " ".join(f"--{name}=..." for name in missing)
            if text not in unique_missing:
                unique_missing.append(text)
        raise ValueError(
            f"No matching path for {module} {service} {action}. Provide one of: " + " OR ".join(unique_missing)
        )

    def get_action_definition(self, api_catalog: dict, module: str, service: str, action: str) -> dict:
        return self._get_action_definition(api_catalog, module, service, action)

    def resolve_action(self, api_catalog: dict, module: str, service: str, action: str, args: dict) -> tuple[dict, str, list[str]]:
        return self._resolve_action(api_catalog, module, service, action, args)

    def _request_catalog(
        self,
        api_catalog: dict,
        action: str,
        token: str,
        args: dict,
        *,
        params: dict | None = None,
        json_body: dict | None = None,
    ):
        module = args["module"]
        service = args["service"]
        action_def, path, _ = self._resolve_action(api_catalog, module, service, action, args)
        log.debug("Resolved %s %s %s -> %s %s", module, service, action, action_def["method"], path)
        return self.request_path(action_def["method"], path, token=token, params=params, json_body=json_body)

    # ------------------------------------------------------------------
    # Generic action methods used by commands.py
    # ------------------------------------------------------------------
    def _list(self, api_catalog: dict, token: str, args: dict, *, params: dict | None = None):
        return self._request_catalog(api_catalog, "list", token, args, params=params)

    def _add(self, api_catalog: dict, token: str, args: dict, payload: dict):
        return self._request_catalog(api_catalog, "add", token, args, json_body=payload)

    def _get(self, api_catalog: dict, token: str, args: dict, *, params: dict | None = None):
        return self._request_catalog(api_catalog, "get", token, args, params=params)

    def _delete(self, api_catalog: dict, token: str, args: dict, *, params: dict | None = None):
        return self._request_catalog(api_catalog, "delete", token, args, params=params)

    def _update(self, api_catalog: dict, token: str, args: dict, payload: dict):
        return self._request_catalog(api_catalog, "update", token, args, json_body=payload)

    def _replace(self, api_catalog: dict, token: str, args: dict, payload: dict):
        return self._request_catalog(api_catalog, "replace", token, args, json_body=payload)

    # ------------------------------------------------------------------
    # Help rendering
    # ------------------------------------------------------------------
    def _service_cli_actions(self, service_entry: dict) -> list[str]:
        actions = service_entry.get("actions") or {}
        cli_actions: list[str] = []
        if "get" in actions or "list" in actions:
            cli_actions.append("get")
        for action in CLI_ACTION_ORDER[1:]:
            if action in actions:
                cli_actions.append(action)
        return cli_actions

    def _render_action_block(self, title: str, action_def: dict) -> str:
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

    def _help(self, api_catalog: dict | None = None, args: dict | None = None, *, version: str = "0.0.0") -> str:
        if args is None:
            args = {}

        module = args.get("module")
        service = args.get("service")
        action = args.get("action")

        header = f"ClearPass API tool v{version}\n"
        usage = (
            "Usage:\n"
            "  arapy <module> <service> <action> [options] [flags]\n"
            "\n"
            "Example:\n"
            "  arapy <module> <service> [add | delete | get | list | update | replace] [--key=value] [--log_level=debug|info|warning|error|critical] [--console]\n"
            "  arapy cache [clear | update]\n"
            "  arapy [--help | ?]\n"
            "  arapy --version\n"
            "\n"
            "Common options:\n"
            "  --file=PATH                        Path to file used to modify multiple ClearPass objects with one CLI action.\n"
            "  --out=PATH                         Override output path and filename.\n"
            "  --data_format=json|csv|raw         Output format (default: json).\n"
            "  --csv_fieldnames=a,b,c             Fields and order for CSV output.\n"
            "  --log_level=debug|info|...         Select log level (default: warning).\n"
           "\n"
            "Common flags:\n"
            "  --help                             Print help message (same as -h and ?).\n"
            "  --console                          Also prints output to terminal.\n"
            "\n"
            "Notes:\n"
            "                                     Action 'list' is the same as 'get --all' \n"


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
            return header + f"Unknown module '{module}'. Available modules: {', '.join(sorted(modules.keys()))}"

        services = modules[module]
        if not service:
            available_services = "\n".join(f"  - {name}" for name in sorted(services.keys()))
            return header + usage + f"\nModule: {module}\nAvailable services:\n" + available_services

        if service not in services:
            return header + f"Unknown service '{service}' under module '{module}'. Available services: {', '.join(sorted(services.keys()))}"

        service_entry = services[service]
        cli_actions = self._service_cli_actions(service_entry)
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
            return header + f"Unknown action '{action}' for {module} {service}.\nAvailable actions: {', '.join(shown_actions)}"

        blocks: list[str] = []
        if action == "get":
            if "list" in action_map:
                blocks.append(self._render_action_block("list (used by `get --all`)", action_map["list"]))
            if "get" in action_map:
                blocks.append(self._render_action_block("get", action_map["get"]))
        elif action == "list":
            blocks.append(self._render_action_block("list (alias for `get --all`)", action_map["list"]))
        else:
            blocks.append(self._render_action_block(action, action_map[action]))

        return "\n\n".join(blocks)
