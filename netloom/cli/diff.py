from __future__ import annotations

import copy
import json
from collections import defaultdict
from typing import Any

from netloom.cli.copy import (
    VALID_MATCH_MODES,
    _copy_item_label,
    _default_artifact_path,
    _extract_items,
    _fetch_source_items,
    _fetch_target_by_id,
    _fetch_target_by_name,
    _has_action,
    _load_catalog,
    _service_args,
    _validate_compare_args,
)
from netloom.core.config import Settings, load_settings_for_profile
from netloom.core.pagination import fetch_all_list_results
from netloom.io.output import should_mask_secrets, write_value_to_file

_MISSING = object()
_SCALAR_TYPES = (str, int, float, bool, type(None))
_DEFAULT_DETAIL_LIMIT = 10
_DEFAULT_VALUE_LIMIT = 5


def _normalize_diff_item(plugin, module: str, service: str, item: Any) -> Any:
    normalizer = getattr(plugin, "normalize_diff_item", None)
    if callable(normalizer):
        return normalizer(module, service, item)
    return item


def _parse_path(path: str) -> tuple[str | int, ...]:
    tokens: list[str | int] = []
    index = 0
    text = path.strip()
    if not text:
        raise ValueError("field paths must not be empty")

    while index < len(text):
        if text[index] == ".":
            index += 1
            if index >= len(text):
                raise ValueError(f"invalid field path: {path}")
            continue

        if text[index] == "[":
            end = text.find("]", index)
            if end <= index + 1:
                raise ValueError(f"invalid field path: {path}")
            token = text[index + 1 : end]
            if not token.isdigit():
                raise ValueError(f"invalid field path: {path}")
            tokens.append(int(token))
            index = end + 1
            continue

        end = index
        while end < len(text) and text[end] not in ".[":
            end += 1
        token = text[index:end].strip()
        if not token:
            raise ValueError(f"invalid field path: {path}")
        tokens.append(token)
        index = end

    return tuple(tokens)


def _parse_field_paths(raw: Any, *, flag_name: str) -> list[tuple[str | int, ...]]:
    if raw in (None, ""):
        return []
    paths: list[tuple[str | int, ...]] = []
    for item in str(raw).split(","):
        text = item.strip()
        if not text:
            raise ValueError(f"{flag_name} must not include empty field paths")
        paths.append(_parse_path(text))
    return paths


def _path_to_string(path: tuple[str | int, ...]) -> str:
    if not path:
        return "value"
    rendered = ""
    for token in path:
        if isinstance(token, int):
            rendered += f"[{token}]"
        else:
            rendered = f"{rendered}.{token}" if rendered else token
    return rendered


def _is_scalar(value: Any) -> bool:
    return isinstance(value, _SCALAR_TYPES)


def _canonical_list_signature(items: list[Any]) -> list[str] | None:
    try:
        return sorted(
            json.dumps(item, sort_keys=True, ensure_ascii=False) for item in items
        )
    except TypeError:
        return None


def _select_paths(value: Any, paths: list[tuple[str | int, ...]]) -> Any:
    if any(not path for path in paths):
        return copy.deepcopy(value)

    if isinstance(value, dict):
        grouped: dict[str, list[tuple[str | int, ...]]] = defaultdict(list)
        for path in paths:
            head = path[0]
            if isinstance(head, str):
                grouped[head].append(path[1:])
        if not grouped:
            return _MISSING
        selected: dict[str, Any] = {}
        for key, child_paths in grouped.items():
            if key not in value:
                continue
            child_value = _select_paths(value[key], child_paths)
            if child_value is not _MISSING:
                selected[key] = child_value
        return selected if selected else _MISSING

    if isinstance(value, list):
        grouped: dict[int, list[tuple[str | int, ...]]] = defaultdict(list)
        for path in paths:
            head = path[0]
            if isinstance(head, int):
                grouped[head].append(path[1:])
        if not grouped:
            return _MISSING
        selected_list: list[Any] = []
        for index in sorted(grouped):
            if 0 <= index < len(value):
                child_value = _select_paths(value[index], grouped[index])
                if child_value is not _MISSING:
                    selected_list.append(child_value)
        return selected_list if selected_list else _MISSING

    return _MISSING


