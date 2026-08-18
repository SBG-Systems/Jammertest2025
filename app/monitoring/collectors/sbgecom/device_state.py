import math
import threading
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional

import numpy as np

from src.logs.sbgecom_log_status import AIDING_GPS1_POS_RECV, AIDING_GPS2_POS_RECV
from src.sbgecom_ids import SbgEComLogId

# time_stamp is packed as a uint32 (microseconds since sensor power up), so it
# wraps around roughly every 71.6 minutes. Comparisons must happen in this
# wrapping space rather than as plain integer subtraction.
_TIME_STAMP_MODULO = 1 << 32


def _device_time_delta_us(a: int, b: int) -> int:
    """Signed a - b in the wrapping 32-bit device time_stamp space."""
    diff = (a - b) % _TIME_STAMP_MODULO
    if diff >= _TIME_STAMP_MODULO // 2:
        diff -= _TIME_STAMP_MODULO
    return diff


def _to_jsonable(value: Any) -> Any:
    """Recursively coerce pysbgecom values into strict, browser-parseable JSON.

    NaN/Infinity are valid in Python's json module but not in standard JSON:
    a browser's response.json() rejects them outright, which previously broke
    the whole /api/data response as soon as any field (e.g. EkfEuler's
    mag_declination without a calibrated magnetometer) was NaN.
    """
    if isinstance(value, np.ndarray):
        return [_to_jsonable(v) for v in value.tolist()]
    if isinstance(value, np.generic):
        return _to_jsonable(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, Enum):
        return value.name
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    return value


