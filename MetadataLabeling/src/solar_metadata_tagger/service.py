from __future__ import annotations

import logging
import math
import platform
import socket
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import TaggerConfig
from .errors import MetadataTaggerError
from .gnss import FixHistoryStore
from .ids import generate_image_id
from .image_validation import ImageInfo, validate_image
from .layout import LayoutResolver
from .models import GnssFix, SiteAssignment, TagResult, utc_iso
from .storage import (
    append_jsonl,
    copy_image_atomic,
    disk_usage,
    ensure_free_space,
    sha256_file,
    write_json_atomic,
)
from .version import __version__

LOGGER = logging.getLogger(__name__)


class MetadataTaggingService:
    """Create durable canonical metadata without depending on a camera SDK."""

    def __init__(
        self,
        config: TaggerConfig,
        fix_store: FixHistoryStore | None = None,
        layout_resolver: LayoutResolver | None = None,
    ) -> None:
        self.config = config
        self.fix_store = fix_store or FixHistoryStore(config.gnss.history_size)
        if layout_resolver is not None:
            self.layout = layout_resolver
        elif config.layout_file is not None:
            self.layout = LayoutResolver.from_geojson(config.layout_file)
        else:
            self.layout = None

    def tag_image(
        self,
        source_image: str | Path,
        *,
        captured_at_utc: datetime | None = None,
        captured_monotonic_ns: int | None = None,
        manual_fix: GnssFix | None = None,
        row: str | None = None,
        panel: str | None = None,
        camera_metadata: dict[str, Any] | None = None,
        trigger_metadata: dict[str, Any] | None = None,
    ) -> TagResult:
        started_ns = time.monotonic_ns()
        source = Path(source_image).expanduser().resolve()
        if not source.is_file():
            raise MetadataTaggerError(
                "IMAGE_NOT_FOUND", "Source image does not exist or is not a file.", path=str(source)
            )

        captured = captured_at_utc or datetime.now(timezone.utc)
        if captured.tzinfo is None:
            raise MetadataTaggerError("TIMESTAMP_INVALID", "captured_at_utc must be timezone-aware.")
        captured = captured.astimezone(timezone.utc)
        if captured.year < 2000 or captured.year > 2100:
            raise MetadataTaggerError(
                "TIMESTAMP_INVALID", "Capture timestamp is outside the supported operational range."
            )
        monotonic_ns = captured_monotonic_ns or time.monotonic_ns()

        storage_before = ensure_free_space(
            self.config.storage.root,
            min_free_gb=self.config.storage.min_free_gb,
            emergency_free_gb=self.config.storage.emergency_free_gb,
        )

        image_info: ImageInfo | None = None
        image_validation_error: MetadataTaggerError | None = None
        if self.config.storage.validate_images:
            try:
                image_info = validate_image(source)
            except MetadataTaggerError as exc:
                image_validation_error = exc

        image_id = generate_image_id(self.config.robot_id, self.config.mission_id, captured)
        warnings: list[str] = []
        if image_validation_error:
            warnings.append(f"image_invalid:{image_validation_error.code}")

        fix = manual_fix or self.fix_store.select_for_capture(
            captured,
            max_age_s=self.config.gnss.max_fix_age_s,
            future_tolerance_s=self.config.gnss.future_tolerance_s,
        )
        location = self._location_payload(fix, captured, warnings)
        assignment = self._assignment(fix, row, panel, warnings)

        missing = _missing_required(self.config.required_fields, location, assignment)
        if image_validation_error:
            missing.append("valid_image")
        status = "complete" if not missing else "partial"
        if missing:
            warnings.append("missing_required_fields:" + ",".join(sorted(set(missing))))
            if self.config.storage.quarantine_on_missing_required:
                status = "quarantined"

        date_path = captured.strftime("%Y/%m/%d")
        image_bucket = "quarantine/images" if status == "quarantined" else "images"
        metadata_bucket = "quarantine/metadata" if status == "quarantined" else "metadata"
        suffix = source.suffix.lower() or ".bin"
        destination_image = self.config.storage.root / image_bucket / date_path / f"{image_id}{suffix}"
        destination_metadata = (
            self.config.storage.root / metadata_bucket / date_path / f"{image_id}.json"
        )
        manifest = self.config.storage.root / "manifests" / f"{self.config.mission_id}.jsonl"

        copy_image_atomic(source, destination_image)
        try:
            digest = sha256_file(destination_image) if self.config.storage.compute_sha256 else None
            storage_after_copy = disk_usage(self.config.storage.root)
            camera_payload = {"model": self.config.camera.model}
            camera_payload.update(_safe_camera_metadata(camera_metadata or {}))
            payload: dict[str, Any] = {
                "schema_version": "2.0.0",
                "image_id": image_id,
                "captured_at_utc": utc_iso(captured),
                "robot_id": self.config.robot_id,
                "mission_id": self.config.mission_id,
                "status": status,
                "image": {
                    "filename": destination_image.name,
                    "relative_path": str(destination_image.relative_to(self.config.storage.root)),
                    "media_type": _media_type(destination_image.suffix),
                    "byte_size": destination_image.stat().st_size,
                    "sha256": digest,
                    "format": image_info.format if image_info else None,
                    "width_px": image_info.width if image_info else None,
                    "height_px": image_info.height if image_info else None,
                    "mode": image_info.mode if image_info else None,
                    "validation_error": image_validation_error.as_dict()
                    if image_validation_error
                    else None,
                    "quality_diagnostics": {
                        "mean_luma_0_255": image_info.mean_luma if image_info else None,
                        "luma_stddev": image_info.luma_stddev if image_info else None,
                        "dark_pixel_percent": image_info.dark_pixel_percent if image_info else None,
                        "bright_pixel_percent": image_info.bright_pixel_percent if image_info else None,
                        "edge_mean": image_info.edge_mean if image_info else None,
                        "advisory_only": True,
                    },
                },
                "timing": {
                    "captured_at_utc": utc_iso(captured),
                    "captured_monotonic_ns": monotonic_ns,
                    "metadata_completed_at_utc": utc_iso(datetime.now(timezone.utc)),
                    "tagging_duration_ms": round((time.monotonic_ns() - started_ns) / 1_000_000, 3),
                },
                "coordinates": location,
                "site": {
                    "row": assignment.row,
                    "panel": assignment.panel,
                    "assignment_method": assignment.method,
                    "layout_feature_id": assignment.feature_id,
                    "assignment_distance_m": _rounded(assignment.distance_m, 3),
                },
                "trigger": trigger_metadata or {},
                "camera": camera_payload,
                "hardware": self.config.hardware.as_dict(),
                "storage": {
                    "device_label": self.config.hardware.storage_device,
                    "root": str(self.config.storage.root),
                    "free_bytes_before": storage_before["free_bytes"],
                    "free_bytes_after_copy": storage_after_copy["free_bytes"],
                },
                "software": {
                    "name": "solar-metadata-tagger",
                    "version": __version__,
                    "python": platform.python_version(),
                    "platform": platform.platform(),
                    "machine": platform.machine(),
                    "hostname": socket.gethostname(),
                },
                "warnings": warnings,
            }
            # Update duration after payload construction without changing capture time.
            payload["timing"]["metadata_completed_at_utc"] = utc_iso(datetime.now(timezone.utc))
            payload["timing"]["tagging_duration_ms"] = round(
                (time.monotonic_ns() - started_ns) / 1_000_000, 3
            )
            write_json_atomic(destination_metadata, payload)
            append_jsonl(manifest, payload)
        except Exception as exc:
            recovery_record = {
                "image_id": image_id,
                "preserved_image": str(destination_image),
                "intended_metadata": str(destination_metadata),
                "error": str(exc),
                "exception_type": type(exc).__name__,
                "recorded_at_utc": utc_iso(datetime.now(timezone.utc)),
            }
            try:
                write_json_atomic(
                    self.config.storage.root / "recovery" / f"{image_id}.json", recovery_record
                )
            except Exception:
                LOGGER.exception("Unable to write recovery record", extra={"event": "recovery_write_failed"})
            LOGGER.exception(
                "Metadata commit failed after image preservation",
                extra={
                    "event": "metadata_commit_failed",
                    "image_id": image_id,
                    "preserved_image": str(destination_image),
                },
            )
            raise

        if not self.config.storage.preserve_source and _is_inside(source, self.config.storage.effective_spool_dir):
            try:
                source.unlink(missing_ok=True)
            except OSError:
                warnings.append("spool_cleanup_failed")
                LOGGER.warning(
                    "Could not remove captured spool image",
                    extra={"event": "spool_cleanup_failed", "path": str(source)},
                )

        LOGGER.info(
            "Tagged image",
            extra={
                "event": "image_tagged",
                "image_id": image_id,
                "status": status,
                "row": assignment.row,
                "panel": assignment.panel,
                "image_path": str(destination_image),
                "metadata_path": str(destination_metadata),
                "warnings": warnings,
            },
        )
        return TagResult(
            image_id=image_id,
            image_path=destination_image,
            metadata_path=destination_metadata,
            status=status,
            warnings=tuple(warnings),
        )

    def _location_payload(
        self, fix: GnssFix | None, captured: datetime, warnings: list[str]
    ) -> dict[str, Any]:
        empty = {
            "latitude": None,
            "longitude": None,
            "altitude_m": None,
            "fix_time_utc": None,
            "received_at_utc": None,
            "fix_age_ms": None,
            "fix_after_capture_ms": None,
            "fresh": False,
            "valid": False,
            "quality_accepted": False,
            "fix_quality": None,
            "satellites": None,
            "hdop": None,
            "speed_mps": None,
            "course_deg": None,
        }
        if fix is None:
            warnings.append("gnss_fix_missing_or_outside_capture_window")
            return empty

        signed_age_s = fix.signed_age_seconds(captured)
        fresh = (
            -self.config.gnss.future_tolerance_s
            <= signed_age_s
            <= self.config.gnss.max_fix_age_s
        )
        coordinates_valid = fix.coordinates_valid
        quality_accepted = True
        if self.config.gnss.require_fix_quality and fix.fix_quality is not None and fix.fix_quality <= 0:
            quality_accepted = False
            warnings.append("gnss_fix_quality_invalid")
        if fix.satellites is not None and fix.satellites < self.config.gnss.min_satellites:
            quality_accepted = False
            warnings.append(f"gnss_satellites_low:{fix.satellites}")
        if fix.hdop is not None and (
            not math.isfinite(fix.hdop) or fix.hdop > self.config.gnss.max_hdop
        ):
            quality_accepted = False
            warnings.append(f"gnss_hdop_high:{fix.hdop}")
        if not fresh:
            warnings.append(f"gnss_fix_outside_window:{signed_age_s:.3f}s")
        if not coordinates_valid:
            warnings.append("gnss_coordinates_invalid")

        valid = fresh and coordinates_valid and quality_accepted
        return {
            "latitude": _rounded(fix.latitude, 8) if coordinates_valid else None,
            "longitude": _rounded(fix.longitude, 8) if coordinates_valid else None,
            "altitude_m": _rounded(fix.altitude_m, 3),
            "fix_time_utc": utc_iso(fix.fix_time_utc) if fix.fix_time_utc else None,
            "received_at_utc": utc_iso(fix.received_at_utc),
            "fix_age_ms": round(max(0.0, signed_age_s) * 1000),
            "fix_after_capture_ms": round(max(0.0, -signed_age_s) * 1000),
            "fresh": fresh,
            "valid": valid,
            "quality_accepted": quality_accepted,
            "fix_quality": fix.fix_quality,
            "satellites": fix.satellites,
            "hdop": _rounded(fix.hdop, 2),
            "speed_mps": _rounded(fix.speed_mps, 3),
            "course_deg": _rounded(fix.course_deg, 2),
        }

    def _assignment(
        self,
        fix: GnssFix | None,
        row: str | None,
        panel: str | None,
        warnings: list[str],
    ) -> SiteAssignment:
        normalized_row = row.strip() if isinstance(row, str) and row.strip() else None
        normalized_panel = panel.strip() if isinstance(panel, str) and panel.strip() else None
        if row is not None or panel is not None:
            if not normalized_row or not normalized_panel:
                warnings.append("manual_row_panel_incomplete")
            return SiteAssignment(normalized_row, normalized_panel, "manual")
        if fix is None or not fix.coordinates_valid:
            warnings.append("row_panel_unresolved_no_coordinates")
            return SiteAssignment(None, None, "unresolved")
        if self.layout is None:
            warnings.append("row_panel_unresolved_no_layout")
            return SiteAssignment(None, None, "no-layout")
        assignment = self.layout.resolve(fix.latitude, fix.longitude)
        if assignment.row is None or assignment.panel is None:
            warnings.append("row_panel_no_layout_match")
        return assignment


