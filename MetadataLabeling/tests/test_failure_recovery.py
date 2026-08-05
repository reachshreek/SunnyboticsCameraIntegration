from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from solar_metadata_tagger.camera.mock_camera import (
    CameraFault,
    MockCamera,
    MockSpeedProvider,
)
from solar_metadata_tagger.config import GnssConfig, StorageConfig, TaggerConfig
from solar_metadata_tagger.errors import MetadataTaggerError
from solar_metadata_tagger.gnss import FixHistoryStore
from solar_metadata_tagger.models import GnssFix
from solar_metadata_tagger.service import MetadataTaggingService
from solar_metadata_tagger.storage import copy_image_atomic, write_json_atomic


def make_config(
    tmp_path: Path,
    mission_id: str = "mission-recovery-1",
    min_free_gb: float = 0.0,
    emergency_free_gb: float = 0.0,
) -> TaggerConfig:
    return TaggerConfig(
        robot_id="robot-1",
        mission_id=mission_id,
        storage=StorageConfig(
            root=tmp_path / "output",
            min_free_gb=min_free_gb,
            emergency_free_gb=emergency_free_gb,
        ),
        gnss=GnssConfig(max_fix_age_s=2.5),
        required_fields=("latitude", "longitude"),
    )


def valid_fix(captured: datetime) -> GnssFix:
    return GnssFix(
        latitude=37.0,
        longitude=-121.0,
        received_at_utc=captured,
        fix_time_utc=captured,
        fix_quality=1,
        satellites=12,
        hdop=0.8,
        speed_mps=0.5,
    )


def test_camera_unavailable_at_startup_raises_and_is_identified(
    tmp_path: Path,
) -> None:
    cam = MockCamera(fault=CameraFault.UNAVAILABLE_AT_STARTUP)
    with pytest.raises(RuntimeError, match="unavailable"):
        cam.open()
    assert cam._open is False


def test_camera_disconnection_during_capture_raises(tmp_path: Path) -> None:
    cam = MockCamera()
    cam.open()
    cam.fault = CameraFault.DISCONNECTED
    with pytest.raises(RuntimeError, match="disconnected"):
        cam.capture(tmp_path)
    assert cam._open is False


def test_camera_disconnection_does_not_lose_previously_written_images(
    tmp_path: Path, png_factory
) -> None:
    config = make_config(tmp_path)
    service = MetadataTaggingService(config)
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    source = png_factory(tmp_path / "frame.png")
    result = service.tag_image(
        source,
        captured_at_utc=captured,
        manual_fix=valid_fix(captured),
    )
    assert result.image_path.exists()

    cam = MockCamera(fault=CameraFault.DISCONNECTED)
    with pytest.raises(RuntimeError):
        cam.open()

    assert result.image_path.exists()


def test_invalid_camera_frame_is_quarantined_not_discarded(
    tmp_path: Path,
) -> None:
    cam = MockCamera(fault=CameraFault.INVALID_FRAME)
    cam.open()
    frame = cam.capture(tmp_path / "spool")
    assert frame.image_path.exists()
    assert frame.image_path.stat().st_size == 0

    config = make_config(tmp_path)
    service = MetadataTaggingService(config)
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    result = service.tag_image(
        frame.image_path,
        captured_at_utc=captured,
        manual_fix=valid_fix(captured),
    )
    assert result.image_path.exists()
    metadata = json.loads(result.metadata_path.read_text())
    assert metadata["image"]["validation_error"] is not None
    assert result.status == "quarantined"


def test_camera_timeout_raises_and_is_identified(tmp_path: Path) -> None:
    cam = MockCamera(fault=CameraFault.TIMEOUT, timeout_s=0.05)
    cam.open()
    with pytest.raises(RuntimeError, match="timed out"):
        cam.capture(tmp_path)


def test_gnss_unavailable_does_not_stop_image_capture(
    tmp_path: Path, png_factory
) -> None:
    config = make_config(tmp_path)
    service = MetadataTaggingService(config)
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    source = png_factory(tmp_path / "frame.png")
    result = service.tag_image(
        source,
        captured_at_utc=captured,
    )
    assert result.image_path.exists()
    metadata = json.loads(result.metadata_path.read_text())
    assert metadata["coordinates"]["valid"] is False
    assert any("gnss_fix_missing" in w for w in metadata["warnings"])


def test_invalid_gnss_coordinates_are_recorded_not_silently_accepted(
    tmp_path: Path, png_factory
) -> None:
    config = make_config(tmp_path)
    service = MetadataTaggingService(config)
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    source = png_factory(tmp_path / "frame.png")
    bad_fix = GnssFix(
        latitude=999.0,
        longitude=999.0,
        received_at_utc=captured,
        fix_quality=1,
    )
    result = service.tag_image(
        source,
        captured_at_utc=captured,
        manual_fix=bad_fix,
    )
    metadata = json.loads(result.metadata_path.read_text())
    assert metadata["coordinates"]["valid"] is False
    assert metadata["coordinates"]["latitude"] is None
    assert any("gnss_coordinates_invalid" in w for w in metadata["warnings"])


