from typing import Any

from fastapi import APIRouter, HTTPException

from src.config import get_trip

router = APIRouter(tags=["trip"])


@router.get("/trip")
def get_trip_summary() -> dict[str, Any]:
    trip = get_trip()
    legs = trip.get("legs", [])

    # Compute overall trip date range from legs if not set at top level
    dates = trip.get("dates")
    if not dates and legs:
        starts = [l["dates"]["start"] for l in legs if l.get("dates", {}).get("start")]
        ends = [l["dates"]["end"] for l in legs if l.get("dates", {}).get("end")]
        if starts and ends:
            dates = {"start": min(starts), "end": max(ends)}

    return {
        "name": trip.get("name"),
        "dates": dates,
        "travelers": trip.get("travelers", []),
        "legs": [
            {
                "id": leg.get("id"),
                "type": leg.get("type"),
                "name": leg.get("name"),
            }
            for leg in legs
        ],
    }


@router.get("/trip/legs")
def get_legs() -> list[dict[str, Any]]:
    trip = get_trip()
    return trip.get("legs", [])


@router.get("/trip/legs/{leg_id}")
def get_leg(leg_id: str) -> dict[str, Any]:
    trip = get_trip()
    for leg in trip.get("legs", []):
        if leg.get("id") == leg_id:
            return leg
    raise HTTPException(status_code=404, detail=f"Leg '{leg_id}' not found")
