"""Cart tools for managing the user's cart and checkout."""

import json
import os
from typing import Optional, Dict, Any
import httpx
from langchain_core.tools import tool
from loguru import logger

API_SERVICE_BASE_URL = os.getenv("API_SERVICE_BASE_URL", "https://api.example.com")

def get_json_api_headers(session_id: str) -> dict:
    return {"Authorization": f"Bearer {session_id}", "Content-Type": "application/json"}

def call_cart_manage_api(action: str, data: dict, session_id: str) -> dict:
    """Call the cart management API."""
    try:
        url = f"{API_SERVICE_BASE_URL}/api/v1/cart/manage"
        headers = get_json_api_headers(session_id)
        payload = {"action": action, **data}

        logger.info(f"Calling cart manage API: {url} with payload: {payload}")
        response = httpx.post(url, json=payload, headers=headers, timeout=10.0)
        response.raise_for_status()

        return response.json()
    except httpx.HTTPError as e:
        logger.error(f"Cart manage API call failed: {e}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error in cart manage: {e}")
        return {"success": False, "error": str(e)}

def fetch_cart_from_api(session_id: str) -> dict:
    """Fetch the current cart from API."""
    try:
        url = f"{API_SERVICE_BASE_URL}/api/v1/cart"
        headers = get_json_api_headers(session_id)

        logger.info(f"Fetching cart from API: {url}")
        response = httpx.get(url, headers=headers, timeout=10.0)
        response.raise_for_status()

        return response.json()
    except httpx.HTTPError as e:
        logger.error(f"Cart fetch API call failed: {e}")
        return {"items": [], "total_items": 0, "error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error in cart fetch: {e}")
        return {"items": [], "total_items": 0, "error": str(e)}

def _pick_number(source: dict, keys: list[str], default: float = 0.0) -> float:
    """Best-effort extraction of numeric totals from varying backend key names."""
    if not isinstance(source, dict):
        return default
    for k in keys:
        if k not in source:
            continue
        v = source.get(k)
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            s = v.strip()
            if not s:
                continue
            s = s.replace(",", ".")
            try:
                return float(s)
            except ValueError:
                continue
    return default


@tool
def manage_cart_tool(
    session_id: str,
    action: str,
    items: Optional[str] = None,
) -> Dict[str, Any]:
    """Manage the cart: add, remove, update, or clear items.

    action values:
      "add"    — Add one or more items to cart.
      "remove" — Remove one or more items from cart.
      "update" — Update quantity, notes, or modifiers for one or more items.
      "clear"  — Remove all items from cart. No other params needed.

    *** CRITICAL - IDs ***
    - item_id is REQUIRED for add/remove/update — get it from context or tool results
    - NEVER make up IDs
    - When updating, ALWAYS include all existing modifiers or they will be removed

    Args:
        session_id: Leon session ID.
        action: "add" | "remove" | "update" | "clear"
        items: JSON string — list of item objects. Format per action:

          add:    '[{"item_id": 123, "quantity": 1, "notes": "No onions",
                    "modifiers": [{"id": 6188463, "quantity": 1}]}]'

          update: '[{"item_id": 123, "quantity": 2,
                    "modifiers": [{"id": 6188463, "quantity": 1}]}]'
                  — MUST include all existing modifiers or they will be removed

          remove: '[{"item_id": 123}, {"item_id": 456}]'

          clear:  not needed

    Returns:
        Success or error result from the cart API.
    """
    logger.info(f"[CART] manage_cart_tool | action={action} items={items}")

    try:
        items_list = json.loads(items or "[]")
    except json.JSONDecodeError:
        items_list = []

    if action in ("add", "remove", "update", "clear"):
        data = {} if action == "clear" else {"items": items_list}
        result = call_cart_manage_api(
            action, data, session_id=session_id
        )
        cart_data = fetch_cart_from_api(session_id=session_id)
        logger.info(
            f"[CART] manage_cart_tool result | action={action} session_id={session_id} "
            f"items_in_cart={len(cart_data.get('items', [])) if isinstance(cart_data, dict) else 0}"
        )
        return {
            "action": action,
            "api_result": result,
            "cart": cart_data,
        }
    else:
        return {"success": False, "error": f"Unknown action '{action}'. Use add, remove, update, or clear."}


