from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from .gnss import FixHistoryStore


@dataclass(frozen=True)
class SpeedSample:
    """One speed observation used by the capture scheduler."""

    speed_mps: float
    measured_at_utc: datetime
    source: str

    @property
    def valid(self) -> bool:
        return (
            math.isfinite(self.speed_mps)
            and self.speed_mps >= 0.0
            and self.measured_at_utc.tzinfo is not None
        )

    def age_seconds(self, at_utc: datetime | None = None) -> float:
        at = at_utc or datetime.now(timezone.utc)

        if at.tzinfo is None or self.measured_at_utc.tzinfo is None:
            raise ValueError("Speed timestamps must be timezone-aware")

        return (
            at.astimezone(timezone.utc)
            - self.measured_at_utc.astimezone(timezone.utc)
        ).total_seconds()

    def is_fresh(
        self,
        max_age_s: float,
        at_utc: datetime | None = None,
    ) -> bool:
        age = self.age_seconds(at_utc)
        return self.valid and 0.0 <= age <= max_age_s


class SpeedProvider(Protocol):
    """Interface for GNSS and future robot-controller speed sources."""

    def sample(self) -> SpeedSample | None:
        """Return the newest speed sample or None when unavailable."""


class GnssSpeedProvider:
    """Use speed already decoded from the NaviSys GNSS NMEA stream."""

    def __init__(self, fix_store: FixHistoryStore) -> None:
        self.fix_store = fix_store

    def sample(self) -> SpeedSample | None:
        fix = self.fix_store.snapshot()

        if fix is None or fix.speed_mps is None:
            return None

        sample = SpeedSample(
            speed_mps=fix.speed_mps,
            measured_at_utc=fix.received_at_utc,
            source="gnss",
        )

        return sample if sample.valid else None