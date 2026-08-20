from typing import List

from flask import Flask

from app.blueprints.api import api_bp
from app.blueprints.main import main_bp
from app.blueprints.tiles import tiles_bp
from app.models.config import INSConfig, MapConfig


def create_app(ins_configs: List[INSConfig] = None, map_config: MapConfig = None, monitor=None):
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
    app.config['INS_CONFIGS'] = ins_configs
    app.config['MAP_CONFIG'] = map_config
    app.config['MONITOR'] = monitor

    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(tiles_bp, url_prefix='/tiles')

    return app
