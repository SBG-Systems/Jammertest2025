# SBG Systems - INS Monitoring system

Quick'n'Dirty Dashboard created fo follow INS data during Jammertest 2025

## Install

Ensure to have python and [Poetry](https://python-poetry.org/docs/#installation) installed and available in path.

```sh
# Install dependencies (creates the virtual env automatically)
poetry install

# Fetch frontend assets (MapLibre GL JS, map style fonts and icon sprite) -
# these aren't committed to the repo, so this needs internet access once.
tools/fetch_frontend_assets.sh
```


## Configure

Create `config.json` from `config_template.json`
Ensure each `id` field is unique upon all configured INS.

`config.json` expects an object with a `devices` array and a `map` object.

`devices` is an array of INS configuration objects. Available fields are :

- `id` **mandatory** Unique ID for the system
- `name` **mandatory** Display name
- `connection_type` **mandatory**
    - `ethernet` Connect to INS through INS Rest API
    - `fake` Use local file at `<project source>/app/monitoring/collectors/fake_data.json` to send data
- `ip_address` **madatory** if `connection_type` is set to `ethernet`
- `color` Color as hex code (for map display)

`map` configures the trajectory map. Its `source` field selects between two modes :

- `source: "online"` (default, needs internet at runtime) - the map is a plain raster layer fetched from a classic XYZ tile service. Fields :
    - `tile_url` Raster tile URL template (defaults to `"https://tile.openstreetmap.org/{z}/{x}/{y}.png"`; no `{s}` subdomain placeholder - MapLibre doesn't support it)
    - `max_zoom` Maximum zoom level (defaults to `19`)
- `source: "mbtiles"` (works offline) - the app serves a local mbtiles file itself over `/tiles/<z>/<x>/<y>.pbf`, and MapLibre GL JS renders it client-side using the [OSM Liberty](app/static/styles/osm-liberty/LICENSE.md) style at `app/static/styles/osm-liberty/`. There is no external map server (tileserver-gl, MapTiler, ...) to run alongside the app. Fields :
    - `mbtiles_path` **mandatory** Path to the mbtiles file built by `tools/build_map.sh` (relative to the working directory `app.py` is run from)

```json
"map": { "source": "mbtiles", "mbtiles_path": "tools/data/zones.mbtiles" }
```

MapLibre GL JS, the OSM Liberty style's fonts and its icon sprite are fetched by `tools/fetch_frontend_assets.sh` (see Install) instead of being committed - only the adapted `style.json` itself is tracked in git. With `source: "mbtiles"`, once that script and `tools/build_map.sh` have been run, the whole dashboard, including the map, works fully offline.


## Run

```sh
poetry run python app.py
```

Go to [http://127.0.0.1:5000/](http://127.0.0.1:5000/)
