from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

from ..config import CameraConfig
from ..errors import MetadataTaggerError
from ..models import CapturedFrame
from ..storage import write_bytes_atomic


class OpenCvCameraSource:
    """USB webcam adapter for bench development before the LUCID camera arrives."""

    def __init__(self, config: CameraConfig) -> None:
        self.config = config
        self._capture = None
        self._sequence = 0

    def open(self) -> None:
        try:
            import cv2
        except ImportError as exc:
            raise MetadataTaggerError(
                "CAMERA_DEPENDENCY_MISSING",
                "OpenCV is required for the opencv camera source. Install the webcam extra.",
            ) from exc
        capture = cv2.VideoCapture(self.config.opencv_device)
        if self.config.width:
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
        if self.config.height:
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
        if not capture.isOpened():
            capture.release()
            raise MetadataTaggerError(
                "CAMERA_OPEN_FAILED",
                "USB webcam could not be opened.",
                device=self.config.opencv_device,
            )
        self._capture = capture

    def capture(self, spool_dir: Path) -> CapturedFrame:
        if self._capture is None:
            raise MetadataTaggerError("CAMERA_NOT_OPEN", "USB webcam is not open.")
        ok, frame = self._capture.read()
        captured_at = datetime.now(timezone.utc)
        monotonic_ns = time.monotonic_ns()
        if not ok or frame is None:
            raise MetadataTaggerError("CAMERA_CAPTURE_FAILED", "USB webcam returned no frame.")
        try:
            import cv2

            normalized = self.config.output_format.lower().lstrip(".")
            extension = ".jpg" if normalized in {"jpg", "jpeg"} else f".{normalized}"
            params = [cv2.IMWRITE_JPEG_QUALITY, 95] if extension == ".jpg" else []
            encoded_ok, encoded = cv2.imencode(extension, frame, params)
        except Exception as exc:
            raise MetadataTaggerError(
                "CAMERA_ENCODE_FAILED", "USB webcam frame could not be encoded.", detail=str(exc)
            ) from exc
        if not encoded_ok:
            raise MetadataTaggerError("CAMERA_ENCODE_FAILED", "USB webcam frame encode failed.")
        spool_dir.mkdir(parents=True, exist_ok=True)
        path = spool_dir / f"opencv-{captured_at.strftime('%Y%m%dT%H%M%S.%fZ')}-{self._sequence:06d}{extension}"
        write_bytes_atomic(path, encoded.tobytes())
        self._sequence += 1
        height, width = frame.shape[:2]
        return CapturedFrame(
            image_path=path,
            captured_at_utc=captured_at,
            monotonic_ns=monotonic_ns,
            camera_metadata={
                "source": "opencv-usb-webcam",
                "device": self.config.opencv_device,
                "width_px": int(width),
                "height_px": int(height),
                "sequence_index": self._sequence - 1,
                "model": self.config.model,
            },
        )

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def health(self) -> dict[str, object]:
        return {
            "source": "opencv",
            "open": self._capture is not None,
            "device": self.config.opencv_device,
            "frames_captured": self._sequence,
        }
