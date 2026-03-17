from pathlib import Path
from typing import Any

import yaml

TRIP_YAML_PATH = Path(__file__).parent.parent / "trip.yaml"

_trip_data: dict[str, Any] | None = None


def load_trip() -> dict[str, Any]:
    global _trip_data
    with open(TRIP_YAML_PATH, "r") as f:
        raw = yaml.safe_load(f)
    if "trip" not in raw:
        raise ValueError("trip.yaml must have a top-level 'trip' key")
    data = raw["trip"]
    # legs may be top-level (outside trip: block) or nested inside
    if "legs" not in data and "legs" in raw:
        data["legs"] = raw["legs"]
    if "logistics" not in data and "logistics" in raw:
        data["logistics"] = raw["logistics"]
    _trip_data = data
    return _trip_data


def get_trip() -> dict[str, Any]:
    if _trip_data is None:
        return load_trip()
    return _trip_data
