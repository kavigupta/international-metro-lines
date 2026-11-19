import time

import requests

QUERY = """
[out:json][timeout:{timeout}];
relation["type"="route"]["route"~"^(subway|light_rail|tram)$"]({south},{west},{north},{east})->.routes;
.routes out geom;
rel(br.routes)["type"="route_master"];
out body;
"""


SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]


class OverpassTimeout(Exception):
    pass


def fetch_routes(south, west, north, east, timeout=600):
    """Elements of the routes in the box, and the route_masters they belong to."""
    query = QUERY.format(south=south, west=west, north=north, east=east, timeout=timeout)
    wait = 10
    attempt = 0
    while True:
        server = SERVERS[attempt % len(SERVERS)]
        attempt += 1
        try:
            response = requests.post(
                server,
                data={"data": query},
                headers={"User-Agent": "international-metro-lines/0.1", "Accept": "application/json"},
                timeout=(30, timeout + 100),
            )
            if response.status_code not in (429, 502, 503, 504):
                break
            problem = response.status_code
        except (requests.ConnectionError, requests.Timeout) as e:
            problem = type(e).__name__
        if attempt % len(SERVERS) != 0:
            print(f"{server} gave {problem}, trying the next server")
            continue
        print(f"{server} gave {problem}, all servers tried, retrying in {wait}s")
        time.sleep(wait)
        wait = min(wait * 2, 600)
    response.raise_for_status()
    result = response.json()
    # Overpass reports running out of time or memory as a remark on an otherwise successful response
    if "runtime error" in result.get("remark", ""):
        raise OverpassTimeout(result["remark"])
    return result["elements"]