def test_gnss_signal_loss_does_not_stop_image_capture(
    tmp_path: Path, png_factory
) -> None:
    config = make_config(tmp_path)
    service = MetadataTaggingService(config)
    for i in range(3):
        source = png_factory(tmp_path / f"frame_{i}.png")
        captured = datetime(2026, 7, 15, 12, 0, i, tzinfo=timezone.utc)
        result = service.tag_image(
            source,
            captured_at_utc=captured,
        )
        assert result.image_path.exists()


def test_missing_speed_activates_fallback(tmp_path: Path) -> None:
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


def test_invalid_speed_activates_fallback(tmp_path: Path) -> None:
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
        speed_provider=MockSpeedProvider(mode="invalid"),
    )
    triggers = iter(provider)
    next(triggers)
    fallback = next(triggers)
    assert fallback.metadata["capture_mode"] == "fixed-rate-fallback"


def test_stale_speed_activates_fallback(tmp_path: Path) -> None:
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


def test_stale_speed_does_not_remain_active_after_timeout(tmp_path: Path) -> None:
    from solar_metadata_tagger.speed import SpeedSample

    stale_sample = SpeedSample(
        speed_mps=1.0,
        measured_at_utc=datetime(2020, 1, 1, tzinfo=timezone.utc),
        source="test-stale",
    )
    assert not stale_sample.is_fresh(max_age_s=2.5)


def test_valid_speed_recovery_returns_to_distance_capture(tmp_path: Path) -> None:
    from solar_metadata_tagger.config import CaptureConfig
    from solar_metadata_tagger.speed import SpeedSample
    from solar_metadata_tagger.triggers import TriggerProvider

    class RecoveringSpeedProvider:
        def __init__(self):
            self._call_count = 0

        def sample(self):
            self._call_count += 1
            if self._call_count <= 3:
                return None
            return SpeedSample(
                speed_mps=10.0,
                measured_at_utc=datetime.now(timezone.utc),
                source="mock-recovered",
            )

    provider = TriggerProvider(
        CaptureConfig(
            trigger_mode="distance",
            along_track_coverage_m=0.01,
            required_overlap_fraction=0.0,
            speed_timeout_s=1.0,
            speed_poll_s=0.001,
            fallback_interval_s=0.005,
            min_capture_interval_s=0.001,
            min_moving_speed_mps=0.0,
            max_images=3,
        ),
        speed_provider=RecoveringSpeedProvider(),
    )

    triggers = list(provider)
    modes = [t.metadata["capture_mode"] for t in triggers]
    assert "distance-initial" in modes
    assert "distance" in modes


def test_ssd_unavailable_raises_storage_error(tmp_path: Path) -> None:
    from solar_metadata_tagger.storage import ensure_free_space
    with pytest.raises(MetadataTaggerError) as exc_info:
        ensure_free_space(
            tmp_path,
            min_free_gb=999999.0,
            emergency_free_gb=999999.0,
        )
    assert exc_info.value.code == "STORAGE_EMERGENCY_LOW"


def test_ssd_full_stops_capture(tmp_path: Path, png_factory) -> None:
    config = make_config(
        tmp_path,
        min_free_gb=999999.0,
        emergency_free_gb=999999.0,
    )
    service = MetadataTaggingService(config)
    source = png_factory(tmp_path / "frame.png")
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(MetadataTaggerError) as exc_info:
        service.tag_image(
            source,
            captured_at_utc=captured,
            manual_fix=valid_fix(captured),
        )
    assert exc_info.value.code == "STORAGE_EMERGENCY_LOW"


def test_filesystem_write_failure_creates_recovery_record(
    tmp_path: Path, png_factory
) -> None:
    config = make_config(tmp_path)
    service = MetadataTaggingService(config)
    source = png_factory(tmp_path / "frame.png")
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)

    original_write = write_json_atomic
    call_count = 0

    def fail_first(destination, payload):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise MetadataTaggerError(
                "METADATA_WRITE_FAILED",
                "Simulated filesystem write failure.",
            )
        return original_write(destination, payload)

    with patch(
        "solar_metadata_tagger.service.write_json_atomic",
        side_effect=fail_first,
    ):
        with pytest.raises(MetadataTaggerError):
            service.tag_image(
                source,
                captured_at_utc=captured,
                manual_fix=valid_fix(captured),
            )

    recovery_files = list((tmp_path / "output" / "recovery").glob("*.json"))
    assert len(recovery_files) == 1
    recovery = json.loads(recovery_files[0].read_text())
    assert "preserved_image" in recovery
    assert "error" in recovery