def _remove_path(value: Any, path: tuple[str | int, ...]) -> Any:
    if value is _MISSING:
        return _MISSING
    if not path:
        return _MISSING

    head, *tail = path
    if isinstance(value, dict) and isinstance(head, str):
        updated = copy.deepcopy(value)
        if head not in updated:
            return updated
        if not tail:
            updated.pop(head, None)
            return updated
        child = _remove_path(updated[head], tuple(tail))
        if child is _MISSING:
            updated.pop(head, None)
        else:
            updated[head] = child
        return updated

    if isinstance(value, list) and isinstance(head, int):
        updated = copy.deepcopy(value)
        if not (0 <= head < len(updated)):
            return updated
        if not tail:
            updated.pop(head)
            return updated
        child = _remove_path(updated[head], tuple(tail))
        if child is _MISSING:
            updated.pop(head)
        else:
            updated[head] = child
        return updated

    return copy.deepcopy(value)


def _apply_field_filters(
    value: Any,
    include_paths: list[tuple[str | int, ...]],
    ignore_paths: list[tuple[str | int, ...]],
) -> Any:
    filtered = copy.deepcopy(value)
    if include_paths:
        filtered = _select_paths(filtered, include_paths)
        if filtered is _MISSING:
            return None
    for path in ignore_paths:
        filtered = _remove_path(filtered, path)
        if filtered is _MISSING:
            return None
    return filtered


def _collect_changed_values(
    source: Any,
    target: Any,
    *,
    prefix: tuple[str | int, ...] = (),
) -> list[tuple[str, Any, Any]]:
    if source == target:
        return []

    if isinstance(source, dict) and isinstance(target, dict):
        changes: list[tuple[str, Any, Any]] = []
        for key in sorted(set(source.keys()) | set(target.keys()), key=str):
            next_prefix = (*prefix, key)
            if key not in source or key not in target:
                changes.append(
                    (_path_to_string(next_prefix), source.get(key), target.get(key))
                )
                continue
            changes.extend(
                _collect_changed_values(source[key], target[key], prefix=next_prefix)
            )
        return changes

    if isinstance(source, list) and isinstance(target, list):
        if source == target:
            return []
        source_signature = _canonical_list_signature(source)
        target_signature = _canonical_list_signature(target)
        if source_signature is not None and source_signature == target_signature:
            return []
        if all(_is_scalar(item) for item in source + target):
            changes: list[tuple[str, Any, Any]] = []
            for index in range(max(len(source), len(target))):
                next_prefix = (*prefix, index)
                left = source[index] if index < len(source) else _MISSING
                right = target[index] if index < len(target) else _MISSING
                if left == right:
                    continue
                changes.append(
                    (
                        _path_to_string(next_prefix),
                        None if left is _MISSING else left,
                        None if right is _MISSING else right,
                    )
                )
            return changes
        return [(_path_to_string(prefix), source, target)]

    return [(_path_to_string(prefix), source, target)]


def _format_preview(value: Any, *, limit: int = 120) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3]}..."


def _match_key(
    item: dict[str, Any],
    match_mode: str,
) -> tuple[tuple[str, str] | None, str | None]:
    if match_mode not in VALID_MATCH_MODES:
        raise ValueError("--match-by must be one of: auto, name, id")

    if match_mode in {"auto", "name"} and item.get("name") not in (None, ""):
        return ("name", str(item["name"])), "name"

    if match_mode in {"auto", "id"} and item.get("id") not in (None, ""):
        return ("id", str(item["id"])), "id"

    return None, None


def _candidate_refs(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": item.get("id"),
            "name": item.get("name"),
            "label": _copy_item_label(item),
        }
        for item in items
    ]


def _build_match_groups(
    items: list[dict[str, Any]], match_mode: str
) -> tuple[dict[tuple[str, str], dict[str, Any]], list[dict[str, Any]]]:
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    no_key_items: list[dict[str, Any]] = []
    for item in items:
        key, resolved_match = _match_key(item, match_mode)
        if key is None:
            no_key_items.append({"item": item, "match_by": resolved_match})
            continue
        bucket = groups.setdefault(key, {"items": [], "match_by": resolved_match})
        bucket["items"].append(item)
    return groups, no_key_items


def _target_name_candidates(
    cp,
    token: str,
    api_catalog: dict,
    module: str,
    service: str,
    name: str,
) -> list[dict[str, Any]]:
    if _has_action(api_catalog, module, service, "list"):
        list_args = _service_args(
            module,
            service,
            "list",
            filter=json.dumps({"name": name}),
        )
        result = fetch_all_list_results(cp, token, api_catalog, list_args)
        return [item for item in _extract_items(result) if item.get("name") == name]
    match = _fetch_target_by_name(cp, token, api_catalog, module, service, name)
    return [match] if isinstance(match, dict) else []


