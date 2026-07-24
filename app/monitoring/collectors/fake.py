import json
import os
from typing import Any, Dict


class FakeIns:

    def __init__(self):
        pass

    def fetch_data(self) -> Dict[str, Any]:
        with open(os.path.join(os.path.dirname(__file__), 'fake_data.json'), 'r') as f:
            return json.load(f)
        return {}

    def reboot(self) -> None:
        pass

    def start_data_logger(self) -> None:
        pass

    def stop_data_logger(self) -> None:
        pass
