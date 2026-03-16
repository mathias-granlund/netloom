from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from urllib.parse import quote

import requests

from netloom.io.output import sanitize_secrets

log = logging.getLogger(__name__)
_PLACEHOLDER_RE = re.compile(r"\{([^}]+)\}")
_TEXT_CONTENT_MARKERS = (
    "json",
    "xml",
    "javascript",
    "yaml",
    "html",
    "csv",
    "x-www-form-urlencoded",
)


@dataclass(frozen=True)
class ResponseMetadata:
    content_type: str = ""
    filename: str | None = None
    is_binary: bool = False


def _parse_content_type(value: str | None) -> str:
    return (value or "").split(";", 1)[0].strip().lower()


def _is_binary_content_type(content_type: str | None) -> bool:
    parsed = _parse_content_type(content_type)
    if not parsed:
        return False
    if parsed.startswith("text/"):
        return False
    return not any(marker in parsed for marker in _TEXT_CONTENT_MARKERS)


def _filename_from_content_disposition(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', value, re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip().strip('"')


class ClearPassClient:
    def __init__(
        self,
        server: str,
        *,
        https_prefix: str,
        verify_ssl: bool = False,
        timeout: int = 15,
        mask_secrets: bool = True,
    ):
        self.server = server
        self.https_prefix = https_prefix
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.mask_secrets = mask_secrets
        self.session = requests.Session()
        self.session.headers.update({"accept": "application/json"})
        self.last_response_meta = ResponseMetadata()

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
        url = f"{self.https_prefix}{self.server}{path}"
        headers = {"Authorization": f"Bearer {token}"} if token else None
        response = self.session.request(
            method=method.upper(),
            url=url,
            params=params,
            json=json_body,
            headers=headers,
            verify=self.verify_ssl,
            timeout=self.timeout,
        )
        self.last_response_meta = ResponseMetadata(
            content_type=_parse_content_type(response.headers.get("content-type")),
            filename=_filename_from_content_disposition(
                response.headers.get("content-disposition")
            ),
            is_binary=_is_binary_content_type(response.headers.get("content-type")),
        )

        try:
            response.raise_for_status()
        except requests.HTTPError:
            content_type = response.headers.get("content-type", "")
            body = response.text
            if len(body) > 4000:
                body = body[:4000] + "\n... (truncated)"

            request_json = sanitize_secrets(json_body, mask_secrets=self.mask_secrets)

            debug_lines = [
                "HTTP ERROR (details below)",
                f"HTTP {response.status_code} {response.reason}",
                f"URL: {response.url}",
                f"Method: {method.upper()}",
                f"Content-Type: {content_type}",
            ]
            if params:
                debug_lines.append(f"Query params: {params}")
            if request_json is not None:
                debug_lines.append(f"Request JSON: {request_json}")
            debug_lines.append("Response body:")
            debug_lines.extend(body.splitlines() or ["<empty>"])

            log.error(
                "HTTP %s %s - %s", response.status_code, response.reason, response.url
            )
            for line in debug_lines:
                if line.strip():
                    log.debug(line)
            raise

        if response.status_code == 204 or not response.content:
            return None

        if self.last_response_meta.is_binary:
            return response.content

        try:
            return response.json()
        except ValueError:
            return response.text

    def login(self, api_paths: dict, credentials: dict) -> dict:
        payload = {
            "grant_type": credentials["grant_type"],
            "client_id": credentials["client_id"],
            "client_secret": credentials["client_secret"],
        }
        return self.request(api_paths, "POST", "oauth", json_body=payload)

    def _get_service_entry(self, api_catalog: dict, module: str, service: str) -> dict:
        modules = api_catalog.get("modules") or {}
        try:
            return modules[module][service]
        except KeyError as exc:
            raise KeyError(f"Unknown service '{service}' in module '{module}'") from exc

    def _get_action_definition(
        self, api_catalog: dict, module: str, service: str, action: str
    ) -> dict:
        service_entry = self._get_service_entry(api_catalog, module, service)
        actions = service_entry.get("actions") or {}
        try:
            return actions[action]
        except KeyError as exc:
            raise KeyError(
                f"Action '{action}' is not available for {module} {service}"
            ) from exc

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

    def _resolve_action(
        self, api_catalog: dict, module: str, service: str, action: str, args: dict
    ) -> tuple[dict, str, list[str]]:
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
            best_path, placeholders = sorted(
                candidates, key=lambda item: (-len(item[1]), len(item[0]))
            )[0]
            return action_def, self._expand_path_template(best_path, args), placeholders

        if len(paths) == 1 and not self._extract_placeholders(paths[0]):
            return action_def, paths[0], []

        unique_missing: list[str] = []
        for missing in missing_sets:
            text = " ".join(f"--{name}=..." for name in missing)
            if text not in unique_missing:
                unique_missing.append(text)
        raise ValueError(
            f"No matching path for {module} {service} {action}. Provide one of: "
            + " OR ".join(unique_missing)
        )

    def get_action_definition(
        self, api_catalog: dict, module: str, service: str, action: str
    ) -> dict:
        return self._get_action_definition(api_catalog, module, service, action)

    def resolve_action(
        self, api_catalog: dict, module: str, service: str, action: str, args: dict
    ) -> tuple[dict, str, list[str]]:
        return self._resolve_action(api_catalog, module, service, action, args)

    def request_action(
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
        action_def, path, _ = self._resolve_action(
            api_catalog, module, service, action, args
        )
        log.debug(
            "Resolved %s %s %s -> %s %s",
            module,
            service,
            action,
            action_def["method"],
            path,
        )
        return self.request_path(
            action_def["method"], path, token=token, params=params, json_body=json_body
        )

    def list(
        self, api_catalog: dict, token: str, args: dict, *, params: dict | None = None
    ):
        return self.request_action(api_catalog, "list", token, args, params=params)

    def add(self, api_catalog: dict, token: str, args: dict, payload: dict):
        return self.request_action(api_catalog, "add", token, args, json_body=payload)

    def get(
        self, api_catalog: dict, token: str, args: dict, *, params: dict | None = None
    ):
        return self.request_action(api_catalog, "get", token, args, params=params)

    def delete(
        self, api_catalog: dict, token: str, args: dict, *, params: dict | None = None
    ):
        return self.request_action(api_catalog, "delete", token, args, params=params)

    def update(self, api_catalog: dict, token: str, args: dict, payload: dict):
        return self.request_action(
            api_catalog, "update", token, args, json_body=payload
        )

    def replace(self, api_catalog: dict, token: str, args: dict, payload: dict):
        return self.request_action(
            api_catalog, "replace", token, args, json_body=payload
        )
