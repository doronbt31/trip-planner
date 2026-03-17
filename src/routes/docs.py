"""Document routes — HTML viewer and JSON API."""
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates

from src.config import get_trip

# HTML routes (no prefix)
router = APIRouter(tags=["docs"])
# API routes (registered under /api prefix in main.py)
api_router = APIRouter(tags=["docs-api"])

REPO_ROOT = Path(__file__).parent.parent.parent
DOCS_DIR = REPO_ROOT / "data" / "docs"

templates = Jinja2Templates(directory=str(REPO_ROOT / "templates"))

# Mapping from subfolder name → leg ids that folder is associated with
_FOLDER_TO_LEGS: dict[str, list[str]] = {
    "flights": ["copenhagen_pre", "austria_flachau"],
    "cruise": ["cruise"],
    "hotels": ["copenhagen_pre", "austria_flachau", "grossarl"],
}

# Booking ref embedded in the flights filenames
_FLIGHTS_BOOKING_REF = "ZKPHJW"
_CRUISE_BOOKING_NUMBERS = {"69970978", "69971030"}


def _derive_label(filename: str) -> str:
    """Turn a raw filename into a human-readable label."""
    return Path(filename).stem


def _derive_type(subfolder: str) -> str:
    mapping = {
        "flights": "flight",
        "cruise": "cruise",
        "hotels": "hotel",
    }
    return mapping.get(subfolder, "other")


def _booking_ref_for_file(filename: str, subfolder: str) -> str | None:
    """Extract a booking ref from a filename if detectable."""
    if subfolder == "flights" and _FLIGHTS_BOOKING_REF in filename:
        return _FLIGHTS_BOOKING_REF
    if subfolder == "cruise":
        for ref in _CRUISE_BOOKING_NUMBERS:
            if ref in filename:
                return ref
    return None


def _all_documents(trip_data: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Build document list by scanning data/docs/ subfolders.

    Associates files with legs based on subfolder name.
    Adds metadata from trip.yaml where available.
    """
    if trip_data is None:
        trip_data = get_trip()

    # Build a quick leg name lookup
    leg_names: dict[str, str] = {
        leg["id"]: leg.get("name", leg["id"])
        for leg in trip_data.get("legs", [])
    }

    docs: list[dict[str, Any]] = []
    doc_index = 0

    if not DOCS_DIR.exists():
        return docs

    # Scan top-level PDFs first (not in a subfolder)
    for pdf in sorted(DOCS_DIR.glob("*.pdf")):
        doc_index += 1
        doc_id = f"doc_{doc_index:03d}"
        rel_path = pdf.relative_to(REPO_ROOT)
        docs.append(
            {
                "id": doc_id,
                "label": _derive_label(pdf.name),
                "type": "other",
                "leg_id": None,
                "leg_name": None,
                "booking_ref": None,
                "path": str(rel_path),
                "file_exists": pdf.exists(),
            }
        )

    # Scan subfolders
    for subfolder in sorted(DOCS_DIR.iterdir()):
        if not subfolder.is_dir():
            continue
        folder_name = subfolder.name
        associated_legs = _FOLDER_TO_LEGS.get(folder_name, [])
        doc_type = _derive_type(folder_name)

        for pdf in sorted(subfolder.glob("*.pdf")):
            doc_index += 1
            doc_id = f"doc_{doc_index:03d}"
            rel_path = pdf.relative_to(REPO_ROOT)
            booking_ref = _booking_ref_for_file(pdf.name, folder_name)

            # Use first associated leg for display; if multiple, show them all
            primary_leg_id = associated_legs[0] if associated_legs else None
            primary_leg_name = leg_names.get(primary_leg_id, primary_leg_id) if primary_leg_id else None

            docs.append(
                {
                    "id": doc_id,
                    "label": _derive_label(pdf.name),
                    "type": doc_type,
                    "leg_id": primary_leg_id,
                    "leg_name": primary_leg_name,
                    "booking_ref": booking_ref,
                    "path": str(rel_path),
                    "file_exists": pdf.exists(),
                }
            )

    return docs


# ── HTML routes ────────────────────────────────────────────────────────────────

@router.get("/docs")
async def docs_page(request: Request):
    trip = get_trip()
    all_docs = _all_documents(trip)

    legs_meta = [
        {"id": leg["id"], "name": leg.get("name", leg["id"])}
        for leg in trip.get("legs", [])
    ]

    return templates.TemplateResponse(
        "docs.html",
        {
            "request": request,
            "docs": all_docs,
            "legs_meta": legs_meta,
            "trip_name": trip.get("name", "Trip"),
        },
    )


@router.get("/docs/view/{doc_id}")
async def doc_viewer(request: Request, doc_id: str):
    all_docs = _all_documents()
    doc = next((d for d in all_docs if d["id"] == doc_id), None)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found")

    return templates.TemplateResponse(
        "doc_viewer.html",
        {
            "request": request,
            "doc": doc,
            "trip_name": get_trip().get("name", "Trip"),
        },
    )


# ── API routes (registered under /api prefix) ─────────────────────────────────

@api_router.get("/docs")
def list_docs() -> list[dict[str, Any]]:
    """Return JSON list of all documents (no file path exposed)."""
    return [
        {k: v for k, v in doc.items() if k != "path"}
        for doc in _all_documents()
    ]


@api_router.get("/docs/{doc_id}/file")
def serve_doc_file(doc_id: str) -> FileResponse:
    """Serve raw PDF file — used by the iframe in doc_viewer.html."""
    for doc in _all_documents():
        if doc["id"] == doc_id:
            file_path = REPO_ROOT / doc["path"]
            if not file_path.exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"File for document '{doc_id}' not found at '{doc['path']}'",
                )
            return FileResponse(path=str(file_path), media_type="application/pdf")
    raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found")


@api_router.get("/docs/{doc_id}")
def serve_doc(doc_id: str) -> FileResponse:
    """Legacy endpoint — serves the PDF file (same as /file)."""
    return serve_doc_file(doc_id)
