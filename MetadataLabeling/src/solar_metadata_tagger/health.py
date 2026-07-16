from __future__ import annotations

import os
import platform
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .gnss import FixHistoryStore, SerialGnssReader
from .models import utc_iso
from .storage import disk_usage, write_json_atomic


class HealthReporter:
    def __init__(
        self,
        root: Path,
        *,
        camera: Any,
        fix_store: FixHistoryStore,
        gnss_reader: SerialGnssReader | None,
        interval_s: float,
    ) -> None:
        self.root = root
        self.camera = camera
        self.fix_store = fix_store
        self.gnss_reader = gnss_reader
        self.interval_s = interval_s
        self._last_write_monotonic = 0.0

    def maybe_write(self, *, service_state: str, stats: dict[str, Any], force: bool = False) -> Path | None:
        now_mono = time.monotonic()
        if not force and now_mono - self._last_write_monotonic < self.interval_s:
            return None
        self._last_write_monotonic = now_mono
        fix = self.fix_store.snapshot()
        payload = {
            "timestamp_utc": utc_iso(datetime.now(timezone.utc)),
            "service_state": service_state,
            "pid": os.getpid(),
            "host": platform.node(),
            "machine": platform.machine(),
            "camera": self.camera.health(),
            "gnss": {
                "enabled": self.gnss_reader is not None,
                "reader_alive": self.gnss_reader.is_alive if self.gnss_reader else False,
                "port": self.gnss_reader.resolved_port if self.gnss_reader else None,
                "last_error": self.gnss_reader.last_error.as_dict()
                if self.gnss_reader and self.gnss_reader.last_error
                else None,
                "last_fix_received_at_utc": utc_iso(fix.received_at_utc) if fix else None,
                "coordinates_valid": fix.coordinates_valid if fix else False,
            },
            "storage": disk_usage(self.root),
            "mission": stats,
        }
        destination = self.root / "health" / "status.json"
        write_json_atomic(destination, payload)
        return destination
