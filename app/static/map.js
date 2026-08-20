class TrajectoryMonitor {
    constructor() {
        this.updateInterval = 1000;
        this.isRunning = false;
        this.map = null;

        this.insConfigs = new Map();
        this.trajectorySourceIds = {};
        this.markers = {};

        this.trackedIns = "";

        this.init();
    }

    init() {
        const mapConfig = window.MAP_CONFIG || {source: 'mbtiles'};

        if (mapConfig.source === 'online') {
            this.initMap({
                version: 8,
                sources: {
                    basemap: {
                        type: 'raster',
                        tiles: [mapConfig.tile_url],
                        tileSize: 256,
                        maxzoom: mapConfig.max_zoom,
                        attribution: '© OpenStreetMap contributors'
                    }
                },
                layers: [
                    {id: 'basemap', type: 'raster', source: 'basemap'}
                ]
            });
            return;
        }

        // MapLibre resolves vector tile/glyph URLs from a worker with no document
        // origin, so relative URLs from the style JSON must be made absolute here.
        fetch('/static/styles/osm-liberty/style.json')
            .then((response) => response.json())
            .then((style) => this.initMap(style));
    }

    initMap(style) {
        // Root-relative paths only: string-concat the origin so template tokens
        // like {z}/{x}/{y} or {fontstack}/{range} aren't URL-encoded away.
        const origin = window.location.origin;
        const toAbsolute = (path) => (/^https?:\/\//.test(path) ? path : origin + path);

        for (const source of Object.values(style.sources)) {
            if (source.tiles) {
                source.tiles = source.tiles.map(toAbsolute);
            }
        }
        if (style.glyphs) {
            style.glyphs = toAbsolute(style.glyphs);
        }

        this.map = new maplibregl.Map({
            container: 'map',
            style,
            center: [2.1662488, 48.9100065],
            zoom: 17
        });

        this.map.addControl(new maplibregl.NavigationControl());
        this.map.on('error', (e) => console.error('MapLibre error:', e && e.error));

        this.map.on('load', () => {
            if (typeof window.INS_CONFIGS !== 'undefined') {
                const insIds = Object.keys(window.INS_CONFIGS);

                insIds.forEach((insId) => {
                    const config = window.INS_CONFIGS[insId];

                    // Store configuration
                    this.insConfigs[insId] = {
                        name: config.name,
                        color: config.color,
                        visible: true
                    };

                    // Empty trajectory creation
                    const sourceId = `trajectory-${insId}`;
                    this.map.addSource(sourceId, {
                        type: 'geojson',
                        data: {
                            type: 'Feature',
                            geometry: {type: 'LineString', coordinates: []}
                        }
                    });
                    this.map.addLayer({
                        id: sourceId,
                        type: 'line',
                        source: sourceId,
                        paint: {
                            'line-color': config.color,
                            'line-width': 3,
                            'line-opacity': 0.8
                        }
                    });

                    // Marker
                    const el = document.createElement('div');
                    el.style.backgroundColor = config.color;
                    el.style.width = '16px';
                    el.style.height = '16px';
                    el.style.borderRadius = '50%';
                    el.style.border = '2px solid white';
                    el.style.boxShadow = '0 2px 6px rgba(0,0,0,0.3)';
                    // Hide marker at init. Display once it has data
                    el.style.opacity = '0';

                    const currentMarker = new maplibregl.Marker({element: el})
                        .setLngLat([2.1662488, 48.9100065]);

                    // Stores references
                    this.trajectorySourceIds[insId] = sourceId;
                    this.markers[insId] = currentMarker;
                });
            }

            this.startMonitoring();
        });
    }

    startMonitoring() {
        if (this.isRunning) return;

        this.isRunning = true;
        this.fetchData();
        this.intervalId = setInterval(() => this.fetchData(), this.updateInterval);
    }

    stopMonitoring() {
        this.isRunning = false;
        if (this.intervalId) {
            clearInterval(this.intervalId);
        }
    }

    async fetchData() {
        try {
            const response = await fetch('/api/positions');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            this.updateDisplay(data);

        } catch (error) {
            console.error('Error on fetching positions:', error);
        }
    }

    setTrackedIns(insId) {
        this.trackedIns = insId;
    }

    updateDisplay(positions) {
        const insIds = Object.keys(positions);
        insIds.forEach((insId) => {
            if (insId in this.trajectorySourceIds && positions[insId].length > 0) {
                if (this.insConfigs[insId].visible) {
                    // GeoJSON/MapLibre coordinates are [lng, lat], API positions are [lat, lng]
                    const coordinates = positions[insId].map(([lat, lng]) => [lng, lat]);
                    this.map.getSource(this.trajectorySourceIds[insId]).setData({
                        type: 'Feature',
                        geometry: {type: 'LineString', coordinates}
                    });

                    const [lat, lng] = positions[insId][0];
                    this.markers[insId].setLngLat([lng, lat]);
                    this.markers[insId].getElement().style.opacity = '1';
                    this.markers[insId].addTo(this.map);

                    if (this.trackedIns === insId) {
                        const [lastLat, lastLng] = positions[insId].at(-1);
                        this.map.panTo([lastLng, lastLat]);
                    }
                }
            }
        });
    }

    toggleInsVisibility(insId) {
        if (this.insConfigs[insId]){
            if (this.insConfigs[insId].visible) {
                this.hideIns(insId);
            } else {
                this.showIns(insId);
            }
            this.updateInsVisibilityToggle(insId);
        }
    }

    hideIns(insId) {
        if (this.trajectorySourceIds[insId]) {
            this.map.setLayoutProperty(this.trajectorySourceIds[insId], 'visibility', 'none');
            this.markers[insId].remove();
            this.insConfigs[insId].visible = false;
        }
    }

    showIns(insId) {
        if (this.trajectorySourceIds[insId]) {
            this.map.setLayoutProperty(this.trajectorySourceIds[insId], 'visibility', 'visible');
            this.markers[insId].addTo(this.map);
            this.insConfigs[insId].visible = true;
        }
    }

    updateInsVisibilityToggle(insId) {
        const button = document.getElementById(`map-toggle-${insId}`);
        if (button) {
            if (this.insConfigs[insId].visible) {
                button.textContent = '👁️ Visible';
                button.classList.remove('hidden');
            } else {
                button.textContent = '🙈 Hidden';
                button.classList.add('hidden');
            }
        }
    }

}

// Init map when page is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.trajectoryMonitor = new TrajectoryMonitor();
});
