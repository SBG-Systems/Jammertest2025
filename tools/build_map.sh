#!/usr/bin/env bash
set -euo pipefail

DEST_DIR="./data"
mkdir -p "$DEST_DIR"

DOWNLOAD_URLS=(
    "https://download.geofabrik.de/europe/france/ile-de-france-latest.osm.pbf"
    "https://download.geofabrik.de/europe/norway/nord-norge-latest.osm.pbf"
    "https://raw.githubusercontent.com/systemed/tilemaker/refs/heads/master/resources/config-openmaptiles.json"
    "https://raw.githubusercontent.com/systemed/tilemaker/refs/heads/master/resources/process-openmaptiles.lua"
    "https://raw.githubusercontent.com/systemed/tilemaker/refs/heads/master/get-landcover.sh"
    "https://raw.githubusercontent.com/systemed/tilemaker/refs/heads/master/get-coastline.sh"
)

SCRIPTS=(
    "get-landcover.sh"
    "get-coastline.sh"
)

download_if_missing() {
    local url="$1"
    local dest_dir="$2"
    local filename
    filename="$(basename "$url")"
    local filepath="${dest_dir}/${filename}"

    if [[ -f "$filepath" ]]; then
        echo "[SKIP] $filename already exists."
    else
        echo "[DL]   $filename"
        curl -fL --retry 3 -o "$filepath" "$url"
    fi
}

echo "=== Downloads ==="
for url in "${DOWNLOAD_URLS[@]}"; do
    download_if_missing "$url" "$DEST_DIR"
done

echo "=== Scripts ==="
for script in "${SCRIPTS[@]}"; do
    chmod +x "${DEST_DIR}/${script}"

    echo "[RUN]  $script"
    (cd "$DEST_DIR" && "./${script}")
done

echo "=== Build mbtiles ==="
for pbf_file in "${DEST_DIR}"/*.osm.pbf; do
    docker run --rm -it --pull always -v ${DEST_DIR}:/data -w /data ghcr.io/systemed/tilemaker:master \
        $(basename "$pbf_file") \
        --merge \
        --output /data/zones.mbtiles \
        --config /data/config-openmaptiles.json \
        --process /data/process-openmaptiles.lua
done
