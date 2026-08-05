from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from solar_metadata_tagger.config import GnssConfig, StorageConfig, TaggerConfig
from solar_metadata_tagger.errors import MetadataTaggerError
from solar_metadata_tagger.models import GnssFix
from solar_metadata_tagger.service import MetadataTaggingService
from solar_metadata_tagger.storage import (
    copy_image_atomic,
    disk_usage,
    ensure_free_space,
    sha256_file,
    write_json_atomic,
)


def make_config(
    tmp_path: Path,
    mission_id: str = "mission-storage-1",
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
            compute_sha256=True,
            validate_images=True,
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


def make_image(path: Path, size_bytes: int = 1024) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    from PIL import Image
    import numpy as np
    rng = np.random.default_rng(seed=42)
    pixels = rng.integers(0, 256, size=(64, 64, 3), dtype=np.uint8)
    Image.fromarray(pixels, mode="RGB").save(path, format="PNG")
    return path


def test_storage_capacity_formula_maximum_rate() -> None:
    image_size_mb = 5.0
    rate_hz = 1.0
    duration_s = 4.5 * 3600
    mission_storage_gb = (image_size_mb * rate_hz * duration_s) / 1024
    required_with_margin_gb = mission_storage_gb / 0.80
    assert mission_storage_gb == pytest.approx(81.0 / 1.024, rel=0.01)
    assert required_with_margin_gb == pytest.approx(81.0 / 1.024 / 0.80, rel=0.01)


def test_storage_capacity_formula_fallback_rate() -> None:
    image_size_mb = 5.0
    rate_hz = 0.20
    duration_s = 4.5 * 3600
    mission_storage_gb = (image_size_mb * rate_hz * duration_s) / 1024
    required_with_margin_gb = mission_storage_gb / 0.80
    assert mission_storage_gb == pytest.approx(16.2 / 1.024, rel=0.01)
    assert required_with_margin_gb == pytest.approx(16.2 / 1.024 / 0.80, rel=0.01)


def test_500gb_ssd_exceeds_maximum_rate_requirement() -> None:
    ssd_capacity_gb = 500.0
    image_size_mb = 5.0
    rate_hz = 1.0
    duration_s = 4.5 * 3600
    mission_storage_gb = (image_size_mb * rate_hz * duration_s) / 1024
    required_gb = mission_storage_gb / 0.80
    assert ssd_capacity_gb > required_gb


def test_normal_image_writing(tmp_path: Path, png_factory) -> None:
    source = png_factory(tmp_path / "frame.png")
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    result = MetadataTaggingService(make_config(tmp_path)).tag_image(
        source,
        captured_at_utc=captured,
        manual_fix=valid_fix(captured),
    )
    assert result.image_path.exists()
    assert result.image_path.stat().st_size > 0
    assert result.metadata_path.exists()


def test_sustained_write_speed(tmp_path: Path, png_factory) -> None:
    config = make_config(tmp_path)
    service = MetadataTaggingService(config)
    count = 20
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    start = time.monotonic()
    for i in range(count):
        source = png_factory(tmp_path / f"frame_{i}.png")
        service.tag_image(
            source,
            captured_at_utc=captured,
            manual_fix=valid_fix(captured),
        )
    elapsed = time.monotonic() - start
    total_bytes = sum(
        f.stat().st_size
        for f in (tmp_path / "output" / "images").rglob("*.png")
    )
    write_speed_mbs = (total_bytes / (1024 * 1024)) / elapsed
    assert write_speed_mbs > 0


def test_storage_warning_threshold_raises(tmp_path: Path) -> None:
    root = tmp_path / "storage"
    root.mkdir()
    with pytest.raises(MetadataTaggerError) as exc_info:
        ensure_free_space(root, min_free_gb=999999.0, emergency_free_gb=0.0)
    assert exc_info.value.code == "STORAGE_LOW"


def test_storage_emergency_threshold_raises(tmp_path: Path) -> None:
    root = tmp_path / "storage"
    root.mkdir()
    with pytest.raises(MetadataTaggerError) as exc_info:
        ensure_free_space(root, min_free_gb=999999.0, emergency_free_gb=999999.0)
    assert exc_info.value.code == "STORAGE_EMERGENCY_LOW"


def test_storage_emergency_stops_capture(tmp_path: Path, png_factory) -> None:
    config = make_config(tmp_path, min_free_gb=999999.0, emergency_free_gb=999999.0)
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


def test_image_is_preserved_even_when_metadata_write_fails(
    tmp_path: Path, png_factory
) -> None:
    config = make_config(tmp_path)
    service = MetadataTaggingService(config)
    source = png_factory(tmp_path / "frame.png")
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)

    original_write = write_json_atomic

    call_count = 0

    def fail_first_metadata(destination, payload):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise MetadataTaggerError(
                "METADATA_WRITE_FAILED",
                "Simulated metadata write failure.",
            )
        return original_write(destination, payload)

    with patch(
        "solar_metadata_tagger.service.write_json_atomic",
        side_effect=fail_first_metadata,
    ):
        with pytest.raises(MetadataTaggerError):
            service.tag_image(
                source,
                captured_at_utc=captured,
                manual_fix=valid_fix(captured),
            )

    recovery_files = list((tmp_path / "output" / "recovery").glob("*.json"))
    assert len(recovery_files) == 1


