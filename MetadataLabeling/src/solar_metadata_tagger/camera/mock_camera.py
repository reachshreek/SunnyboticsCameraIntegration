from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum, auto
from pathlib import Path
from typing import Any

import numpy as np

from .models import CapturedFrame

PLANNED_WIDTH_PX = 2448
PLANNED_HEIGHT_PX = 2048
PLANNED_PIXEL_FORMAT = "BayerRG8"


class CameraFault(Enum):
    NONE = auto()
    DISCONNECTED = auto()
    TIMEOUT = auto()
    UNAVAILABLE_AT_STARTUP = auto()
    DROPPED_FRAME = auto()
    DELAYED_FRAME = auto()
    INCOMPLETE_FRAME = auto()
    INVALID_FRAME = auto()


class MockCamera:
    """
    Implements CameraSource using synthetic or prerecorded images.

    Designed to be swapped for the real LUCID camera without changing
    any other part of the pipeline.

    Parameters
    ----------
    fault:
        Fault mode to simulate. Defaults to CameraFault.NONE.
    prerecorded_image_path:
        When set, capture() copies this file instead of generating a
        synthetic image.
    frame_delay_s:
        Extra delay injected before capture() returns. Used by
        CameraFault.DELAYED_FRAME.
    timeout_s:
        How long TIMEOUT fault sleeps before raising. Defaults to 30 s
        for production realism but should be set to a short value in
        tests.
    width, height:
        Image dimensions. Default to the planned LUCID resolution.
    pixel_format:
        Pixel format label written into camera_metadata.
    capture_interval_s:
        When set, capture() sleeps until this many seconds have elapsed
        since the previous capture. Simulates the configured fixed
        capture interval without a separate scheduler.
    """

    def __init__(
        self,
        *,
        fault: CameraFault = CameraFault.NONE,
        prerecorded_image_path: Path | None = None,
        frame_delay_s: float = 0.0,
        timeout_s: float = 30.0,
        width: int = PLANNED_WIDTH_PX,
        height: int = PLANNED_HEIGHT_PX,
        pixel_format: str = PLANNED_PIXEL_FORMAT,
        capture_interval_s: float | None = None,
    ) -> None:
        self.fault = fault
        self.prerecorded_image_path = prerecorded_image_path
        self.frame_delay_s = frame_delay_s
        self.timeout_s = timeout_s
        self.width = width
        self.height = height
        self.pixel_format = pixel_format
        self.capture_interval_s = capture_interval_s

        self._open = False
        self._frame_count = 0
        self._last_capture_monotonic: float | None = None

    def open(self) -> None:
        """
        Simulate camera startup.

        Raises RuntimeError when UNAVAILABLE_AT_STARTUP or
        DISCONNECTED is active so the application can exercise its
        startup-failure and recovery paths.
        """
        if self.fault in (
            CameraFault.UNAVAILABLE_AT_STARTUP,
            CameraFault.DISCONNECTED,
        ):
            raise RuntimeError(
                f"MockCamera: camera unavailable at startup "
                f"(fault={self.fault.name})"
            )
        self._open = True

    def capture(self, spool_dir: Path) -> CapturedFrame:
        """
        Return a CapturedFrame whose image file is written to spool_dir.

        Behaviour changes according to the active fault mode:

        - DISCONNECTED      raises RuntimeError immediately.
        - TIMEOUT           sleeps for timeout_s then raises RuntimeError.
        - DROPPED_FRAME     raises RuntimeError (frame never arrives).
        - DELAYED_FRAME     sleeps for frame_delay_s before returning.
        - INCOMPLETE_FRAME  writes a truncated file and returns it.
        - INVALID_FRAME     writes a zero-byte file and returns it.
        - NONE              writes a valid synthetic or prerecorded image.

        When capture_interval_s is set, the method sleeps until the
        configured interval has elapsed since the previous capture,
        simulating a fixed-rate capture schedule.
        """
        if not self._open:
            raise RuntimeError("MockCamera: camera is not open")

        if self.fault == CameraFault.DISCONNECTED:
            self._open = False
            raise RuntimeError("MockCamera: camera disconnected during capture")

        if self.fault == CameraFault.TIMEOUT:
            time.sleep(self.timeout_s)
            raise RuntimeError("MockCamera: camera timed out")

        if self.fault == CameraFault.DROPPED_FRAME:
            raise RuntimeError("MockCamera: frame dropped")

        if self.fault == CameraFault.DELAYED_FRAME:
            time.sleep(self.frame_delay_s)

        if self.capture_interval_s is not None:
            now = time.monotonic()
            if self._last_capture_monotonic is not None:
                elapsed = now - self._last_capture_monotonic
                remaining = self.capture_interval_s - elapsed
                if remaining > 0:
                    time.sleep(remaining)
            self._last_capture_monotonic = time.monotonic()

        spool_dir.mkdir(parents=True, exist_ok=True)

        captured_at = datetime.now(timezone.utc)
        monotonic_ns = time.monotonic_ns()
        frame_id = uuid.uuid4().hex[:16]
        image_path = spool_dir / f"mock_{frame_id}.png"

        if self.fault == CameraFault.INVALID_FRAME:
            image_path.write_bytes(b"")
        elif self.fault == CameraFault.INCOMPLETE_FRAME:
            image_path.write_bytes(b"\x89PNG\r\n\x1a\n")
        elif self.prerecorded_image_path is not None:
            import shutil
            shutil.copy2(self.prerecorded_image_path, image_path)
        else:
            self._write_synthetic_image(image_path)

        self._frame_count += 1

        return CapturedFrame(
            image_path=image_path,
            captured_at_utc=captured_at,
            monotonic_ns=monotonic_ns,
            camera_metadata=self._camera_metadata(frame_id),
        )

    def close(self) -> None:
        """Mark the camera as closed. Safe to call when already closed."""
        self._open = False

    def health(self) -> dict[str, Any]:
        """Return mock health information matching the real camera contract."""
        return {
            "mock": True,
            "open": self._open,
            "fault": self.fault.name,
            "frames_captured": self._frame_count,
            "width_px": self.width,
            "height_px": self.height,
            "pixel_format": self.pixel_format,
            "capture_interval_s": self.capture_interval_s,
        }

    def reconnect(self) -> None:
        """
        Clear a DISCONNECTED fault and reopen the camera.

        Call this from tests that simulate camera reconnection.
        """
        self.fault = CameraFault.NONE
        self._open = False
        self.open()

    def _write_synthetic_image(self, path: Path) -> None:
        """
        Write a synthetic Bayer-pattern PNG at the planned resolution.
        """
        try:
            import cv2
            rng = np.random.default_rng(seed=self._frame_count)
            pixels = rng.integers(
                0, 256, size=(self.height, self.width), dtype=np.uint8
            )
            cv2.imwrite(str(path), pixels)
        except ImportError:
            rng = np.random.default_rng(seed=self._frame_count)
            pixels = rng.integers(
                0, 256, size=(self.height, self.width), dtype=np.uint8
            )
            np.save(str(path), pixels)

    def _camera_metadata(self, frame_id: str) -> dict[str, Any]:
        return {
            "frame_id": frame_id,
            "width_px": self.width,
            "height_px": self.height,
            "pixel_format": self.pixel_format,
            "mock": True,
            "fault": self.fault.name,
        }