@tool
def view_cart_tool(session_id: str) -> Dict[str, Any]:
    """View the current cart contents.

    Use before any remove/update to get current item IDs and modifiers.
    Also use when user asks 'what's in my cart'.

    Args:
        session_id: Leon session ID.

    Returns:
        Current cart contents including items, total count, and subtotal.
    """
    logger.info("[CART] view_cart_tool")
    cart_data = fetch_cart_from_api(session_id=session_id)
    items = cart_data.get("items", [])

    subtotal = _pick_number(
        cart_data,
        ["subtotal", "sub_total", "pre_tax_subtotal", "items_subtotal"],
        default=0.0,
    )
    tax = _pick_number(
        cart_data,
        ["tax", "tax_amount", "tax_total", "vat", "vat_amount"],
        default=0.0,
    )
    total = _pick_number(
        cart_data,
        [
            "total",
            "grand_total",
            "total_amount",
            "amount_total",
            "final_total",
            "total_with_tax",
        ],
        default=0.0,
    )

    return {
        "items": [
            {
                "name": i.get("name", ""),
                "item_id": i.get("item_id"),
                "quantity": i.get("quantity", 1),
                "price": i.get("price", 0),
                "notes": i.get("notes", ""),
                "modifiers": i.get("modifiers", []),
            }
            for i in items
        ],
        "total_items": cart_data.get("total_items", 0),
        "subtotal": subtotal,
        "tax": tax,
        "total": total,
    }


@tool
def checkout_tool(session_id: str) -> Dict[str, Any]:
    """Proceed to checkout — send selected order items and modifiers to backend for payment processing.

    Use only when the user explicitly says they want to checkout, pay, or place their order.

    Args:
        session_id: Leon session ID.

    Returns:
        Backend response with payment information or confirmation.
    """
    logger.info("[CART] checkout_tool")
    cart_data = fetch_cart_from_api(session_id=session_id)
    items = cart_data.get("items", []) if isinstance(cart_data, dict) else []
    total_items = cart_data.get("total_items", 0) if isinstance(cart_data, dict) else 0
    has_items = bool(items) or (isinstance(total_items, (int, float)) and total_items > 0)

    if not has_items:
        logger.info("[CART] checkout blocked: cart is empty")
        return {
            "success": False,
            "action": "checkout_blocked",
            "reason": "empty_cart",
            "message": "Your cart is empty.",
        }

    # Prepare booking data with items and modifiers
    booking_data = {
        "session_id": session_id,
        "items": items,
        "total_items": total_items,
        "subtotal": _pick_number(cart_data, ["subtotal", "sub_total", "pre_tax_subtotal", "items_subtotal"], 0.0),
        "tax": _pick_number(cart_data, ["tax", "tax_amount", "tax_total", "vat", "vat_amount"], 0.0),
        "total": _pick_number(cart_data, ["total", "grand_total", "total_amount", "amount_total", "final_total", "total_with_tax"], 0.0),
    }

    # Send booking data to backend for payment processing
    try:
        url = f"{API_SERVICE_BASE_URL}/api/v1/booking/checkout"
        headers = get_json_api_headers(session_id)
        payload = booking_data

        logger.info(f"Sending booking data to backend: {url}")
        response = httpx.post(url, json=payload, headers=headers, timeout=15.0)
        response.raise_for_status()

        backend_response = response.json()
        logger.info(f"[CART] Checkout successful, backend response: {backend_response}")

        return {
            "success": True,
            "action": "checkout_completed",
            "booking_data": booking_data,
            "backend_response": backend_response,
        }

    except httpx.HTTPStatusError as e:
        logger.error(f"[CART] Checkout API HTTP error: {e.response.status_code} - {e.response.text}")
        return {
            "success": False,
            "action": "checkout_failed",
            "error": f"Payment processing failed: {e.response.status_code}",
            "message": "Unable to process payment. Please try again.",
        }
    except httpx.RequestError as e:
        logger.error(f"[CART] Checkout API request error: {e}")
        return {
            "success": False,
            "action": "checkout_failed",
            "error": f"Network error: {str(e)}",
            "message": "Unable to connect to payment service. Please try again.",
        }
    except Exception as e:
        logger.error(f"[CART] Checkout unexpected error: {e}")
        return {
            "success": False,
            "action": "checkout_failed",
            "error": f"Unexpected error: {str(e)}",
            "message": "An unexpected error occurred. Please try again.",
        }