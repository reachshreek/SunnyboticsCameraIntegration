from __future__ import annotations

import itertools
import time
from datetime import datetime, timezone
from pathlib import Path

from ..config import CameraConfig
from ..errors import MetadataTaggerError
from ..models import CapturedFrame

_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}


class DirectoryCameraSource:
    """Camera simulator that returns files from a directory in deterministic order."""

    def __init__(self, config: CameraConfig) -> None:
        if config.source_directory is None:
            raise MetadataTaggerError(
                "CAMERA_CONFIG_INVALID", "Directory camera source requires source_directory."
            )
        self.config = config
        self.directory = config.source_directory
        self._files: tuple[Path, ...] = ()
        self._index = 0
        self._open = False

    def open(self) -> None:
        if not self.directory.is_dir():
            raise MetadataTaggerError(
                "CAMERA_SOURCE_NOT_FOUND",
                "Simulated image directory was not found.",
                path=str(self.directory),
            )
        files = sorted(
            p for p in self.directory.rglob("*") if p.is_file() and p.suffix.lower() in _IMAGE_SUFFIXES
        )
        if not files:
            raise MetadataTaggerError(
                "CAMERA_SOURCE_EMPTY", "Simulated image directory contains no supported images."
            )
        self._files = tuple(files)
        self._index = 0
        self._open = True

    def capture(self, spool_dir: Path) -> CapturedFrame:
        if not self._open:
            raise MetadataTaggerError("CAMERA_NOT_OPEN", "Directory camera source is not open.")
        if self._index >= len(self._files):
            if not self.config.directory_loop:
                raise MetadataTaggerError(
                    "CAMERA_SOURCE_EXHAUSTED", "All simulated images have been consumed."
                )
            self._index = 0
        source = self._files[self._index]
        self._index += 1
        captured_at = datetime.now(timezone.utc)
        return CapturedFrame(
            image_path=source,
            captured_at_utc=captured_at,
            monotonic_ns=time.monotonic_ns(),
            camera_metadata={
                "source": "directory-simulator",
                "source_path": str(source),
                "sequence_index": self._index - 1,
                "model": self.config.model,
            },
        )

    def close(self) -> None:
        self._open = False

    def health(self) -> dict[str, object]:
        return {
            "source": "directory",
            "open": self._open,
            "directory": str(self.directory),
            "image_count": len(self._files),
            "next_index": self._index,
        }
