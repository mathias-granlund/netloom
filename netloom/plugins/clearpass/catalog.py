from __future__ import annotations

import html
import json
import logging
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from netloom.core.config import Settings, load_settings
from netloom.plugins.clearpass.privileges import (
    normalize_effective_privileges,
    service_privilege_rule_index,
)

log = logging.getLogger(__name__)

OAUTH_ENDPOINTS: dict[str, str] = {
    "oauth": "/api/oauth",
    "oauth-me": "/api/oauth/me",
    "oauth-privileges": "/api/oauth/privileges",
}

_PLACEHOLDER_RE = re.compile(r"\{([^}]+)\}")
_LIST_QUERY_PARAMS = ("filter", "sort", "offset", "limit", "calculate_count")
_ACCESS_RANK = {"allowed": 1, "read-only": 2, "full": 3}


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
        match = re.search(r"https?://[^/]+(?P<path>/.*)$", path)
        path = match.group("path") if match else path
    if not path.startswith("/"):
        path = "/" + path
    if path.startswith("/api/") or path == "/api":
        return path.rstrip("/") or "/api"
    return ("/api" + path).rstrip("/") or "/api"


def _module_to_cli(module_name: str) -> str:
    base = re.sub(r"-v\d+$", "", module_name)
    return base.replace("_", "-").lower()


def _is_json_content(text: str) -> bool:
    stripped = text.lstrip()
    return stripped.startswith("{") or stripped.startswith("[")


def _extract_module_doc_paths_from_api_docs_html(html: str) -> list[str]:
    modules = set()
    for match in re.findall(r"(/api-docs/[A-Za-z0-9_-]+-v\d+)", html):
        modules.add(match)
    for match in re.findall(r"(api-docs/[A-Za-z0-9_-]+-v\d+)", html):
        modules.add("/" + match)
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
                    path = item.get("path")
                    if isinstance(path, str):
                        match = re.search(r"(/api-docs/[A-Za-z0-9_-]+-v\d+)", path)
                        if match:
                            out.append(match.group(1))
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


def _clean_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = html.unescape(value).strip()
    if "<" in cleaned and ">" in cleaned:
        # ClearPass docs often embed HTML fragments that we want as plain text.
        cleaned = re.sub(r"(?i)<br\s*/?>", "\n", cleaned)
        cleaned = re.sub(
            r"(?i)<(p|div|tr|li|table|thead|tbody|ul|ol|h\d)\b[^>]*>",
            "\n",
            cleaned,
        )
        cleaned = re.sub(
            r"(?i)</(p|div|tr|li|table|thead|tbody|ul|ol|h\d)>",
            "\n",
            cleaned,
        )
        cleaned = re.sub(r"(?i)</(td|th)>", " | ", cleaned)
        cleaned = re.sub(r"(?i)<[^>]+>", "", cleaned)

    normalized_lines: list[str] = []
    for raw_line in cleaned.splitlines():
        line = " ".join(raw_line.strip().split())
        if not line:
            continue
        line = re.sub(r"\s+\|\s+", " | ", line)
        line = re.sub(r"\s+([,.;:!?])", r"\1", line)
        line = re.sub(
            r'"\s*([^"]*?)\s*"',
            lambda match: f'"{match.group(1).strip()}"',
            line,
        )
        line = re.sub(r"([{\[(:])\s+", r"\1", line)
        line = re.sub(r"\s+([}\]):])", r"\1", line)
        line = re.sub(r"\s+\|$", "", line)
        normalized_lines.append(line)

    cleaned = "\n".join(normalized_lines)
    return cleaned or None


def _dedupe_texts(items: list[str]) -> list[str]:
    return _dedupe_keep_order(
        [item for item in (_clean_text(x) for x in items) if item]
    )


