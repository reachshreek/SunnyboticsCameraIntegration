from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class GnssFix:
    latitude: float
    longitude: float
    received_at_utc: datetime
    fix_time_utc: datetime | None = None
    altitude_m: float | None = None
    fix_quality: int | None = None
    satellites: int | None = None
    hdop: float | None = None
    speed_mps: float | None = None
    course_deg: float | None = None
    source_sentence: str | None = None

    def signed_age_seconds(self, at: datetime) -> float:
        """Positive when the fix was received before capture; negative when after."""
        if at.tzinfo is None or self.received_at_utc.tzinfo is None:
            raise ValueError("GNSS and capture timestamps must be timezone-aware")
        return (
            at.astimezone(timezone.utc) - self.received_at_utc.astimezone(timezone.utc)
        ).total_seconds()

    def age_seconds(self, at: datetime) -> float:
        return abs(self.signed_age_seconds(at))

    @property
    def coordinates_valid(self) -> bool:
        return (
            math.isfinite(self.latitude)
            and math.isfinite(self.longitude)
            and -90.0 <= self.latitude <= 90.0
            and -180.0 <= self.longitude <= 180.0
        )


@dataclass(frozen=True)
class SiteAssignment:
    row: str | None
    panel: str | None
    method: str
    feature_id: str | None = None
    distance_m: float | None = None


@dataclass(frozen=True)
class CapturedFrame:
    image_path: Path
    captured_at_utc: datetime
    monotonic_ns: int
    camera_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CaptureTrigger:
    trigger_id: str
    triggered_at_utc: datetime
    row: str | None = None
    panel: str | None = None
    mission_point_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    source_file: Path | None = None


@dataclass(frozen=True)
class TagResult:
    image_id: str
    image_path: Path
    metadata_path: Path
    status: str
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            "image_id": self.image_id,
            "image_path": str(self.image_path),
            "metadata_path": str(self.metadata_path),
            "status": self.status,
            "warnings": list(self.warnings),
        }
