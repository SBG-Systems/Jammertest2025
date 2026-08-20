import itertools
import json

from app.models.config import INSConfig, MapConfig
from typing import List

colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6',
          '#1abc9c', '#e67e22', '#34495e', '#e91e63', '#00bcd4']
color_cycle = itertools.cycle(colors)

def load_config_data(json_path: str) -> dict:
    with open(json_path, 'r') as f:
        return json.load(f)

def get_ins_configs(config_data: dict) -> List[INSConfig]:
    ins_configs = []
    for config_json_data in config_data["devices"]:
        if config_json_data["connection_type"] == 'ethernet':
            ins_configs.append(INSConfig(
                id=config_json_data["id"],
                name=config_json_data["name"],
                color=config_json_data.get("color", next(color_cycle)),
                connection_type=config_json_data["connection_type"],
                ip_address=config_json_data["ip_address"]
            ))
        elif config_json_data["connection_type"] == 'serial':
            ins_configs.append(INSConfig(
                id=config_json_data["id"],
                name=config_json_data["name"],
                color=config_json_data.get("color", next(color_cycle)),
                connection_type=config_json_data["connection_type"],
                serial_port=config_json_data["serial_port"],
                serial_baudrate=config_json_data.get("serial_baudrate", 115200),
                power_relay_gpio_pin=config_json_data.get("power_relay_gpio_pin", None)
            ))
        elif config_json_data["connection_type"] == 'fake':
            ins_configs.append(INSConfig(
                id=config_json_data["id"],
                name=config_json_data["name"],
                color=config_json_data.get("color", next(color_cycle)),
                connection_type=config_json_data["connection_type"]
            ))
    return ins_configs

def get_map_config(config_data: dict) -> MapConfig:
    map_json_data = config_data.get("map", {})
    source = map_json_data.get("source", "online")
    if source == "mbtiles":
        return MapConfig(source=source, mbtiles_path=map_json_data["mbtiles_path"])
    elif source == "online":
        return MapConfig(
            source=source,
            tile_url=map_json_data.get("tile_url", "https://tile.openstreetmap.org/{z}/{x}/{y}.png"),
            max_zoom=map_json_data.get("max_zoom", 19)
        )
    else:
        raise ValueError(f'Unknown map source "{source}", expected "mbtiles" or "online"')