def _type_label_for_schema(schema: dict[str, Any]) -> str:
    if not isinstance(schema, dict):
        return "object"

    ref = schema.get("$ref")
    if isinstance(ref, str) and ref:
        return ref

    schema_type = schema.get("type") or schema.get("dataType")
    if isinstance(schema_type, str):
        if schema_type.lower() == "array":
            items = schema.get("items")
            if isinstance(items, dict):
                return f"array[{_type_label_for_schema(items)}]"
        return schema_type

    nested = schema.get("schema")
    if isinstance(nested, dict):
        return _type_label_for_schema(nested)

    return "object"


def _model_required_names(model: dict[str, Any]) -> set[str]:
    required = {
        str(name)
        for name in model.get("required", []) or []
        if isinstance(name, str) and name
    }
    properties = model.get("properties")
    if isinstance(properties, dict):
        for name, prop in properties.items():
            if isinstance(prop, dict) and prop.get("required") is True:
                required.add(str(name))
    return required


def _example_for_schema(
    schema: dict[str, Any], models: dict[str, Any], seen: set[str] | None = None
):
    if seen is None:
        seen = set()

    if not isinstance(schema, dict):
        return {}

    ref = schema.get("$ref")
    if isinstance(ref, str) and ref:
        return _example_for_model(models, ref, seen=seen)

    nested = schema.get("schema")
    if isinstance(nested, dict):
        return _example_for_schema(nested, models, seen=seen)

    enum = schema.get("enum")
    if isinstance(enum, list) and enum:
        return enum[0]

    default_value = schema.get("defaultValue")
    if default_value not in (None, ""):
        return default_value

    schema_type = str(schema.get("type") or schema.get("dataType") or "").lower()
    if schema_type in {"int", "integer", "long"}:
        return 0
    if schema_type in {"number", "float", "double"}:
        return 0
    if schema_type in {"bool", "boolean"}:
        return True
    if schema_type == "array":
        items = schema.get("items")
        if isinstance(items, dict):
            return [_example_for_schema(items, models, seen=set(seen))]
        return []
    if schema_type == "object":
        properties = schema.get("properties")
        if isinstance(properties, dict):
            return {
                str(name): _example_for_schema(prop, models, seen=set(seen))
                for name, prop in properties.items()
                if isinstance(prop, dict)
            }
        return {}
    return ""


def _example_for_model(
    models: dict[str, Any], model_name: str, seen: set[str] | None = None
):
    if seen is None:
        seen = set()
    if not model_name or model_name in seen:
        return {}
    seen.add(model_name)

    model = models.get(model_name)
    if not isinstance(model, dict):
        return {}

    example: dict[str, Any] = {}

    extends = model.get("extends")
    if isinstance(extends, dict):
        ref = extends.get("$ref")
        if isinstance(ref, str) and ref:
            parent = _example_for_model(models, ref, seen=set(seen))
            if isinstance(parent, dict):
                example.update(parent)

    properties = model.get("properties")
    if isinstance(properties, dict):
        for name, prop in properties.items():
            if isinstance(prop, dict):
                example[str(name)] = _example_for_schema(prop, models, seen=set(seen))

    return example


def _body_fields_for_model(
    models: dict[str, Any], model_name: str, seen: set[str] | None = None
) -> list[dict[str, Any]]:
    if seen is None:
        seen = set()
    if not model_name or model_name in seen:
        return []
    seen.add(model_name)

    model = models.get(model_name)
    if not isinstance(model, dict):
        return []

    fields: list[dict[str, Any]] = []

    extends = model.get("extends")
    if isinstance(extends, dict):
        ref = extends.get("$ref")
        if isinstance(ref, str) and ref:
            fields.extend(_body_fields_for_model(models, ref, seen=set(seen)))

    required = _model_required_names(model)
    properties = model.get("properties")
    if not isinstance(properties, dict):
        return fields

    existing_names = {field["name"] for field in fields}
    for name, prop in properties.items():
        if not isinstance(prop, dict):
            continue
        field_name = str(name)
        if field_name in existing_names:
            continue
        fields.append(
            {
                "name": field_name,
                "type": _type_label_for_schema(prop),
                "required": field_name in required,
                "description": _clean_text(prop.get("description")),
            }
        )
        existing_names.add(field_name)

    return fields