class MockSpeedProvider:
    """
    Implements SpeedProvider for capture-scheduler testing.

    Covers every speed scenario listed in section 4.2 of the
    validation procedure.

    Parameters
    ----------
    mode:
        One of the string values below.
    fixed_speed_mps:
        Speed returned in 'fixed' and 'changing' modes.
    speeds_mps:
        Sequence of speed values cycled through in 'sequence' mode.
    stale_age_s:
        How old to make the sample timestamp in 'stale' mode.
    """

    MODES = frozenset({
        "fixed",
        "stationary",
        "changing",
        "missing",
        "invalid",
        "stale",
        "sequence",
    })

    def __init__(
        self,
        mode: str = "fixed",
        *,
        fixed_speed_mps: float = 0.5,
        speeds_mps: list[float] | None = None,
        stale_age_s: float = 10.0,
    ) -> None:
        if mode not in self.MODES:
            raise ValueError(
                f"MockSpeedProvider: unknown mode {mode!r}. "
                f"Choose from {sorted(self.MODES)}"
            )
        self.mode = mode
        self.fixed_speed_mps = fixed_speed_mps
        self.speeds_mps = speeds_mps or []
        self.stale_age_s = stale_age_s
        self._call_count = 0

    def sample(self):
        """Return a SpeedSample or None depending on the active mode."""
        from .speed import SpeedSample

        self._call_count += 1

        if self.mode == "missing":
            return None

        if self.mode == "invalid":
            return SpeedSample(
                speed_mps=float("nan"),
                measured_at_utc=datetime.now(timezone.utc),
                source="mock-invalid",
            )

        if self.mode == "stale":
            stale_time = (
                datetime.now(timezone.utc)
                - timedelta(seconds=self.stale_age_s)
            )
            return SpeedSample(
                speed_mps=self.fixed_speed_mps,
                measured_at_utc=stale_time,
                source="mock-stale",
            )

        if self.mode == "stationary":
            return SpeedSample(
                speed_mps=0.0,
                measured_at_utc=datetime.now(timezone.utc),
                source="mock-stationary",
            )

        if self.mode == "changing":
            speed = (
                0.0
                if (self._call_count // 5) % 2 == 0
                else self.fixed_speed_mps
            )
            return SpeedSample(
                speed_mps=speed,
                measured_at_utc=datetime.now(timezone.utc),
                source="mock-changing",
            )

        if self.mode == "sequence" and self.speeds_mps:
            speed = self.speeds_mps[
                (self._call_count - 1) % len(self.speeds_mps)
            ]
            return SpeedSample(
                speed_mps=speed,
                measured_at_utc=datetime.now(timezone.utc),
                source="mock-sequence",
            )

        return SpeedSample(
            speed_mps=self.fixed_speed_mps,
            measured_at_utc=datetime.now(timezone.utc),
            source="mock-fixed",
        )
