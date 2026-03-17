"""Weather forecasts via Open-Meteo API (free, no key required)."""
import time
from datetime import date
from typing import Any

import httpx

# In-memory cache: key -> (timestamp, data)
_cache: dict[str, tuple[float, Any]] = {}
_CACHE_TTL = 3600.0  # 1 hour

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Copenhagen coordinates used for the cruise leg
_COPENHAGEN_LAT = 55.6761
_COPENHAGEN_LON = 12.5683

_WMO_MAP: dict[int, tuple[str, str]] = {
    0: ("☀️", "Clear"),
    1: ("🌤️", "Partly cloudy"),
    2: ("🌤️", "Partly cloudy"),
    3: ("🌤️", "Partly cloudy"),
    45: ("🌫️", "Foggy"),
    48: ("🌫️", "Foggy"),
    51: ("🌧️", "Rain"),
    53: ("🌧️", "Rain"),
    55: ("🌧️", "Rain"),
    61: ("🌧️", "Rain"),
    63: ("🌧️", "Rain"),
    65: ("🌧️", "Rain"),
    71: ("❄️", "Snow"),
    73: ("❄️", "Snow"),
    75: ("❄️", "Snow"),
    77: ("❄️", "Snow"),
    80: ("🌦️", "Showers"),
    81: ("🌦️", "Showers"),
    82: ("🌦️", "Showers"),
    95: ("⛈️", "Thunderstorm"),
    96: ("⛈️", "Thunderstorm"),
    99: ("⛈️", "Thunderstorm"),
}


def _wmo_to_icon(code: int) -> tuple[str, str]:
    return _WMO_MAP.get(code, ("🌡️", "Unknown"))


async def _fetch_forecast(lat: float, lon: float) -> dict[str, Any] | None:
    cache_key = f"{lat:.4f},{lon:.4f}"
    now = time.time()
    if cache_key in _cache:
        ts, data = _cache[cache_key]
        if now - ts < _CACHE_TTL:
            return data

    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode",
        "timezone": "auto",
        "forecast_days": 16,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(OPEN_METEO_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
            _cache[cache_key] = (now, data)
            return data
    except Exception:
        return None


def _parse_forecast(
    raw: dict[str, Any],
    start_date: str,
    end_date: str,
) -> list[dict[str, Any]]:
    """Parse Open-Meteo response into day dicts filtered to [start_date, end_date]."""
    daily = raw.get("daily", {})
    dates = daily.get("time", [])
    maxes = daily.get("temperature_2m_max", [])
    mins = daily.get("temperature_2m_min", [])
    precips = daily.get("precipitation_sum", [])
    codes = daily.get("weathercode", [])

    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)

    result: list[dict[str, Any]] = []
    for i, d in enumerate(dates):
        day_date = date.fromisoformat(d)
        if day_date < start or day_date > end:
            continue
        code = int(codes[i]) if i < len(codes) and codes[i] is not None else 0
        icon, description = _wmo_to_icon(code)
        result.append(
            {
                "date": d,
                "temp_max": round(maxes[i]) if i < len(maxes) and maxes[i] is not None else None,
                "temp_min": round(mins[i]) if i < len(mins) and mins[i] is not None else None,
                "precip": round(precips[i], 1) if i < len(precips) and precips[i] is not None else None,
                "icon": icon,
                "description": description,
            }
        )
    return result


async def get_weather_for_legs(trip_data: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Return weather forecast for each leg, keyed by leg id.

    For the 'cruise' leg, Copenhagen coordinates are used and a note is added.
    Each leg's forecast is filtered to its dates.start – dates.end range.
    """
    result: dict[str, list[dict[str, Any]]] = {}

    for leg in trip_data.get("legs", []):
        leg_id: str = leg.get("id", "")
        dates_block = leg.get("dates", {})
        start_date: str = dates_block.get("start", "")
        end_date: str = dates_block.get("end", "")
        if not start_date or not end_date:
            continue

        if leg_id == "cruise":
            lat, lon = _COPENHAGEN_LAT, _COPENHAGEN_LON
            note = {"note": "Weather shown for Copenhagen (embarkation port)"}
        else:
            coords = leg.get("coordinates")
            if not coords or len(coords) < 2:
                continue
            lat, lon = float(coords[0]), float(coords[1])
            note = None

        raw = await _fetch_forecast(lat, lon)
        if raw is None:
            result[leg_id] = [{"unavailable": True, "reason": "Weather API unreachable"}]
            continue

        days = _parse_forecast(raw, start_date, end_date)

        if not days:
            # Trip dates are outside the 16-day forecast window
            from datetime import date as _date, timedelta
            available_from = (_date.today() + timedelta(days=1)).isoformat()
            result[leg_id] = [{
                "unavailable": True,
                "reason": f"Forecast not yet available — trip starts {start_date}. Check back closer to departure.",
                "available_from": available_from,
            }]
            continue

        if note:
            result[leg_id] = [note] + days  # type: ignore[list-item]
        else:
            result[leg_id] = days

    return result
