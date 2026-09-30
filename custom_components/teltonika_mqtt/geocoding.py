"""Fully local reverse geocoding for Teltonika MQTT."""

from __future__ import annotations

from functools import lru_cache
import json
import math
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).parent / "data"
_POLYGON_FILE = _DATA_DIR / "geocoding_polygons.json"
_CYPRUS_FILE = _DATA_DIR / "geocoding.json"


@lru_cache(maxsize=1)
def _districts() -> tuple[dict[str, Any], ...]:
    with _POLYGON_FILE.open(encoding="utf-8") as file:
        return tuple(json.load(file)["districts"])


@lru_cache(maxsize=1)
def _cyprus_places() -> tuple[dict[str, Any], ...]:
    with _CYPRUS_FILE.open(encoding="utf-8") as file:
        return tuple(json.load(file)["places"])


def _point_in_ring(lon: float, lat: float, ring: list[list[float]]) -> bool:
    """Return whether a point is inside a linear ring using ray casting."""
    inside = False
    j = len(ring) - 1
    for i, (xi, yi) in enumerate(ring):
        xj, yj = ring[j]
        if ((yi > lat) != (yj > lat)) and (
            lon < (xj - xi) * (lat - yi) / (yj - yi) + xi
        ):
            inside = not inside
        j = i
    return inside


def _point_in_polygon(lon: float, lat: float, rings: list[list[list[float]]]) -> bool:
    """Return whether point is in polygon outer ring and outside its holes."""
    if not rings or not _point_in_ring(lon, lat, rings[0]):
        return False
    return not any(_point_in_ring(lon, lat, hole) for hole in rings[1:])


def _turkey_lookup(latitude: float, longitude: float) -> str | None:
    for district in _districts():
        min_lon, min_lat, max_lon, max_lat = district["bbox"]
        if not (min_lon <= longitude <= max_lon and min_lat <= latitude <= max_lat):
            continue
        for polygon in district["polygons"]:
            if _point_in_polygon(longitude, latitude, polygon):
                return f'{district["city"]} / {district["province"]}'
    return None


def _cyprus_lookup(latitude: float, longitude: float) -> str | None:
    """Use the compact Turkish-named Cyprus locality set until polygon data is bundled."""
    lat_scale = math.cos(math.radians(latitude))
    best: dict[str, Any] | None = None
    best_distance = float("inf")
    for place in _cyprus_places():
        dlat = latitude - float(place["lat"])
        dlon = (longitude - float(place["lon"])) * lat_scale
        distance = dlat * dlat + dlon * dlon
        if distance < best_distance:
            best_distance = distance
            best = place
    if best is None:
        return None
    return f'{best["city"]} / {best["province"]}'


def geocode_location(latitude: float, longitude: float) -> str | None:
    """Return bundled district/city and province without network access."""
    if 35.7 <= latitude <= 42.2 and 25.5 <= longitude <= 45.0:
        return _turkey_lookup(latitude, longitude)
    if 34.4 <= latitude <= 35.8 and 32.0 <= longitude <= 34.7:
        return _cyprus_lookup(latitude, longitude)
    return None
