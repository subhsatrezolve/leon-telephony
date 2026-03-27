from dotenv import load_dotenv
import requests,logging
import pandas as pd
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class LotteAgent:
    def __init__(self, join_images=False, enable_logging=False):
        
        self.chat_history = []
        self.join_images = join_images
        self.enable_logging = enable_logging
        self.rooms = self.get_rooms()
        self.room_facilities = self.get_rooms_facilities()
        self.map_facilties_to_rooms()

    def log(self, message):
        if self.enable_logging:
            logging.info(message)

    def map_facilties_to_rooms(self):
        rooms = self.rooms
        facilities = self.room_facilities

        for room in rooms:
            room_name = room.get("name")
            matching_facility = next((facility for facility in facilities if facility["name"].lower() in room_name.lower()), None)

            if matching_facility:
                room["facilities"] = {
                    "features": matching_facility.get("features", []),
                    "description": matching_facility.get("description", ""),
                    "floor_plan_link": matching_facility.get("floor_plan_link")
                }
            else:
                room["facilities"] = {
                    "features": [],
                    "description": "",
                    "floor_plan_link": None
                }

        self.rooms = rooms

    def get_rooms_facilities(self):

        URLS = ["https://www.lottenypalace.com/the-palace",
                "https://www.lottenypalace.com/the-towers/rooms-and-suites",
                "https://www.lottenypalace.com/suites",
                "https://www.lottenypalace.com/royal-suite-collection"
                ]
        headers = {
            "User-Agent": "Mozilla/5.0"
        }


        data = []
        for URL in URLS:
            response = requests.get(URL, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')

            rooms = soup.select('.rooms-section__each-room')
            for room in rooms:
                name = room.select_one('h2').text.strip()

                features = [li.text.strip() for li in room.select('.room-features li')]
                description = room.select_one('.rooms-section__each-room--full-copy-holder > p')
                description = description.text.strip() if description else ''
                floor_plan_link_element = room.select(".rooms-section__each-room--copy-section > .room-features > li > a")
                floor_plan_link = None
                for element in floor_plan_link_element:
                    if 'href' in element.attrs:
                        floor_plan_link = element['href']
                        break
                data.append({
                    'name': name,
                    'features': features,
                    "description":description,
                    "floor_plan_link":floor_plan_link
                })
            return data
    def get_rooms(self):
        """
        Fetch all available rooms from the hotel API and format them for use.
        """
        url = "https://newbooking.azds.com/api/hotel/lotte-ny-palace/rooms?lang=en"
        response = requests.get(url)
        rooms = response.json().get('rooms', [])
        formatted_rooms = []

        for room in rooms:
            formatted_rooms.append({
                "name": room.get("name"),
                "code": room.get("code"),
                "max_occupants": room.get("maxOccupants", 0),
                "description": room.get("description", ""),
                "beds": room.get("beds", 0),
                "bed_types": ",".join(room.get("attributes", {}).get("bedtype", [])),
                "images": ",".join([i.get("url") for i in room.get("images", [])]) if self.join_images else room.get("images", []),
                "views": ",".join(room.get("attributes", {}).get("views", [])),
                "buildings": ",".join(room.get("attributes", {}).get("buildings", [])),
                "is_virtual_tour": bool(room.get("virtualTourUrl")),
                "virtual_tour_url": room.get("virtualTourUrl"),
                "amenities": room.get("amenitiesList", []),
                "soldOut": room.get("soldOut"),
                "numberOfUnits": room.get("numberOfUnits", 0)
            })
        self.log("Fetched and formatted room data.")
        return formatted_rooms

    def check_nearest_availability(self,from_date: str,to_date:str,adults:int = 1,children: int = 0):
        """
        from_date is users check-in date
        to_date is users check-out date
        
        Check the nearest availability for given date range and guest count.
        """
        
        from_date = pd.to_datetime(from_date, format="%m/%d/%Y") + pd.Timedelta(days=2)
        to_date = pd.to_datetime(to_date, format="%m/%d/%Y") + pd.Timedelta(days=7)
        
        # convert to yyyy-mm-dd format
        from_date = from_date.strftime("%Y-%m-%d")
        to_date = to_date.strftime("%Y-%m-%d")
        
        url = f"https://newbooking.azds.com/api/lotte-ny-palace/calendar?from={from_date}&to={to_date}&adults={adults}&children={children}&autoscroll=1&nightlyPricing=1"
        self.log("URL for nearest availability: "+url)
        response = requests.get(url)
        self.log(f"Fetching Calendar")
        availabilities = []
        try:
            availabilities_ = response.json().get("availabilities",[])
            for availability in availabilities_:
                status = availability.get("status")
                if status == "open":
                    availabilities.append(
                        {
                            "from":availability.get("from"),
                            "to": availability.get("to"),
                            "prices":availability.get("prices")
                        }
                    )
            return availabilities
        except Exception as e:
            pass
            

    def get_room_variant(self, from_date: str, to_date: str, adults: int = 1, children: int = 0):
        """
        Fetch available room variants for specific date range and guest count.
        """
        from_date = from_date.replace("/", "%2F")
        to_date = to_date.replace("/", "%2F")
        url = f"https://newbooking.azds.com/api/hotel/lotte-ny-palace/rates?from={from_date}&to={to_date}&adults={adults}&children={children}&lang=en"
        response = requests.get(url)
        self.log(f"Fetching room variants from URL: {url}")

        try:
            variants = response.json().get('rates', [])
            formatted = [{
                "name": v.get("description"),
                "variant_code": v.get("code"),
                "room_code": v.get("roomCode"),
                "currency": v.get("currency"),
                "base_price_before_tax": v.get("basePriceBeforeTax"),
                "base_price_after_tax": v.get("basePriceAfterTax"),
                "image": v.get("image"),
                "numberOfUnits": v.get("numberOfUnits", 0),
                "cancellationText": v.get("cancellationText", ""),
                "currency": v.get("currency", ""),
                "guaranteePolicy": v.get("guaranteePolicy", ""),
                "tax": v.get("tax", ""),
                "text": v.get("text", ""),
                "description": v.get("description", "")
            } for v in variants]
            self.log(f"Fetched {len(formatted)} room variants.")
            return formatted
        except Exception as e:
            self.log(f"Error parsing room variants: {str(e)}")
            return []

    def get_room_variant_by_room_code(self, room_code, room_variants_df) -> pd.DataFrame:
        """
        Filter room variants by room code.
        """
        return room_variants_df[room_variants_df["room_code"] == room_code]

    def run(self, check_in_date: str, check_out_date: str, number_of_adults: int, number_of_children: int, min_price: int = None, max_price: int = None, bed_size: str = None):
        """
        Combine room info and available variants for selected criteria.
        """
        variants = self.get_room_variant(check_in_date, check_out_date, number_of_adults, number_of_children)
        if not variants:
            self.log("No variants available for the provided criteria.")
            return "No rooms available for the selected date range and number of guests."

        if min_price is not None:
            variants = [v for v in variants if v.get('base_price_after_tax', 0) >= min_price]
        if max_price is not None:
            variants = [v for v in variants if v.get('base_price_after_tax', 0) <= max_price]

        if not variants:
            self.log("No variants available for the provided criteria after price filtering.")
            return "No rooms available for the selected date range and number of guests within the specified budget."

        room_variants_df = pd.DataFrame(variants)
        filtered_rooms = []
        for room in self.rooms:
            room_code = room.get("code")
            room_variant = self.get_room_variant_by_room_code(room_code, room_variants_df)
            variant_list = room_variant.to_dict(orient="records")

            if variant_list:  # Only add room if it has variants
                room["variants"] = variant_list
                filtered_rooms.append(room)
        
        if bed_size:
            filtered_rooms = [
                room for room in filtered_rooms
                if bed_size.lower() in room.get('bed_types', '').lower()
            ]

        # Sort rooms by the lowest price of their variants
        filtered_rooms.sort(key=lambda r: min([v.get('base_price_after_tax', float('inf')) for v in r['variants']]))

        self.log("Formatted final room data with variants.")
        return filtered_rooms

    