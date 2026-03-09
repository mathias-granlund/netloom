from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import config
from .logger import AppLogger

log = AppLogger().get_logger(__name__)


# Minimal static endpoints needed to obtain a token (login bootstrap).
OAUTH_ENDPOINTS: dict[str, str] = {
    "oauth": "/api/oauth",
    "oauth-me": "/api/oauth/me",
    "oauth-privileges": "/api/oauth/privileges",
}


_PLACEHOLDER_RE = re.compile(r"\{([^}]+)\}")
_LIST_QUERY_PARAMS = ("filter", "sort", "offset", "limit", "calculate_count")


@dataclass(frozen=True)
class EndpointCacheConfig:
    ttl_seconds: int = 24 * 3600
    cache_filename: str = "api_endpoints_cache.json"


def _camel_to_kebab(name: str) -> str:
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1-\2", name)
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", s1)
    return s2.replace("_", "-").lower()


def _clean_apigility_route(route: str) -> str:
    route = re.sub(r"\[.*?\]", "", route)
    return route.rstrip("/") or "/"


def _ensure_api_prefix(path: str) -> str:
    path = path.strip()
    if not path:
        return "/api"
    if path.startswith("http://") or path.startswith("https://"):
        m = re.search(r"https?://[^/]+(?P<path>/.*)$", path)
        path = m.group("path") if m else path
    if not path.startswith("/"):
        path = "/" + path
    if path.startswith("/api/") or path == "/api":
        return path.rstrip("/") or "/api"
    return ("/api" + path).rstrip("/") or "/api"


def _module_to_cli(module_name: str) -> str:
    base = re.sub(r"-v\d+$", "", module_name)
    return base.replace("_", "-").lower()


def _is_json_content(text: str) -> bool:
    t = text.lstrip()
    return t.startswith("{") or t.startswith("[")


def _extract_module_doc_paths_from_api_docs_html(html: str) -> list[str]:
    modules = set()
    for m in re.findall(r"(/api-docs/[A-Za-z0-9_-]+-v\d+)", html):
        modules.add(m)
    for m in re.findall(r"(api-docs/[A-Za-z0-9_-]+-v\d+)", html):
        modules.add("/" + m)
    return sorted(modules)


def _extract_modules_from_api_docs(text: str) -> list[str]:
    if _is_json_content(text):
        try:
            data = json.loads(text)
        except Exception:
            return []
        out: list[str] = []
        if isinstance(data, dict):
            apis = data.get("apis")
            if isinstance(apis, list):
                for item in apis:
                    if not isinstance(item, dict):
                        continue
                    p = item.get("path")
                    if isinstance(p, str):
                        m = re.search(r"(/api-docs/[A-Za-z0-9_-]+-v\d+)", p)
                        if m:
                            out.append(m.group(1))
        return sorted(set(out))
    return _extract_module_doc_paths_from_api_docs_html(text)


def _extract_placeholders(path: str) -> list[str]:
    return _PLACEHOLDER_RE.findall(path)


def _normalize_template_placeholders(path: str) -> str:
    placeholders = _extract_placeholders(path)
    if len(placeholders) == 1:
        name = placeholders[0]
        if name == "id" or name.endswith("_id"):
            return path.replace("{" + name + "}", "{id}")
    return path


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _normalize_param_name(name: str) -> str:
    return "id" if name == "id" or name.endswith("_id") else name


def _resolve_model_property_names(models: dict[str, Any], model_name: str, seen: set[str] | None = None) -> list[str]:
    if not model_name:
        return []
    if seen is None:
        seen = set()
    if model_name in seen:
        return []
    seen.add(model_name)

    model = models.get(model_name)
    if not isinstance(model, dict):
        return []

    params: list[str] = []

    extends = model.get("extends")
    if isinstance(extends, dict):
        ref = extends.get("$ref")
        if isinstance(ref, str):
            params.extend(_resolve_model_property_names(models, ref, seen=seen))

    properties = model.get("properties")
    if isinstance(properties, dict):
        params.extend(str(name) for name in properties.keys())

    for submodels_key in ("subTypes", "subTypesModels"):
        submodels = model.get(submodels_key)
        if isinstance(submodels, list):
            for sub in submodels:
                if isinstance(sub, str):
                    params.extend(_resolve_model_property_names(models, sub, seen=seen))

    return _dedupe_keep_order(params)


