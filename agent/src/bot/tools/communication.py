"""Booking-related tool(s) used by the ElevenLabs HTTP API)."""

import os
import json
import requests
from langchain_core.tools import tool
from loguru import logger


@tool
def send_booking_to_backend(
    customer_name: str = "",
    room_name: str = "",
    check_in_date: str = "",
    check_out_date: str = "",
    num_guests: int = 1,
    image_url: str = "",
    phone_number: str = "",
    from_number: str = "",
):
    """Send complete booking information to backend and return confirmation message.
    
    This tool receives all booking details and sends them to the backend for processing.
    If phone_number is provided, it should already include the country code (e.g., '+1234567890').
    If phone_number is not provided but from_number is available, it will use from_number.
    Otherwise, the backend will extract the phone number from Twilio automatically.
    
    Args:
        customer_name: The guest's full name (optional)
        room_name: The selected room name (optional)
        check_in_date: Check-in date in YYYY-MM-DD format (optional)
        check_out_date: Check-out date in YYYY-MM-DD format (optional)
        num_guests: Number of guests (optional, default: 1)
        image_url: The room's image URL (optional)
        phone_number: The guest's phone number with country code (optional, e.g., '+1234567890'). Only pass this if the guest provided a different number than the one they're calling from.
        from_number: The caller's phone number from Twilio (optional, e.g., '<MOBILE_NUMBER>'). Use this if phone_number is not provided and guest confirmed using the calling number.
    
    Returns:
        str: Confirmation message "Thank you for choosing Rezolve Hotels"
    """
    # Look up image_url from hotel_rooms.json if not provided but room_name is available
    if not image_url and room_name:
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            hotel_rooms_path = os.path.join(project_root, "data", "hotel_rooms.json")
            if os.path.exists(hotel_rooms_path):
                with open(hotel_rooms_path, "r") as f:
                    rooms_data = json.load(f)
                
                rooms_list = rooms_data.get("hotel_rooms", [])
                for room in rooms_list:
                    if room_name.lower() in room.get("name", "").lower():
                        image_urls = room.get("image_urls", [])
                        if image_urls and len(image_urls) > 0:
                            image_url = image_urls[0]
                            logger.info(f"Found image_url for {room_name}: {image_url}")
                        break
        except Exception as e:
            logger.warning(f"Could not look up image_url for {room_name}: {e}")
    
    # Calculate total amount - try to import helper function
    total_amount = "0"
    if room_name and check_in_date and check_out_date:
        try:
            from .room_availability_four_llm import calculate_total_booking_amount
            logger.info(
                "Calculating total amount for room='%s', check_in='%s', check_out='%s'",
                room_name,
                check_in_date,
                check_out_date,
            )
            total_amount = calculate_total_booking_amount(
                room_name, check_in_date, check_out_date
            )
            logger.info("Calculated total amount for booking: $%s", total_amount)
            if total_amount == "0":
                logger.warning(
                    "Total amount calculation returned 0 - this may indicate room not found or invalid price"
                )
        except ImportError:
            logger.warning(
                "calculate_total_booking_amount not available, skipping total calculation"
            )
        except Exception as e:
            logger.error("Error calculating total amount: %s", e, exc_info=True)
    
    booking_info = {
        "customer_name": customer_name,
        "room_name": room_name,
        "check_in_date": check_in_date,
        "check_out_date": check_out_date,
        "num_guests": num_guests,
        "image_url": image_url,
        "total_amount": total_amount,
    }

    if phone_number:
        booking_info["phone_number"] = phone_number
        logger.info("Using guest-provided phone number: %s", phone_number)
    elif from_number and from_number != "Unknown":
        booking_info["phone_number"] = from_number
        logger.info("Using caller's number from Twilio: %s", from_number)
    else:
        logger.warning("No phone number provided - backend will extract from Twilio")
    
    try:
        logger.info("Sending booking information to backend: %s", booking_info)
        req_ = requests.request(
            "POST",
            f"{os.getenv('API_URL')}/process-payment-sms/david-1",
            json=booking_info,
        )
        
        logger.info("Backend response status: %s", req_.status_code)
        
        if req_.status_code == 200:
            data = req_.json()
            payment_token = data.get("payment_token", "")
            logger.info("Payment token received: %s", payment_token)
            logger.info("SMS sent successfully")
            return "Thank you for choosing Rezolve Hotels"
        else:
            logger.error(
                "Backend returned error status: %s, response: %s",
                req_.status_code,
                req_.text,
            )
            return "There was an error processing your booking. Please try again later."
            
    except requests.exceptions.RequestException as e:
        logger.error("Request to backend failed: %s", e)
        return "There was an error processing your booking. Please try again later."
    except Exception as e:
        logger.error("Unexpected error in send_booking_to_backend: %s", e)
        return "There was an error processing your booking. Please try again later."
