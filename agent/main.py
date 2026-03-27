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
    get_room_availability_room,
    describe_room_to_guest,
    get_total_booking_amount,
    get_room_amenities,
    send_booking_to_backend,
    get_faq_answer,
    get_travel_places,
    web_search,
)
from schema import (
    ToolTextResponse,
    RoomAvailabilityRequest,
    DescribeRoomRequest,
    RoomAmenitiesRequest,
    TotalAmountRequest,
    BookingRequest,
    FAQRequest,
    TravelInfoRequest,
    WebSearchRequest,
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
        "message": "Rezolve Hotels Agent API",
        "docs": "Visit /docs for interactive API documentation",
    }


@app.post("/tools/room-availability", response_model=ToolTextResponse)
async def room_availability_tool(payload: RoomAvailabilityRequest) -> ToolTextResponse:
    """
    ElevenLabs HTTP tool: discover suitable rooms for given dates, guest count,
    and optional amenity / room-name filters.
    """
    try:
        text = get_room_availability_room.invoke(
            {
                "check_in_date": payload.check_in_date,
                "check_out_date": payload.check_out_date,
                "min_guests": payload.min_guests,
                "amenities": payload.amenities,
                "room_name": payload.room_name,
            }
        )
        return ToolTextResponse(response=str(text), actions=[])
    except Exception as e:
        logger.error(f"/tools/room-availability failed: {e}")
        raise HTTPException(status_code=500, detail="room-availability failed")


@app.get("/tools/food-menu")
async def get_food_menu() -> Dict[str, Any]:
    """
    Return the current food and beverage menu defined in `food_menu.json`.

    This can be used by the ElevenLabs HTTP tool so the agent can answer
    guest questions about what’s available on the menu.
    """
    menu_path = (
        Path(__file__).resolve().parent
        / "src"
        / "bot"
        / "data"
        / "food_menu.json"
    )

    try:
        with menu_path.open("r", encoding="utf-8") as f:
            menu_data = json.load(f)
    except FileNotFoundError:
        logger.error(f"Food menu file not found at {menu_path}")
        raise HTTPException(status_code=500, detail="Food menu data not found")
    except json.JSONDecodeError:
        logger.error(f"Food menu file is not valid JSON at {menu_path}")
        raise HTTPException(status_code=500, detail="Food menu data is invalid")

    return menu_data


@app.post("/tools/describe-room", response_model=ToolTextResponse)
async def describe_room_tool(payload: DescribeRoomRequest) -> ToolTextResponse:
    """
    ElevenLabs HTTP tool: describe a specific room in concierge style.
    """
    try:
        text = describe_room_to_guest.invoke({"room_name": payload.room_name})
        return ToolTextResponse(response=str(text), actions=[])
    except Exception as e:
        logger.error(f"/tools/describe-room failed: {e}")
        raise HTTPException(status_code=500, detail="describe-room failed")


@app.post("/tools/room-amenities", response_model=ToolTextResponse)
async def room_amenities_tool(payload: RoomAmenitiesRequest) -> ToolTextResponse:
    """
    ElevenLabs HTTP tool: answer amenity and facilities questions for a specific room.

    Use this when the guest asks what a particular room includes or whether
    it has a specific feature, such as laundry services, a bathtub, or
    kitchen facilities.
    """
    try:
        text = get_room_amenities.invoke(
            {
                "room_name": payload.room_name,
                "amenity_query": payload.amenity_query or "",
            }
        )
        return ToolTextResponse(response=str(text), actions=[])
    except Exception as e:
        logger.error(f"/tools/room-amenities failed: {e}")
        raise HTTPException(status_code=500, detail="room-amenities failed")


@app.post("/tools/total-amount", response_model=ToolTextResponse)
async def total_amount_tool(payload: TotalAmountRequest) -> ToolTextResponse:
    """
    ElevenLabs HTTP tool: calculate total booking amount as a number string.
    """
    try:
        amount = get_total_booking_amount.invoke(
            {
                "room_name": payload.room_name,
                "check_in_date": payload.check_in_date,
                "check_out_date": payload.check_out_date,
            }
        )
        return ToolTextResponse(response=str(amount), actions=[])
    except Exception as e:
        logger.error(f"/tools/total-amount failed: {e}")
        raise HTTPException(status_code=500, detail="total-amount failed")


@app.post("/tools/send-booking", response_model=ToolTextResponse)
async def send_booking_tool(payload: BookingRequest) -> ToolTextResponse:
    """
    ElevenLabs HTTP tool: send completed booking to backend and return confirmation text.
    """
    try:
        text = send_booking_to_backend.invoke(
            {
                "customer_name": payload.customer_name or "",
                "room_name": payload.room_name or "",
                "check_in_date": payload.check_in_date or "",
                "check_out_date": payload.check_out_date or "",
                "num_guests": payload.num_guests,
                "image_url": payload.image_url or "",
                "phone_number": payload.phone_number or "",
                "from_number": payload.from_number or "",
            }
        )
        return ToolTextResponse(response=str(text), actions=[])
    except Exception as e:
        logger.error(f"/tools/send-booking failed: {e}")
        raise HTTPException(status_code=500, detail="send-booking failed")


@app.post("/tools/faq", response_model=ToolTextResponse)
async def faq_tool(payload: FAQRequest) -> ToolTextResponse:
    """
    ElevenLabs HTTP tool: answer hotel FAQ-style questions.
    """
    try:
        text = get_faq_answer.invoke({"query": payload.question})
        return ToolTextResponse(response=str(text), actions=[])
    except Exception as e:
        logger.error(f"/tools/faq failed: {e}")
        raise HTTPException(status_code=500, detail="faq failed")


@app.post("/tools/travel-places", response_model=ToolTextResponse)
async def travel_places_tool(payload: TravelInfoRequest) -> ToolTextResponse:
    """
    ElevenLabs HTTP tool: answer nearby places / attractions questions using Google Places.
    """
    try:
        text = get_travel_places.invoke({"query": payload.query})
        return ToolTextResponse(response=str(text), actions=[])
    except Exception as e:
        logger.error(f"/tools/travel-places failed: {e}")
        raise HTTPException(status_code=500, detail="travel-places failed")


@app.post("/tools/web-search", response_model=ToolTextResponse)
async def web_search_tool(payload: WebSearchRequest) -> ToolTextResponse:
    """
    ElevenLabs HTTP tool: unified web search with smart routing.

    This tool is the single entry point Julia should use for:
    - Normal web queries (handled by Serp API `web_search`), and
    - Nearby / nearest place queries (handled by Google Places via `get_travel_places`).
    """
    try:
        base_query = payload.query
        location_context = (payload.location_context or "").strip()

        if location_context:
            combined_query = f"{base_query} near {location_context}"
        else:
            combined_query = base_query

        intent_hint = (payload.result_type or "generic").lower()
        lower_q = base_query.lower()
        is_places_like = any(
            kw in lower_q
            for kw in ["nearest", "closest", "nearby", "around here", "near the hotel"]
        )

        if intent_hint == "places" or is_places_like:
            text = get_travel_places.invoke({"query": combined_query})
            logger.info(f"Used Google Places for query: {combined_query}")
            logger.info(f"Google Places response: {text}")
        else:
            text = web_search.invoke({"query": combined_query})
            logger.info(f"Used SerpAPI web_search for query: {combined_query}")
            logger.info(f"SerpAPI web_search response: {text}")

        return ToolTextResponse(response=str(text), actions=[])
    except Exception as e:
        logger.error(f"/tools/web-search failed: {e}")
        raise HTTPException(status_code=500, detail="web-search failed")


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