def _extract_response_codes(operation: dict[str, Any]) -> list[str]:
    codes: list[str] = []
    for item in operation.get("responseMessages", []) or []:
        if not isinstance(item, dict):
            continue
        code = item.get("code")
        if code is None:
            continue
        message = _clean_text(item.get("message"))
        codes.append(f"{code} {message}".strip() if message else str(code))
    return _dedupe_texts(codes)


def _extract_response_content_types(
    operation: dict[str, Any], subdoc: dict[str, Any]
) -> list[str]:
    raw_types = operation.get("produces")
    if raw_types is None:
        raw_types = subdoc.get("produces")
    if isinstance(raw_types, str):
        raw_types = [raw_types]
    if not isinstance(raw_types, list):
        return []
    return _dedupe_texts([str(item) for item in raw_types if isinstance(item, str)])


def _extract_body_metadata(
    operation: dict[str, Any], models: dict[str, Any]
) -> tuple[Any | None, list[str], list[dict[str, Any]], str | None]:
    for param in operation.get("parameters", []) or []:
        if not isinstance(param, dict):
            continue
        if str(param.get("paramType") or "").lower() != "body":
            continue

        description = _clean_text(param.get("description"))
        model_name = None
        if isinstance(param.get("type"), str):
            model_name = param["type"]
        elif isinstance(param.get("$ref"), str):
            model_name = param["$ref"]
        elif isinstance(param.get("schema"), dict):
            schema = param["schema"]
            if isinstance(schema.get("$ref"), str):
                model_name = schema["$ref"]

        if model_name:
            fields = _body_fields_for_model(models, model_name)
            required = [field["name"] for field in fields if field.get("required")]
            example = _example_for_model(models, model_name)
            return example or None, required, fields, description

        field_name = str(param.get("name") or "body")
        field = {
            "name": field_name,
            "type": _type_label_for_schema(param),
            "required": bool(param.get("required")),
            "description": description,
        }
        example = {field_name: _example_for_schema(param, models)}
        required = [field_name] if field["required"] else []
        return example, required, [field], description

    return None, [], [], None


def _resolve_model_property_names(
    models: dict[str, Any], model_name: str, seen: set[str] | None = None
) -> list[str]:
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


def _extract_operation_params(
    operation: dict[str, Any], models: dict[str, Any]
) -> list[str]:
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
    return any(param in _LIST_QUERY_PARAMS for param in params)


def _path_segments(path: str) -> list[str]:
    return [
        segment
        for segment in path.strip("/").split("/")
        if segment and segment != "api"
    ]


def _derive_service_key(base_path: str, normalized_path: str) -> str:
    base_segments = _path_segments(base_path)
    path_segments = _path_segments(normalized_path)
    if path_segments[: len(base_segments)] != base_segments:
        fixed = [
            segment
            for segment in path_segments
            if not (segment.startswith("{") and segment.endswith("}"))
        ]
        return fixed[-1] if fixed else "unknown"

    relative = path_segments[len(base_segments) :]
    if not relative:
        return base_segments[-1]

    if len(relative) == 1 and relative[0].startswith("{") and relative[0].endswith("}"):
        return base_segments[-1]
    if (
        len(relative) == 2
        and not relative[0].startswith("{")
        and relative[1].startswith("{")
        and relative[1].endswith("}")
    ):
        return base_segments[-1]

    fixed_suffix = [
        segment
        for segment in relative
        if not (segment.startswith("{") and segment.endswith("}"))
    ]
    if not fixed_suffix:
        return base_segments[-1]
    return base_segments[-1] + "-" + "-".join(fixed_suffix)


def _count_services(modules: dict[str, dict[str, Any]]) -> int:
    return sum(len(services or {}) for services in modules.values())


def _best_access_level(values: list[str]) -> str | None:
    normalized = [value for value in values if value in _ACCESS_RANK]
    if not normalized:
        return None
    return max(normalized, key=lambda value: _ACCESS_RANK[value])


def _lowest_access_level(values: list[str]) -> str | None:
    normalized = [value for value in values if value in _ACCESS_RANK]
    if not normalized:
        return None
    return min(normalized, key=lambda value: _ACCESS_RANK[value])


