"""Sunnybotics camera capture and metadata package."""

from .config import TaggerConfig
from .models import CapturedFrame, CaptureTrigger, GnssFix, SiteAssignment, TagResult
from .runner import CaptureService
from .service import MetadataTaggingService
from .version import __version__

__all__ = [
    "CapturedFrame",
    "CaptureService",
    "CaptureTrigger",
    "GnssFix",
    "MetadataTaggingService",
    "SiteAssignment",
    "TagResult",
    "TaggerConfig",
    "__version__",
]
