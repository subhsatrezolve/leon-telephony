"""Hotel booking API routes for room management, offers, and payments."""

import json
import os
import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks
from integrations.lotte_hotel_client import LotteAgent
from src.models.schemas import RequestRoom, SendOfferRequest, SuggestionModel, RequestOffers, PaymentRequest
from livekit.api import LiveKitAPI
from livekit.protocol.room import SendDataRequest
from src.services.session_store import RedisSessionStore
from twilio.rest import Client
router = APIRouter()

async def payments_signal_handler(room_id, room_code, index,source="web"):
    print(f"[DEBUG] payments_signal_handler triggered for source={source}")
    if source != "web":
        return
    api = LiveKitAPI()
    try:
        await api.room.send_data(
            send=SendDataRequest(
                room=room_id,
                data=json.dumps(
                    {
                        "room_code": room_code,
                        "variant_index": index,
                    }
                ).encode(),
                topic="payments",
            )
        )
    except Exception as e:
        print("Error sending payments data:", e)
async def offers_signal_handler(room_name, room_code, roomOffers=None,source="web"):
    print(f"[DEBUG] offers_signal_handler triggered for source={source}")
    if source != "web":
        return
    api = LiveKitAPI()
    try:
        await api.room.send_data(
            send=SendDataRequest(
                room=room_name,
                data=json.dumps(
                    {
                        "roomCode": room_code,
                        "offerCodes": roomOffers if roomOffers else ""
                    }
                ).encode('utf-8'),
                topic="offers",
            )
        )
    except Exception as e:
        print("Error sending offers data:", e)


async def rooms_signal_handler(room_name, data, codes, check_in_date, check_out_date, topic,source="web"):
    print(f"[DEBUG] rooms_signal_handler triggered for source={source}")
    if source != "web":
        return
    # store session rooms

    engine = RedisSessionStore(url=os.getenv("REDIS_URL"))
    engine.store(
        key=f"room:{room_name}",
        value=data,
    )
    for room in data:
        variants = room.get("variants", [])
        code = room.get("code", "")

        engine.store(
            key=f"offers:{check_in_date}:{check_out_date}:{room_name}:{code}",
            value=variants,
        )

    api = LiveKitAPI()
    try:
        await api.room.send_data(
            send=SendDataRequest(
                room=room_name,
                data=codes.encode('utf-8'),
                topic=topic,
            )
        )

    except Exception as e:
        print("Error sending room data:", e)


@router.post("/send-offers")
async def send_offers(data: SendOfferRequest, background_tasks: BackgroundTasks):
    """
    Receives:
      - room_id (str)
      - offer_code (legacy: a single code)
      - roomOffers (optional): comma-separated recommended offer codes
    """
    print(f"[DEBUG] /send-offers called, source={getattr(data, 'source', 'web')}")
    #print("Send Offers Data: ", data)
    background_tasks.add_task(
        offers_signal_handler,
        data.room_id,
        data.offer_code,
        data.roomOffers,
        getattr(data, "source", "web"),
    )
    return {
        "status" : 200
    }


@router.post("/process-payment")
async def process_payment(data: PaymentRequest, background_tasks: BackgroundTasks):
    print(f"[DEBUG] /process-payment called, source={getattr(data, 'source', 'web')}")
    background_tasks.add_task(
        payments_signal_handler,
        data.room_id,
        data.room_code,
        data.index,
        getattr(data, "source", "web"),
    )
    return {
        "status": 200
    }


