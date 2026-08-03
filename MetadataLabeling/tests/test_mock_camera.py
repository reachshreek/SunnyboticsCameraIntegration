from __future__ import annotations

import time
from pathlib import Path

import pytest

from solar_metadata_tagger.camera.mock_camera import (
    CameraFault,
    MockCamera,
    MockSpeedProvider,
    PLANNED_HEIGHT_PX,
    PLANNED_WIDTH_PX,
    PLANNED_PIXEL_FORMAT,
)
from solar_metadata_tagger.models import CapturedFrame


def test_mock_camera_open_and_close(tmp_path: Path) -> None:
    cam = MockCamera()
    cam.open()
    assert cam._open is True
    cam.close()
    assert cam._open is False


def test_mock_camera_returns_valid_frame(tmp_path: Path) -> None:
    cam = MockCamera()
    cam.open()
    frame = cam.capture(tmp_path)
    cam.close()

    assert isinstance(frame, CapturedFrame)
    assert frame.image_path.exists()
    assert frame.image_path.stat().st_size > 0
    assert frame.captured_at_utc.tzinfo is not None
    assert frame.monotonic_ns > 0


def test_mock_camera_correct_dimensions_in_metadata(tmp_path: Path) -> None:
    cam = MockCamera()
    cam.open()
    frame = cam.capture(tmp_path)
    cam.close()

    assert frame.camera_metadata["width_px"] == PLANNED_WIDTH_PX
    assert frame.camera_metadata["height_px"] == PLANNED_HEIGHT_PX
    assert frame.camera_metadata["pixel_format"] == PLANNED_PIXEL_FORMAT


def test_mock_camera_returns_prerecorded_image(
    tmp_path: Path, png_factory
) -> None:
    source = png_factory(tmp_path / "source.png")
    cam = MockCamera(prerecorded_image_path=source)
    cam.open()
    frame = cam.capture(tmp_path / "spool")
    cam.close()

    assert frame.image_path.exists()
    assert frame.image_path.stat().st_size == source.stat().st_size


def test_mock_camera_invalid_frame_is_empty(tmp_path: Path) -> None:
    cam = MockCamera(fault=CameraFault.INVALID_FRAME)
    cam.open()
    frame = cam.capture(tmp_path)
    cam.close()

    assert frame.image_path.exists()
    assert frame.image_path.stat().st_size == 0


def test_mock_camera_incomplete_frame_has_partial_content(
    tmp_path: Path,
) -> None:
    cam = MockCamera(fault=CameraFault.INCOMPLETE_FRAME)
    cam.open()
    frame = cam.capture(tmp_path)
    cam.close()

    content = frame.image_path.read_bytes()
    assert len(content) > 0
    assert len(content) < 100


def test_mock_camera_dropped_frame_raises(tmp_path: Path) -> None:
    cam = MockCamera(fault=CameraFault.DROPPED_FRAME)
    cam.open()
    with pytest.raises(RuntimeError, match="dropped"):
        cam.capture(tmp_path)


def test_mock_camera_disconnection_raises(tmp_path: Path) -> None:
    cam = MockCamera(fault=CameraFault.DISCONNECTED)
    with pytest.raises(RuntimeError, match="unavailable|disconnected"):
        cam.open()


def test_mock_camera_disconnection_during_capture_raises(
    tmp_path: Path,
) -> None:
    cam = MockCamera()
    cam.open()
    cam.fault = CameraFault.DISCONNECTED
    with pytest.raises(RuntimeError, match="disconnected"):
        cam.capture(tmp_path)
    assert cam._open is False


def test_mock_camera_reconnect(tmp_path: Path) -> None:
    cam = MockCamera(fault=CameraFault.DISCONNECTED)
    cam.reconnect()
    assert cam._open is True
    frame = cam.capture(tmp_path)
    assert frame.image_path.exists()
    cam.close()


def test_mock_camera_unavailable_at_startup_raises(tmp_path: Path) -> None:
    cam = MockCamera(fault=CameraFault.UNAVAILABLE_AT_STARTUP)
    with pytest.raises(RuntimeError, match="unavailable"):
        cam.open()


def test_mock_camera_delayed_frame(tmp_path: Path) -> None:
    cam = MockCamera(
        fault=CameraFault.DELAYED_FRAME,
        frame_delay_s=0.05,
    )
    cam.open()
    start = time.monotonic()
    cam.capture(tmp_path)
    elapsed = time.monotonic() - start
    cam.close()

    assert elapsed >= 0.05


def test_mock_camera_capture_without_open_raises(tmp_path: Path) -> None:
    cam = MockCamera()
    with pytest.raises(RuntimeError, match="not open"):
        cam.capture(tmp_path)


def test_mock_camera_health_reports_fault(tmp_path: Path) -> None:
    cam = MockCamera(fault=CameraFault.DROPPED_FRAME)
    h = cam.health()
    assert h["mock"] is True
    assert h["fault"] == "DROPPED_FRAME"
    assert h["width_px"] == PLANNED_WIDTH_PX
    assert h["height_px"] == PLANNED_HEIGHT_PX


def test_mock_camera_frame_count_increments(tmp_path: Path) -> None:
    cam = MockCamera()
    cam.open()
    cam.capture(tmp_path)
    cam.capture(tmp_path)
    cam.capture(tmp_path)
    cam.close()
    assert cam._frame_count == 3


def test_mock_camera_implements_camera_source_protocol(
    tmp_path: Path,
) -> None:
    from solar_metadata_tagger.camera.base import CameraSource
    cam = MockCamera()
    assert isinstance(cam, CameraSource)