def _extract_operation_params(operation: dict[str, Any], models: dict[str, Any]) -> list[str]:
    params: list[str] = []
    for param in operation.get("parameters", []) or []:
        if not isinstance(param, dict):
            continue
        param_type = str(param.get("paramType") or "").lower()
        name = param.get("name")

        if param_type == "body":
            model_name = None
            if isinstance(param.get("type"), str):
                model_name = param["type"]
            elif isinstance(param.get("$ref"), str):
                model_name = param["$ref"]
            elif isinstance(param.get("schema"), dict):
                schema = param["schema"]
                if isinstance(schema.get("$ref"), str):
                    model_name = schema["$ref"]
                elif isinstance(schema.get("type"), str):
                    model_name = schema["type"]
            if model_name:
                params.extend(_resolve_model_property_names(models, model_name))
            elif isinstance(name, str) and name:
                params.append(name)
            continue

        if param_type == "path":
            continue

        if isinstance(name, str) and name:
            params.append(_normalize_param_name(name))

    return _dedupe_keep_order(params)


def _has_list_query_params(params: list[str]) -> bool:
    return any(p in _LIST_QUERY_PARAMS for p in params)


def _path_segments(path: str) -> list[str]:
    return [seg for seg in path.strip("/").split("/") if seg and seg != "api"]


def _derive_service_key(base_path: str, normalized_path: str) -> str:
    base_segments = _path_segments(base_path)
    path_segments = _path_segments(normalized_path)
    if path_segments[: len(base_segments)] != base_segments:
        fixed = [seg for seg in path_segments if not (seg.startswith("{") and seg.endswith("}"))]
        return fixed[-1] if fixed else "unknown"

    relative = path_segments[len(base_segments) :]
    if not relative:
        return base_segments[-1]

    # Alternate identifier lookup: /resource/name/{name} should stay under the base service.
    if len(relative) == 1 and relative[0].startswith("{") and relative[0].endswith("}"):
        return base_segments[-1]
    if (
        len(relative) == 2
        and not relative[0].startswith("{")
        and relative[1].startswith("{")
        and relative[1].endswith("}")
    ):
        return base_segments[-1]

    fixed_suffix = [seg for seg in relative if not (seg.startswith("{") and seg.endswith("}"))]
    if not fixed_suffix:
        return base_segments[-1]
    return base_segments[-1] + "-" + "-".join(fixed_suffix)


def _count_services(modules: dict[str, dict[str, Any]]) -> int:
    return sum(len(services or {}) for services in modules.values())


def _format_name_list(items: list[str], *, limit: int = 60) -> str:
    if not items:
        return "<none>"
    if len(items) <= limit:
        return ", ".join(items)
    shown = ", ".join(items[:limit])
    remaining = len(items) - limit
    return f"{shown}, ... (+{remaining} more)"