def _resolve_match_detail(
    cp,
    token: str,
    api_catalog: dict,
    module: str,
    service: str,
    item: dict[str, Any],
    match_mode: str,
) -> dict[str, Any]:
    label = _copy_item_label(item)
    if match_mode in {"auto", "name"} and item.get("name") not in (None, ""):
        name_candidates = _target_name_candidates(
            cp, token, api_catalog, module, service, str(item["name"])
        )
        if len(name_candidates) > 1:
            return {
                "status": "ambiguous_match",
                "match_by": "name",
                "target_match": None,
                "target_candidates": name_candidates,
                "match_reason": f"multiple target objects matched by name for {label}",
            }
        if len(name_candidates) == 1:
            return {
                "status": "matched",
                "match_by": "name",
                "target_match": name_candidates[0],
                "target_candidates": name_candidates,
                "match_reason": "matched target by name",
            }
        if match_mode == "name":
            return {
                "status": "unmatched",
                "match_by": "name",
                "target_match": None,
                "target_candidates": [],
                "match_reason": f"no target object matched by name for {label}",
            }

    if match_mode in {"auto", "id"} and item.get("id") not in (None, ""):
        id_candidate = _fetch_target_by_id(
            cp, token, api_catalog, module, service, item.get("id")
        )
        candidates = [id_candidate] if isinstance(id_candidate, dict) else []
        if candidates:
            return {
                "status": "matched",
                "match_by": "id",
                "target_match": candidates[0],
                "target_candidates": candidates,
                "match_reason": "matched target by id",
            }
        return {
            "status": "unmatched",
            "match_by": "id" if match_mode == "id" else None,
            "target_match": None,
            "target_candidates": [],
            "match_reason": f"no target object matched by id for {label}",
        }

    return {
        "status": "unmatched",
        "match_by": None,
        "target_match": None,
        "target_candidates": [],
        "match_reason": f"no usable match key for {label}",
    }


