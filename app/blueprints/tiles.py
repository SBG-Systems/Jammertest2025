import gzip
import os
import sqlite3

from flask import Blueprint, Response, abort, current_app

tiles_bp = Blueprint('tiles', __name__)

GZIP_MAGIC = b'\x1f\x8b'

@tiles_bp.route('/<int:z>/<int:x>/<int:y>.pbf')
def get_tile(z, x, y):
    mbtiles_path = current_app.config['MAP_CONFIG'].mbtiles_path
    if not os.path.isfile(mbtiles_path):
        abort(404, f'No mbtiles file at {mbtiles_path}. Run tools/build_map.sh to generate it.')

    tms_y = (2 ** z - 1) - y
    conn = sqlite3.connect(mbtiles_path)
    try:
        row = conn.execute(
            'SELECT tile_data FROM tiles WHERE zoom_level = ? AND tile_column = ? AND tile_row = ?',
            (z, x, tms_y)
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        abort(404)

    tile_data = row[0]
    if tile_data[:2] == GZIP_MAGIC:
        tile_data = gzip.decompress(tile_data)

    return Response(tile_data, mimetype='application/x-protobuf')