class SbgEComDeviceState:
    """Thread-safe aggregation of the latest sbgECom logs for one device.

    Continuously updated by the serial reader thread (via update()), and read
    on demand by the collector's fetch_data() - mirroring the shape produced
    by InsRestApiClient so downstream consumers (cache, API, UI) don't need
    to care whether an INS is reached over Ethernet or serial.

    Every sbgECom log carries its own time_stamp (microseconds since sensor
    power up), which is the device's own clock and the only rigorous way to
    tell whether a given log is still current: relying on our wall-clock
    receive time instead would only detect "we stopped receiving bytes", not
    "this particular log stopped being produced while others keep flowing".
    SbgEComLogUtc is the sole log that anchors that device clock to a real
    calendar date, so it's used as the reference to date every other log.

    Only fields with a well-known, stable meaning (EKF position/attitude,
    UTC time) are reshaped into the ins_measurement.ekf structure the map
    view relies on. Everything else (GNSS status, device status, ...) is
    kept under raw_logs using pysbgecom's native field names: matching the
    exact REST API nesting/enum strings for those requires cross-checking
    against the product's actual REST API implementation, not guessing.
    """

    _ONLINE_TIMEOUT_SECONDS = 3.0
    # A log whose time_stamp has fallen this far behind the device's current
    # time (tracked from whichever log was most recently received) is treated
    # as absent rather than replayed forever: e.g. if EKF_NAV stops being
    # output while other logs keep flowing, online stays True but the stale
    # nav fix must not keep being reported as the current position.
    _LOG_STALE_TIMEOUT_US = 3_000_000

    def __init__(self):
        self._lock = threading.RLock()
        self._last_activity_at: float = 0.0
        self._logs: Dict[str, Any] = {}
        self._latest_device_time_us: Optional[int] = None

    def mark_activity(self):
        with self._lock:
            self._last_activity_at = time.time()

    def update(self, msg_id: int, log: Any):
        with self._lock:
            self._last_activity_at = time.time()
            self._logs[self._log_key(msg_id)] = log

            time_stamp = getattr(log, "time_stamp", None)
            if time_stamp is not None:
                if (self._latest_device_time_us is None
                        or _device_time_delta_us(time_stamp, self._latest_device_time_us) > 0):
                    self._latest_device_time_us = time_stamp

    @staticmethod
    def _log_key(msg_id: int) -> str:
        try:
            return SbgEComLogId(msg_id).name.lower()
        except ValueError:
            return f"log_{msg_id}"

    def _get_fresh(self, key: str) -> Any:
        log = self._logs.get(key)
        if log is None or self._latest_device_time_us is None:
            return None

        age_us = _device_time_delta_us(self._latest_device_time_us, log.time_stamp)
        if age_us > self._LOG_STALE_TIMEOUT_US:
            return None
        return log

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            online = (time.time() - self._last_activity_at) <= self._ONLINE_TIMEOUT_SECONDS
            data = {
                "online": online,
                "ins_measurement": self._build_ins_measurement(),
                "status": self._build_status(),
                "raw_logs": {name: vars(log) for name, log in self._logs.items()},
            }
            if not online:
                data["error_message"] = "no data received from serial port"
            return _to_jsonable(data)

    def _build_ins_measurement(self) -> Dict[str, Any]:
        measurement: Dict[str, Any] = {}

        ekf_nav = self._get_fresh("ekf_nav")
        ekf_euler = self._get_fresh("ekf_euler")
        if ekf_nav is not None or ekf_euler is not None:
            ekf: Dict[str, Any] = {}
            if ekf_nav is not None:
                ekf["latitude"] = float(ekf_nav.position[0])
                ekf["longitude"] = float(ekf_nav.position[1])
                ekf["altitude"] = float(ekf_nav.position[2])
                ekf["posStd"] = [float(v) for v in ekf_nav.position_std_dev]
            if ekf_euler is not None:
                ekf["euler"] = [float(v) for v in ekf_euler.euler]
            measurement["ekf"] = ekf

        # Date the actual EKF measurement being reported (via its own
        # time_stamp), not just "whenever UTC_TIME itself last arrived" -
        # otherwise dateTime and the position it's shown next to can silently
        # refer to two different instants.
        dated_log = ekf_nav if ekf_nav is not None else ekf_euler
        date_time = self._real_date_time_of(dated_log) if dated_log is not None else self._real_date_time_of(self._get_fresh("utc_time"))
        if date_time is not None:
            measurement["dateTime"] = date_time

        return measurement

    def _build_status(self) -> Dict[str, Any]:
        """Best-effort status block matching the shape the UI unconditionally
        dereferences once online (data.status.utc/.ins/.aiding).

        Only utc status/clock state and EKF alignment are backed by real
        pysbgecom bitmask definitions. The INS solution "type" the REST API
        reports (singlePoint/dgps/sbas/rtkFloat/...) reflects which GNSS
        aiding quality is in use - that derivation isn't available from the
        EKF status word alone, so we surface the raw Kalman filter solution
        mode name instead of guessing a GNSS quality label.
        """
        status: Dict[str, Any] = {
            "utc": {"utcStatus": "invalid", "clockStatus": "error"},
            "ins": {"type": "invalid", "alignment": False},
            "aiding": {"gnss1": {"enabled": False}, "gnss2": {"enabled": False}},
        }

        utc_time = self._get_fresh("utc_time")
        if utc_time is not None:
            status["utc"] = {
                "utcStatus": utc_time.get_utc_status_as_string(),
                "clockStatus": utc_time.get_clock_state_as_string(),
            }

        ekf_source = self._get_fresh("ekf_nav") or self._get_fresh("ekf_euler")
        if ekf_source is not None:
            status["ins"] = {
                "type": ekf_source.get_solution_mode(ekf_source.status).name,
                "alignment": bool(ekf_source.status & ekf_source.SOL_ALIGN_VALID),
            }

        device_status = self._get_fresh("status")
        if device_status is not None:
            status["aiding"] = {
                "gnss1": {"enabled": bool(device_status.aiding_status & AIDING_GPS1_POS_RECV)},
                "gnss2": {"enabled": bool(device_status.aiding_status & AIDING_GPS2_POS_RECV)},
            }

        return status

    def _real_date_time_of(self, log: Any) -> Optional[str]:
        """Real-world UTC date/time at which `log` was captured on the device.

        Anchored on the freshest UTC_TIME log: it's the only log giving the
        device_time_stamp <-> calendar_date correspondence, so every other
        log's timestamp is dated relative to that anchor rather than assumed
        to be "now".
        """
        utc_time = self._get_fresh("utc_time")
        if utc_time is None or log is None:
            return None

        delta_us = _device_time_delta_us(log.time_stamp, utc_time.time_stamp)
        anchor = datetime(
            utc_time.year, utc_time.month, utc_time.day,
            utc_time.hour, utc_time.minute, utc_time.second,
            utc_time.nano_second // 1_000,
        )
        real_date_time = anchor + timedelta(microseconds=delta_us)
        return real_date_time.strftime("%Y-%m-%dT%H:%M:%S.") + f"{real_date_time.microsecond // 1000:03d}Z"
