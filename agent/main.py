"""Main entry point for the hotel booking bot using ElevenLabs hosted voice agents."""

import json
import os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from loguru import logger

from src.bot.tools import (
    recommend_menu_tool,
    get_food_item_tool,
    manage_cart_tool,
    view_cart_tool,
    checkout_tool,
)
from schema import (
    ToolTextResponse,
    RecommendMenuRequest,
    GetFoodItemRequest,
    ManageCartRequest,
    ViewCartRequest,
    CheckoutRequest,
    CheckoutResponse,
)


load_dotenv(override=True)

ELEVENLABS_AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

logger.info("🚀 Starting Rezolve Hotels Agent API with ElevenLabs hosted voice agents")

app = FastAPI(
    title="Rezolve Hotels Agent API",
    description="API for Rezolve Hotels agent (ElevenLabs hosted voice + HTTP tools)",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check and API info endpoint."""
    return {
        "status": "running",
        "message": "Leon Agent API",
        "docs": "Visit /docs for interactive API documentation",
    }


@app.post("/tools/recommend-menu", response_model=ToolTextResponse)
async def recommend_menu_endpoint(payload: RecommendMenuRequest) -> ToolTextResponse:
    """
    ElevenLabs HTTP tool: search menu items.
    """
    try:
        text = recommend_menu_tool.invoke(
            {
                "session_id": payload.session_id,
                "menu_id": payload.menu_id,
                "query": payload.query,
                "category": payload.category,
                "tags": payload.tags,
                "exclude_allergens": payload.exclude_allergens,
                "dietary_options": payload.dietary_options,
                "calories": payload.calories,
                "calories_gt": payload.calories_gt,
                "calories_lt": payload.calories_lt,
                "min_price": payload.min_price,
                "max_price": payload.max_price,
                "alcoholic_only": payload.alcoholic_only,
                "page": payload.page,
                "page_size": payload.page_size,
                "categories": payload.categories,
                "dietary_options_list": payload.dietary_options_list,
                "allergens": payload.allergens,
            }
        )
        return ToolTextResponse(response=str(text), actions=[])
    except Exception as e:
        logger.error(f"/tools/recommend-menu failed: {e}")
        raise HTTPException(status_code=500, detail="recommend-menu failed")


@app.post("/tools/get-food-item", response_model=ToolTextResponse)
async def get_food_item_endpoint(payload: GetFoodItemRequest) -> ToolTextResponse:
    """
    ElevenLabs HTTP tool: fetch full details for one menu item.
    """
    try:
        text = get_food_item_tool.invoke({"session_id": payload.session_id, "menu_id": payload.menu_id, "item_id": payload.item_id})
        return ToolTextResponse(response=str(text), actions=[])
    except Exception as e:
        logger.error(f"/tools/get-food-item failed: {e}")
        raise HTTPException(status_code=500, detail="get-food-item failed")


@app.post("/tools/manage-cart", response_model=ToolTextResponse)
async def manage_cart_endpoint(payload: ManageCartRequest) -> ToolTextResponse:
    """
    ElevenLabs HTTP tool: manage the cart.
    """
    try:
        text = manage_cart_tool.invoke(
            {
                "session_id": payload.session_id,
                "action": payload.action,
                "items": payload.items,
            }
        )
        return ToolTextResponse(response=str(text), actions=[])
    except Exception as e:
        logger.error(f"/tools/manage-cart failed: {e}")
        raise HTTPException(status_code=500, detail="manage-cart failed")


@app.post("/tools/view-cart", response_model=ToolTextResponse)
async def view_cart_endpoint(payload: ViewCartRequest) -> ToolTextResponse:
    """
    ElevenLabs HTTP tool: view the current cart.
    """
    try:
        text = view_cart_tool.invoke({"session_id": payload.session_id})
        return ToolTextResponse(response=str(text), actions=[])
    except Exception as e:
        logger.error(f"/tools/view-cart failed: {e}")
        raise HTTPException(status_code=500, detail="view-cart failed")


@app.post("/tools/checkout", response_model=CheckoutResponse)
async def checkout_endpoint(payload: CheckoutRequest) -> CheckoutResponse:
    """
    ElevenLabs HTTP tool: proceed to checkout and send booking data to backend.
    """
    try:
        result = checkout_tool.invoke({"session_id": payload.session_id})

        # Parse the result from checkout_tool
        if isinstance(result, dict):
            return CheckoutResponse(
                success=result.get("success", False),
                action=result.get("action", "checkout_failed"),
                booking_data=result.get("booking_data"),
                backend_response=result.get("backend_response"),
                error=result.get("error"),
                message=result.get("message"),
            )
        else:
            # Fallback for unexpected response format
            return CheckoutResponse(
                success=False,
                action="checkout_failed",
                error="Unexpected response format",
                message="An unexpected error occurred during checkout."
            )
    except Exception as e:
        logger.error(f"/tools/checkout failed: {e}")
        return CheckoutResponse(
            success=False,
            action="checkout_failed",
            error=str(e),
            message="Checkout failed due to an internal error."
        )


@app.post("/")
async def twilio_entry(request: Request):
    """
    Twilio calls this endpoint when a phone call starts.

    This registers the call with the ElevenLabs ConvAI voice agent platform and
    returns the TwiML provided by ElevenLabs to connect the call.
    """
    form = await request.form()
    from_number = form.get("From")
    to_number = form.get("To")
    direction = form.get("Direction", "inbound")
    call_sid = form.get("CallSid")

    if not ELEVENLABS_AGENT_ID or not ELEVENLABS_API_KEY:
        logger.error("ELEVENLABS_AGENT_ID or ELEVENLABS_API_KEY not configured")
        raise HTTPException(status_code=500, detail="Voice agent is not configured")

    payload = {
        "agent_id": ELEVENLABS_AGENT_ID,
        "from_number": from_number,
        "to_number": to_number,
        "direction": direction or "inbound",
        "conversation_initiation_client_data": {
            "twilio_call_sid": call_sid,
        },
    }

    logger.info(
        f"☎️ Registering Twilio call with ElevenLabs | "
        f"from={from_number} to={to_number} direction={direction} call_sid={call_sid}"
    )

    import requests

    try:
        resp = requests.post(
            "https://api.elevenlabs.io/v1/convai/twilio/register-call",
            headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=10,
        )
    except Exception as e:
        logger.error(f"Error calling ElevenLabs register-call API: {e}")
        raise HTTPException(
            status_code=502,
            detail="Failed to contact voice agent provider",
        )

    if not resp.ok:
        logger.error(
            f"ElevenLabs register-call failed: {resp.status_code} {resp.text}"
        )
        raise HTTPException(
            status_code=502,
            detail="Failed to initialize voice agent",
        )

    twiml = resp.text
    return HTMLResponse(content=twiml, media_type="application/xml")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)

