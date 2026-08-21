#!/usr/bin/env bash
set -euo pipefail

# Frontend third-party assets (JS lib, font glyphs, icon sprite) are fetched here
# instead of being committed to the repo. Run this once after `poetry install`,
# while internet access is available - the app itself runs fully offline afterwards.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATIC_DIR="${SCRIPT_DIR}/../app/static"

MAPLIBRE_VERSION="4.7.1"
VENDOR_DIR="${STATIC_DIR}/vendor/maplibre-gl"

echo "=== MapLibre GL JS ${MAPLIBRE_VERSION} ==="
if [[ -f "${VENDOR_DIR}/maplibre-gl.js" ]]; then
    echo "[SKIP] already fetched."
else
    mkdir -p "$VENDOR_DIR"
    curl -fL --retry 3 -o "${VENDOR_DIR}/maplibre-gl.js" \
        "https://unpkg.com/maplibre-gl@${MAPLIBRE_VERSION}/dist/maplibre-gl.js"
    curl -fL --retry 3 -o "${VENDOR_DIR}/maplibre-gl.css" \
        "https://unpkg.com/maplibre-gl@${MAPLIBRE_VERSION}/dist/maplibre-gl.css"
fi

echo "=== Fonts (Roboto glyphs, for app/static/styles/osm-liberty/style.json) ==="
FONTS_DIR="${STATIC_DIR}/fonts"
if [[ -d "${FONTS_DIR}/Roboto Regular" ]]; then
    echo "[SKIP] already fetched."
else
    WORK_DIR="$(mktemp -d)"
    trap 'rm -rf "$WORK_DIR"' EXIT
    curl -fL --retry 3 -o "${WORK_DIR}/font-glyphs.zip" \
        "https://github.com/orangemug/font-glyphs/archive/refs/heads/gh-pages.zip"
    unzip -q "${WORK_DIR}/font-glyphs.zip" -d "$WORK_DIR"

    mkdir -p "$FONTS_DIR"
    for font in "Roboto Regular" "Roboto Medium" "Roboto Condensed Italic"; do
        rm -rf "${FONTS_DIR}/${font}"
        cp -r "${WORK_DIR}/font-glyphs-gh-pages/glyphs/${font}" "${FONTS_DIR}/${font}"
    done
fi

echo "=== Sprite (OSM Liberty icons) ==="
SPRITE_DIR="${STATIC_DIR}/sprites/osm-liberty"
if [[ -f "${SPRITE_DIR}/osm-liberty.png" ]]; then
    echo "[SKIP] already fetched."
else
    mkdir -p "$SPRITE_DIR"
    for f in osm-liberty.json osm-liberty.png "osm-liberty@2x.json" "osm-liberty@2x.png"; do
        curl -fL --retry 3 -o "${SPRITE_DIR}/${f}" \
            "https://raw.githubusercontent.com/maputnik/osm-liberty/gh-pages/sprites/${f}"
    done
fi

echo "=== Done ==="
