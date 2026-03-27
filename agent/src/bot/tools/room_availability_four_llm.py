"""Additional room availability tools for four-llm-rps-hospitality agent architecture."""

import os
import json
import random
from langchain_core.tools import tool
from loguru import logger
from typing import Union, Optional
from datetime import datetime

# Load hotel rooms data from shared data directory under src/bot
try:
    bot_root = os.path.dirname(os.path.dirname(__file__))
    hotel_rooms_path = os.path.join(bot_root, "data", "hotel_rooms.json")
    if os.path.exists(hotel_rooms_path):
        with open(hotel_rooms_path, "r") as f:
            ROOMS_DATA = json.load(f)
    else:
        ROOMS_DATA = {"hotel_rooms": []}
        logger.warning("hotel_rooms.json not found in src/bot/data, using empty data")
except Exception as e:
    logger.warning(f"Could not load hotel_rooms.json from src/bot/data: {e}")
    ROOMS_DATA = {"hotel_rooms": []}

concierge_responses = [
    "What do you think? I'm happy to share more about any of these, or we can move forward with securing your room.",
    "Does one of these stand out to you? I can provide more details about the features, or if you're ready, let's reserve it for you.",
    "I'd love to tell you more about what each room, or if something has already caught your attention, we can finalize your booking right away."
]


