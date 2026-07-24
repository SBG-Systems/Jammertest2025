import threading
import time
import logging
from typing import Any, Dict, List

from app.models.config import INSConfig
from app.monitoring.collectors.ins_rest_api_client import InsRestApiClient
from app.monitoring.collectors.ins_serial_client import InsSerialClient
from app.monitoring.collectors.fake import FakeIns
from app.storage.cache_manager import get_or_create_cache


logger = logging.getLogger(__name__)

class MonitoringScheduler:
    def __init__(self):
        self._running = False
        self._monitor_thread = None
        self._update_interval_ns: float = 1e9
        self._clients = {}

    def setup(self, ins_configs: List[INSConfig] = None):
        for ins_config in ins_configs:
            if ins_config.connection_type == 'ethernet':
                self._clients[ins_config.id] = InsRestApiClient(ins_config.ip_address)
            elif ins_config.connection_type == 'serial':
                self._clients[ins_config.id] = InsSerialClient(ins_config.serial_port, ins_config.serial_baudrate)
            elif ins_config.connection_type == 'fake':
                self._clients[ins_config.id] = FakeIns()

    def start(self):
        if self._running:
            return

        for client in self._clients.values():
            start = getattr(client, 'start', None)
            if start:
                start()

        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def stop(self):
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=10)

        for client in self._clients.values():
            stop = getattr(client, 'stop', None)
            if stop:
                stop()

    def reboot(self, ins_id: str) -> None:
        client = self._clients[ins_id]
        reboot = getattr(client, 'reboot', None)
        if not reboot:
            raise NotImplementedError(f"Reboot is not supported for {ins_id}")
        reboot()

    def reboot_all(self) -> Dict[str, Dict[str, Any]]:
        results = {}
        for ins_id, client in self._clients.items():
            if not getattr(client, 'reboot', None):
                continue
            try:
                self.reboot(ins_id)
                results[ins_id] = {'success': True}
            except Exception as e:
                logger.error(f"Error on rebooting {ins_id}: {e}")
                results[ins_id] = {'success': False, 'error': str(e)}
        return results

    def _monitor_loop(self):

        cache = get_or_create_cache()

        while self._running:
            start_time = time.time_ns()
            for ins_id, client in self._clients.items():
                try:
                    data = client.fetch_data()
                    cache.store_data(ins_id, data)
                except Exception as e:
                    logger.error(f"Error on fetching data for {ins_id}: {e}")

            # Adjust to update_interval
            elapsed = time.time_ns() - start_time
            sleep_time = max(0., self._update_interval_ns - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time * 1e-9)
