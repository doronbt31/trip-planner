"""
Export trip planner pages to static HTML for GitHub Pages deployment.

Usage:
    python scripts/export_static.py [--out dist]

Fetches all pages from the FastAPI app using in-process ASGI transport,
rewrites internal links for static serving, copies static assets and photos.

Output layout:
    dist/
      index.html
      map.html
      itinerary.html
      gallery.html
      docs.html
      static/          ← copied from static/
      photos/          ← copied from data/photos/
"""
import argparse
import asyncio
import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import httpx

# ── URL rewrite rules applied to every exported page ──────────────────────────
# Order matters: more specific patterns first.
_REWRITES: list[tuple[str, str]] = [
    # Photo API URLs → local photos/ dir
    ('/api/gallery/photos/', 'photos/'),
    # Static assets
    ('/static/', 'static/'),
    # Internal navigation links (href= and src=)
    ('href="/itinerary#', 'href="itinerary.html#'),
    ('href="/gallery#', 'href="gallery.html#'),
    ('href="/itinerary"', 'href="itinerary.html"'),
    ('href="/map"', 'href="map.html"'),
    ('href="/gallery"', 'href="gallery.html"'),
    ('href="/docs"', 'href="docs.html"'),
    ('href="/chat"', 'href="chat.html"'),
    # "← Home" link and any explicit root href
    ('href="/"', 'href="index.html"'),
    # Chat API endpoint in fetch() calls — mark as unavailable
    ('"/api/chat"', '"#static-no-api"'),
]

# Pages to export: (url_path, output_filename)
_PAGES: list[tuple[str, str]] = [
    ("/", "index.html"),
    ("/map", "map.html"),
    ("/itinerary", "itinerary.html"),
    ("/gallery", "gallery.html"),
    ("/docs", "docs.html"),
    ("/chat", "chat.html"),
]


def _apply_rewrites(html: str) -> str:
    for old, new in _REWRITES:
        html = html.replace(old, new)
    return html


def _inject_static_banner(html: str) -> str:
    """Add a small banner to chat page noting AI is unavailable offline."""
    banner = (
        '<div style="background:#fff3cd;border:1px solid #ffc107;padding:8px 16px;'
        'font-size:0.82rem;text-align:center;color:#856404">'
        '⚠️ AI chat requires the live server — not available in this static snapshot.'
        '</div>'
    )
    return html.replace('<div id="chat-window"', banner + '\n  <div id="chat-window"', 1)


async def fetch_pages(out_dir: Path) -> None:
    # Import app here so REPO_ROOT is in sys.path
    from main import app  # noqa: PLC0415

    out_dir.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        for url_path, filename in _PAGES:
            print(f"  Fetching {url_path} …", end=" ", flush=True)
            try:
                resp = await client.get(url_path, follow_redirects=True)
                resp.raise_for_status()
            except Exception as exc:
                print(f"FAILED ({exc})")
                continue

            html = resp.text
            html = _apply_rewrites(html)
            if filename == "chat.html":
                html = _inject_static_banner(html)

            dest = out_dir / filename
            dest.write_text(html, encoding="utf-8")
            print(f"→ {dest.relative_to(REPO_ROOT)}")


def copy_assets(out_dir: Path) -> None:
    # static/
    src_static = REPO_ROOT / "static"
    dst_static = out_dir / "static"
    if src_static.exists():
        if dst_static.exists():
            shutil.rmtree(dst_static)
        shutil.copytree(src_static, dst_static)
        count = sum(1 for _ in dst_static.rglob("*") if _.is_file())
        print(f"  Copied static/ → {count} files")
    else:
        dst_static.mkdir(parents=True, exist_ok=True)
        print("  static/ is empty — skipped")

    # data/photos/ → dist/photos/
    src_photos = REPO_ROOT / "data" / "photos"
    dst_photos = out_dir / "photos"
    if src_photos.exists():
        photo_exts = {".jpg", ".jpeg", ".png", ".webp"}
        if dst_photos.exists():
            shutil.rmtree(dst_photos)
        dst_photos.mkdir(parents=True, exist_ok=True)

        count = 0
        for photo in src_photos.rglob("*"):
            if photo.is_file() and photo.suffix.lower() in photo_exts:
                rel = photo.relative_to(src_photos)
                dest = dst_photos / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(photo, dest)
                count += 1
        print(f"  Copied photos/ → {count} image{'s' if count != 1 else ''}")
    else:
        print("  data/photos/ not found — skipped")


def write_nojekyll(out_dir: Path) -> None:
    """GitHub Pages needs .nojekyll to serve files starting with underscore."""
    (out_dir / ".nojekyll").touch()
    print("  Created .nojekyll")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export trip planner to static HTML")
    parser.add_argument("--out", default="dist", help="Output directory (default: dist)")
    args = parser.parse_args()

    out_dir = REPO_ROOT / args.out
    print(f"\nExporting to {out_dir.relative_to(REPO_ROOT)}/\n")

    print("Pages:")
    asyncio.run(fetch_pages(out_dir))

    print("\nAssets:")
    copy_assets(out_dir)
    write_nojekyll(out_dir)

    # Summary
    html_files = list(out_dir.glob("*.html"))
    print(f"\nDone — {len(html_files)} HTML pages exported to {out_dir.relative_to(REPO_ROOT)}/")
    print(f"Test: open {out_dir / 'index.html'}")


if __name__ == "__main__":
    main()