def _filter_actions_for_access(
    actions: dict[str, Any], access_level: str
) -> dict[str, Any]:
    if access_level == "full":
        return dict(actions)
    allowed_actions = {"list", "get"}
    return {
        action_name: action_def
        for action_name, action_def in actions.items()
        if action_name in allowed_actions
    }


def _filter_catalog_by_effective_privileges(
    catalog: dict[str, Any], effective_privileges: list[dict[str, str]]
) -> tuple[dict[str, Any], dict[str, Any]]:
    modules = catalog.get("modules") or {}
    rules = service_privilege_rule_index()
    effective_access: dict[str, str] = {}
    for item in effective_privileges:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        access = item.get("access")
        if not isinstance(name, str) or not isinstance(access, str):
            continue
        current = effective_access.get(name)
        best = _best_access_level([access, current] if current else [access])
        if best is not None:
            effective_access[name] = best

    if not effective_access:
        return dict(modules), {
            "effective_privileges": effective_privileges,
            "mapping_rule_count": len(rules),
            "filtered_service_count": 0,
            "filtered_services": [],
            "preserved_unmapped_service_count": _count_services(modules),
            "filter_applied": False,
        }

    filtered_modules: dict[str, dict[str, Any]] = {}
    filtered_services: list[dict[str, Any]] = []
    preserved_unmapped_services: list[dict[str, Any]] = []

    for module_name, services in modules.items():
        if not isinstance(services, dict):
            continue
        next_services: dict[str, Any] = {}
        for service_name, service_entry in services.items():
            if not isinstance(service_entry, dict):
                continue
            rule = rules.get((module_name, service_name))
            if rule is None:
                next_services[service_name] = service_entry
                preserved_unmapped_services.append(
                    {"module": module_name, "service": service_name}
                )
                continue

            if getattr(rule, "match", "any") == "all":
                if not all(name in effective_access for name in rule.privileges):
                    filtered_services.append(
                        {"module": module_name, "service": service_name}
                    )
                    continue
                matched_levels = [effective_access[name] for name in rule.privileges]
                access_level = _lowest_access_level(matched_levels)
            else:
                matched_levels = [
                    effective_access[name]
                    for name in rule.privileges
                    if name in effective_access
                ]
                access_level = _best_access_level(matched_levels)
            if access_level is None:
                filtered_services.append({"module": module_name, "service": service_name})
                continue

            actions = service_entry.get("actions") or {}
            filtered_actions = _filter_actions_for_access(actions, access_level)
            if not filtered_actions:
                filtered_services.append({"module": module_name, "service": service_name})
                continue

            next_entry = dict(service_entry)
            next_entry["actions"] = filtered_actions
            next_entry["required_privileges"] = list(rule.privileges)
            next_entry["privilege_match"] = getattr(rule, "match", "any")
            next_entry["granted_access"] = access_level
            next_services[service_name] = next_entry

        if next_services:
            filtered_modules[module_name] = next_services

    metadata = {
        "effective_privileges": effective_privileges,
        "mapping_rule_count": len(rules),
        "filtered_service_count": len(filtered_services),
        "filtered_services": filtered_services,
        "preserved_unmapped_service_count": len(preserved_unmapped_services),
        "filter_applied": True,
    }
    return filtered_modules, metadata


def _format_name_list(items: list[str], *, limit: int = 60) -> str:
    if not items:
        return "<none>"
    if len(items) <= limit:
        return ", ".join(items)
    shown = ", ".join(items[:limit])
    remaining = len(items) - limit
    return f"{shown}, ... (+{remaining} more)"


