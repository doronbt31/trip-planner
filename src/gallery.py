from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).parent.parent
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def _photos_in_dir(photos_dir: str) -> list[dict[str, str]]:
    """Scan a directory and return list of photo dicts."""
    folder = REPO_ROOT / photos_dir
    if not folder.exists():
        return []
    photos = []
    for f in sorted(folder.iterdir()):
        if f.suffix.lower() in SUPPORTED_EXTENSIONS:
            # URL path: /api/gallery/photos/{leg_id}/{folder}/{filename}
            # We'll derive leg_id and folder from the path relative to data/photos/
            rel = f.relative_to(REPO_ROOT / "data" / "photos")
            parts = rel.parts  # e.g. ("copenhagen_pre", "day1_kings_gardens", "photo.jpg")
            if len(parts) == 3:
                leg_id, folder_name, filename = parts
                url = f"/api/gallery/photos/{leg_id}/{folder_name}/{filename}"
            else:
                url = f"/api/gallery/raw/{f.relative_to(REPO_ROOT)}"
            photos.append({
                "filename": f.name,
                "path": str(f.relative_to(REPO_ROOT)),
                "url": url,
                "caption": f.stem.replace("_", " ").replace("-", " ").title(),
            })
    return photos


def get_gallery(trip_data: dict[str, Any]) -> dict[str, Any]:
    """
    Returns:
    {
      leg_id: {
        "name": str,
        "stops": [
          { "name": str, "photos_dir": str, "photos": [...] }
        ],
        "cruise_ports": [   # only for cruise leg
          { "port": str, "photos_dir": str, "photos": [...] }
        ]
      }
    }
    """
    result: dict[str, Any] = {}

    for leg in trip_data.get("legs", []):
        leg_id = leg.get("id", "")
        leg_entry: dict[str, Any] = {
            "name": leg.get("name", leg_id),
            "stops": [],
            "cruise_ports": [],
        }

        if leg_id == "cruise":
            seen_dirs: set[str] = set()
            for port in leg.get("itinerary", []):
                photos_dir = port.get("photos_dir")
                if not photos_dir or photos_dir in seen_dirs:
                    continue
                seen_dirs.add(photos_dir)
                leg_entry["cruise_ports"].append({
                    "port": port.get("port", ""),
                    "photos_dir": photos_dir,
                    "photos": _photos_in_dir(photos_dir),
                })
        elif leg_id == "grossarl":
            photos_dir = leg.get("photos_dir")
            if photos_dir:
                leg_entry["stops"].append({
                    "name": leg.get("name", "Großarl"),
                    "photos_dir": photos_dir,
                    "photos": _photos_in_dir(photos_dir),
                })
        else:
            seen_dirs = set()
            for day in leg.get("days", []):
                for stop in day.get("stops", []):
                    photos_dir = stop.get("photos_dir")
                    if not photos_dir or photos_dir in seen_dirs:
                        continue
                    seen_dirs.add(photos_dir)
                    leg_entry["stops"].append({
                        "name": stop.get("name", ""),
                        "photos_dir": photos_dir,
                        "photos": _photos_in_dir(photos_dir),
                    })

        result[leg_id] = leg_entry

    return result
