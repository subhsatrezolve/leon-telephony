"""LiveKit room management API for creating video conferencing rooms."""
from fastapi.responses import HTMLResponse
from fastapi import Request
from fastapi import APIRouter
from livekit import api as lkapi
import uuid
import os
from dotenv import load_dotenv
import requests

load_dotenv()
router = APIRouter()
ELEVENLABS_AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
AGENT_STREAM_WS_URL = os.getenv("AGENT_STREAM_WS_URL", "").strip()

@router.post("/create")
async def create_room(data: dict):
    """Create a new LiveKit room with user access token and start agent."""
    room_name = uuid.uuid4().hex
    api = lkapi.LiveKitAPI()
    await api.room.create_room(
        lkapi.CreateRoomRequest(
            name=room_name,
            empty_timeout=10*60,
            max_participants=2
        ),
    )
    access = lkapi.AccessToken(
        api_key=os.getenv("LIVEKIT_API_KEY"),
        api_secret=os.getenv("LIVEKIT_API_SECRET"),
    ).with_identity(
        identity="user"
    ).with_name(
        name="User"
    ).with_grants(
        lkapi.VideoGrants(
            room_join=True,
            room=room_name,
            can_subscribe=True,
            can_publish=True,
            can_publish_data=True
        )
    ).to_jwt()
    language = data.get("locale","English")
    # Start the agent in the room
    if language == "en":
        language = "English"
    elif language == "ko":
        language = "Korean"
    elif language == "ja":
        language = "Japanese"
    agent = requests.post(
        "http://agent:8001/start",
        json={"room_name": room_name, "participant_name": "Rezolve Hotels", "language": language},
    )
    if agent.status_code != 200:
        return {"error": "Failed to start agent"}
    else:
        agent_data = agent.json()
        return {
            "token" : access,
            "room_name": room_name,
            "agent": agent_data
        }

@router.post("/twilio/stream")
async def twilio_stream_entry(request: Request):
    """
    Twilio webhook that returns TwiML to connect the call to a WebSocket stream.
    Configure AGENT_STREAM_WS_URL (e.g. wss://ws-julia5.demo.rezolvecloud.com/ws)
    so the agent stream starts when the call connects.
    """
    stream_url = AGENT_STREAM_WS_URL
    if not stream_url:
        return HTMLResponse(
            content="""<?xml version="1.0" encoding="UTF-8"?>
                    <Response>
                    <Say language="en">Agent stream URL is not configured. Set AGENT_STREAM_WS_URL.</Say>
                    </Response>""",
            media_type="application/xml",
        )
    return HTMLResponse(
        content=f"""<?xml version="1.0" encoding="UTF-8"?>
                <Response>
                <Connect>
                <Stream url="{stream_url}"/>
                </Connect>
                </Response>""",
        media_type="application/xml",
    )


@router.post("/twilio")
async def twilio_entry(request: Request):
    """Twilio calls this endpoint when a phone call starts (ElevenLabs ConvAI register-call)."""
    form = await request.form()
    from_number = form.get("From")
    to_number = form.get("To")
    direction = form.get("Direction", "inbound")
    call_sid = form.get("CallSid")

    if not ELEVENLABS_AGENT_ID or not ELEVENLABS_API_KEY:
        return HTMLResponse(
            content="""<?xml version="1.0" encoding="UTF-8"?>
                    <Response>
                    <Say language="en">The voice agent is not configured.</Say>
                    </Response>""",
            media_type="application/xml",
        )

    payload = {
        "agent_id": ELEVENLABS_AGENT_ID,
        "from_number": from_number,
        "to_number": to_number,
        "direction": direction or "inbound",
        "conversation_initiation_client_data": {
            "twilio_call_sid": call_sid,
        },
    }

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
    except Exception:
        return HTMLResponse(
            content="""<?xml version="1.0" encoding="UTF-8"?>
                    <Response>
                    <Say language="en">We are unable to connect your call right now.</Say>
                    </Response>""",
            media_type="application/xml",
        )

    if not resp.ok:
        return HTMLResponse(
            content="""<?xml version="1.0" encoding="UTF-8"?>
                    <Response>
                    <Say language="en">The voice agent is currently unavailable.</Say>
                    </Response>""",
            media_type="application/xml",
        )

    twiml = resp.text
    return HTMLResponse(content=twiml, media_type="application/xml")