def _missing_required(
    required: tuple[str, ...], location: dict[str, Any], assignment: SiteAssignment
) -> list[str]:
    coordinates_accepted = bool(location.get("valid"))
    values = {
        "latitude": location.get("latitude") if coordinates_accepted else None,
        "longitude": location.get("longitude") if coordinates_accepted else None,
        "row": assignment.row,
        "panel": assignment.panel,
    }
    return [field for field in required if values.get(field) is None]


def _rounded(value: float | None, digits: int) -> float | None:
    return round(value, digits) if value is not None and math.isfinite(value) else None


def _media_type(suffix: str) -> str:
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
        ".bmp": "image/bmp",
        ".raw": "application/octet-stream",
    }.get(suffix.lower(), "application/octet-stream")


def _safe_camera_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    # Keep JSON-compatible values and prevent accidental replacement of system metadata.
    forbidden = {"hardware", "software", "robot_id", "mission_id", "image_id"}
    result: dict[str, Any] = {}
    for key, value in metadata.items():
        if key in forbidden:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            result[str(key)] = value
        elif isinstance(value, (list, tuple)):
            result[str(key)] = list(value)
        elif isinstance(value, dict):
            result[str(key)] = value
        else:
            result[str(key)] = str(value)
    return result


def _is_inside(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory.resolve())
        return True
    except ValueError:
        return False
