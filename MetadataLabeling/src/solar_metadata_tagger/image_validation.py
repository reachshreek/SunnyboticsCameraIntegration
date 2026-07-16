from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .errors import MetadataTaggerError


@dataclass(frozen=True)
class ImageInfo:
    format: str
    width: int
    height: int
    mode: str
    mean_luma: float
    luma_stddev: float
    dark_pixel_percent: float
    bright_pixel_percent: float
    edge_mean: float


def validate_image(path: Path) -> ImageInfo:
    """Decode the entire file and calculate lightweight quality diagnostics.

    The diagnostics are intentionally advisory. Field acceptance thresholds must be
    established with the real LUCID camera, lens, polarizer, speed, and illumination.
    """
    if not path.is_file():
        raise MetadataTaggerError("IMAGE_NOT_FOUND", "Image file does not exist.", path=str(path))
    if path.stat().st_size <= 0:
        raise MetadataTaggerError("IMAGE_EMPTY", "Image file is empty.", path=str(path))
    try:
        from PIL import Image, ImageFilter, ImageStat, UnidentifiedImageError
    except ImportError as exc:
        raise MetadataTaggerError(
            "IMAGE_DEPENDENCY_MISSING", "Pillow is required for image validation."
        ) from exc
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            image.load()
            width, height = image.size
            image_format = image.format or path.suffix.lstrip(".").upper()
            mode = image.mode
            diagnostic = image.convert("L")
            diagnostic.thumbnail((512, 512))
            histogram = diagnostic.histogram()
            pixel_count = max(1, sum(histogram))
            dark = sum(histogram[:16])
            bright = sum(histogram[240:])
            stats = ImageStat.Stat(diagnostic)
            edges = diagnostic.filter(ImageFilter.FIND_EDGES)
            edge_mean = float(ImageStat.Stat(edges).mean[0])
            mean_luma = float(stats.mean[0])
            luma_stddev = float(stats.stddev[0])
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise MetadataTaggerError(
            "IMAGE_INVALID", "Image cannot be decoded or is truncated.", path=str(path), detail=str(exc)
        ) from exc
    if width < 1 or height < 1:
        raise MetadataTaggerError(
            "IMAGE_INVALID_DIMENSIONS", "Image dimensions must be positive.", width=width, height=height
        )
    return ImageInfo(
        format=image_format,
        width=width,
        height=height,
        mode=mode,
        mean_luma=round(mean_luma, 3),
        luma_stddev=round(luma_stddev, 3),
        dark_pixel_percent=round(100.0 * dark / pixel_count, 3),
        bright_pixel_percent=round(100.0 * bright / pixel_count, 3),
        edge_mean=round(edge_mean, 3),
    )
