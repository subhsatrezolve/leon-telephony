"""FastAPI main application for hotel booking API."""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routes import hotel_booking, health, livekit_room
# from src.database.connection import init_db

app = FastAPI(
    title="Hotel Booking API",
    description="API for hotel room booking and availability",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(hotel_booking.router, prefix="", tags=["hotel-booking"])
app.include_router(livekit_room.router, prefix="/agent", tags=["livekit"])

# @app.on_event("startup")
# async def startup_event():
#     """Initialize database on startup."""
#     await init_db()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)