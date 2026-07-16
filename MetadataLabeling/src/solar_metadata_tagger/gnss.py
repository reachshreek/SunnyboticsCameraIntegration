from __future__ import annotations

import glob
import logging
import threading
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from .errors import MetadataTaggerError
from .models import GnssFix
from .nmea import NmeaParser

LOGGER = logging.getLogger(__name__)


class FixHistoryStore:
    """Thread-safe bounded GNSS history used to match fixes to frame capture time."""

    def __init__(self, maxlen: int = 256) -> None:
        if maxlen < 1:
            raise ValueError("maxlen must be positive")
        self._lock = threading.Lock()
        self._fixes: deque[GnssFix] = deque(maxlen=maxlen)

    def update(self, fix: GnssFix) -> None:
        with self._lock:
            self._fixes.append(fix)

    def snapshot(self) -> GnssFix | None:
        with self._lock:
            return self._fixes[-1] if self._fixes else None

    def select_for_capture(
        self,
        captured_at_utc: datetime,
        *,
        max_age_s: float,
        future_tolerance_s: float,
    ) -> GnssFix | None:
        """Prefer the newest fix at/before capture, then a very-near future fix."""
        if captured_at_utc.tzinfo is None:
            raise ValueError("captured_at_utc must be timezone-aware")
        with self._lock:
            fixes = tuple(self._fixes)
        before = [
            fix
            for fix in fixes
            if 0.0 <= fix.signed_age_seconds(captured_at_utc) <= max_age_s
        ]
        if before:
            return min(before, key=lambda fix: fix.signed_age_seconds(captured_at_utc))
        future = [
            fix
            for fix in fixes
            if -future_tolerance_s <= fix.signed_age_seconds(captured_at_utc) < 0.0
        ]
        if future:
            return min(future, key=lambda fix: abs(fix.signed_age_seconds(captured_at_utc)))
        return None


# Backward-compatible name used by the first version.
LatestFixStore = FixHistoryStore


class SerialGnssReader:
    """Resilient background reader for a NaviSys USB GNSS receiver emitting NMEA 0183."""

    def __init__(
        self,
        store: FixHistoryStore,
        port: str = "auto",
        baudrate: int = 9600,
        timeout_s: float = 1.0,
        reconnect_delay_s: float = 2.0,
    ) -> None:
        self.store = store
        self.port = port
        self.baudrate = baudrate
        self.timeout_s = timeout_s
        self.reconnect_delay_s = reconnect_delay_s
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._last_error: MetadataTaggerError | None = None
        self._resolved_port: str | None = None

    @property
    def last_error(self) -> MetadataTaggerError | None:
        return self._last_error

    @property
    def resolved_port(self) -> str | None:
        return self._resolved_port

    @property
    def is_alive(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self) -> None:
        if self.is_alive:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="gnss-reader", daemon=True)
        self._thread.start()

    def stop(self, timeout_s: float = 3.0) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout_s)

    def _run(self) -> None:
        try:
            import serial  # type: ignore
        except ImportError:
            self._last_error = MetadataTaggerError(
                "GNSS_DEPENDENCY_MISSING", "pyserial is required to read the USB GNSS receiver."
            )
            LOGGER.exception("GNSS dependency missing", extra={"event": "gnss_dependency_missing"})
            return

        parser = NmeaParser()
        while not self._stop.is_set():
            try:
                resolved_port = discover_serial_port(self.port)
                self._resolved_port = resolved_port
                LOGGER.info(
                    "Opening GNSS serial port",
                    extra={"event": "gnss_open", "port": resolved_port, "baudrate": self.baudrate},
                )
                with serial.Serial(resolved_port, self.baudrate, timeout=self.timeout_s) as device:
                    while not self._stop.is_set():
                        raw = device.readline()
                        if not raw:
                            continue
                        line = raw.decode("ascii", errors="replace").strip()
                        if not line:
                            continue
                        try:
                            fix = parser.parse(line, datetime.now(timezone.utc))
                        except MetadataTaggerError as exc:
                            LOGGER.warning(
                                "Rejected GNSS sentence",
                                extra={"event": "gnss_sentence_rejected", **exc.as_log_extra()},
                            )
                            continue
                        except Exception as exc:  # parser must not kill the reader thread
                            error = MetadataTaggerError(
                                "GNSS_PARSE_ERROR", "Unexpected GNSS parser failure.", detail=str(exc)
                            )
                            LOGGER.exception(
                                "Unexpected GNSS parser failure",
                                extra={"event": "gnss_parse_error", **error.as_log_extra()},
                            )
                            continue
                        if fix is not None:
                            self.store.update(fix)
                            self._last_error = None
            except Exception as exc:  # serial drivers can raise platform-specific exceptions
                if self._stop.is_set():
                    break
                error = (
                    exc
                    if isinstance(exc, MetadataTaggerError)
                    else MetadataTaggerError(
                        "GNSS_SERIAL_ERROR",
                        "GNSS serial connection failed.",
                        detail=str(exc),
                        exception_type=type(exc).__name__,
                    )
                )
                self._last_error = error
                LOGGER.error("GNSS reader error", extra={"event": "gnss_error", **error.as_log_extra()})
                self._stop.wait(self.reconnect_delay_s)


def discover_serial_port(configured_port: str) -> str:
    if configured_port != "auto":
        path = Path(configured_port)
        if not path.exists():
            raise MetadataTaggerError(
                "GNSS_DEVICE_NOT_FOUND", "Configured GNSS serial device does not exist.", path=str(path)
            )
        return str(path)

    by_id = sorted(glob.glob("/dev/serial/by-id/*"))
    if by_id:
        candidates = [
            p
            for p in by_id
            if any(
                token in Path(p).name.lower()
                for token in ("navisys", "u-blox", "ublox", "gnss", "gps")
            )
        ]
        return candidates[0] if candidates else by_id[0]

    fallback = sorted(glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*"))
    if fallback:
        return fallback[0]

    raise MetadataTaggerError(
        "GNSS_DEVICE_NOT_FOUND",
        "No USB GNSS serial device was found.",
        searched=["/dev/serial/by-id/*", "/dev/ttyACM*", "/dev/ttyUSB*"],
    )
