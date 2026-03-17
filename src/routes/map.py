from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.config import get_trip
from src.map_builder import build_map

router = APIRouter(tags=["map"])
templates = Jinja2Templates(directory="templates")


@router.get("/map", response_class=HTMLResponse)
def map_page(request: Request) -> HTMLResponse:
    trip = get_trip()
    map_html = build_map(trip)
    return templates.TemplateResponse(
        "map.html",
        {"request": request, "map_html": map_html, "trip_name": trip.get("name", "Family Trip")},
    )
