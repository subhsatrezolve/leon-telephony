"""Pydantic schemas for API models."""

from typing import Optional,Literal
from pydantic import BaseModel

class BaseRequest(BaseModel):
    source: Literal["web", "call"] = "web" 
    
class PaymentRequest(BaseModel):
    room_id:str
    index:int
    room_code:str

class SuggestionModel(BaseModel):
    room: str
    intent_of_visit: Optional[str] = None


class SendOfferRequest(BaseModel):
    room_id: str
    offer_code: Optional[str] = None
    roomOffers: Optional[str] = None


class RequestOffers(BaseModel):
    check_in_date: str
    check_out_date: str
    room_id: str
    room_code: str


class RequestRoom(BaseModel):
    check_in_date: str
    check_out_date: str
    number_of_adults: int = 1
    number_of_children: int = 0
    room_id: str = None
    show_cards: bool = True
    room_code: str = None
    topic: Optional[str] = None
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    bed_size: Optional[str] = None
    
class SuggestionModel(BaseModel):
    room: str

