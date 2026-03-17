from datetime import date
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.config import get_trip

router = APIRouter(tags=["home"])
templates = Jinja2Templates(directory="templates")


def _build_reminders(trip: dict[str, Any]) -> list[dict[str, Any]]:
    """Return upcoming action items derived from trip data."""
    reminders = []

    for leg in trip.get("legs", []):
        if leg.get("id") == "cruise" and leg.get("booking", {}).get("balance_due"):
            booking = leg["booking"]
            reminders.append({
                "icon": "💳",
                "text": f"Cruise balance due: ${booking['balance_due']:,.2f} — booking {booking.get('number', '')}",
                "date": booking["balance_due_date"],
                "urgency": "urgent",
            })

        logistics = leg.get("logistics", {})
        flight = logistics.get("flight", {})
        if flight.get("order") and flight.get("date"):
            reminders.append({
                "icon": "✈️",
                "text": f"Flight check-in: {flight.get('from', '')} → {flight.get('to', '')} (order {flight['order']})",
                "date": flight["date"],
                "urgency": "soon",
            })

    # Sort by date
    reminders.sort(key=lambda r: r["date"])
    return reminders


@router.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    trip = get_trip()
    legs = trip.get("legs", [])

    # Compute trip date range
    starts = [l["dates"]["start"] for l in legs if l.get("dates", {}).get("start")]
    ends = [l["dates"]["end"] for l in legs if l.get("dates", {}).get("end")]
    trip_start = min(starts) if starts else ""
    trip_end = max(ends) if ends else ""

    # Compute trip length
    try:
        delta = date.fromisoformat(trip_end) - date.fromisoformat(trip_start)
        trip_days = delta.days + 1
    except Exception:
        trip_days = 0

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "trip_name": trip.get("name", "Family Trip"),
            "travelers": trip.get("travelers", []),
            "legs": legs,
            "trip_start": trip_start,
            "trip_end": trip_end,
            "trip_days": trip_days,
            "reminders": _build_reminders(trip),
        },
    )
