from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from .config import CaptureConfig
from .errors import MetadataTaggerError
from .models import CaptureTrigger
from .speed import SpeedProvider
from .storage import write_json_atomic

LOGGER = logging.getLogger(__name__)


class TriggerProvider:
    def __init__(
        self,
        config: CaptureConfig,
        speed_provider: SpeedProvider | None = None,
    ) -> None:
        self.config = config
        self.speed_provider = speed_provider
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def __iter__(self) -> Iterator[CaptureTrigger]:
        if self.config.trigger_mode == "once":
            yield self._new_trigger("once")
            return

        if self.config.trigger_mode == "interval":
            yield from self._interval_triggers()
            return

        if self.config.trigger_mode == "file":
            yield from self._file_triggers()
            return

        if self.config.trigger_mode == "distance":
            yield from self._distance_triggers()
            return

        raise MetadataTaggerError(
            "TRIGGER_MODE_UNSUPPORTED",
            "Unsupported capture trigger mode.",
            mode=self.config.trigger_mode,
        )

    def mark_success(
        self,
        trigger: CaptureTrigger,
        result: dict[str, object],
    ) -> None:
        if trigger.source_file is None:
            return

        self._finish_file(
            trigger.source_file,
            "processed",
            {"result": result},
        )

    def mark_failure(
        self,
        trigger: CaptureTrigger,
        error: MetadataTaggerError,
    ) -> None:
        if trigger.source_file is None:
            return

        self._finish_file(
            trigger.source_file,
            "failed",
            {"error": error.as_dict()},
        )

    def _interval_triggers(
        self,
    ) -> Iterator[CaptureTrigger]:
        count = 0
        next_deadline = time.monotonic()

        while not self._stop:
            if (
                self.config.max_images is not None
                and count >= self.config.max_images
            ):
                return

            delay = next_deadline - time.monotonic()

            if delay > 0:
                time.sleep(min(delay, 0.2))
                continue

            yield self._new_trigger(
                "interval",
                sequence=count,
            )

            count += 1
            next_deadline += self.config.interval_s

    def _distance_triggers(
        self,
    ) -> Iterator[CaptureTrigger]:
        """
        Generate captures from estimated travel distance.

        A capture is produced immediately at service start. Later
        captures use integrated speed when a fresh speed sample is
        available. Missing or stale speed activates the configured
        fixed-rate fallback.
        """

        spacing_m = self.config.capture_spacing_m
        count = 1
        distance_m = 0.0
        last_tick = time.monotonic()
        last_capture = last_tick

        yield self._new_trigger(
            "distance",
            sequence=0,
            metadata={
                "capture_mode": "distance-initial",
                "capture_spacing_m": round(
                    spacing_m,
                    3,
                ),
                "required_overlap_fraction": (
                    self.config.required_overlap_fraction
                ),
            },
        )

        while not self._stop:
            if (
                self.config.max_images is not None
                and count >= self.config.max_images
            ):
                return

            now_monotonic = time.monotonic()

            elapsed_s = max(
                0.0,
                now_monotonic - last_tick,
            )

            last_tick = now_monotonic
            now_utc = datetime.now(timezone.utc)

            sample = (
                self.speed_provider.sample()
                if self.speed_provider is not None
                else None
            )

            fresh_sample = (
                sample
                if (
                    sample is not None
                    and sample.is_fresh(
                        self.config.speed_timeout_s,
                        at_utc=now_utc,
                    )
                )
                else None
            )

            should_capture = False
            capture_mode = "distance"
            speed_mps: float | None = None
            speed_source: str | None = None
            speed_age_s: float | None = None

            if fresh_sample is not None:
                speed_mps = fresh_sample.speed_mps
                speed_source = fresh_sample.source
                speed_age_s = fresh_sample.age_seconds(
                    now_utc
                )

                if (
                    speed_mps
                    >= self.config.min_moving_speed_mps
                ):
                    distance_m += (
                        speed_mps
                        * elapsed_s
                    )

                if (
                    distance_m >= spacing_m
                    and (
                        now_monotonic
                        - last_capture
                        >= self.config.min_capture_interval_s
                    )
                ):
                    should_capture = True

            elif (
                now_monotonic
                - last_capture
                >= self.config.fallback_interval_s
            ):
                should_capture = True
                capture_mode = "fixed-rate-fallback"

            if should_capture:
                estimated_distance = distance_m

                if capture_mode == "distance":
                    distance_m = max(
                        0.0,
                        distance_m - spacing_m,
                    )
                else:
                    distance_m = 0.0

                last_capture = now_monotonic

                LOGGER.info(
                    "Capture trigger generated",
                    extra={
                        "event": (
                            "capture_trigger_generated"
                        ),
                        "capture_mode": capture_mode,
                        "speed_source": speed_source,
                        "speed_mps": speed_mps,
                        "speed_age_s": speed_age_s,
                        "estimated_distance_m": (
                            estimated_distance
                        ),
                        "capture_spacing_m": spacing_m,
                    },
                )

                yield self._new_trigger(
                    "distance",
                    sequence=count,
                    metadata={
                        "capture_mode": capture_mode,
                        "speed_source": speed_source,
                        "speed_mps": (
                            round(speed_mps, 3)
                            if speed_mps is not None
                            else None
                        ),
                        "speed_sample_age_s": (
                            round(speed_age_s, 3)
                            if speed_age_s is not None
                            else None
                        ),
                        (
                            "estimated_distance_"
                            "since_previous_capture_m"
                        ): round(
                            estimated_distance,
                            3,
                        ),
                        "capture_spacing_m": round(
                            spacing_m,
                            3,
                        ),
                        "required_overlap_fraction": (
                            self.config
                            .required_overlap_fraction
                        ),
                    },
                )

                count += 1
                continue

            time.sleep(
                self.config.speed_poll_s
            )

    def _file_triggers(
        self,
    ) -> Iterator[CaptureTrigger]:
        directory = self.config.trigger_directory

        if directory is None:
            raise MetadataTaggerError(
                "TRIGGER_CONFIG_INVALID",
                "capture.trigger_directory is required "
                "for file triggers.",
            )

        incoming = directory / "incoming"
        processing = directory / "processing"
        processed = directory / "processed"
        failed = directory / "failed"

        for path in (
            incoming,
            processing,
            processed,
            failed,
        ):
            path.mkdir(
                parents=True,
                exist_ok=True,
            )

        count = 0

        while not self._stop:
            if (
                self.config.max_images is not None
                and count >= self.config.max_images
            ):
                return

            candidates = sorted(
                incoming.glob("*.json")
            )

            if not candidates:
                time.sleep(
                    self.config.trigger_poll_s
                )
                continue

            source = candidates[0]
            claimed = processing / source.name

            try:
                os.replace(
                    source,
                    claimed,
                )
            except FileNotFoundError:
                continue

            try:
                raw = json.loads(
                    claimed.read_text(
                        encoding="utf-8",
                    )
                )

                if not isinstance(raw, dict):
                    raise MetadataTaggerError(
                        "TRIGGER_INVALID",
                        "Trigger JSON root must be "
                        "an object.",
                        path=str(claimed),
                    )

                requested_at = (
                    _parse_optional_timestamp(
                        raw.get(
                            "requested_at_utc"
                        )
                    )
                )

                trigger = CaptureTrigger(
                    trigger_id=str(
                        raw.get("trigger_id")
                        or claimed.stem
                    ),
                    triggered_at_utc=(
                        requested_at
                        or datetime.now(
                            timezone.utc
                        )
                    ),
                    row=_optional_text(
                        raw.get("row")
                    ),
                    panel=_optional_text(
                        raw.get("panel")
                    ),
                    mission_point_id=(
                        _optional_text(
                            raw.get(
                                "mission_point_id"
                            )
                        )
                    ),
                    metadata={
                        str(key): value
                        for key, value
                        in raw.items()
                        if key
                        not in {
                            "trigger_id",
                            "requested_at_utc",
                            "row",
                            "panel",
                            "mission_point_id",
                        }
                    },
                    source_file=claimed,
                )

            except Exception as exc:
                error = (
                    exc
                    if isinstance(
                        exc,
                        MetadataTaggerError,
                    )
                    else MetadataTaggerError(
                        "TRIGGER_INVALID",
                        "Trigger JSON could not "
                        "be read.",
                        detail=str(exc),
                    )
                )

                self._finish_file(
                    claimed,
                    "failed",
                    {
                        "error": (
                            error.as_dict()
                        )
                    },
                )

                LOGGER.error(
                    "Rejected capture trigger",
                    extra={
                        "event": (
                            "trigger_rejected"
                        ),
                        **error.as_log_extra(),
                    },
                )

                continue

            count += 1
            yield trigger

    def _finish_file(
        self,
        processing_file: Path,
        outcome: str,
        extra: dict[str, object],
    ) -> None:
        directory = (
            processing_file.parent.parent
            / outcome
        )

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        try:
            raw = json.loads(
                processing_file.read_text(
                    encoding="utf-8",
                )
            )

            if not isinstance(raw, dict):
                raw = {
                    "original": raw
                }

        except Exception:
            raw = {}

        raw.update(extra)

        raw["completed_at_utc"] = (
            datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )

        destination = (
            directory
            / processing_file.name
        )

        write_json_atomic(
            destination,
            raw,
        )

        processing_file.unlink(
            missing_ok=True
        )

    @staticmethod
    def _new_trigger(
        source: str,
        *,
        sequence: int | None = None,
        metadata: dict[str, object] | None = None,
    ) -> CaptureTrigger:
        now = datetime.now(
            timezone.utc
        )

        trigger_metadata: dict[str, object] = {
            "source": source,
            "sequence": sequence,
        }

        trigger_metadata.update(
            metadata or {}
        )

        return CaptureTrigger(
            trigger_id=(
                f"{source}-"
                f"{uuid.uuid4().hex[:12]}"
            ),
            triggered_at_utc=now,
            metadata=trigger_metadata,
        )


def _parse_optional_timestamp(
    value: object,
) -> datetime | None:
    if value is None:
        return None

    if not isinstance(value, str):
        raise MetadataTaggerError(
            "TRIGGER_INVALID",
            "requested_at_utc must be "
            "an ISO-8601 string.",
        )

    try:
        parsed = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            )
        )
    except ValueError as exc:
        raise MetadataTaggerError(
            "TRIGGER_INVALID",
            "requested_at_utc is invalid.",
        ) from exc

    if parsed.tzinfo is None:
        raise MetadataTaggerError(
            "TRIGGER_INVALID",
            "requested_at_utc must include "
            "a timezone.",
        )

    return parsed.astimezone(
        timezone.utc
    )


def _optional_text(
    value: object,
) -> str | None:
    if value is None:
        return None

    if (
        not isinstance(value, str)
        or not value.strip()
    ):
        raise MetadataTaggerError(
            "TRIGGER_INVALID",
            "Optional trigger identifiers must "
            "be non-empty strings.",
        )

    return value.strip()