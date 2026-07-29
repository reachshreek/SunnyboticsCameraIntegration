import json
from datetime import datetime, timezone

import pytest

from solar_metadata_tagger.config import (
    CaptureConfig,
)
from solar_metadata_tagger.speed import (
    SpeedSample,
)
from solar_metadata_tagger.triggers import (
    TriggerProvider,
)


class ConstantSpeedProvider:
    def __init__(
        self,
        speed_mps: float,
    ) -> None:
        self.speed_mps = speed_mps

    def sample(
        self,
    ) -> SpeedSample:
        return SpeedSample(
            speed_mps=self.speed_mps,
            measured_at_utc=datetime.now(
                timezone.utc
            ),
            source="test",
        )


class StaleSpeedProvider:
    def sample(
        self,
    ) -> SpeedSample:
        return SpeedSample(
            speed_mps=10.0,
            measured_at_utc=datetime(
                2020,
                1,
                1,
                tzinfo=timezone.utc,
            ),
            source="test-stale",
        )


def test_capture_spacing_calculation() -> None:
    config = CaptureConfig(
        along_track_coverage_m=1.62,
        required_overlap_fraction=0.30,
    )

    assert config.capture_spacing_m == (
        pytest.approx(1.134)
    )

    assert (
        config.maximum_capture_rate_hz
        == pytest.approx(1.0)
    )


def test_file_trigger_claim_and_complete(
    tmp_path,
) -> None:
    root = (
        tmp_path
        / "triggers"
    )

    incoming = (
        root
        / "incoming"
    )

    incoming.mkdir(
        parents=True
    )

    (
        incoming
        / "point.json"
    ).write_text(
        json.dumps(
            {
                "row": "A",
                "panel": "001",
            }
        )
    )

    provider = TriggerProvider(
        CaptureConfig(
            trigger_mode="file",
            trigger_directory=root,
            max_images=1,
        )
    )

    trigger = next(
        iter(provider)
    )

    assert trigger.row == "A"
    assert trigger.panel == "001"

    assert (
        trigger.source_file
        is not None
    )

    assert (
        trigger.source_file
        .parent
        .name
        == "processing"
    )

    provider.mark_success(
        trigger,
        {
            "status": "complete"
        },
    )

    completed = json.loads(
        (
            root
            / "processed"
            / "point.json"
        ).read_text()
    )

    assert (
        completed["result"]["status"]
        == "complete"
    )


def test_file_trigger_does_not_require_row_or_panel(
    tmp_path,
) -> None:
    root = (
        tmp_path
        / "triggers"
    )

    incoming = (
        root
        / "incoming"
    )

    incoming.mkdir(
        parents=True
    )

    (
        incoming
        / "point.json"
    ).write_text(
        json.dumps(
            {
                "trigger_id": "point-1",
                "mission_point_id": (
                    "mission-point-1"
                ),
            }
        )
    )

    provider = TriggerProvider(
        CaptureConfig(
            trigger_mode="file",
            trigger_directory=root,
            max_images=1,
        )
    )

    trigger = next(
        iter(provider)
    )

    assert trigger.row is None
    assert trigger.panel is None

    assert (
        trigger.mission_point_id
        == "mission-point-1"
    )


def test_distance_trigger_uses_speed() -> None:
    provider = TriggerProvider(
        CaptureConfig(
            trigger_mode="distance",
            along_track_coverage_m=0.01,
            required_overlap_fraction=0.0,
            speed_timeout_s=1.0,
            speed_poll_s=0.001,
            fallback_interval_s=1.0,
            min_capture_interval_s=0.001,
            min_moving_speed_mps=0.0,
            max_images=2,
        ),
        speed_provider=(
            ConstantSpeedProvider(
                speed_mps=10.0
            )
        ),
    )

    triggers = iter(
        provider
    )

    first = next(
        triggers
    )

    second = next(
        triggers
    )

    assert (
        first.metadata["capture_mode"]
        == "distance-initial"
    )

    assert (
        second.metadata["capture_mode"]
        == "distance"
    )

    assert (
        second.metadata["speed_source"]
        == "test"
    )

    assert (
        second.metadata["speed_mps"]
        == 10.0
    )


def test_distance_trigger_falls_back_without_speed() -> None:
    provider = TriggerProvider(
        CaptureConfig(
            trigger_mode="distance",
            speed_poll_s=0.001,
            fallback_interval_s=0.005,
            min_capture_interval_s=0.001,
            max_images=2,
        )
    )

    triggers = iter(
        provider
    )

    next(
        triggers
    )

    fallback = next(
        triggers
    )

    assert (
        fallback.metadata["capture_mode"]
        == "fixed-rate-fallback"
    )

    assert (
        fallback.metadata["speed_source"]
        is None
    )


def test_stale_speed_uses_fallback() -> None:
    provider = TriggerProvider(
        CaptureConfig(
            trigger_mode="distance",
            speed_timeout_s=0.01,
            speed_poll_s=0.001,
            fallback_interval_s=0.005,
            min_capture_interval_s=0.001,
            max_images=2,
        ),
        speed_provider=(
            StaleSpeedProvider()
        ),
    )

    triggers = iter(
        provider
    )

    next(
        triggers
    )

    fallback = next(
        triggers
    )

    assert (
        fallback.metadata["capture_mode"]
        == "fixed-rate-fallback"
    )


def test_zero_speed_does_not_create_distance_capture() -> None:
    provider = TriggerProvider(
        CaptureConfig(
            trigger_mode="distance",
            speed_timeout_s=1.0,
            speed_poll_s=0.001,
            fallback_interval_s=0.005,
            min_capture_interval_s=0.001,
            min_moving_speed_mps=0.02,
            max_images=2,
        ),
        speed_provider=(
            ConstantSpeedProvider(
                speed_mps=0.0
            )
        ),
    )

    triggers = iter(
        provider
    )

    first = next(
        triggers
    )

    assert (
        first.metadata["capture_mode"]
        == "distance-initial"
    )

    provider.stop()