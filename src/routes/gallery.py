from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from src.config import get_trip
from src.gallery import get_gallery

router = APIRouter(tags=["gallery"])
templates = Jinja2Templates(directory="templates")

REPO_ROOT = Path(__file__).parent.parent.parent
PHOTOS_ROOT = REPO_ROOT / "data" / "photos"


@router.get("/gallery", response_class=HTMLResponse)
async def gallery_page(request: Request) -> HTMLResponse:
    trip = get_trip()
    gallery = get_gallery(trip)

    # Build lightbox_data: { leg_id: { stop_idx: [url1, url2, ...] } }
    lightbox_data: dict[str, dict[str, list[str]]] = {}
    for leg_id, leg_data in gallery.items():
        sections = leg_data.get("stops", []) + leg_data.get("cruise_ports", [])
        lightbox_data[leg_id] = {
            str(i): [p["url"] for p in section["photos"]]
            for i, section in enumerate(sections)
        }

    return templates.TemplateResponse(
        "gallery.html",
        {
            "request": request,
            "gallery": gallery,
            "trip_name": trip.get("name", "Family Trip"),
            "lightbox_data": lightbox_data,
        },
    )


@router.get("/api/gallery")
def gallery_json() -> dict[str, Any]:
    return get_gallery(get_trip())


@router.get("/api/gallery/photos/{leg_id}/{folder}/{filename}")
def serve_photo(leg_id: str, folder: str, filename: str) -> FileResponse:
    file_path = PHOTOS_ROOT / leg_id / folder / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Photo not found: {leg_id}/{folder}/{filename}")
    return FileResponse(path=str(file_path))
