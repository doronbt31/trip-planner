from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.config import get_trip
from src.gallery import get_gallery
from src.itinerary_builder import build_itinerary, build_legs_meta
from src.weather import get_weather_for_legs

router = APIRouter(tags=["itinerary"])
templates = Jinja2Templates(directory="templates")


@router.get("/itinerary", response_class=HTMLResponse)
async def itinerary_page(request: Request) -> HTMLResponse:
    trip = get_trip()
    days = build_itinerary(trip)
    legs_meta = build_legs_meta(trip)

    # Fetch weather; if it fails for any reason, pass empty dict so template skips gracefully
    try:
        weather = await get_weather_for_legs(trip)
    except Exception:
        weather = {}

    # Build photo counts per photos_dir
    gallery = get_gallery(trip)
    photo_counts: dict[str, int] = {}
    for leg_data in gallery.values():
        for stop in leg_data.get("stops", []) + leg_data.get("cruise_ports", []):
            photo_counts[stop["photos_dir"]] = len(stop["photos"])

    # Build thumbnail lookup: photos_dir -> first photo URL (or None)
    thumbnails: dict[str, str | None] = {}
    for leg_data in gallery.values():
        for section in leg_data.get("stops", []) + leg_data.get("cruise_ports", []):
            photos = section.get("photos", [])
            thumbnails[section["photos_dir"]] = photos[0]["url"] if photos else None

    return templates.TemplateResponse(
        "itinerary.html",
        {
            "request": request,
            "days": days,
            "legs_meta": legs_meta,
            "trip_name": trip.get("name", "Family Trip"),
            "weather": weather,
            "photo_counts": photo_counts,
            "thumbnails": thumbnails,
        },
    )
