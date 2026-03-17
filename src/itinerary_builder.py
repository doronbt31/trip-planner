from datetime import date, timedelta
from typing import Any

LEG_COLORS: dict[str, str] = {
    "copenhagen_pre": "#378ADD",
    "cruise": "#E8882A",
    "austria_flachau": "#3aaa5e",
    "grossarl": "#C9A84C",
}


def _parse_date(s: str) -> date:
    return date.fromisoformat(s)


def _fmt_date(d: date) -> str:
    return d.isoformat()


def _display_date(d: date) -> str:
    """Return e.g. 'Thu, Aug 6'."""
    return d.strftime("%a, %b %-d")


def _build_stop(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": raw.get("name", ""),
        "type": raw.get("type", "activity"),
        "notes": raw.get("notes") or None,
        "stroller_friendly": raw.get("stroller_friendly"),
        "photos_dir": raw.get("photos_dir", ""),
        "tips": raw.get("tips", []),
    }


def _copenhagen_days(leg: dict[str, Any], day_offset: int, leg_color: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for raw_day in leg.get("days", []):
        raw_date = raw_day.get("date")
        if not raw_date:
            continue
        stops = [_build_stop(s) for s in raw_day.get("stops", [])]
        result.append({
            "date": str(raw_date),
            "day_number": day_offset + len(result) + 1,
            "leg_id": leg["id"],
            "leg_name": leg["name"],
            "leg_color": leg_color,
            "theme": raw_day.get("theme", ""),
            "stops": stops,
            "cruise_port": None,
            "is_at_sea": False,
            "is_travel_day": False,
            "travel_notes": "",
        })
    return result


def _cruise_days(leg: dict[str, Any], day_offset: int, leg_color: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    # Group itinerary entries by date — multiple ports on same day (e.g. Aug 11)
    seen_dates: dict[str, list[dict[str, Any]]] = {}
    for entry in leg.get("itinerary", []):
        d = str(entry["date"])
        seen_dates.setdefault(d, []).append(entry)

    for d_str, entries in seen_dates.items():
        at_sea = any(e.get("port") == "At sea" for e in entries)
        cruise_port: list[dict[str, Any]] | None = None
        if not at_sea:
            ports = []
            for e in entries:
                ports.append({
                    "port": e.get("port", ""),
                    "arrival": e.get("arrival"),
                    "departure": e.get("departure"),
                    "notes": e.get("notes"),
                    "photos_dir": e.get("photos_dir", ""),
                    "tips": e.get("tips", []),
                })
            cruise_port = ports  # type: ignore[assignment]

        result.append({
            "date": d_str,
            "day_number": day_offset + len(result) + 1,
            "leg_id": leg["id"],
            "leg_name": leg["name"],
            "leg_color": leg_color,
            "theme": "At Sea" if at_sea else (entries[0].get("port", "")),
            "stops": [],
            "cruise_port": cruise_port,
            "is_at_sea": at_sea,
            "is_travel_day": False,
            "travel_notes": "",
        })
    return result


def _austria_flachau_days(
    leg: dict[str, Any], day_offset: int, leg_color: str
) -> list[dict[str, Any]]:
    """
    austria_flachau uses day_range (e.g. "1-3") instead of a specific date per group.
    We still need real calendar dates. We calculate them from the leg start date.
    Aug 16 (index 0) is the travel day — handled separately — so the leg days start Aug 17.
    """
    leg_start = _parse_date(leg["dates"]["start"])
    # Aug 16 is a travel day generated separately; actual stay begins Aug 17
    stay_start = leg_start + timedelta(days=1)

    result: list[dict[str, Any]] = []
    for raw_day in leg.get("days", []):
        day_range: str = str(raw_day.get("day_range", ""))
        stops = [_build_stop(s) for s in raw_day.get("stops", [])]
        theme = raw_day.get("theme", "")

        # Parse range bounds (1-indexed relative to leg start day 1 = Aug 17)
        if "-" in day_range:
            start_rel, end_rel = [int(x) for x in day_range.split("-", 1)]
        else:
            start_rel = end_rel = int(day_range) if day_range else 1

        # Emit one card per calendar day in the range
        for rel_day in range(start_rel, end_rel + 1):
            cal_date = stay_start + timedelta(days=rel_day - 1)
            result.append({
                "date": _fmt_date(cal_date),
                "day_number": day_offset + len(result) + 1,
                "leg_id": leg["id"],
                "leg_name": leg["name"],
                "leg_color": leg_color,
                "theme": theme,
                "stops": stops,
                "cruise_port": None,
                "is_at_sea": False,
                "is_travel_day": False,
                "travel_notes": f"Day range {day_range}",
            })
    return result


def _grossarl_days(leg: dict[str, Any], day_offset: int, leg_color: str) -> list[dict[str, Any]]:
    start = _parse_date(leg["dates"]["start"])
    end = _parse_date(leg["dates"]["end"])
    highlights: list[str] = leg.get("highlights", [])
    travel_notes = "; ".join(highlights) if highlights else ""

    result: list[dict[str, Any]] = []
    current = start
    while current < end:
        result.append({
            "date": _fmt_date(current),
            "day_number": day_offset + len(result) + 1,
            "leg_id": leg["id"],
            "leg_name": leg["name"],
            "leg_color": leg_color,
            "theme": leg["stay"]["name"] if "stay" in leg and "name" in leg["stay"] else leg["name"],
            "stops": [],
            "cruise_port": None,
            "is_at_sea": False,
            "is_travel_day": False,
            "travel_notes": travel_notes,
        })
        current += timedelta(days=1)
    return result


def _travel_day(
    leg: dict[str, Any],
    day_number: int,
    leg_color: str,
    travel_notes: str,
    d: str,
) -> dict[str, Any]:
    return {
        "date": d,
        "day_number": day_number,
        "leg_id": leg["id"],
        "leg_name": leg["name"],
        "leg_color": leg_color,
        "theme": "Travel Day",
        "stops": [],
        "cruise_port": None,
        "is_at_sea": False,
        "is_travel_day": True,
        "travel_notes": travel_notes,
    }


def build_itinerary(trip: dict[str, Any]) -> list[dict[str, Any]]:
    legs: list[dict[str, Any]] = trip.get("legs", [])
    legs_by_id: dict[str, dict[str, Any]] = {leg["id"]: leg for leg in legs}

    all_days: list[dict[str, Any]] = []

    for leg in legs:
        leg_id: str = leg["id"]
        leg_color = LEG_COLORS.get(leg_id, "#888888")

        if leg_id == "copenhagen_pre":
            days = _copenhagen_days(leg, len(all_days), leg_color)
            all_days.extend(days)

        elif leg_id == "cruise":
            days = _cruise_days(leg, len(all_days), leg_color)
            all_days.extend(days)

        elif leg_id == "austria_flachau":
            # Aug 16 is a travel day: disembark + flight CPH→MUC + drive to Flachau
            flight = leg.get("logistics", {}).get("flight", {})
            flight_from = flight.get("from", "CPH")
            flight_to = flight.get("to", "MUC")
            dep = flight.get("departure", "")
            arr = flight.get("arrival", "")
            notes_parts = [
                "Disembark Copenhagen 08:00",
                f"Fly {flight_from} → {flight_to} {dep}–{arr}",
                "Drive to Flachau",
            ]
            if flight.get("notes"):
                notes_parts.append(flight["notes"])
            travel_note = " · ".join(notes_parts)

            travel = _travel_day(
                leg,
                day_number=len(all_days) + 1,
                leg_color=leg_color,
                travel_notes=travel_note,
                d=leg["dates"]["start"],
            )
            all_days.append(travel)

            stay_days = _austria_flachau_days(leg, len(all_days), leg_color)
            all_days.extend(stay_days)

        elif leg_id == "grossarl":
            days = _grossarl_days(leg, len(all_days), leg_color)
            all_days.extend(days)

        else:
            # Generic land leg fallback
            days = _copenhagen_days(leg, len(all_days), leg_color)
            all_days.extend(days)

    # Add human-readable date to each day
    for day in all_days:
        try:
            day["display_date"] = _display_date(_parse_date(day["date"]))
        except Exception:
            day["display_date"] = day["date"]

    return all_days


def build_legs_meta(trip: dict[str, Any]) -> list[dict[str, Any]]:
    """Return lightweight leg metadata for the sidebar/tabs."""
    legs: list[dict[str, Any]] = trip.get("legs", [])
    result = []
    for leg in legs:
        leg_id = leg["id"]
        dates = leg.get("dates", {})
        start = dates.get("start", "")
        end = dates.get("end", "")
        result.append({
            "id": leg_id,
            "name": leg.get("name", leg_id),
            "color": LEG_COLORS.get(leg_id, "#888888"),
            "date_range": f"{start} – {end}" if start and end else "",
        })
    return result
