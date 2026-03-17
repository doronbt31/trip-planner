"""Weather API routes."""
from typing import Any

from fastapi import APIRouter, HTTPException

from src.config import get_trip
from src.weather import get_weather_for_legs

router = APIRouter(tags=["weather"])


@router.get("/weather")
async def get_all_weather() -> dict[str, Any]:
    trip = get_trip()
    return await get_weather_for_legs(trip)


@router.get("/weather/{leg_id}")
async def get_leg_weather(leg_id: str) -> list[Any]:
    trip = get_trip()
    all_weather = await get_weather_for_legs(trip)
    if leg_id not in all_weather:
        raise HTTPException(status_code=404, detail=f"Leg '{leg_id}' not found")
    return all_weather[leg_id]
