from flask import Blueprint, render_template, current_app

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    ins_configs = current_app.config.get('INS_CONFIGS', {})
    map_config = current_app.config.get('MAP_CONFIG')
    return render_template('index.html', ins_configs=ins_configs, map_config=map_config)