def test_image_preserved_after_metadata_write_failure(
    tmp_path: Path, png_factory
) -> None:
    config = make_config(tmp_path)
    service = MetadataTaggingService(config)
    source = png_factory(tmp_path / "frame.png")
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)

    original_write = write_json_atomic
    call_count = 0

    def fail_first(destination, payload):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise MetadataTaggerError(
                "METADATA_WRITE_FAILED",
                "Simulated write failure.",
            )
        return original_write(destination, payload)

    with patch(
        "solar_metadata_tagger.service.write_json_atomic",
        side_effect=fail_first,
    ):
        with pytest.raises(MetadataTaggerError):
            service.tag_image(
                source,
                captured_at_utc=captured,
                manual_fix=valid_fix(captured),
            )

    preserved = list((tmp_path / "output" / "images").rglob("*.png"))
    assert len(preserved) == 1
    assert preserved[0].stat().st_size > 0


def test_application_restart_preserves_all_written_images(
    tmp_path: Path, png_factory
) -> None:
    config = make_config(tmp_path, mission_id="mission-restart")
    service1 = MetadataTaggingService(config)
    for i in range(5):
        source = png_factory(tmp_path / f"frame_{i}.png")
        captured = datetime(2026, 7, 15, 12, 0, i, tzinfo=timezone.utc)
        service1.tag_image(
            source,
            captured_at_utc=captured,
            manual_fix=valid_fix(captured),
        )

    service2 = MetadataTaggingService(config)
    for i in range(5, 10):
        source = png_factory(tmp_path / f"frame_{i}.png")
        captured = datetime(2026, 7, 15, 12, 0, i, tzinfo=timezone.utc)
        service2.tag_image(
            source,
            captured_at_utc=captured,
            manual_fix=valid_fix(captured),
        )

    images = list((tmp_path / "output" / "images").rglob("*.png"))
    assert len(images) == 10
    for image in images:
        assert image.stat().st_size > 0


def test_atomic_write_survives_interruption(tmp_path: Path) -> None:
    destination = tmp_path / "output.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text('{"original": true}', encoding="utf-8")

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=destination.parent,
            prefix=".output.json.",
            delete=False,
            encoding="utf-8",
        ) as tmp:
            temp_path = Path(tmp.name)
            tmp.write('{"new": true}')
        temp_path.unlink(missing_ok=True)
    except Exception:
        pass

    assert destination.read_text(encoding="utf-8") == '{"original": true}'


def test_failed_subsystem_is_identified_by_error_code(tmp_path: Path) -> None:
    from solar_metadata_tagger.storage import ensure_free_space

    try:
        ensure_free_space(
            tmp_path,
            min_free_gb=999999.0,
            emergency_free_gb=0.0,
        )
    except MetadataTaggerError as exc:
        assert exc.code == "STORAGE_LOW"
        assert exc.message is not None
        assert "free_gb" in exc.context
    else:
        pytest.fail("Expected MetadataTaggerError was not raised")


def test_unaffected_subsystem_continues_after_gnss_loss(
    tmp_path: Path, png_factory
) -> None:
    config = make_config(tmp_path)
    service = MetadataTaggingService(config)
    results = []
    for i in range(5):
        source = png_factory(tmp_path / f"frame_{i}.png")
        captured = datetime(2026, 7, 15, 12, 0, i, tzinfo=timezone.utc)
        fix = valid_fix(captured) if i < 2 else None
        result = service.tag_image(
            source,
            captured_at_utc=captured,
            manual_fix=fix,
        )
        results.append(result)

    assert all(r.image_path.exists() for r in results)
    assert results[0].status == "complete"
    assert results[2].status == "quarantined"


def test_camera_reconnection_resumes_capture(tmp_path: Path) -> None:
    cam = MockCamera(fault=CameraFault.DISCONNECTED)
    cam.reconnect()
    assert cam._open is True
    frame = cam.capture(tmp_path)
    assert frame.image_path.exists()
    cam.close()


def test_error_as_dict_contains_required_fields() -> None:
    exc = MetadataTaggerError(
        "TEST_CODE",
        "Test message",
        detail="some detail",
        path="/some/path",
    )
    d = exc.as_dict()
    assert d["error_code"] == "TEST_CODE"
    assert d["message"] == "Test message"
    assert "detail" in d["context"]
    assert "path" in d["context"]


def test_incomplete_file_identified_after_power_interruption(
    tmp_path: Path,
) -> None:
    path = tmp_path / "interrupted.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\n")
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    fix = GnssFix(
        latitude=37.0,
        longitude=-121.0,
        received_at_utc=captured,
        fix_quality=1,
        satellites=12,
        hdop=0.8,
    )
    result = MetadataTaggingService(make_config(tmp_path)).tag_image(
        path,
        captured_at_utc=captured,
        manual_fix=fix,
    )
    metadata = json.loads(result.metadata_path.read_text())
    assert metadata["image"]["validation_error"] is not None
    assert result.status == "quarantined"
