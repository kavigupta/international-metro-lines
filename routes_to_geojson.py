from collections import defaultdict

import shapely
from shapely.geometry import LineString, MultiLineString, Point

TRACK_ROLES = ("", "forward", "backward")


def routes_to_geojson(relations):
    """
    Takes the elements of an Overpass `out geom` response for route relations, and returns a GeoJSON
    FeatureCollection of lines with a `color` and an `offset`, which is how many line widths to shift
    a line so that colors sharing a track sit side by side.
    """
    masters = {
        m["ref"]: r["id"]
        for r in relations
        if r["tags"].get("type") == "route_master"
        for m in r["members"]
        if m["type"] == "relation"
    }
    routes = [r for r in relations if r["tags"].get("type") == "route" and "colour" in r["tags"]]
    kept = [r for group in group_by_route(routes, masters).values() for r in one_direction(group)]
    colors_by_way, coords_by_way = colors_on_tracks(kept)
    return {"type": "FeatureCollection", "features": features(colors_by_way, coords_by_way)}


def group_by_route(routes, masters):
    """Groups by route_master where there is one, since network, ref and color can repeat between cities."""
    groups = defaultdict(list)
    for r in routes:
        tags = r["tags"]
        if r["id"] in masters:
            key = "master", masters[r["id"]], tags["colour"].lower()
        else:
            key = tags.get("network"), tags.get("ref", tags.get("name")), tags["colour"].lower()
        groups[key].append(r)
    return groups


def one_direction(relations):
    """
    The relations running the same way as the longest one. Each direction is usually its own relation on
    its own track, so this leaves one line per route, while keeping branches.
    """
    lines = [track_line(r) for r in relations]
    longest = max(lines, key=lambda line: line.length)
    return [r for r, line in zip(relations, lines) if same_direction(line, longest)]


def track_line(relation):
    return MultiLineString([coords for _, coords in tracks(relation)])


def tracks(relation):
    for m in relation["members"]:
        if m["type"] == "way" and m["role"] in TRACK_ROLES:
            yield m["ref"], [(p["lon"], p["lat"]) for p in m["geometry"]]


def same_direction(a, b):
    a_start, a_end = endpoints(a)
    b_start, b_end = endpoints(b)
    return a_start.distance(b_start) + a_end.distance(b_end) <= a_start.distance(b_end) + a_end.distance(b_start)


def endpoints(line):
    return Point(line.geoms[0].coords[0]), Point(line.geoms[-1].coords[-1])


def colors_on_tracks(relations):
    colors_by_way = defaultdict(set)
    coords_by_way = {}
    for r in relations:
        for way, coords in tracks(r):
            colors_by_way[way].add(r["tags"]["colour"].lower())
            # consistent direction, so the same offset puts a color on the same side of adjacent ways
            coords_by_way[way] = coords if coords[0] <= coords[-1] else coords[::-1]
    return colors_by_way, coords_by_way


def features(colors_by_way, coords_by_way):
    """Joins consecutive tracks with the same color and offset into single lines."""
    lines = defaultdict(list)
    for way, colors in colors_by_way.items():
        colors = sorted(colors)
        for i, color in enumerate(colors):
            lines[color, i - (len(colors) - 1) / 2].append(LineString(coords_by_way[way]))
    result = []
    for (color, offset), parts in lines.items():
        merged = shapely.line_merge(MultiLineString(parts), directed=True)
        for line in getattr(merged, "geoms", [merged]):
            result.append(
                {
                    "type": "Feature",
                    "properties": {"color": color, "offset": offset},
                    "geometry": {"type": "LineString", "coordinates": [list(c) for c in line.coords]},
                }
            )
    return result
