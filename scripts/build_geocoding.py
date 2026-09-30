#!/usr/bin/env python3
"""Build compact local district polygons for offline reverse geocoding."""

import json
import math
from pathlib import Path
from urllib.request import urlopen

BASE = "https://raw.githubusercontent.com/ttezer/turkiye-harita-verisi/master/dist"
GEO_URL = BASE + "/geojson/districts.geojson"
META_URL = BASE + "/json/districts.json"
OUT = Path("custom_components/teltonika_mqtt/data/geocoding_polygons.json")
TOLERANCE = 0.00035  # ~30-40 m; keeps the runtime bundle compact.


def fetch_json(url):
    with urlopen(url, timeout=120) as response:
        return json.load(response)


def point_segment_distance(p, a, b):
    x, y = p; x1, y1 = a; x2, y2 = b
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(x - x1, y - y1)
    t = max(0.0, min(1.0, ((x-x1)*dx + (y-y1)*dy)/(dx*dx+dy*dy)))
    return math.hypot(x-(x1+t*dx), y-(y1+t*dy))


def simplify(points, tolerance=TOLERANCE):
    if len(points) <= 4:
        return points
    closed = points[0] == points[-1]
    work = points[:-1] if closed else points
    if len(work) <= 3:
        return points
    keep = [False] * len(work)
    keep[0] = keep[-1] = True
    stack = [(0, len(work)-1)]
    while stack:
        start, end = stack.pop()
        best_i, best_d = None, 0.0
        for i in range(start+1, end):
            d = point_segment_distance(work[i], work[start], work[end])
            if d > best_d:
                best_i, best_d = i, d
        if best_i is not None and best_d > tolerance:
            keep[best_i] = True
            stack.extend(((start, best_i), (best_i, end)))
    result = [[round(work[i][0], 5), round(work[i][1], 5)] for i in range(len(work)) if keep[i]]
    if len(result) < 3:
        result = [[round(p[0], 5), round(p[1], 5)] for p in work[:3]]
    result.append(result[0])
    return result


def simplify_geometry(geometry):
    def polygon(rings):
        return [simplify(ring) for ring in rings if len(ring) >= 4]
    if geometry["type"] == "Polygon":
        return [polygon(geometry["coordinates"])]
    if geometry["type"] == "MultiPolygon":
        return [polygon(poly) for poly in geometry["coordinates"]]
    raise ValueError(geometry["type"])


def main():
    metadata = fetch_json(META_URL)
    geo = fetch_json(GEO_URL)
    by_hdx = {x["hdx_id"]: x for x in metadata}
    by_id = {x["id"]: x for x in metadata}
    districts = []
    for feature in geo["features"]:
        p = feature.get("properties", {})
        meta = by_hdx.get(p.get("hdx_id")) or by_id.get(p.get("id"))
        if meta is None:
            # Exported GeoJSON may use the normalized HDX id as its id.
            meta = by_hdx.get(p.get("parent_hdx_id")) if p.get("level") == "district" else None
        if meta is None:
            raise RuntimeError(f"Cannot map polygon properties: {p}")
        plate = meta["plate_code"]
        province = next((x["parent_name"] for x in []), None)
        districts.append({
            "city": meta["name"],
            "plate": plate,
            "bbox": [round(v, 5) for v in meta["bbox"]],
            "polygons": simplify_geometry(feature["geometry"]),
        })

    # Province names from stable plate-code mapping.
    provinces = {
        "01":"Adana","02":"Adıyaman","03":"Afyonkarahisar","04":"Ağrı","05":"Amasya","06":"Ankara","07":"Antalya","08":"Artvin","09":"Aydın","10":"Balıkesir",
        "11":"Bilecik","12":"Bingöl","13":"Bitlis","14":"Bolu","15":"Burdur","16":"Bursa","17":"Çanakkale","18":"Çankırı","19":"Çorum","20":"Denizli",
        "21":"Diyarbakır","22":"Edirne","23":"Elazığ","24":"Erzincan","25":"Erzurum","26":"Eskişehir","27":"Gaziantep","28":"Giresun","29":"Gümüşhane","30":"Hakkâri",
        "31":"Hatay","32":"Isparta","33":"Mersin","34":"İstanbul","35":"İzmir","36":"Kars","37":"Kastamonu","38":"Kayseri","39":"Kırklareli","40":"Kırşehir",
        "41":"Kocaeli","42":"Konya","43":"Kütahya","44":"Malatya","45":"Manisa","46":"Kahramanmaraş","47":"Mardin","48":"Muğla","49":"Muş","50":"Nevşehir",
        "51":"Niğde","52":"Ordu","53":"Rize","54":"Sakarya","55":"Samsun","56":"Siirt","57":"Sinop","58":"Sivas","59":"Tekirdağ","60":"Tokat",
        "61":"Trabzon","62":"Tunceli","63":"Şanlıurfa","64":"Uşak","65":"Van","66":"Yozgat","67":"Zonguldak","68":"Aksaray","69":"Bayburt","70":"Karaman",
        "71":"Kırıkkale","72":"Batman","73":"Şırnak","74":"Bartın","75":"Ardahan","76":"Iğdır","77":"Yalova","78":"Karabük","79":"Kilis","80":"Osmaniye","81":"Düzce"
    }
    for d in districts:
        d["province"] = provinces[d.pop("plate")]

    payload = {
        "source": "ttezer/turkiye-harita-verisi district polygons (HDX COD-AB-TUR; CC BY-IGO)",
        "method": "point-in-polygon",
        "simplification_tolerance_degrees": TOLERANCE,
        "districts": districts,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Wrote {len(districts)} districts, {OUT.stat().st_size} bytes")


if __name__ == "__main__":
    main()