@router.post("/process-payment-sms/{agent_name}")
async def process_payment_sms(agent_name: str, data: dict):
    '''
    booking_info = {
        "phone_number": phone_number,
        "customer_name": customer_name,
        "room_name": room_name,
        "check_in_date": check_in_date,
        "check_out_date": check_out_date,
        "num_guests": num_guests,
        "image_url": image_url,
        "total_amount": total_amount
    }
    '''
    engine = RedisSessionStore(url=os.getenv("REDIS_URL"))
    token = ":".join([agent_name, str(uuid.uuid4())])
    engine.store(
        key=f"payments_sms:{token}",
        value=data,
    )
    print(f"[DEBUG] process_payment_sms called for phone_number={data.get('phone_number')}")

    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    client = Client(account_sid, auth_token)

    customer_name = data.get("customer_name", "Guest")
    phone_number = data.get("phone_number", "")
    room_name = data.get("room_name", "Selected Room")
    check_in_date = data.get("check_in_date", "")
    check_out_date = data.get("check_out_date", "")
    num_guests = data.get("num_guests", 1)
    total_amount = data.get("total_amount", "0")

    payment_link = "pay?token=" + token
    
    # Send to whatsapp
    if phone_number:
        wp_messaging_sid = os.getenv('TWILIO_WP_MESSAGING_SERVICE_SID')
        wp_content_sid = os.getenv('TWILIO_PAYMENT_LINK_WP_SID')

        if wp_messaging_sid and wp_content_sid:
            try:
                wp_message = client.messages.create(
                    to=f"whatsapp:{phone_number}",
                    messaging_service_sid=wp_messaging_sid,
                    content_sid=wp_content_sid,
                    content_variables=json.dumps(
                        {
                            "1": customer_name,
                            "2": room_name,
                            "3": check_in_date,
                            "4": check_out_date,
                            "5": str(num_guests),
                            "6": payment_link,
                            "7": f"${total_amount}" if total_amount != "0" else ""
                        }
                    )
                )
                print(f"Sent booking confirmation WhatsApp to {phone_number} | Message SID: {wp_message.sid}")
            except Exception as e:
                print(f"Warning: Could not send WhatsApp message to {phone_number}: {e}")
        else:
            print("WhatsApp messaging service SID or content SID not configured, skipping WhatsApp message")
    else:
        print("No phone number provided, skipping WhatsApp message.")

    return {
        "status": 200,
        "payment_token": token
    }


@router.get("/get-payment-info/{token}")
async def get_payment_info(token: str):

    engine = RedisSessionStore(url=os.getenv("REDIS_URL"))
    data = engine.fetch(f"payments_sms:{token}")
    if data is None:
        raise HTTPException(status_code=404, detail="Payment info not found")
    return data

@router.get("/send-success-sms")
async def send_success_sms(token: str):

    engine = RedisSessionStore(url=os.getenv("REDIS_URL"))
    data = engine.fetch(f"payments_sms:{token}")
    if data is None:
        raise HTTPException(status_code=404, detail="Payment info not found")
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    client = Client(account_sid, auth_token)

    customer_name = data.get("customer_name", "Guest")
    phone_number = data.get("phone_number", "")
    room_name = data.get("room_name", "Selected Room")
    check_in_date = data.get("check_in_date", "")
    check_out_date = data.get("check_out_date", "")
    num_guests = data.get("num_guests", 1)
    # message = client.messages.create(
    #     # shorten_urls=True,
    #     messaging_service_sid=os.getenv('TWILIO_MESSAGING_SERVICE_SID'),
    #     body=f'''Dear {customer_name},\nThank you for completing your payment. Your booking for {room_name} from {check_in_date} to {check_out_date} for {num_guests} guest(s) is now confirmed.\nWe look forward to hosting you and ensuring a memorable stay!''',
    #     to=str(phone_number)
    # )



    wp_message = client.messages.create(
        to="whatsapp:" + str(phone_number),
        messaging_service_sid=os.getenv('TWILIO_WP_MESSAGING_SERVICE_SID'),
        content_sid=os.getenv('TWILIO_PAYMENT_SUCCESS_WP_SID'),
        content_variables=json.dumps(
            {
                "1": customer_name,
            }
        )
    )
    print(f"Sent payment success SMS to {phone_number} | Message SID: {wp_message.sid}")

    
    # send to whatsapp too

    if not data.get("phone_number"):
        print("No phone number provided, skipping SMS.")
        return

    return {
        "status": 200
    }   

@router.post("/clear-payment-info/{token}")
async def clear_payment_info(token: str):

    engine = RedisSessionStore(url=os.getenv("REDIS_URL"))
    engine.delete(f"payments_sms:{token}")
    return {
        "status": 200
    }


@router.post("/get-offers")
async def get_offers(data: RequestOffers):
    engine = RedisSessionStore(url=os.getenv("REDIS_URL"))
    offers = engine.fetch(
        f"offers:{data.check_in_date}:{data.check_out_date}:{data.room_id}:{data.room_code}")
    if offers is None:
        return {}
    return offers


