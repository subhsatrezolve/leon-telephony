"""Menu tools: recommend_menu_tool and get_food_item_tool."""

from __future__ import annotations

from typing import Any, Optional
import os

import httpx
from langchain_core.tools import tool
from loguru import logger

API_SERVICE_BASE_URL = os.getenv("API_SERVICE_BASE_URL", "https://api.example.com")

def get_json_api_headers(session_id: str) -> dict:
    return {"Authorization": f"Bearer {session_id}", "Content-Type": "application/json"}

def store_last_shown_items(items, session_id):
    # Placeholder - could implement Redis storage if needed
    pass

def _strip_recommend_item_keys(item: dict) -> dict:
    """Strip fields irrelevant at recommendation stage (modifiers are fetched later via get_food_item_tool)."""
    if not isinstance(item, dict):
        return item
    cleaned = dict(item)
    cleaned.pop("image_url", None)
    cleaned.pop("modifier_group_ids", None)
    cleaned.pop("modifier_groups", None)
    return cleaned


def _strip_detail_item_keys(item: dict) -> dict:
    """Strip only image_url from a full item detail response; modifiers are preserved."""
    if not isinstance(item, dict):
        return item
    cleaned = dict(item)
    cleaned.pop("modifier_group_ids", None)
    cleaned.pop("image_url", None)
    return cleaned


def _normalize_get_foods_payload(data: Any) -> list[dict]:
    """Turn get-foods JSON body into a list of item dicts."""
    if isinstance(data, dict) and "results" in data:
        raw = data["results"]
    elif isinstance(data, list):
        raw = data
    else:
        return []
    out: list[dict] = []
    for row in raw:
        if isinstance(row, dict):
            out.append(_strip_recommend_item_keys(row))
    return out


def _non_empty_str(val: Optional[str]) -> bool:
    return bool(val and str(val).strip())


