from typing import Any, Dict, Optional, List

from pydantic import BaseModel, Field


class ToolTextResponse(BaseModel):
    response: str
    actions: list[Dict[str, Any]] = Field(default_factory=list)


class RecommendMenuRequest(BaseModel):
    session_id: str = Field(..., description="Session ID")
    menu_id: Optional[int] = Field(None, description="Menu ID")
    query: Optional[str] = Field(None, description="Free-text nearest-match search")
    category: Optional[str] = Field(None, description="Menu section name")
    tags: Optional[str] = Field(None, description="Comma-separated tag values")
    exclude_allergens: Optional[str] = Field(None, description="Comma-separated allergen names")
    dietary_options: Optional[str] = Field(None, description="Comma-separated dietary labels")
    calories: Optional[int] = Field(None, description="Exact calorie count")
    calories_gt: Optional[int] = Field(None, description="Minimum calories")
    calories_lt: Optional[int] = Field(None, description="Maximum calories")
    min_price: Optional[float] = Field(None, description="Minimum price")
    max_price: Optional[float] = Field(None, description="Maximum price")
    alcoholic_only: Optional[bool] = Field(None, description="Only alcoholic items")
    page: int = Field(1, description="Page number")
    page_size: int = Field(5, description="Items per page")
    categories: list[str] = Field(default_factory=list, description="Dynamic list of categories")
    dietary_options_list: list[str] = Field(default_factory=list, description="Dynamic list of dietary options")
    allergens: list[str] = Field(default_factory=list, description="Dynamic list of allergens")


class GetFoodItemRequest(BaseModel):
    session_id: str = Field(..., description="Session ID")
    menu_id: Optional[int] = Field(None, description="Menu ID")
    item_id: int = Field(..., description="Product ID")


class ManageCartRequest(BaseModel):
    session_id: str = Field(..., description="Session ID")
    action: str = Field(..., description="Action: add, remove, update, clear")
    items: Optional[str] = Field(None, description="JSON string of items")


class ViewCartRequest(BaseModel):
    session_id: str = Field(..., description="Session ID")


class CheckoutRequest(BaseModel):
    session_id: str = Field(..., description="Session ID")


class CheckoutResponse(BaseModel):
    success: bool = Field(..., description="Whether checkout was successful")
    action: str = Field(..., description="Action taken: checkout_completed or checkout_failed")
    booking_data: Optional[Dict[str, Any]] = Field(None, description="Booking data sent to backend")
    backend_response: Optional[Dict[str, Any]] = Field(None, description="Response from backend payment service")
    error: Optional[str] = Field(None, description="Error message if checkout failed")
    message: Optional[str] = Field(None, description="User-friendly message")