@tool
def describe_room_to_guest(room_name: str) -> str:
    """Describe a specific room to the guest in a warm, concierge-style manner.
    
    Args:
        room_name: The name of the room to describe
    
    Returns:
        A detailed, conversational description of the room
    """
    try:
        rooms_list = ROOMS_DATA.get('hotel_rooms', [])
        
        # Function to convert price to spoken format
        def price_to_words(price_str):
            try:
                price_num = float(str(price_str).replace('$', '').replace(',', '').strip())
                ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine']
                teens = ['Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen']
                tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']
                
                def convert_hundreds(num):
                    result = ""
                    if num >= 100:
                        result += ones[num // 100] + " Hundred "
                        num %= 100
                    if num >= 20:
                        result += tens[num // 10] + " "
                        num %= 10
                    elif num >= 10:
                        result += teens[num - 10] + " "
                        num = 0
                    if num > 0:
                        result += ones[num] + " "
                    return result.strip()
                
                dollar_amount = int(price_num)
                if dollar_amount == 0:
                    return "Zero Dollars"
                
                result = ""
                if dollar_amount >= 1000:
                    thousands = dollar_amount // 1000
                    result += convert_hundreds(thousands) + " Thousand "
                    dollar_amount %= 1000
                
                if dollar_amount > 0:
                    result += convert_hundreds(dollar_amount)
                
                return result.strip() + " Dollars"
            except:
                return str(price_str)
        
        for room in rooms_list:
            if room_name.lower() in room["name"].lower():
                # Convert price to spoken format
                spoken_price = price_to_words(room['price_per_night'])
                
                # Create a warm, concierge-style description
                description = f"I'd be delighted to tell you about the {room['name']} at {room['hotel_name']}. "
                description += f"This exquisite room is priced at {spoken_price} per night and features {room['bed_option']}. "
                description += f"It comfortably accommodates {room['max_guests'].lower()}. "
                description += f"{room['luxurious_comfort']['description']} "
                description += "Would you like to proceed with booking this room, or would you prefer to hear about our other available options?"
                
                return description
        
        return f"I apologize, but I couldn't locate the '{room_name}' in our current inventory. May I suggest showing you our available room options instead? I'd be happy to help you find the perfect accommodation for your stay."
    except Exception as e:
        logger.error(f"Error in describe_room_to_guest: {e}")
        return "I'm terribly sorry, but I'm unable to retrieve the room information at the moment. Please allow me a moment to assist you with our available options."


@tool
def get_room_amenities(room_name: str, amenity_query: Optional[str] = None) -> str:
    """Return structured amenity data for a specific room as JSON.

    This tool is intentionally kept simple: it looks up the room in the
    shared JSON data and returns the relevant amenity fields so that the
    LLM can decide how best to answer questions like:
    - \"What amenities does this room have?\"
    - \"Does this room have laundry services?\"
    - \"Does this room include a bathtub or kitchen?\"

    Args:
        room_name: Name of the room to look up (substring match).
        amenity_query: Optional free-form text from the user about what
                       they're interested in. Currently not used for any
                       filtering; it is echoed back in the JSON payload
                       so the LLM can decide how to use it.

    Returns:
        A JSON string with keys like:
        {
          \"status\": \"ok\" | \"error\",
          \"room_name\": ...,
          \"hotel_name\": ...,
          \"amenity_query\": ...,
          \"area_details\": {...},
          \"max_guests\": ...,
          \"luxurious_comfort_description\": ...,
          \"amenities\": [...],            # primary amenity list
          \"accessible_features\": [...],  # accessibility-related features
        }

        On error, status will be \"error\" and a \"message\" field will
        describe what went wrong.
    """
    try:
        rooms_list = ROOMS_DATA.get("hotel_rooms", [])
        if not rooms_list:
            logger.error("No hotel_rooms found in ROOMS_DATA when calling get_room_amenities")
            return json.dumps(
                {
                    "status": "error",
                    "message": "No room data is currently available to look up amenities.",
                    "room_name": room_name,
                    "amenity_query": amenity_query,
                },
                ensure_ascii=False,
            )

        room = None
        for r in rooms_list:
            if not isinstance(r, dict):
                continue
            if room_name.lower() in r.get("name", "").lower():
                room = r
                break

        if not room:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"Room '{room_name}' was not found in the current inventory.",
                    "room_name": room_name,
                    "amenity_query": amenity_query,
                },
                ensure_ascii=False,
            )

        lux = room.get("luxurious_comfort", {}) or {}
        lux_features = lux.get("features", []) or []
        accessible_features = room.get("accessible_features", []) or []

        data = {
            "status": "ok",
            "room_name": room.get("name", room_name),
            "hotel_name": room.get("hotel_name"),
            "price_per_night": room.get("price_per_night"),
            "bed_option": room.get("bed_option"),
            "image_urls": room.get("image_urls", []) or [],
            "amenity_query": amenity_query,
            "area_details": room.get("area_details"),
            "max_guests": room.get("max_guests"),
            "luxurious_comfort_description": lux.get("description"),
            "amenities": lux_features + accessible_features,
            "accessible_features": accessible_features,
        }

        return json.dumps(data, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Error in get_room_amenities: {e}")
        return json.dumps(
            {
                "status": "error",
                "message": "Unexpected error while retrieving room amenities.",
                "room_name": room_name,
                "amenity_query": amenity_query,
            },
            ensure_ascii=False,
        )


def _parse_price_words_to_number(price_words: str) -> float:
    """Parse price words (e.g., 'Five Hundred Dollars') to numeric value."""
    try:
        text = str(price_words).replace("Dollars", "").strip().lower()
        if not text:
            return 0.0
        
        word_map = {
            'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
            'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
            'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15,
            'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19,
            'twenty': 20, 'thirty': 30, 'forty': 40, 'fifty': 50,
            'sixty': 60, 'seventy': 70, 'eighty': 80, 'ninety': 90
        }
        
        words = text.split()
        total = 0
        current = 0
        
        for word in words:
            if word == 'hundred':
                current = (current if current > 0 else 1) * 100
            elif word == 'thousand':
                total += (current if current > 0 else 1) * 1000
                current = 0
            elif word in word_map:
                current += word_map[word]
        
        total += current
        return float(total)
    except Exception as e:
        logger.error(f"Error parsing price words '{price_words}': {e}")
        return 0.0


def calculate_total_booking_amount(room_name: str, check_in_date: str, check_out_date: str) -> str:
    """Helper function to calculate total booking amount (can be called directly, not as a tool).
    
    Args:
        room_name: Name of the selected room
        check_in_date: Check-in date in YYYY-MM-DD format
        check_out_date: Check-out date in YYYY-MM-DD format
    
    Returns:
        Total amount as a number string (e.g., "1842") or "0" if calculation fails
    """
    try:
        rooms_list = ROOMS_DATA.get('hotel_rooms', [])
        room = None
        for r in rooms_list:
            if room_name.lower() in r.get("name", "").lower():
                room = r
                break
        
        if not room:
            logger.error(f"Room '{room_name}' not found")
            return "0"
        
        price_words = room.get("price_per_night", "")
        price_per_night = _parse_price_words_to_number(price_words)
        
        if price_per_night <= 0:
            logger.error(f"Invalid price for room '{room_name}': {price_words}")
            return "0"
        
        check_in = datetime.strptime(check_in_date, '%Y-%m-%d')
        check_out = datetime.strptime(check_out_date, '%Y-%m-%d')
        nights = (check_out - check_in).days
        
        if nights <= 0:
            logger.error(f"Invalid date range: check_in={check_in_date}, check_out={check_out_date}")
            return "0"
        
        total_amount = int(price_per_night * nights)
        logger.info(f"Calculated total for {room_name}: ${price_per_night}/night × {nights} nights = ${total_amount}")
        return str(total_amount)
    except Exception as e:
        logger.error(f"Error calculating total amount: {e}")
        return "0"


@tool
def get_total_booking_amount(room_name: str, check_in_date: str, check_out_date: str) -> str:
    """Calculate the total booking amount as a number (price_per_night × number_of_nights).
    
    Call this tool BEFORE asking for payment confirmation. The tool returns a number (e.g., '1842').
    You MUST convert this number to words and say: 'Your total payable amount for the stay is [amount in words]. Would you like to proceed with the payment?'
    
    Args:
        room_name: Name of the selected room
        check_in_date: Check-in date in YYYY-MM-DD format
        check_out_date: Check-out date in YYYY-MM-DD format
    
    Returns:
        Total amount as a number string (e.g., "1842") - LLM converts to words
    """
    return calculate_total_booking_amount(room_name, check_in_date, check_out_date)


@tool
def get_room_availability_room(
    check_in_date: str,
    check_out_date: str,
    min_guests: Union[int, str] = 1,
    amenities: Optional[str] = None,
    room_name: Optional[str] = None,
):
    """Discover available rooms for the guest, optionally filtering by amenities or room name.

    Normal flow (unchanged):
    - Use this to find rooms that can host the specified number of guests between the given dates.
    - The tool will return a warm, conversational suggestion of suitable rooms.

    Extended discovery flow:
    - If the guest asks for rooms with specific amenities (e.g. "bathtub", "sea view", "kitchen"),
      pass them as a comma-separated string in `amenities`. The tool will:
        * Filter rooms that can host the guest count
        * Further filter by the requested amenities
        * Return up to 5 matching rooms
    - If the guest asks for a room by name or part of the name, pass it via `room_name`.
      The tool will prioritise rooms whose name matches that text.
    - You can call this tool again even after the guest has already selected a room,
      for example if they want to review other options with different amenities.

    Args:
        check_in_date: Check-in date in YYYY-MM-DD format
        check_out_date: Check-out date in YYYY-MM-DD format
        min_guests: Number of guests (integer or string that can be converted to integer)
        amenities: Optional comma-separated list of amenity keywords for filtering (e.g. "bathtub,sea view")
        room_name: Optional room name or partial name text to search by
    """
    try:
        # Ensure min_guests is an integer
        if isinstance(min_guests, str):
            try:
                min_guests = int(min_guests)
            except ValueError:
                logger.error(f"Invalid min_guests value: {min_guests}")
                return "Invalid number of guests specified."

        available_rooms = []

        # Access the hotel_rooms list from the dictionary
        rooms_list = ROOMS_DATA.get('hotel_rooms', [])
        
        if not rooms_list:
            logger.error("No hotel_rooms found in ROOMS_DATA")
            return "Unable to retrieve room availability at this time."

        # Define guest capacity mapping
        guest_capacity_map = {
            "Up to Two Guests": 2,
            "Up to Three Guests": 3,
            "Up to Four Guests": 4,
            "Up to Eight Guests": 8
        }

        # Check if requested guests exceed maximum capacity
        if min_guests > 8:
            return "No rooms available for more than 8 guests."

        # Function to convert date format from YYYY-MM-DD to natural spoken format
        def format_date_naturally(date_str):
            try:
                from datetime import datetime
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                month_names = {
                    1: 'January', 2: 'February', 3: 'March', 4: 'April',
                    5: 'May', 6: 'June', 7: 'July', 8: 'August',
                    9: 'September', 10: 'October', 11: 'November', 12: 'December'
                }

                # Convert day to ordinal
                day = date_obj.day
                if day in [11, 12, 13]:
                    ordinal = f"{day}th"
                elif day % 10 == 1:
                    ordinal = f"{day}st"
                elif day % 10 == 2:
                    ordinal = f"{day}nd"
                elif day % 10 == 3:
                    ordinal = f"{day}rd"
                else:
                    ordinal = f"{day}th"

                return f"{month_names[date_obj.month]} {ordinal} {date_obj.year}"
            except:
                return date_str

        # Format dates naturally if provided
        formatted_checkin = format_date_naturally(check_in_date) if check_in_date else check_in_date
        formatted_checkout = format_date_naturally(check_out_date) if check_out_date else check_out_date

        # Pre-process filters
        amenity_terms = []
        if amenities:
            amenity_terms = [
                a.strip().lower()
                for a in str(amenities).split(",")
                if a and a.strip()
            ]

        room_name_query = str(room_name).strip().lower() if room_name else ""

        # Filter rooms that can accommodate the requested number of guests
        for room in rooms_list:
            if not isinstance(room, dict):
                logger.error(f"Room item is not a dictionary: {type(room)}")
                continue
            
            if "max_guests" not in room or "name" not in room:
                logger.error(f"Room missing required fields: {room}")
                continue

            # Get the capacity of this room
            room_capacity = guest_capacity_map.get(room["max_guests"], 0)

            # Basic capacity filter
            if room_capacity < min_guests:
                continue

            # Optional room name filter (partial, case-insensitive)
            if room_name_query and room_name_query not in room["name"].lower():
                continue

            # Optional amenities filter if amenity keywords are provided
            if amenity_terms:
                lux = room.get("luxurious_comfort", {}) or {}
                lux_features = lux.get("features", []) or []
                accessible_features = room.get("accessible_features", []) or []
                # Combine all feature-like fields into a searchable text
                all_features_text = " ".join(
                    [str(f) for f in lux_features + accessible_features]
                ).lower()

                # Require that every requested amenity term appears somewhere in the features text
                if not all(term in all_features_text for term in amenity_terms):
                    continue

            available_rooms.append(room["name"])

        logger.debug(f"Available rooms for {min_guests} guests: {available_rooms}")

        # No rooms matched any of the criteria
        if not available_rooms:
            if amenity_terms or room_name_query:
                return (
                    "I’m afraid I couldn’t find any rooms that match those specific details. "
                    "If you’d like, we can relax the amenity or name preferences and I can share other suitable options."
                )
            return "No rooms available for the specified dates and guest count."

        # Discovery-style response:
        # - If amenity or room-name filters are used → list up to 5 matching rooms
        # - Otherwise preserve the original 3-room suggestion flow
        guest_text = "guest" if min_guests == 1 else "guests"

        if amenity_terms or room_name_query:
            # Deterministic slicing instead of random choice, capped at 5 rooms
            matched_rooms = available_rooms[:5]
            rooms_str = "; ".join(matched_rooms)

            filter_desc_parts = []
            if room_name_query:
                filter_desc_parts.append(f"matching the name '{room_name}'")
            if amenity_terms:
                filter_desc_parts.append(
                    "that include " + ", ".join(amenity_terms)
                )
            filter_desc = " and ".join(filter_desc_parts) if filter_desc_parts else "suitable for your stay"

            return (
                f"For your stay from {formatted_checkin} to {formatted_checkout} for {min_guests} {guest_text}, "
                f"here are some rooms {filter_desc}: {rooms_str}. "
                "If any of these sound appealing, you can ask me to describe one in more detail or explore other options."
            )

        # Original flow: pick up to 3 rooms and present them in a concierge-style suggestion
        random_rooms = random.sample(available_rooms, min(3, len(available_rooms)))
        logger.debug(f"Randomly selected rooms: {random_rooms}")

        primary = random_rooms[0]
        alternates = random_rooms[1:]
        alt_text = ""
        if alternates:
            alt_text = f" Alternatively, the {' or the '.join(alternates)} would also be wonderful choices."

        return (
            f"Perfect! I have some lovely options for you from {formatted_checkin} to {formatted_checkout} "
            f"for {min_guests} {guest_text}. May I suggest the {primary}?{alt_text} "
            f"{random.choice(concierge_responses)}"
        )

    except Exception as e:
        logger.error(f"Error in get_room_availability_room: {e}")
        return "Unable to retrieve room availability at this time."