class ApiEndpointCache:
    """
    Cache format (v2):
      {
        "version": 2,
        "generated_at": "...",
        "server": "host:port",
        "modules": {
          "policyelements": {
            "network-device": {
              "actions": {
                "list": {"method": "GET", "paths": ["/api/network-device"], "params": [...]},
                "get": {"method": "GET", "paths": ["/api/network-device/{id}", "/api/network-device/name/{name}"]},
                ...
              }
            }
          }
        }
      }
    """

    def __init__(self, cp_client, *, token: str, cfg: EndpointCacheConfig | None = None):
        self.cp = cp_client
        self.token = token
        self.cfg = cfg or EndpointCacheConfig()

        cache_dir = Path(getattr(config, "CACHE_DIR", Path("./cache")))
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_path = cache_dir / self.cfg.cache_filename

    def get_catalog(self, *, force_refresh: bool = False) -> dict[str, Any]:
        if not force_refresh:
            catalog = self._load_if_fresh()
            if catalog:
                return catalog
        catalog = self._build_catalog_from_clearpass()
        self._save(catalog)
        return catalog

    def _load_if_fresh(self) -> dict[str, Any] | None:
        try:
            st = self.cache_path.stat()
        except FileNotFoundError:
            return None

        age = time.time() - st.st_mtime
        if age > self.cfg.ttl_seconds:
            return None

        try:
            data = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except Exception:
            return None

        if isinstance(data, dict) and data.get("version") == 2 and isinstance(data.get("modules"), dict):
            return data
        return None

    def _save(self, api_catalog: dict[str, Any]) -> None:
        tmp = self.cache_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(api_catalog, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self.cache_path)

    def _raw_get_text(self, path: str) -> str:
        base = self.cp.https_prefix + self.cp.server
        url = base + path
        headers = {
            "Accept": "application/json, application/vnd.swagger+json, */*",
            "Authorization": f"Bearer {self.token}",
        }
        resp = self.cp.session.get(url, headers=headers, verify=self.cp.verify_ssl, timeout=self.cp.timeout)
        resp.raise_for_status()
        return resp.text

    def _load_json(self, path: str) -> dict[str, Any] | None:
        try:
            text = self._raw_get_text(path)
        except Exception as exc:
            log.debug("[api_catalog] fetch %s failed: %s", path, exc)
            return None
        if not _is_json_content(text):
            return None
        try:
            parsed = json.loads(text)
        except Exception as exc:
            log.debug("[api_catalog] parse %s failed: %s", path, exc)
            return None
        return parsed if isinstance(parsed, dict) else None

    def _merge_action(self, service_actions: dict[str, Any], action_name: str, method: str, path: str, params: list[str]) -> None:
        entry = service_actions.setdefault(action_name, {"method": method, "paths": []})
        entry["method"] = method
        entry["paths"] = _dedupe_keep_order(entry.get("paths", []) + [path])
        if params:
            entry["params"] = _dedupe_keep_order(entry.get("params", []) + params)

    def _process_swagger_subdoc(self, module_services: dict[str, Any], subdoc: dict[str, Any]) -> None:
        apis = subdoc.get("apis")
        if not isinstance(apis, list) or not apis:
            return

        models = subdoc.get("models")
        if not isinstance(models, dict):
            models = {}

        resource_path = subdoc.get("resourcePath") or apis[0].get("path")
        if not isinstance(resource_path, str):
            return
        base_path = _normalize_template_placeholders(_ensure_api_prefix(_clean_apigility_route(resource_path)))

        raw_entries: list[dict[str, Any]] = []
        for api_item in apis:
            if not isinstance(api_item, dict):
                continue
            raw_path = api_item.get("path")
            if not isinstance(raw_path, str):
                continue
            normalized_path = _normalize_template_placeholders(_ensure_api_prefix(raw_path))
            service_key = _derive_service_key(base_path, normalized_path)
            for operation in api_item.get("operations", []) or []:
                if not isinstance(operation, dict):
                    continue
                method = str(operation.get("method") or "").upper().strip()
                if method not in {"GET", "POST", "DELETE", "PATCH", "PUT"}:
                    continue
                params = _extract_operation_params(operation, models)
                raw_entries.append(
                    {
                        "service": service_key,
                        "base_path": base_path,
                        "path": normalized_path,
                        "method": method,
                        "params": params,
                        "placeholders": _extract_placeholders(normalized_path),
                    }
                )

        by_service: dict[str, list[dict[str, Any]]] = {}
        for entry in raw_entries:
            by_service.setdefault(entry["service"], []).append(entry)

        for service_key, entries in by_service.items():
            service = module_services.setdefault(service_key, {"actions": {}})
            actions = service.setdefault("actions", {})

            has_item_style = any(entry["placeholders"] for entry in entries)
            has_post_on_base = any(entry["method"] == "POST" and entry["path"] == entry["base_path"] for entry in entries)

            for entry in entries:
                method = entry["method"]
                params = entry["params"]
                path = entry["path"]
                base_path = entry["base_path"]

                if method == "GET":
                    is_base_get = path == base_path
                    if is_base_get and (_has_list_query_params(params) or has_item_style or has_post_on_base):
                        action_name = "list"
                    else:
                        action_name = "get"
                elif method == "POST":
                    action_name = "add"
                elif method == "DELETE":
                    action_name = "delete"
                elif method == "PATCH":
                    action_name = "update"
                else:
                    action_name = "replace"

                self._merge_action(actions, action_name, method, path, params)

    def _process_apigility_services(self, module_services: dict[str, Any], listing: dict[str, Any]) -> bool:
        services = listing.get("services")
        if not isinstance(services, list) or not services:
            return False

        added = 0
        for svc in services:
            if not isinstance(svc, dict):
                continue
            route = svc.get("route")
            if not isinstance(route, str):
                continue

            base_path = _normalize_template_placeholders(_ensure_api_prefix(_clean_apigility_route(route)))
            service_key = _camel_to_kebab(str(svc.get("name") or base_path.strip("/").split("/")[-1]))
            service = module_services.setdefault(service_key, {"actions": {}})
            actions = service.setdefault("actions", {})

            collection_methods = {str(m).upper() for m in svc.get("collection_http_methods", []) if isinstance(m, str)}
            entity_methods = {str(m).upper() for m in svc.get("entity_http_methods", []) if isinstance(m, str)}
            entity_id = str(svc.get("entity_identifier_name") or "id")
            entity_id = _normalize_param_name(entity_id)
            entity_path = base_path + "/{" + entity_id + "}"

            for method in sorted(collection_methods):
                if method == "GET":
                    self._merge_action(actions, "list", "GET", base_path, list(_LIST_QUERY_PARAMS))
                elif method == "POST":
                    self._merge_action(actions, "add", "POST", base_path, [])

            for method in sorted(entity_methods):
                if method == "GET":
                    self._merge_action(actions, "get", "GET", entity_path, [])
                elif method == "DELETE":
                    self._merge_action(actions, "delete", "DELETE", entity_path, [])
                elif method == "PATCH":
                    self._merge_action(actions, "update", "PATCH", entity_path, [])
                elif method == "PUT":
                    self._merge_action(actions, "replace", "PUT", entity_path, [])

            added += 1

        return added > 0


    def _log_module_services(self, cli_module: str, module_services: dict[str, Any]) -> None:
        service_names = sorted(module_services.keys())
        if service_names:
            log.debug(
                "[api_catalog] Loaded module: %s with (%d) services -> %s",
                cli_module,
                len(service_names),
                _format_name_list(service_names),
            )
        else:
            log.info("[api_catalog] %s: 0 services", cli_module)

    def _build_catalog_from_clearpass(self) -> dict[str, Any]:
        api_docs_text = self._raw_get_text("/api-docs")
        module_doc_paths = _extract_modules_from_api_docs(api_docs_text)

        log.info("Discovered %d modules from /api-docs", len(module_doc_paths))
        discovered_modules = [_module_to_cli(path.rsplit("/", 1)[-1]) for path in module_doc_paths]
        if discovered_modules:
            log.debug("[api_catalog] modules: %s", _format_name_list(discovered_modules))

        modules: dict[str, dict[str, Any]] = {}

        for module_path in module_doc_paths:
            module_name = module_path.rsplit("/", 1)[-1]
            cli_module = _module_to_cli(module_name)
            module_services = modules.setdefault(cli_module, {})

            listing = self._load_json(f"/api/apigility/documentation/{module_name}")
            if listing is None:
                for alt in (
                    f"/api/apigility/documentation/{module_name}/swagger",
                    module_path,
                    f"{module_path}.json",
                ):
                    listing = self._load_json(alt)
                    if listing is not None:
                        break

            if listing is None:
                log.warning("[api_catalog] %s: no JSON docs found", module_name)
                continue

            if self._process_apigility_services(module_services, listing):
                self._log_module_services(cli_module, module_services)
                continue

            listing_apis = listing.get("apis")
            if not isinstance(listing_apis, list) or not listing_apis:
                log.warning(
                    "[api_catalog] %s: JSON docs contained neither usable 'services' nor usable 'apis' (keys=%s)",
                    module_name,
                    list(listing.keys())[:30],
                )
                continue

            for item in listing_apis:
                if not isinstance(item, dict):
                    continue
                p = item.get("path")
                if not isinstance(p, str):
                    continue

                if p.startswith("/api/"):
                    sub_path = p
                elif p.startswith(f"/{module_name}/"):
                    sub_path = f"/api/apigility/documentation{p}"
                elif p.startswith("/"):
                    sub_path = f"/api/apigility/documentation/{module_name}{p}"
                else:
                    sub_path = f"/api/apigility/documentation/{module_name}/{p}"

                subdoc = self._load_json(sub_path)
                if not subdoc:
                    continue
                self._process_swagger_subdoc(module_services, subdoc)

            if not module_services:
                log.warning("[api_catalog] %s: no services were extracted", module_name)
                continue

            self._log_module_services(cli_module, module_services)

        catalog: dict[str, Any] = {
            "version": 2,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "server": getattr(self.cp, "server", None),
            "modules": modules,
        }
        total_modules = len(modules)
        total_services = _count_services(modules)
        log.info("Total modules in cache: %d", total_modules)
        log.info("Total services in cache: %d", total_services)
        return catalog


def get_api_catalog(cp_client, *, token: str, force_refresh: bool = False) -> dict[str, Any]:
    return ApiEndpointCache(cp_client, token=token).get_catalog(force_refresh=force_refresh)


def get_cache_file_path() -> Path:
    cache_dir = Path(getattr(config, "CACHE_DIR", Path("./cache")))
    return cache_dir / EndpointCacheConfig().cache_filename


def load_cached_catalog() -> dict[str, Any] | None:
    p = get_cache_file_path()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except Exception:
        return None

    if isinstance(data, dict) and data.get("version") == 2 and isinstance(data.get("modules"), dict):
        return data
    return None


def clear_api_cache() -> bool:
    p = get_cache_file_path()
    try:
        p.unlink()
        return True
    except FileNotFoundError:
        return False
