import time

import requests

QUERY = """
[out:json][timeout:{timeout}];
relation["type"="route"]["route"~"^(subway|light_rail|tram)$"]({south},{west},{north},{east})->.routes;
.routes out geom;
rel(br.routes)["type"="route_master"];
out body;
"""


class OverpassTimeout(Exception):
    pass


def fetch_routes(south, west, north, east, timeout=600):
    """Elements of the routes in the box, and the route_masters they belong to."""
    query = QUERY.format(south=south, west=west, north=north, east=east, timeout=timeout)
    wait = 10
    while True:
        response = requests.post(
            "https://overpass-api.de/api/interpreter",
            data={"data": query},
            headers={"User-Agent": "international-metro-lines/0.1", "Accept": "application/json"},
            timeout=timeout + 100,
        )
        if response.status_code not in (429, 502, 503, 504):
            break
        print(f"Overpass returned {response.status_code}, retrying in {wait}s")
        time.sleep(wait)
        wait = min(wait * 2, 600)
    response.raise_for_status()
    result = response.json()
    # Overpass reports running out of time or memory as a remark on an otherwise successful response
    if "runtime error" in result.get("remark", ""):
        raise OverpassTimeout(result["remark"])
    return result["elements"]