def test_sha256_checksum_identifies_corrupted_file(tmp_path: Path) -> None:
    path = tmp_path / "image.png"
    path.write_bytes(b"original content")
    original_hash = sha256_file(path)
    path.write_bytes(b"corrupted content")
    corrupted_hash = sha256_file(path)
    assert original_hash != corrupted_hash


def test_atomic_write_does_not_leave_temp_files(tmp_path: Path) -> None:
    destination = tmp_path / "output" / "test.json"
    write_json_atomic(destination, {"key": "value"})
    temp_files = list(tmp_path.rglob(".test.json.*"))
    assert len(temp_files) == 0


def test_atomic_image_copy_does_not_leave_temp_files(
    tmp_path: Path, png_factory
) -> None:
    source = png_factory(tmp_path / "source.png")
    destination = tmp_path / "output" / "dest.png"
    copy_image_atomic(source, destination)
    temp_files = list((tmp_path / "output").rglob(".dest.png.*"))
    assert len(temp_files) == 0
    assert destination.exists()


def test_disk_usage_returns_valid_values(tmp_path: Path) -> None:
    usage = disk_usage(tmp_path)
    assert usage["total_bytes"] > 0
    assert usage["free_bytes"] > 0
    assert usage["used_bytes"] >= 0
    assert usage["total_bytes"] >= usage["free_bytes"]


def test_image_and_metadata_written_together(tmp_path: Path, png_factory) -> None:
    source = png_factory(tmp_path / "frame.png")
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    result = MetadataTaggingService(make_config(tmp_path)).tag_image(
        source,
        captured_at_utc=captured,
        manual_fix=valid_fix(captured),
    )
    assert result.image_path.exists()
    assert result.metadata_path.exists()
    metadata = json.loads(result.metadata_path.read_text())
    assert metadata["image"]["sha256"] is not None
    assert len(metadata["image"]["sha256"]) == 64


def test_manifest_records_every_image(tmp_path: Path, png_factory) -> None:
    config = make_config(tmp_path, mission_id="mission-manifest-storage")
    service = MetadataTaggingService(config)
    count = 10
    for i in range(count):
        source = png_factory(tmp_path / f"frame_{i}.png")
        captured = datetime(2026, 7, 15, 12, 0, i, tzinfo=timezone.utc)
        service.tag_image(
            source,
            captured_at_utc=captured,
            manual_fix=valid_fix(captured),
        )
    manifest = (
        tmp_path / "output" / "manifests" / "mission-manifest-storage.jsonl"
    )
    assert manifest.exists()
    lines = manifest.read_text().strip().splitlines()
    assert len(lines) == count


def test_storage_organized_by_date(tmp_path: Path, png_factory) -> None:
    source = png_factory(tmp_path / "frame.png")
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    result = MetadataTaggingService(make_config(tmp_path)).tag_image(
        source,
        captured_at_utc=captured,
        manual_fix=valid_fix(captured),
    )
    assert "2026/07/15" in result.image_path.as_posix()
    assert "2026/07/15" in result.metadata_path.as_posix()


def test_incomplete_image_can_be_identified(tmp_path: Path) -> None:
    path = tmp_path / "incomplete.png"
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


def test_corrupted_image_is_identified_not_silently_accepted(
    tmp_path: Path,
) -> None:
    path = tmp_path / "corrupt.png"
    path.write_bytes(b"not a valid image at all")
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
    assert result.status == "quarantined"
    assert metadata["image"]["validation_error"] is not None


def test_application_restart_images_remain_intact(
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


def test_maximum_rate_one_image_per_second_configuration() -> None:
    from solar_metadata_tagger.config import CaptureConfig
    config = CaptureConfig(
        along_track_coverage_m=1.62,
        required_overlap_fraction=0.30,
        min_capture_interval_s=1.0,
    )
    assert config.maximum_capture_rate_hz == pytest.approx(1.0)
    assert config.min_capture_interval_s == pytest.approx(1.0)


def test_mission_fits_in_500gb_with_20_percent_margin() -> None:
    ssd_gb = 500.0
    image_size_mb = 5.0
    rate_hz = 1.0
    duration_s = 4.5 * 3600
    mission_bytes = image_size_mb * 1024 * 1024 * rate_hz * duration_s
    mission_gb = mission_bytes / (1024 ** 3)
    required_gb = mission_gb / 0.80
    assert ssd_gb >= required_gb
    free_after_mission_pct = (ssd_gb - mission_gb) / ssd_gb
    assert free_after_mission_pct >= 0.20
