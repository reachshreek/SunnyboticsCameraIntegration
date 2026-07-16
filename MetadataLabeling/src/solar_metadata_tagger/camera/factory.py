from __future__ import annotations

from ..config import CameraConfig
from ..errors import MetadataTaggerError
from .base import CameraSource
from .directory import DirectoryCameraSource
from .lucid_arena import LucidArenaCameraSource
from .opencv import OpenCvCameraSource


def create_camera_source(config: CameraConfig) -> CameraSource:
    if config.source == "directory":
        return DirectoryCameraSource(config)
    if config.source == "opencv":
        return OpenCvCameraSource(config)
    if config.source == "lucid":
        return LucidArenaCameraSource(config)
    raise MetadataTaggerError("CAMERA_SOURCE_UNSUPPORTED", "Unsupported camera source.", source=config.source)
