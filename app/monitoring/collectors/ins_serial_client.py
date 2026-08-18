import logging
import threading
import time
from typing import Any, Dict

import serial

from common.interfaces.sbg_interface_serial import SbgInterfaceSerial
from src.sbgecom import SbgEComHandle
from src.sbgecom_ids import SbgEComClass

from app.monitoring.collectors.sbgecom.device_state import SbgEComDeviceState

logger = logging.getLogger(__name__)


class InsSerialClient:
    """Drop-in replacement for InsRestApiClient/FakeIns backed by a serial link.

    Unlike the REST client, data acquisition is push-based: a background
    thread continuously pumps pysbgecom's SbgEComHandle to decode the
    sbgECom stream, while fetch_data() just returns the latest aggregated
    snapshot without performing any I/O itself.
    """

    _RECONNECT_DELAY_SECONDS = 2.0
    _IDLE_SLEEP_SECONDS = 0.001

    def __init__(self, port: str, baudrate: int = 115200):
        self._port = port
        self._baudrate = baudrate
        self._state = SbgEComDeviceState()
        self._running = False
        self._thread = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def fetch_data(self) -> Dict[str, Any]:
        return self._state.snapshot()

    def _run(self):
        while self._running:
            handle = None
            try:
                interface = SbgInterfaceSerial(port=self._port, baudrate=self._baudrate)
                handle = SbgEComHandle(interface)
                handle.set_receive_log_call_back(self._on_log_received, None)
                logger.info(f"Opened serial port {self._port} at {self._baudrate} bauds")
                self._pump(handle)
            except (serial.SerialException, OSError) as exc:
                logger.error(f"Serial port {self._port} error: {exc}")
            finally:
                if handle:
                    handle.close()

            if self._running:
                time.sleep(self._RECONNECT_DELAY_SECONDS)

    def _pump(self, handle: SbgEComHandle):
        while self._running:
            try:
                payload = handle.handle_one_log()
            except RuntimeError:
                continue

            if payload:
                self._state.mark_activity()
            else:
                time.sleep(self._IDLE_SLEEP_SECONDS)

    def _on_log_received(self, msg_class: int, msg_id: int, log: Any, user_arg: Any):
        if msg_class == SbgEComClass.LOG_ECOM_0.value:
            self._state.update(msg_id, log)
