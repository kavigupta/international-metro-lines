# International metro lines

Builds a GeoJSON of subway, light rail and tram routes from OpenStreetMap.

Each route is only produced in one direction to avoid duplication.
Each feature has a `color` and an `offset`, where `offset` is for interline spacing,
i.e., two interlined colors get -0.5 and +0.5 offsets; while 5 get -2, -1, 0, +1, +2 offsets.

```
pip install -r requirements.txt
conda install -c conda-forge tippecanoe
python fetch_global.py
```

This writes `data/transit.geojson`, and `data/transit.pmtiles`, the same lines as vector tiles
in the layer `transit`, which MapLibre can load a piece at a time with the `pmtiles` library.

Overpass responses are cached per tile in `cache/`, so you can run the script multiple times
and not re-download the same data. This also allows it to be resumable from interruption.