@tool
def recommend_menu_tool(
    session_id: str,
    menu_id: Optional[int] = None,
    query: Optional[str] = None,
    category: Optional[str] = None,
    tags: Optional[str] = None,
    exclude_allergens: Optional[str] = None,
    dietary_options: Optional[str] = None,
    calories: Optional[int] = None,
    calories_gt: Optional[int] = None,
    calories_lt: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    alcoholic_only: Optional[bool] = None,
    page: int = 1,
    page_size: int = 5,
    categories: Optional[list[str]] = None,
    dietary_options_list: Optional[list[str]] = None,
    allergens: Optional[list[str]] = None,
) -> list[dict]:
    """
    Search menu items via GET /api/v1/food/get-foods.

    How to fill arguments is defined in the menu agent system prompt (decision matrix).
    Only pass parameters that apply; omit unused optional fields.

    Args:
        session_id: Leon session ID.
        query: Free-text nearest-match search. Always use when the user names a specific product.
        category: Menu section name from injected context, if narrowing to a single category.
        tags: Comma-separated tag values (e.g. "burger,fries"). Use when spanning multiple categories
              or when Julia provides tags instead of a category. Can be combined with query.
        exclude_allergens: Comma-separated allergen names to exclude.
        dietary_options: Comma-separated dietary labels to require.
        categories: Dynamic list of categories (not used in API call).
        dietary_options_list: Dynamic list of dietary options (not used in API call).
        allergens: Dynamic list of allergens (not used in API call).
    """
    cat_opt = (category or "").strip() or None
    q = (query or "").strip() or None

    has_filters = any(
        [
            _non_empty_str(tags),
            _non_empty_str(exclude_allergens),
            _non_empty_str(dietary_options),
            calories is not None,
            calories_gt is not None,
            calories_lt is not None,
            min_price is not None,
            max_price is not None,
            alcoholic_only is True,
        ]
    )
    if not cat_opt and not q and not has_filters:
        logger.warning(
            "[MENU TOOL] recommend_menu_tool called with no category, query, or filters — returning empty"
        )
        return []

    url = f"{API_SERVICE_BASE_URL}/api/v1/food/get-foods"
    ps = min(page_size, 200)
    final: list[dict] = []

    def _build_params(q_param: str | None, pg: int) -> dict:
        params: dict = {"page": pg, "page_size": ps}
        if menu_id is not None:
            params["menu_id"] = menu_id
        if cat_opt:
            params["category"] = cat_opt
        if q_param:
            params["q"] = q_param
        if _non_empty_str(tags):
            params["tags"] = tags
        if _non_empty_str(exclude_allergens):
            params["exclude_allergens"] = exclude_allergens
        if _non_empty_str(dietary_options):
            params["dietary_options"] = dietary_options
        if calories is not None:
            params["calories"] = calories
        if calories_gt is not None:
            params["calories_gt"] = calories_gt
        if calories_lt is not None:
            params["calories_lt"] = calories_lt
        if min_price is not None:
            params["min_price"] = min_price
        if max_price is not None:
            params["max_price"] = max_price
        if alcoholic_only is not None:
            params["alcoholic_only"] = alcoholic_only
        return params

    for attempt in (0, 1):
        if attempt == 1:
            if not q or final:
                break
            logger.info(
                f"[MENU TOOL] No results for query={q!r}, retrying without search term (broader match)"
            )

        q_param = q if attempt == 0 else None
        pg = page if attempt == 0 else 1

        params = _build_params(q_param, pg)
        logger.info(f"[MENU TOOL] GET get-foods params={params}")

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(
                    url,
                    params=params,
                    headers=get_json_api_headers(session_id=session_id),
                )
                response.raise_for_status()
                data = response.json()
            batch = _normalize_get_foods_payload(data)
            logger.info(f"[MENU TOOL] API returned {len(batch)} items")
        except httpx.HTTPStatusError as e:
            logger.error(
                f"[MENU TOOL] API HTTP error: {e.response.status_code} - {e.response.text}"
            )
            batch = []
        except httpx.RequestError as e:
            logger.error(f"[MENU TOOL] API request error: {e}")
            batch = []
        except (ValueError, TypeError) as e:
            logger.error(f"[MENU TOOL] Invalid JSON: {e}")
            batch = []
        except Exception as e:
            logger.error(f"[MENU TOOL] Unexpected error: {e}")
            batch = []

        final = batch
        if final:
            break

    if final:
        store_last_shown_items(final, session_id)

    return final


@tool
def get_food_item_tool(session_id: str, menu_id: Optional[int] = None, item_id: int) -> dict:
    """
    Fetch full details for one menu item by ID (e.g. after the user picks from recommendations).

    Modifier groups and options are included on the item when the API provides them.

    Args:
        session_id: Leon session ID.
        menu_id: Menu ID.
        item_id: Product ID from recommend_menu_tool / last-shown results.

    Returns:
        Item details dict or {} on failure.
    """
    logger.info(f"[FOOD ITEM] Fetching item details for ID: {item_id}")
    url = f"{API_SERVICE_BASE_URL}/api/v1/food/get-foods"
    params: dict[str, Any] = {"id": item_id}
    if menu_id is not None:
        params["menu_id"] = menu_id

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                url,
                params=params,
                headers=get_json_api_headers(session_id=session_id),
            )
            response.raise_for_status()
            data = response.json()

            if isinstance(data, dict) and data.get("status") == "success" and "data" in data:
                item = data["data"]
                if isinstance(item, dict):
                    logger.info(f"[FOOD ITEM] Fetched item: {item.get('name', 'Unknown')}")
                    return _strip_detail_item_keys(item)
            logger.warning(f"[FOOD ITEM] Unexpected response format: {data}")
            return {}

    except httpx.HTTPStatusError as e:
        logger.error(f"[FOOD ITEM] API HTTP error: {e.response.status_code} - {e.response.text}")
        return {}
    except httpx.RequestError as e:
        logger.error(f"[FOOD ITEM] API request error: {e}")
        return {}
    except Exception as e:
        logger.error(f"[FOOD ITEM] Unexpected error: {e}")
        return {}