class ApiEndpointCache:
    def __init__(
        self,
        cp_client,
        *,
        token: str,
        cfg: EndpointCacheConfig | None = None,
        settings: Settings | None = None,
    ):
        self.cp = cp_client
        self.token = token
        self.cfg = cfg or EndpointCacheConfig()
        self.settings = settings or load_settings()
        self.cache_path = self.settings.paths.cache_dir / self.cfg.cache_filename
        self.settings.paths.ensure()

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
            stat = self.cache_path.stat()
        except FileNotFoundError:
            return None

        # A stale cache is treated as a miss so the next read rebuilds it.
        if time.time() - stat.st_mtime > self.cfg.ttl_seconds:
            return None

        try:
            data = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except Exception:
            return None

        if (
            isinstance(data, dict)
            and data.get("version") in {2, 3, 4}
            and isinstance(data.get("modules"), dict)
        ):
            return data
        return None

    def _save(self, api_catalog: dict[str, Any]) -> None:
        tmp = self.cache_path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(api_catalog, indent=2, sort_keys=True), encoding="utf-8"
        )
        os.replace(tmp, self.cache_path)

    def _raw_get_text(self, path: str) -> str:
        url = f"{self.cp.https_prefix}{self.cp.server}{path}"
        headers = {
            "Accept": "application/json, application/vnd.swagger+json, */*",
            "Authorization": f"Bearer {self.token}",
        }
        response = self.cp.session.get(
            url, headers=headers, verify=self.cp.verify_ssl, timeout=self.cp.timeout
        )
        response.raise_for_status()
        return response.text

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

    def _load_effective_privileges(self) -> list[dict[str, str]]:
        try:
            response = self.cp.request(
                OAUTH_ENDPOINTS,
                "GET",
                "oauth-privileges",
                token=self.token,
            )
        except Exception as exc:
            log.warning("[api_catalog] could not fetch effective privileges: %s", exc)
            return []
        if not isinstance(response, dict):
            return []
        privileges = response.get("privileges") or []
        return normalize_effective_privileges(privileges)

    def _merge_action(
        self,
        service_actions: dict[str, Any],
        action_name: str,
        method: str,
        path: str,
        params: list[str],
        *,
        summary: str | None = None,
        notes: list[str] | None = None,
        response_codes: list[str] | None = None,
        response_content_types: list[str] | None = None,
        body_example: Any | None = None,
        body_required: list[str] | None = None,
        body_fields: list[dict[str, Any]] | None = None,
        body_description: str | None = None,
    ) -> None:
        # Multiple docs can describe the same action, so merge instead of overwrite.
        entry = service_actions.setdefault(action_name, {"method": method, "paths": []})
        entry["method"] = method
        entry["paths"] = _dedupe_keep_order(entry.get("paths", []) + [path])
        if params:
            entry["params"] = _dedupe_keep_order(entry.get("params", []) + params)
        if summary and not entry.get("summary"):
            entry["summary"] = summary
        if notes:
            entry["notes"] = _dedupe_texts(entry.get("notes", []) + notes)
        if response_codes:
            entry["response_codes"] = _dedupe_texts(
                entry.get("response_codes", []) + response_codes
            )
        if response_content_types:
            entry["response_content_types"] = _dedupe_texts(
                entry.get("response_content_types", []) + response_content_types
            )
        if body_description and not entry.get("body_description"):
            entry["body_description"] = body_description
        if body_required:
            entry["body_required"] = _dedupe_keep_order(
                entry.get("body_required", []) + body_required
            )
        if body_fields:
            existing_names = {
                field.get("name")
                for field in entry.get("body_fields", [])
                if isinstance(field, dict)
            }
            merged_fields = list(entry.get("body_fields", []))
            for field in body_fields:
                if not isinstance(field, dict):
                    continue
                name = field.get("name")
                if name in existing_names:
                    continue
                merged_fields.append(field)
                existing_names.add(name)
            entry["body_fields"] = merged_fields
        if body_example not in (None, {}, []) and entry.get("body_example") in (
            None,
            {},
            [],
        ):
            entry["body_example"] = body_example

    def _process_swagger_subdoc(
        self, module_services: dict[str, Any], subdoc: dict[str, Any]
    ) -> None:
        apis = subdoc.get("apis")
        if not isinstance(apis, list) or not apis:
            return

        models = subdoc.get("models")
        if not isinstance(models, dict):
            models = {}

        resource_path = subdoc.get("resourcePath") or apis[0].get("path")
        if not isinstance(resource_path, str):
            return
        base_path = _normalize_template_placeholders(
            _ensure_api_prefix(_clean_apigility_route(resource_path))
        )

        raw_entries: list[dict[str, Any]] = []
        for api_item in apis:
            if not isinstance(api_item, dict):
                continue
            raw_path = api_item.get("path")
            if not isinstance(raw_path, str):
                continue
            normalized_path = _normalize_template_placeholders(
                _ensure_api_prefix(raw_path)
            )
            service_key = _derive_service_key(base_path, normalized_path)
            for operation in api_item.get("operations", []) or []:
                if not isinstance(operation, dict):
                    continue
                method = str(operation.get("method") or "").upper().strip()
                if method not in {"GET", "POST", "DELETE", "PATCH", "PUT"}:
                    continue
                params = _extract_operation_params(operation, models)
                body_example, body_required, body_fields, body_description = (
                    _extract_body_metadata(operation, models)
                )
                raw_entries.append(
                    {
                        "service": service_key,
                        "base_path": base_path,
                        "path": normalized_path,
                        "method": method,
                        "params": params,
                        "placeholders": _extract_placeholders(normalized_path),
                        "summary": _clean_text(operation.get("summary")),
                        "notes": _dedupe_texts(
                            [_clean_text(operation.get("notes")) or ""]
                        ),
                        "response_codes": _extract_response_codes(operation),
                        "response_content_types": _extract_response_content_types(
                            operation, subdoc
                        ),
                        "body_example": body_example,
                        "body_required": body_required,
                        "body_fields": body_fields,
                        "body_description": body_description,
                    }
                )

        by_service: dict[str, list[dict[str, Any]]] = {}
        for entry in raw_entries:
            by_service.setdefault(entry["service"], []).append(entry)

        for service_key, entries in by_service.items():
            service = module_services.setdefault(service_key, {"actions": {}})
            actions = service.setdefault("actions", {})
            has_item_style = any(entry["placeholders"] for entry in entries)
            has_post_on_base = any(
                entry["method"] == "POST" and entry["path"] == entry["base_path"]
                for entry in entries
            )

            for entry in entries:
                method = entry["method"]
                params = entry["params"]
                path = entry["path"]
                base_path = entry["base_path"]

                if method == "GET":
                    # Base GET routes with paging/filter params behave like
                    # collection lists.
                    is_base_get = path == base_path
                    if is_base_get and (
                        _has_list_query_params(params)
                        or (
                            not entry["placeholders"]
                            and (has_item_style or has_post_on_base)
                        )
                    ):
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

                self._merge_action(
                    actions,
                    action_name,
                    method,
                    path,
                    params,
                    summary=entry.get("summary"),
                    notes=entry.get("notes"),
                    response_codes=entry.get("response_codes"),
                    response_content_types=entry.get("response_content_types"),
                    body_example=entry.get("body_example"),
                    body_required=entry.get("body_required"),
                    body_fields=entry.get("body_fields"),
                    body_description=entry.get("body_description"),
                )

    def _process_apigility_services(
        self, module_services: dict[str, Any], listing: dict[str, Any]
    ) -> bool:
        services = listing.get("services")
        if not isinstance(services, list) or not services:
            return False

        added = 0
        for service in services:
            if not isinstance(service, dict):
                continue
            route = service.get("route")
            if not isinstance(route, str):
                continue

            base_path = _normalize_template_placeholders(
                _ensure_api_prefix(_clean_apigility_route(route))
            )
            service_key = _camel_to_kebab(
                str(service.get("name") or base_path.strip("/").split("/")[-1])
            )
            service_entry = module_services.setdefault(service_key, {"actions": {}})
            actions = service_entry.setdefault("actions", {})

            collection_methods = {
                str(method).upper()
                for method in service.get("collection_http_methods", [])
                if isinstance(method, str)
            }
            entity_methods = {
                str(method).upper()
                for method in service.get("entity_http_methods", [])
                if isinstance(method, str)
            }
            entity_id = str(service.get("entity_identifier_name") or "id")
            entity_id = _normalize_param_name(entity_id)
            entity_path = base_path + "/{" + entity_id + "}"

            for method in sorted(collection_methods):
                if method == "GET":
                    self._merge_action(
                        actions, "list", "GET", base_path, list(_LIST_QUERY_PARAMS)
                    )
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

    def _log_module_services(
        self, cli_module: str, module_services: dict[str, Any]
    ) -> None:
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
        effective_privileges = self._load_effective_privileges()

        log.info("Discovered %d modules from /api-docs", len(module_doc_paths))
        discovered_modules = [
            _module_to_cli(path.rsplit("/", 1)[-1]) for path in module_doc_paths
        ]
        if discovered_modules:
            log.debug(
                "[api_catalog] modules: %s", _format_name_list(discovered_modules)
            )

        modules: dict[str, dict[str, Any]] = {}

        for module_path in module_doc_paths:
            module_name = module_path.rsplit("/", 1)[-1]
            cli_module = _module_to_cli(module_name)
            module_services = modules.setdefault(cli_module, {})

            # ClearPass exposes both Apigility listings and Swagger subdocuments.
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
                    "[api_catalog] %s: JSON docs contained neither usable "
                    "'services' nor usable 'apis' (keys=%s)",
                    module_name,
                    list(listing.keys())[:30],
                )
                continue

            for item in listing_apis:
                if not isinstance(item, dict):
                    continue
                path = item.get("path")
                if not isinstance(path, str):
                    continue

                if path.startswith("/api/"):
                    sub_path = path
                elif path.startswith(f"/{module_name}/"):
                    sub_path = f"/api/apigility/documentation{path}"
                elif path.startswith("/"):
                    sub_path = f"/api/apigility/documentation/{module_name}{path}"
                else:
                    sub_path = f"/api/apigility/documentation/{module_name}/{path}"

                subdoc = self._load_json(sub_path)
                if not subdoc:
                    continue
                self._process_swagger_subdoc(module_services, subdoc)

            if not module_services:
                log.warning("[api_catalog] %s: no services were extracted", module_name)
                continue

            self._log_module_services(cli_module, module_services)

        filtered_modules, privilege_metadata = _filter_catalog_by_effective_privileges(
            {"modules": modules}, effective_privileges
        )
        if privilege_metadata.get("filter_applied"):
            log.info(
                "Applied privilege filter using %d effective privileges; filtered %d mapped services.",
                len(effective_privileges),
                privilege_metadata.get("filtered_service_count", 0),
            )
        else:
            log.info("Privilege filter not applied; using unfiltered catalog.")

        catalog: dict[str, Any] = {
            "version": 4,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "server": getattr(self.cp, "server", None),
            "modules": filtered_modules,
            "privilege_filter": privilege_metadata,
        }
        log.info("Total modules in cache: %d", len(filtered_modules))
        log.info("Total services in cache: %d", _count_services(filtered_modules))
        return catalog


def get_api_catalog(
    cp_client,
    *,
    token: str,
    force_refresh: bool = False,
    settings: Settings | None = None,
) -> dict[str, Any]:
    return ApiEndpointCache(cp_client, token=token, settings=settings).get_catalog(
        force_refresh=force_refresh
    )


def get_cache_file_path(settings: Settings | None = None) -> Path:
    cfg = EndpointCacheConfig()
    active_settings = settings or load_settings()
    active_settings.paths.ensure()
    return active_settings.paths.cache_dir / cfg.cache_filename


def load_cached_catalog(settings: Settings | None = None) -> dict[str, Any] | None:
    path = get_cache_file_path(settings=settings)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except Exception:
        return None

    if (
        isinstance(data, dict)
        and data.get("version") in {2, 3, 4}
        and isinstance(data.get("modules"), dict)
    ):
        return data
    return None


def clear_api_cache(settings: Settings | None = None) -> bool:
    path = get_cache_file_path(settings=settings)
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        return False
