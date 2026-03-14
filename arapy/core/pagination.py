from __future__ import annotations

from copy import deepcopy
from typing import Any

from arapy.core.resolver import query_params_for_action

DEFAULT_PAGE_SIZE = 1000


def _extract_items(response: Any) -> list[Any] | None:
    if isinstance(response, dict):
        embedded = response.get("_embedded")
        if isinstance(embedded, dict):
            items = embedded.get("items")
            if isinstance(items, list):
                return items
        return None
    if isinstance(response, list):
        return response
    return None


def _extract_total_count(response: Any) -> int | None:
    if not isinstance(response, dict):
        return None
    count = response.get("count")
    if isinstance(count, bool):
        return None
    if isinstance(count, int):
        return count
    if isinstance(count, str) and count.isdigit():
        return int(count)
    return None


def _merge_list_responses(
    first_response: Any,
    all_items: list[Any],
    *,
    total_count: int | None,
) -> Any:
    if isinstance(first_response, dict):
        merged = deepcopy(first_response)
        embedded = merged.get("_embedded")
        if isinstance(embedded, dict) and isinstance(embedded.get("items"), list):
            embedded["items"] = all_items
        if total_count is not None:
            merged["count"] = total_count
        elif "count" in merged:
            merged["count"] = len(all_items)
        links = merged.get("_links")
        if isinstance(links, dict) and "next" in links:
            links = dict(links)
            links.pop("next", None)
            merged["_links"] = links
        return merged
    if isinstance(first_response, list):
        return all_items
    return first_response


def fetch_all_list_results(cp, token: str, api_catalog: dict, args: dict[str, Any]):
    params = query_params_for_action(cp, api_catalog, args, "list")
    action_def = cp.get_action_definition(
        api_catalog, args["module"], args["service"], "list"
    )
    allowed = {
        str(name)
        for name in action_def.get("params", []) or []
        if isinstance(name, str)
    }

    explicit_limit = "limit" in args and args.get("limit") not in (None, "")
    if "limit" in allowed and not explicit_limit:
        params["limit"] = DEFAULT_PAGE_SIZE
    if "offset" in allowed and "offset" not in params:
        params["offset"] = 0

    response = cp.list(api_catalog, token, args, params=params or None)
    page_items = _extract_items(response)
    # Fall back to the first response when the endpoint is not a classic paged list.
    if page_items is None or "limit" not in allowed or "offset" not in allowed:
        return response
    if explicit_limit:
        return response

    all_items = list(page_items)
    total_count = _extract_total_count(response)
    page_size = int(params["limit"])
    current_offset = int(params.get("offset", 0))

    while True:
        if total_count is not None and len(all_items) >= total_count:
            break
        if len(page_items) < page_size:
            break

        next_offset = current_offset + len(page_items)
        if next_offset <= current_offset:
            break

        next_params = dict(params)
        next_params["offset"] = next_offset
        if "calculate_count" in next_params and total_count is not None:
            next_params["calculate_count"] = "false"

        next_response = cp.list(api_catalog, token, args, params=next_params or None)
        page_items = _extract_items(next_response)
        if page_items is None or not page_items:
            break

        all_items.extend(page_items)
        current_offset = next_offset

        if total_count is None:
            total_count = _extract_total_count(next_response)

    return _merge_list_responses(response, all_items, total_count=total_count)