def _diff_entry(
    *,
    label: str,
    match_by_requested: str,
    match_by_used: str | None,
    status: str,
    source_item: dict[str, Any] | None,
    target_item: dict[str, Any] | None,
    source_normalized: Any | None = None,
    target_normalized: Any | None = None,
    changed: list[tuple[str, Any, Any]] | None = None,
    match_reason: str | None = None,
    target_candidates: list[dict[str, Any]] | None = None,
    source_candidates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    entry = {
        "label": label,
        "status": status,
        "match_by": match_by_used,
        "match_by_requested": match_by_requested,
        "source_id": source_item.get("id") if isinstance(source_item, dict) else None,
        "source_name": (
            source_item.get("name") if isinstance(source_item, dict) else None
        ),
        "target_id": target_item.get("id") if isinstance(target_item, dict) else None,
        "target_name": (
            target_item.get("name") if isinstance(target_item, dict) else None
        ),
        "match_reason": match_reason,
    }

    if source_candidates is not None:
        entry["source_candidate_count"] = len(source_candidates)
        entry["source_candidates"] = _candidate_refs(source_candidates)
    if target_candidates is not None:
        entry["target_candidate_count"] = len(target_candidates)
        entry["target_candidates"] = _candidate_refs(target_candidates)

    if status == "different":
        changed = changed or []
        entry["changed_fields"] = [path for path, _, _ in changed]
        entry["changed_values"] = {
            path: {"source": source_value, "target": target_value}
            for path, source_value, target_value in changed
        }
        entry["source"] = source_normalized
        entry["target"] = target_normalized
    elif status in {"only_in_source", "ambiguous_match"}:
        entry["source"] = source_normalized
        if target_normalized is not None:
            entry["target"] = target_normalized
    elif status == "only_in_target":
        entry["target"] = target_normalized

    return entry


def _print_item_list(title: str, items: list[dict[str, Any]]) -> None:
    if not items:
        return
    print(title)
    hidden = max(len(items) - _DEFAULT_DETAIL_LIMIT, 0)
    for item in items[:_DEFAULT_DETAIL_LIMIT]:
        print(f"- {item['label']}")
    if hidden:
        print(f"  ... {hidden} more")


def _print_differences(items: list[dict[str, Any]]) -> None:
    if not items:
        return
    print("Different:")
    hidden_items = max(len(items) - _DEFAULT_DETAIL_LIMIT, 0)
    for item in items[:_DEFAULT_DETAIL_LIMIT]:
        print(f"- {item['label']}")
        changed_values = item.get("changed_values") or {}
        changed_paths = list(item.get("changed_fields") or [])
        hidden_values = max(len(changed_paths) - _DEFAULT_VALUE_LIMIT, 0)
        for path in changed_paths[:_DEFAULT_VALUE_LIMIT]:
            values = changed_values.get(path) or {}
            print(
                f"  {path}: {_format_preview(values.get('source'))} -> "
                f"{_format_preview(values.get('target'))}"
            )
        if hidden_values:
            print(f"  ... {hidden_values} more changed fields")
    if hidden_items:
        print(f"  ... {hidden_items} more changed items")


def _print_ambiguous(items: list[dict[str, Any]]) -> None:
    if not items:
        return
    print("Ambiguous matches:")
    hidden = max(len(items) - _DEFAULT_DETAIL_LIMIT, 0)
    for item in items[:_DEFAULT_DETAIL_LIMIT]:
        print(f"- {item['label']}")
        reason = item.get("match_reason")
        if reason:
            print(f"  reason: {reason}")
        candidates = item.get("target_candidates") or []
        if candidates:
            labels = ", ".join(
                candidate.get("label") or "<unknown>" for candidate in candidates[:5]
            )
            print(f"  target candidates: {labels}")
    if hidden:
        print(f"  ... {hidden} more")


def _emit_diff_summary(report: dict[str, Any]) -> None:
    summary = report["summary"]
    print("Diff completed")
    print(f"Source profile: {report['source_profile']}")
    print(f"Target profile: {report['target_profile']}")
    print(f"Service: {report['module']} {report['service']}")
    print(f"Match by: {report['match_by']}")
    print(f"Compared: {summary['compared']}")
    print(f"Only in source: {summary['only_in_source']}")
    print(f"Only in target: {summary['only_in_target']}")
    print(f"Different: {summary['different']}")
    print(f"Same: {summary['same']}")
    print(f"Ambiguous matches: {summary['ambiguous_match']}")

    _print_differences(
        [item for item in report["items"] if item["status"] == "different"]
    )
    _print_item_list(
        "Only in source:",
        [item for item in report["items"] if item["status"] == "only_in_source"],
    )
    _print_item_list(
        "Only in target:",
        [item for item in report["items"] if item["status"] == "only_in_target"],
    )
    _print_ambiguous(
        [item for item in report["items"] if item["status"] == "ambiguous_match"]
    )
    print(f"Report: {report['artifacts']['report']}")


def handle_diff_command(
    args: dict[str, Any],
    *,
    settings: Settings | None,
    plugin,
) -> dict[str, Any]:
    _validate_compare_args(
        args,
        module_key="module",
        service_key="service",
        operation_name="diff",
    )

    module = str(args["module"])
    service = str(args["service"])
    source_profile = str(args["from"])
    target_profile = str(args["to"])
    match_by = str(args.get("match_by", "auto"))
    include_paths = _parse_field_paths(args.get("fields"), flag_name="--fields")
    ignore_paths = _parse_field_paths(
        args.get("ignore_fields"), flag_name="--ignore-fields"
    )

    source_settings = load_settings_for_profile(source_profile)
    target_settings = load_settings_for_profile(target_profile)
    active_settings = settings or target_settings
    mask_secrets = should_mask_secrets(args, active_settings)
    catalog_view = str(args.get("catalog_view") or "visible").strip().lower()
    if catalog_view not in {"visible", "full"}:
        catalog_view = "visible"

    source_cp = plugin.build_client(source_settings, mask_secrets=mask_secrets)
    source_token = plugin.resolve_auth_token(source_cp, source_settings)
    source_catalog = _load_catalog(
        plugin,
        source_cp,
        source_token,
        source_settings,
        catalog_view=catalog_view,
    )

    target_cp = plugin.build_client(target_settings, mask_secrets=mask_secrets)
    target_token = plugin.resolve_auth_token(target_cp, target_settings)
    target_catalog = _load_catalog(
        plugin,
        target_cp,
        target_token,
        target_settings,
        catalog_view=catalog_view,
    )

    source_items = _fetch_source_items(
        source_cp, source_token, source_catalog, module, service, args
    )
    if not source_items:
        raise ValueError("No source objects matched the requested selector")

    diff_items: list[dict[str, Any]] = []
    symmetric_scope = bool(args.get("all")) or bool(args.get("filter"))

    if symmetric_scope:
        target_items = _fetch_source_items(
            target_cp, target_token, target_catalog, module, service, args
        )
        source_groups, source_no_key = _build_match_groups(source_items, match_by)
        target_groups, target_no_key = _build_match_groups(target_items, match_by)

        for key in sorted(set(source_groups.keys()) | set(target_groups.keys())):
            source_group = source_groups.get(key, {"items": [], "match_by": key[0]})
            target_group = target_groups.get(key, {"items": [], "match_by": key[0]})
            source_bucket = source_group["items"]
            target_bucket = target_group["items"]
            resolved_match = source_group.get("match_by") or target_group.get(
                "match_by"
            )
            label = str(key[1])

            if len(source_bucket) > 1 or len(target_bucket) > 1:
                if len(source_bucket) > 1 and len(target_bucket) > 1:
                    reason = (
                        f"multiple source and target objects share {resolved_match} "
                        f"'{label}'"
                    )
                elif len(source_bucket) > 1:
                    reason = f"multiple source objects share {resolved_match} '{label}'"
                else:
                    reason = f"multiple target objects share {resolved_match} '{label}'"
                diff_items.append(
                    _diff_entry(
                        label=label,
                        match_by_requested=match_by,
                        match_by_used=resolved_match,
                        status="ambiguous_match",
                        source_item=source_bucket[0] if source_bucket else None,
                        target_item=target_bucket[0] if target_bucket else None,
                        source_normalized=(
                            _apply_field_filters(
                                _normalize_diff_item(
                                    plugin, module, service, source_bucket[0]
                                ),
                                include_paths,
                                ignore_paths,
                            )
                            if source_bucket
                            else None
                        ),
                        target_normalized=(
                            _apply_field_filters(
                                _normalize_diff_item(
                                    plugin, module, service, target_bucket[0]
                                ),
                                include_paths,
                                ignore_paths,
                            )
                            if target_bucket
                            else None
                        ),
                        match_reason=reason,
                        source_candidates=source_bucket or None,
                        target_candidates=target_bucket or None,
                    )
                )
                continue

            if source_bucket and target_bucket:
                source_item = source_bucket[0]
                target_item = target_bucket[0]
                source_normalized = _apply_field_filters(
                    _normalize_diff_item(plugin, module, service, source_item),
                    include_paths,
                    ignore_paths,
                )
                target_normalized = _apply_field_filters(
                    _normalize_diff_item(plugin, module, service, target_item),
                    include_paths,
                    ignore_paths,
                )
                changed = _collect_changed_values(source_normalized, target_normalized)
                status = "same" if not changed else "different"
                diff_items.append(
                    _diff_entry(
                        label=_copy_item_label(source_item),
                        match_by_requested=match_by,
                        match_by_used=resolved_match,
                        status=status,
                        source_item=source_item,
                        target_item=target_item,
                        source_normalized=source_normalized,
                        target_normalized=target_normalized,
                        changed=changed,
                        match_reason=(
                            f"matched by {resolved_match}" if resolved_match else None
                        ),
                    )
                )
                continue

            if source_bucket:
                source_item = source_bucket[0]
                diff_items.append(
                    _diff_entry(
                        label=_copy_item_label(source_item),
                        match_by_requested=match_by,
                        match_by_used=resolved_match,
                        status="only_in_source",
                        source_item=source_item,
                        target_item=None,
                        source_normalized=_apply_field_filters(
                            _normalize_diff_item(plugin, module, service, source_item),
                            include_paths,
                            ignore_paths,
                        ),
                        match_reason=(
                            f"no target object matched by {resolved_match}"
                            if resolved_match
                            else "no target object matched"
                        ),
                    )
                )
                continue

            target_item = target_bucket[0]
            diff_items.append(
                _diff_entry(
                    label=_copy_item_label(target_item),
                    match_by_requested=match_by,
                    match_by_used=resolved_match,
                    status="only_in_target",
                    source_item=None,
                    target_item=target_item,
                    target_normalized=_apply_field_filters(
                        _normalize_diff_item(plugin, module, service, target_item),
                        include_paths,
                        ignore_paths,
                    ),
                    match_reason=(
                        f"no source object matched by {resolved_match}"
                        if resolved_match
                        else "no source object matched"
                    ),
                )
            )

        for item in source_no_key:
            source_item = item["item"]
            diff_items.append(
                _diff_entry(
                    label=_copy_item_label(source_item),
                    match_by_requested=match_by,
                    match_by_used=item.get("match_by"),
                    status="only_in_source",
                    source_item=source_item,
                    target_item=None,
                    source_normalized=_apply_field_filters(
                        _normalize_diff_item(plugin, module, service, source_item),
                        include_paths,
                        ignore_paths,
                    ),
                    match_reason="no usable source match key",
                )
            )

        for item in target_no_key:
            target_item = item["item"]
            diff_items.append(
                _diff_entry(
                    label=_copy_item_label(target_item),
                    match_by_requested=match_by,
                    match_by_used=item.get("match_by"),
                    status="only_in_target",
                    source_item=None,
                    target_item=target_item,
                    target_normalized=_apply_field_filters(
                        _normalize_diff_item(plugin, module, service, target_item),
                        include_paths,
                        ignore_paths,
                    ),
                    match_reason="no usable target match key",
                )
            )
    else:
        for source_item in source_items:
            label = _copy_item_label(source_item)
            source_normalized = _apply_field_filters(
                _normalize_diff_item(plugin, module, service, source_item),
                include_paths,
                ignore_paths,
            )
            match_detail = _resolve_match_detail(
                target_cp,
                target_token,
                target_catalog,
                module,
                service,
                source_item,
                match_by,
            )
            if match_detail["status"] == "ambiguous_match":
                diff_items.append(
                    _diff_entry(
                        label=label,
                        match_by_requested=match_by,
                        match_by_used=match_detail.get("match_by"),
                        status="ambiguous_match",
                        source_item=source_item,
                        target_item=None,
                        source_normalized=source_normalized,
                        match_reason=match_detail.get("match_reason"),
                        target_candidates=match_detail.get("target_candidates"),
                    )
                )
                continue

            target_match = match_detail.get("target_match")
            if target_match is None:
                diff_items.append(
                    _diff_entry(
                        label=label,
                        match_by_requested=match_by,
                        match_by_used=match_detail.get("match_by"),
                        status="only_in_source",
                        source_item=source_item,
                        target_item=None,
                        source_normalized=source_normalized,
                        match_reason=match_detail.get("match_reason"),
                        target_candidates=match_detail.get("target_candidates"),
                    )
                )
                continue

            target_normalized = _apply_field_filters(
                _normalize_diff_item(plugin, module, service, target_match),
                include_paths,
                ignore_paths,
            )
            changed = _collect_changed_values(source_normalized, target_normalized)
            status = "same" if not changed else "different"
            diff_items.append(
                _diff_entry(
                    label=label,
                    match_by_requested=match_by,
                    match_by_used=match_detail.get("match_by"),
                    status=status,
                    source_item=source_item,
                    target_item=target_match,
                    source_normalized=source_normalized,
                    target_normalized=target_normalized,
                    changed=changed,
                    match_reason=match_detail.get("match_reason"),
                    target_candidates=match_detail.get("target_candidates"),
                )
            )

    summary = {
        "compared": sum(
            1 for item in diff_items if item["status"] in {"same", "different"}
        ),
        "only_in_source": sum(
            1 for item in diff_items if item["status"] == "only_in_source"
        ),
        "only_in_target": sum(
            1 for item in diff_items if item["status"] == "only_in_target"
        ),
        "different": sum(1 for item in diff_items if item["status"] == "different"),
        "same": sum(1 for item in diff_items if item["status"] == "same"),
        "ambiguous_match": sum(
            1 for item in diff_items if item["status"] == "ambiguous_match"
        ),
    }

    out_path = str(args.get("out") or "").strip() or _default_artifact_path(
        active_settings,
        module,
        service,
        source_profile,
        target_profile,
        "diff",
        timestamp=None,
    )
    report = {
        "mode": "diff",
        "module": module,
        "service": service,
        "source_profile": source_profile,
        "target_profile": target_profile,
        "match_by": match_by,
        "field_filters": {
            "fields": [_path_to_string(path) for path in include_paths],
            "ignore_fields": [_path_to_string(path) for path in ignore_paths],
        },
        "summary": summary,
        "items": diff_items,
        "artifacts": {"report": out_path},
    }

    write_value_to_file(
        report,
        out_path,
        data_format="json",
        mask_secrets=mask_secrets,
    )
    _emit_diff_summary(report)
    return report


__all__ = ["handle_diff_command"]
