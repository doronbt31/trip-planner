# Trip Planner

A local web app for managing and serving family trip information and documents.
`trip.yaml` is the single source of truth.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
uvicorn main:app --reload
```

API docs available at http://localhost:8000/docs

## Project Structure

```
trip-planner/
├── trip.yaml              # Source of truth — trip data and document references
├── main.py                # FastAPI app entry point
├── data/
│   └── docs/              # PDF storage (subfolders: flights/, cruise/, hotels/, etc.)
├── src/
│   ├── config.py          # Loads and parses trip.yaml
│   └── routes/
│       ├── trip.py        # Trip info endpoints (/api/trip, /api/trip/legs)
│       └── docs.py        # Document serving endpoints (/api/docs)
├── templates/             # Jinja2 HTML templates (future frontend)
├── static/                # CSS/JS (future frontend)
└── requirements.txt
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/trip` | Full trip summary (name, dates, travelers, legs) |
| GET | `/api/trip/legs` | All trip legs |
| GET | `/api/trip/legs/{leg_id}` | Single leg by ID |
| GET | `/api/docs` | List all documents (id, label, type, leg, booking_ref) |
| GET | `/api/docs/{doc_id}` | Serve the PDF file for a document |

## Adding Documents

1. Place PDF files under `data/docs/<category>/` (e.g. `data/docs/flights/outbound.pdf`)
2. Reference the path in `trip.yaml` under the relevant leg's `documents` list
