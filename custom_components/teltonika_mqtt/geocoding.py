"""Local geocoding helpers for Teltonika MQTT."""

from __future__ import annotations

from functools import lru_cache
import json
import math
from pathlib import Path
from typing import Any

_DATA_FILE = Path(__file__).parent / "data" / "geocoding.json"


@lru_cache(maxsize=1)
def _places() -> tuple[dict[str, Any], ...]:
    with _DATA_FILE.open(encoding="utf-8") as file:
        return tuple(json.load(file)["places"])


def geocode_location(latitude: float, longitude: float) -> str | None:
    """Return the nearest bundled city/district and province."""
    # Limit lookup to Turkey and Cyprus so unrelated coordinates never get
    # assigned to the nearest Turkish locality.
    in_turkey = 35.7 <= latitude <= 42.2 and 25.5 <= longitude <= 45.0
    in_cyprus = 34.4 <= latitude <= 35.8 and 32.0 <= longitude <= 34.7
    if not (in_turkey or in_cyprus):
        return None

    lat_scale = math.cos(math.radians(latitude))
    best: dict[str, Any] | None = None
    best_distance = float("inf")
    for place in _places():
        dlat = latitude - float(place["lat"])
        dlon = (longitude - float(place["lon"])) * lat_scale
        distance = dlat * dlat + dlon * dlon
        if distance < best_distance:
            best_distance = distance
            best = place

    if best is None:
        return None
    return f'{best["city"]} / {best["province"]}'
