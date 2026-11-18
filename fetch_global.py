import json
import os

from fetch_routes import OverpassTimeout, fetch_routes
from routes_to_geojson import routes_to_geojson

TILE_DEGREES = 10
CACHE = "cache/tiles"
OUTPUT = "data/transit.geojson"


def fetch_tile(south, west, size):
    """Elements in the tile, splitting it into quarters if Overpass can't do it in one go."""
    path = f"{CACHE}/{south}_{west}_{size}.json"
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    try:
        elements = fetch_routes(south, west, south + size, west + size)
    except OverpassTimeout:
        print(f"Splitting {south},{west} ({size} degrees)")
        half = size / 2
        elements = [
            e for s in (south, south + half) for w in (west, west + half) for e in fetch_tile(s, w, half)
        ]
    os.makedirs(CACHE, exist_ok=True)
    with open(path, "w") as f:
        json.dump(elements, f)
    return elements


def main():
    elements = {}
    for south in range(-90, 90, TILE_DEGREES):
        for west in range(-180, 180, TILE_DEGREES):
            tile = fetch_tile(south, west, TILE_DEGREES)
            print(f"{south},{west}: {len(tile)} elements")
            for e in tile:
                elements[e["type"], e["id"]] = e
    geojson = routes_to_geojson(list(elements.values()))
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w") as f:
        json.dump(geojson, f)
    print(f"Wrote {len(geojson['features'])} features to {OUTPUT}")


if __name__ == "__main__":
    main()