def test_speed_provider_fixed_returns_valid_sample() -> None:
    provider = MockSpeedProvider(mode="fixed", fixed_speed_mps=0.5)
    sample = provider.sample()
    assert sample is not None
    assert sample.valid
    assert sample.speed_mps == pytest.approx(0.5)
    assert sample.source == "mock-fixed"


def test_speed_provider_stationary_returns_zero() -> None:
    provider = MockSpeedProvider(mode="stationary")
    sample = provider.sample()
    assert sample is not None
    assert sample.speed_mps == pytest.approx(0.0)


def test_speed_provider_missing_returns_none() -> None:
    provider = MockSpeedProvider(mode="missing")
    assert provider.sample() is None


def test_speed_provider_invalid_sample_fails_valid() -> None:
    provider = MockSpeedProvider(mode="invalid")
    sample = provider.sample()
    assert sample is not None
    assert not sample.valid


def test_speed_provider_stale_sample_is_not_fresh() -> None:
    provider = MockSpeedProvider(mode="stale", stale_age_s=10.0)
    sample = provider.sample()
    assert sample is not None
    assert sample.valid
    assert not sample.is_fresh(max_age_s=2.5)


def test_speed_provider_stale_activates_fallback() -> None:
    from solar_metadata_tagger.config import CaptureConfig
    from solar_metadata_tagger.triggers import TriggerProvider

    provider = TriggerProvider(
        CaptureConfig(
            trigger_mode="distance",
            speed_timeout_s=2.5,
            speed_poll_s=0.001,
            fallback_interval_s=0.005,
            min_capture_interval_s=0.001,
            max_images=2,
        ),
        speed_provider=MockSpeedProvider(mode="stale", stale_age_s=10.0),
    )

    triggers = iter(provider)
    next(triggers)
    fallback = next(triggers)

    assert fallback.metadata["capture_mode"] == "fixed-rate-fallback"


def test_speed_provider_changing_alternates() -> None:
    provider = MockSpeedProvider(mode="changing", fixed_speed_mps=1.0)
    samples = [provider.sample() for _ in range(10)]
    speeds = [s.speed_mps for s in samples if s is not None]
    assert 0.0 in speeds
    assert 1.0 in speeds


def test_speed_provider_sequence_cycles() -> None:
    provider = MockSpeedProvider(
        mode="sequence",
        speeds_mps=[0.2, 0.5, 1.0],
    )
    speeds = [provider.sample().speed_mps for _ in range(6)]
    assert speeds == pytest.approx([0.2, 0.5, 1.0, 0.2, 0.5, 1.0])


def test_speed_provider_fixed_generates_distance_trigger() -> None:
    from solar_metadata_tagger.config import CaptureConfig
    from solar_metadata_tagger.triggers import TriggerProvider

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
        speed_provider=MockSpeedProvider(mode="fixed", fixed_speed_mps=10.0),
    )

    triggers = iter(provider)
    first = next(triggers)
    second = next(triggers)

    assert first.metadata["capture_mode"] == "distance-initial"
    assert second.metadata["capture_mode"] == "distance"
    assert second.metadata["speed_source"] == "mock-fixed"


def test_speed_provider_stationary_does_not_trigger_distance_capture() -> None:
    from solar_metadata_tagger.config import CaptureConfig
    from solar_metadata_tagger.triggers import TriggerProvider

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
        speed_provider=MockSpeedProvider(mode="stationary"),
    )

    triggers = iter(provider)
    first = next(triggers)
    assert first.metadata["capture_mode"] == "distance-initial"
    provider.stop()


def test_capture_spacing_is_1134_m() -> None:
    from solar_metadata_tagger.config import CaptureConfig

    config = CaptureConfig(
        along_track_coverage_m=1.62,
        required_overlap_fraction=0.30,
    )
    assert config.capture_spacing_m == pytest.approx(1.134)


def test_minimum_capture_interval_enforced() -> None:
    from solar_metadata_tagger.config import CaptureConfig

    config = CaptureConfig(
        along_track_coverage_m=1.62,
        required_overlap_fraction=0.30,
    )
    assert config.maximum_capture_rate_hz == pytest.approx(1.0)

def test_mock_camera_timeout_is_configurable(tmp_path: Path) -> None:
    cam = MockCamera(fault=CameraFault.TIMEOUT, timeout_s=0.05)
    cam.open()
    start = time.monotonic()
    with pytest.raises(RuntimeError, match="timed out"):
        cam.capture(tmp_path)
    elapsed = time.monotonic() - start
    assert elapsed >= 0.05
    assert elapsed < 5.0


def test_mock_camera_fixed_capture_interval(tmp_path: Path) -> None:
    cam = MockCamera(capture_interval_s=0.05)
    cam.open()
    cam.capture(tmp_path)
    start = time.monotonic()
    cam.capture(tmp_path)
    elapsed = time.monotonic() - start
    cam.close()
    assert elapsed >= 0.05

def test_missing_speed_activates_fallback() -> None:
    from solar_metadata_tagger.config import CaptureConfig
    from solar_metadata_tagger.triggers import TriggerProvider

    provider = TriggerProvider(
        CaptureConfig(
            trigger_mode="distance",
            speed_poll_s=0.001,
            fallback_interval_s=0.005,
            min_capture_interval_s=0.001,
            max_images=2,
        ),
        speed_provider=MockSpeedProvider(mode="missing"),
    )

    triggers = iter(provider)
    next(triggers)
    fallback = next(triggers)

    assert fallback.metadata["capture_mode"] == "fixed-rate-fallback"
    assert fallback.metadata["speed_source"] is None