@router.post("/nearest-availability")
async def nearest_availability(data: RequestRoom):
    agent = LotteAgent()
    availabilities = agent.check_nearest_availability(
        from_date=data.check_in_date,
        to_date=data.check_out_date,
        adults=data.number_of_adults,
        children=data.number_of_children
    )
    if availabilities is None:
        raise HTTPException(
            status_code=500, detail="Error fetching availability")
    if len(availabilities) == 0:
        raise HTTPException(status_code=404, detail="No availability found")
    return availabilities


@router.post("/list-rooms",)
async def list_rooms(data: RequestRoom, background_tasks: BackgroundTasks):
    print(f"[DEBUG] /list-rooms called, source={getattr(data, 'source', 'web')}")
    print("Request Data: ", data)
    api = LiveKitAPI()
    if data.show_cards:
        try:
            await api.room.send_data(
                send=SendDataRequest(
                    room=data.room_id,
                    data="Processing".encode(),
                    topic="status",
                )
            )
        except Exception as e:
            print("Error sending room data:", e)

    print("Room ID: ", data.room_id)
    agent = LotteAgent()
    data_ = agent.run(
        check_in_date=data.check_in_date,
        check_out_date=data.check_out_date,
        number_of_adults=data.number_of_adults,
        number_of_children=data.number_of_children,
        min_price=data.min_price,
        max_price=data.max_price,
        bed_size=data.bed_size
    )
    if data.show_cards:
        if isinstance(data_, str):
            api = LiveKitAPI()
            try:
                await api.room.send_data(
                    send=SendDataRequest(
                        room=data.room_id,
                        data="XXXX".encode(),
                        topic=data.topic or "rooms"
                    )
                )
                await api.room.send_data(
                    send=SendDataRequest(
                        room=data.room_id,
                        data="Completed".encode(),
                        topic="status",
                    )
                )
            except Exception as e:
                print("Error sending room data:", e)
        else:
            codes = [i.get("code") for i in data_]
            codes = ",".join(codes)
            background_tasks.add_task(
                rooms_signal_handler,
                data.room_id,
                data_,
                data.room_code if data.room_code else codes,
                data.check_in_date,
                data.check_out_date,
                data.topic or "rooms",
                getattr(data, "source", "web"),
            )
    else:
        if isinstance(data_, str):
            api = LiveKitAPI()
            try:
                await api.room.send_data(
                    send=SendDataRequest(
                        room=data.room_id,
                        data="XXXX".encode(),
                        topic=data.topic or "rooms",
                    )
                )
                await api.room.send_data(
                    send=SendDataRequest(
                        room=data.room_id,
                        data="Completed".encode(),
                        topic="status",
                    )
                )
            except Exception as e:
                print("Error sending room data:", e)
    if isinstance(data_, str):
        return {"error": data_, "status": 500}
    else:
        return data_


@router.post("/suggestions")
async def get_suggestions(data: SuggestionModel):
    engine = RedisSessionStore(url=os.getenv("REDIS_URL"))
    data = engine.fetch(f"room:{data.room}")
    if data is None:
        raise HTTPException(status_code=404, detail="Room not found")
    # await asyncio.sleep(4)  # Allow time for the transport to stabilize
    return data


@router.post("/get-cabs")
async def get_cabs(data: dict):
    print(f"[DEBUG] /get-cabs called, source={data.get('source', 'web')}")
    if data.get("source", "web") != "web":
        return {"status": "ignored"}
    api = LiveKitAPI()
    try:
        await api.room.send_data(
            send=SendDataRequest(
                room=data.get("room_id"),
                data=json.dumps(
                    data
                ).encode('utf-8'),
                topic="cabs",
            )
        )
    except Exception as e:
        print("Error sending cabs data:", e)
    return {"status": 200}

@router.post("/get-food")
async def get_food(data: dict):
    print(f"[DEBUG] /get-food called, source={data.get('source', 'web')}")
    if data.get("source", "web") != "web":
        return {"status": "ignored"}
    api = LiveKitAPI()
    try:
        await api.room.send_data(
            send=SendDataRequest(
                room=data.get("room_id"),
                data=json.dumps(
                    data
                ).encode('utf-8'),
                topic="food",
            )
        )
    except Exception as e:
        print("Error sending food data:", e)
    return {"status": 200}
