from __future__ import annotations

import logging
import signal
import threading
import time
from typing import Any

from .camera import create_camera_source
from .config import TaggerConfig
from .errors import MetadataTaggerError
from .gnss import FixHistoryStore, SerialGnssReader
from .health import HealthReporter
from .mission import MissionStats
from .service import MetadataTaggingService
from .triggers import TriggerProvider

LOGGER = logging.getLogger(__name__)


class CaptureService:
    def __init__(self, config: TaggerConfig) -> None:
        self.config = config
        self.stop_event = threading.Event()
        self.fix_store = FixHistoryStore(config.gnss.history_size)
        self.gnss_reader = (
            SerialGnssReader(
                self.fix_store,
                port=config.gnss.port,
                baudrate=config.gnss.baudrate,
                timeout_s=config.gnss.timeout_s,
                reconnect_delay_s=config.gnss.reconnect_delay_s,
            )
            if config.gnss.enabled
            else None
        )
        self.camera = create_camera_source(config.camera)
        self.tagger = MetadataTaggingService(config, fix_store=self.fix_store)
        self.triggers = TriggerProvider(config.capture)
        self.stats = MissionStats(config.mission_id)
        self.health = HealthReporter(
            config.storage.root,
            camera=self.camera,
            fix_store=self.fix_store,
            gnss_reader=self.gnss_reader,
            interval_s=config.capture.health_interval_s,
        )

    def request_stop(self, *_: Any) -> None:
        self.stop_event.set()
        self.triggers.stop()

    def run(self) -> int:
        self._install_signal_handlers()
        LOGGER.info(
            "Capture service starting",
            extra={
                "event": "service_start",
                "robot_id": self.config.robot_id,
                "mission_id": self.config.mission_id,
                "camera_source": self.config.camera.source,
                "trigger_mode": self.config.capture.trigger_mode,
            },
        )
        if self.config.capture.startup_delay_s:
            self.stop_event.wait(self.config.capture.startup_delay_s)
        try:
            if self.gnss_reader:
                self.gnss_reader.start()
            self.camera.open()
            self.health.maybe_write(
                service_state="running", stats=self.stats.as_dict(), force=True
            )
            for trigger in self.triggers:
                if self.stop_event.is_set():
                    break
                trigger_payload = {
                    "trigger_id": trigger.trigger_id,
                    "triggered_at_utc": trigger.triggered_at_utc.isoformat().replace("+00:00", "Z"),
                    "mission_point_id": trigger.mission_point_id,
                    **trigger.metadata,
                }
                try:
                    frame = self.camera.capture(self.config.storage.effective_spool_dir)
                except MetadataTaggerError as exc:
                    self.stats.record_capture_failure(exc.as_dict())
                    self.triggers.mark_failure(trigger, exc)
                    LOGGER.error(
                        "Image capture failed",
                        extra={"event": "capture_failed", "trigger_id": trigger.trigger_id, **exc.as_log_extra()},
                    )
                    self.health.maybe_write(
                        service_state="degraded", stats=self.stats.as_dict(), force=True
                    )
                    if not self.config.capture.continue_on_error:
                        raise
                    self._recover_camera()
                    continue
                try:
                    result = self.tagger.tag_image(
                        frame.image_path,
                        captured_at_utc=frame.captured_at_utc,
                        captured_monotonic_ns=frame.monotonic_ns,
                        row=trigger.row,
                        panel=trigger.panel,
                        camera_metadata=frame.camera_metadata,
                        trigger_metadata=trigger_payload,
                    )
                except MetadataTaggerError as exc:
                    self.stats.record_tagging_failure(exc.as_dict())
                    self.triggers.mark_failure(trigger, exc)
                    LOGGER.error(
                        "Image tagging failed",
                        extra={"event": "tagging_failed", "trigger_id": trigger.trigger_id, **exc.as_log_extra()},
                    )
                    self.health.maybe_write(
                        service_state="degraded", stats=self.stats.as_dict(), force=True
                    )
                    if not self.config.capture.continue_on_error:
                        raise
                    continue
                self.stats.record_result(result)
                self.stats.write(self.config.storage.root)
                self.triggers.mark_success(trigger, result.as_dict())
                self.health.maybe_write(service_state="running", stats=self.stats.as_dict())
            return 0
        finally:
            self.request_stop()
            try:
                self.camera.close()
            finally:
                if self.gnss_reader:
                    self.gnss_reader.stop()
            self.stats.write(self.config.storage.root, final=True)
            self.health.maybe_write(
                service_state="stopped", stats=self.stats.as_dict(final=True), force=True
            )
            LOGGER.info(
                "Capture service stopped", extra={"event": "service_stop", **self.stats.as_dict(final=True)}
            )


    def _recover_camera(self) -> None:
        """Best-effort camera reconnect after a transient GigE/USB failure."""
        try:
            self.camera.close()
        except Exception:
            LOGGER.exception("Camera close failed during recovery", extra={"event": "camera_recovery_close_failed"})
        if self.stop_event.wait(self.config.camera.reconnect_delay_s):
            return
        try:
            self.camera.open()
            LOGGER.info("Camera recovered", extra={"event": "camera_recovered"})
        except MetadataTaggerError as exc:
            LOGGER.error(
                "Camera reconnect failed",
                extra={"event": "camera_reconnect_failed", **exc.as_log_extra()},
            )

    def _install_signal_handlers(self) -> None:
        if threading.current_thread() is not threading.main_thread():
            return
        signal.signal(signal.SIGTERM, self.request_stop)
        signal.signal(signal.SIGINT, self.request_stop)
