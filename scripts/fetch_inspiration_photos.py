"""
Fetch inspiration photos from Unsplash for each stop in trip.yaml.

Usage:
    python scripts/fetch_inspiration_photos.py
    python scripts/fetch_inspiration_photos.py --leg copenhagen_pre

Requires:
    UNSPLASH_ACCESS_KEY in .env (free tier: 50 req/hour)
    pip install httpx python-dotenv pyyaml
"""
import argparse
import os
import sys
import time
from pathlib import Path

import httpx
import yaml
from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).parent.parent
UNSPLASH_API = "https://api.unsplash.com/search/photos"
PHOTOS_PER_STOP = 4
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def get_access_key() -> str:
    key = os.environ.get("UNSPLASH_ACCESS_KEY", "")
    if not key:
        print("ERROR: UNSPLASH_ACCESS_KEY not set. Add it to your .env file.")
        print("Sign up free at https://unsplash.com/developers")
        sys.exit(1)
    return key


def load_trip() -> dict:
    with open(REPO_ROOT / "trip.yaml") as f:
        raw = yaml.safe_load(f)
    data = raw.get("trip", {})
    if "legs" not in data and "legs" in raw:
        data["legs"] = raw["legs"]
    return data


def has_photos(folder: Path) -> bool:
    """Return True if the folder already contains at least one image file."""
    if not folder.exists():
        return False
    return any(f.suffix.lower() in SUPPORTED_EXTENSIONS for f in folder.iterdir())


def build_query(stop_name: str, context: str) -> str:
    return f"{stop_name} {context}".strip()


def fetch_photos(query: str, access_key: str, count: int = PHOTOS_PER_STOP) -> list[str]:
    """Call Unsplash search and return list of regular-size image URLs."""
    resp = httpx.get(
        UNSPLASH_API,
        params={"query": query, "per_page": count, "orientation": "landscape"},
        headers={"Authorization": f"Client-ID {access_key}"},
        timeout=15.0,
    )
    if resp.status_code == 429:
        print("  ⚠️  Rate limited — waiting 60s...")
        time.sleep(60)
        return fetch_photos(query, access_key, count)
    resp.raise_for_status()
    results = resp.json().get("results", [])
    return [r["urls"]["regular"] for r in results]


def download_photo(url: str, dest: Path, index: int) -> None:
    """Download a photo and save it with a sequential filename."""
    ext = ".jpg"
    filename = dest / f"photo_{index:02d}{ext}"
    with httpx.stream("GET", url, timeout=30.0, follow_redirects=True) as resp:
        resp.raise_for_status()
        with open(filename, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=8192):
                f.write(chunk)


def process_stop(
    name: str,
    photos_dir: str,
    query: str,
    access_key: str,
) -> int:
    """Fetch and download photos for one stop. Returns count of new photos."""
    folder = REPO_ROOT / photos_dir
    folder.mkdir(parents=True, exist_ok=True)

    if has_photos(folder):
        print(f"  ⏭  {name} — already has photos, skipping")
        return 0

    print(f"  🔍 {name} — searching: '{query}'")
    try:
        urls = fetch_photos(query, access_key)
    except httpx.HTTPStatusError as e:
        print(f"  ❌ {name} — API error {e.response.status_code}: {e}")
        return 0

    if not urls:
        print(f"  ⚠️  {name} — no results found")
        return 0

    for i, url in enumerate(urls, start=1):
        try:
            download_photo(url, folder, i)
        except Exception as e:
            print(f"  ❌ {name} — failed to download photo {i}: {e}")

    print(f"  ✅ {name} — saved {len(urls)} photos → {photos_dir}")
    time.sleep(0.3)  # be polite to the API
    return len(urls)


def process_leg(leg: dict, access_key: str) -> dict[str, int]:
    """Process all stops in a leg. Returns {stop_name: photo_count}."""
    leg_id = leg.get("id", "")
    leg_name = leg.get("name", leg_id)
    country = leg.get("country", "")
    print(f"\n📍 {leg_name}")

    results: dict[str, int] = {}

    if leg_id == "cruise":
        seen_dirs: set[str] = set()
        for port in leg.get("itinerary", []):
            photos_dir = port.get("photos_dir")
            if not photos_dir or photos_dir in seen_dirs or port.get("port") == "At sea":
                continue
            seen_dirs.add(photos_dir)
            port_name = port["port"].split(",")[0]  # "Geiranger, Norway" → "Geiranger"
            query = build_query(port_name, "Norway fjord")
            count = process_stop(port["port"], photos_dir, query, access_key)
            results[port["port"]] = count

    elif leg_id == "grossarl":
        photos_dir = leg.get("photos_dir")
        if photos_dir:
            stay = leg.get("stay", {})
            hotel_name = stay.get("name", "Kinderhotel Waldhof")
            query = build_query(hotel_name, "Austria Alps family hotel")
            count = process_stop(hotel_name, photos_dir, query, access_key)
            results[hotel_name] = count

    else:
        for day in leg.get("days", []):
            for stop in day.get("stops", []):
                photos_dir = stop.get("photos_dir")
                if not photos_dir:
                    continue
                stop_name = stop["name"]
                stop_type = stop.get("type", "")
                if stop_type in ("nature", "activity", "museum", "culture"):
                    context = f"{country}"
                elif stop_type == "food":
                    context = f"restaurant {country}"
                else:
                    context = country
                query = build_query(stop_name, context)
                count = process_stop(stop_name, photos_dir, query, access_key)
                results[stop_name] = count

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Unsplash inspiration photos for the trip")
    parser.add_argument("--leg", help="Only fetch for a specific leg ID (e.g. copenhagen_pre)")
    args = parser.parse_args()

    access_key = get_access_key()
    trip = load_trip()
    legs = trip.get("legs", [])

    if args.leg:
        legs = [l for l in legs if l.get("id") == args.leg]
        if not legs:
            print(f"ERROR: leg '{args.leg}' not found in trip.yaml")
            sys.exit(1)

    total_photos = 0
    total_stops = 0

    for leg in legs:
        results = process_leg(leg, access_key)
        total_photos += sum(results.values())
        total_stops += len(results)

    print(f"\n✨ Done — {total_photos} photos fetched across {total_stops} stops")
    print("Drop your real trip photos into the same folders after the trip — they'll replace these automatically.")


if __name__ == "__main__":
    main()
