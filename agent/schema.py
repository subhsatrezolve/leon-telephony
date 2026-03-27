from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ToolTextResponse(BaseModel):
    response: str
    actions: list[Dict[str, Any]] = Field(default_factory=list)


class RoomAvailabilityRequest(BaseModel):
    check_in_date: str = Field(..., description="Check-in date in YYYY-MM-DD")
    check_out_date: str = Field(..., description="Check-out date in YYYY-MM-DD")
    min_guests: int = Field(1, description="Minimum number of guests")
    amenities: Optional[str] = Field(
        None,
        description=(
            "Optional comma-separated list of amenity keywords to filter rooms by, "
            "e.g. 'bathtub,sea view,kitchen'. Leave empty to ignore amenity filtering."
        ),
    )
    room_name: Optional[str] = Field(
        None,
        description=(
            "Optional room name or partial name text to search for, "
            "e.g. 'suite', 'ocean view'. Leave empty for general availability."
        ),
    )


class DescribeRoomRequest(BaseModel):
    room_name: str = Field(..., description="Room name to describe")


class RoomAmenitiesRequest(BaseModel):
    room_name: str = Field(..., description="Room name to get amenities for")
    amenity_query: Optional[str] = Field(
        "",
        description="Specific amenity the guest is asking about (e.g. 'laundry', 'bathtub', 'kitchen', 'wifi'). Leave empty for a general amenities overview.",
    )


class TotalAmountRequest(BaseModel):
    room_name: str
    check_in_date: str
    check_out_date: str


class BookingRequest(BaseModel):
    customer_name: Optional[str] = ""
    room_name: Optional[str] = ""
    check_in_date: Optional[str] = ""
    check_out_date: Optional[str] = ""
    num_guests: int = 1
    image_url: Optional[str] = ""
    phone_number: Optional[str] = ""
    from_number: Optional[str] = ""


class FAQRequest(BaseModel):
    question: str


class TravelInfoRequest(BaseModel):
    query: str


class WebSearchRequest(BaseModel):
    query: str = Field(
        ...,
        description="Natural-language web search query the agent wants answered.",
    )
    location_context: Optional[str] = Field(
        "",
        description=(
            "Optional location context for nearby/nearest queries, e.g. "
            "'Rezolve Hotel, 2 E 61st Street, New York, NY 10065'."
        ),
    )
    result_type: Optional[str] = Field(
        "generic",
        description='Optional routing hint: "generic" (default) or "places" for nearby/nearest lookups.',
    )

