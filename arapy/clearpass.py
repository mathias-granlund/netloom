#clearpass.py

#---- standard libs

from doctest import debug
from tabnanny import verbose

from arapy import config
from .logger import AppLogger
log = AppLogger().get_logger(__name__)

import requests

class ClearPassClient:
    def __init__(self, server: str, *, https_prefix: str, verify_ssl: bool = False, timeout: int = 15):
        self.server = server
        self.https_prefix = https_prefix
        self.verify_ssl = verify_ssl
        self.timeout = timeout

        self.session = requests.Session()
        self.session.headers.update({"accept": "application/json"})

    def request(self, api_paths: dict, method: str, endpoint_key: str, token: str | None = None,
                *, path_suffix: str = "", params: dict | None = None, json_body: dict | None = None):
        base = self.https_prefix + self.server
        path = api_paths[endpoint_key]
        url = base + path + (path_suffix or "")

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
        except requests.HTTPError as e:
            content_type = resp.headers.get("content-type", "")
            body = resp.text
            if len(body) > 4000:
                body = body[:4000] + "\n... (truncated)"

            # Mask secrets in request JSON (if any)
            request_json = json_body
            if isinstance(request_json, dict):
                masked = dict(request_json)
                for k in config.SECRETS:
                    if k in masked:
                        masked[k] = "***"
                request_json = masked

            # One-line-per-record debug output
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

            # Keep response body readable; split into lines so each becomes its own log record
            debug_lines.append("Response body:")
            if body:
                debug_lines.extend(body.splitlines())
            else:
                debug_lines.append("<empty>")

            # Summary at ERROR (one line), full dump at DEBUG (many lines)
            log.error("HTTP %s %s - %s", resp.status_code, resp.reason, resp.url)
            for line in debug_lines:
                if line.strip():
                    log.debug(line)

            # Re-raise original exception (keeps traceback clean)
            raise

        # No content responses (204) and responses with empty body will return None to avoid JSON parsing errors.
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

# The following methods are generic handlers for the list, get, add and delete actions.
# They can be used for any endpoint that follows the standard REST patterns, and can be called from the command handlers in commands.py.
# This way we can avoid writing separate methods for each endpoint when the logic is the same.

#---- Generic method for [module] [service] [action]=list
    def _list(self, api_paths: dict, token: str, args:dict, *, offset: int = 0, limit: int = 25, sort: str = "+id", filter: str | None = None, calculate_count: bool | None = None):
        params = {
            "offset": offset,
            "limit": limit,
            "sort": sort,
        }
        if calculate_count is not None:
            params["calculate_count"] = calculate_count
        if filter is not None:
            params["filter"] = filter

        log.info(f"Listing {args['service']} with filter='{filter}', sort='{sort}', offset={offset}, limit={limit}, calculate_count={calculate_count}")

        return self.request(api_paths, "GET", args["service"], token=token, params=params)

#---- Generic method for [module] [service] [action]=add
    def _add(self, api_paths: dict, token: str, args:dict, payload: dict):

        log.info(f"Adding {args['service']} name: {payload.get('name')}")
        log.debug(f"Adding {args['service']} with payload: {payload}")

        return self.request(api_paths, "POST", args["service"], token=token, json_body=payload)

#---- Generic method for [module] [service] [action]=get
    def _get(self, api_paths: dict, token: str, args, entity):

        log.info(f"Fetching {args['service']}: {entity}")

        return self.request(api_paths, "GET", args["service"], token=token, path_suffix=f"/{entity}")

#---- Generic method for [module] [service] [action]=delete
    def _delete(self, api_paths: dict, token: str, args, entity):

        log.info(f"Deleting {args['service']}: {entity}")

        return self.request(api_paths, "DELETE", args["service"], token=token, path_suffix=f"/{entity}")