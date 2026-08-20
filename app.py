#!/usr/bin/env python3
import logging

from app.utils.config import load_config_data, get_ins_configs, get_map_config
from app import create_app
from app.monitoring import create_monitor

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load app config
config_data = load_config_data('config.json')
ins_configs = get_ins_configs(config_data)
map_config = get_map_config(config_data)

# Create monitor
monitor = create_monitor(ins_configs=ins_configs)

# Create flask app
app = create_app(ins_configs=ins_configs, map_config=map_config, monitor=monitor)

# Start everything
if __name__ == '__main__':
    try:
        monitor.start()
        app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False, threaded=True)
    finally:
        monitor.stop()
