# Trip Planner — Project Rules

## Source of Truth
- `trip.yaml` is the **only** source of truth. Never hardcode trip data in Python.
- When adding new data fields, update `trip.yaml` first, then adapt the code.

## Family
- This is a family of **5**: 2 adults + 3 children.
- Always verify traveler counts match 5 when reviewing documents or bookings.

## Data / Documents
- All PDF paths in `trip.yaml` are relative to the repo root (e.g. `data/docs/flights/...`).
- Never delete files from `data/docs/` — treat them as immutable booking records.

## Code Style
- Use Python type hints throughout.
- No database — keep all state in `trip.yaml` and in-memory at runtime.
- Keep routes thin; business logic belongs in helper functions, not route handlers.

## Itinerary Validation Checklist
When reviewing or modifying the itinerary, flag:
- Gaps between legs (a night with no accommodation)
- Mismatched ports (cruise disembark city ≠ next hotel city)
- Missing documents for any leg
- Traveler count mismatches on bookings
