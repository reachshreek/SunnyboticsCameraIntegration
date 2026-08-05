from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from solar_metadata_tagger.config import (
    GnssConfig,
    StorageConfig,
    TaggerConfig,
)
from solar_metadata_tagger.models import GnssFix
from solar_metadata_tagger.service import MetadataTaggingService


def make_config(
    tmp_path: Path,
    robot_id: str = "robot-1",
    mission_id: str = "mission-pipeline-1",
) -> TaggerConfig:
    return TaggerConfig(
        robot_id=robot_id,
        mission_id=mission_id,
        storage=StorageConfig(
            root=tmp_path / "output",
            min_free_gb=0,
            emergency_free_gb=0,
        ),
        gnss=GnssConfig(max_fix_age_s=2.5),
        required_fields=("latitude", "longitude"),
    )


def valid_fix(captured: datetime) -> GnssFix:
    return GnssFix(
        latitude=37.0,
        longitude=-121.0,
        altitude_m=10.0,
        received_at_utc=captured,
        fix_time_utc=captured,
        fix_quality=1,
        satellites=12,
        hdop=0.8,
        speed_mps=0.2,
    )


def make_realistic_image(path: Path, size: tuple[int, int] = (2448, 2048)) -> Path:
    """
    Write a realistic-resolution PNG using PIL.
    The spec requires realistic dimensions and file sizes,
    not small placeholder images.
    """
    from PIL import Image
    import numpy as np

    path.parent.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed=42)
    pixels = rng.integers(0, 256, size=(size[1], size[0], 3), dtype=np.uint8)
    Image.fromarray(pixels, mode="RGB").save(path, format="PNG")
    return path


def tag_one(
    tmp_path: Path,
    source: Path,
    service: MetadataTaggingService,
    captured: datetime,
    fix: GnssFix | None = None,
    row: str | None = None,
    panel: str | None = None,
    trigger_metadata: dict | None = None,
    camera_metadata: dict | None = None,
):
    return service.tag_image(
        source,
        captured_at_utc=captured,
        manual_fix=fix or valid_fix(captured),
        row=row,
        panel=panel,
        trigger_metadata=trigger_metadata,
        camera_metadata=camera_metadata,
    )


def test_image_capture_input_is_accepted(tmp_path: Path, png_factory) -> None:
    source = png_factory(tmp_path / "frame.png")
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    result = MetadataTaggingService(make_config(tmp_path)).tag_image(
        source,
        captured_at_utc=captured,
        manual_fix=valid_fix(captured),
    )
    assert result.image_path.exists()
    assert result.metadata_path.exists()


def test_image_naming_includes_robot_and_mission(tmp_path: Path, png_factory) -> None:
    source = png_factory(tmp_path / "frame.png")
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    result = MetadataTaggingService(make_config(tmp_path)).tag_image(
        source,
        captured_at_utc=captured,
        manual_fix=valid_fix(captured),
    )
    assert "robot-1" in result.image_id
    assert "mission-pipeline-1" in result.image_id


def test_image_encoding_produces_valid_output_file(tmp_path: Path, png_factory) -> None:
    source = png_factory(tmp_path / "frame.png")
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    result = MetadataTaggingService(make_config(tmp_path)).tag_image(
        source,
        captured_at_utc=captured,
        manual_fix=valid_fix(captured),
    )
    assert result.image_path.stat().st_size > 0
    metadata = json.loads(result.metadata_path.read_text())
    assert metadata["image"]["byte_size"] > 0
    assert metadata["image"]["media_type"] == "image/png"


def test_timestamp_is_recorded_in_metadata(tmp_path: Path, png_factory) -> None:
    source = png_factory(tmp_path / "frame.png")
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    result = MetadataTaggingService(make_config(tmp_path)).tag_image(
        source,
        captured_at_utc=captured,
        manual_fix=valid_fix(captured),
    )
    metadata = json.loads(result.metadata_path.read_text())
    assert metadata["captured_at_utc"] == "2026-07-15T12:00:00.000Z"


def test_robot_id_appears_in_every_record(tmp_path: Path, png_factory) -> None:
    config = make_config(tmp_path, robot_id="robot-99")
    service = MetadataTaggingService(config)
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)

    for i in range(5):
        source = png_factory(tmp_path / f"frame_{i}.png")
        result = service.tag_image(
            source,
            captured_at_utc=captured,
            manual_fix=valid_fix(captured),
        )
        metadata = json.loads(result.metadata_path.read_text())
        assert metadata["robot_id"] == "robot-99"


def test_mission_id_appears_in_every_record(tmp_path: Path, png_factory) -> None:
    config = make_config(tmp_path, mission_id="mission-abc")
    service = MetadataTaggingService(config)
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)

    for i in range(5):
        source = png_factory(tmp_path / f"frame_{i}.png")
        result = service.tag_image(
            source,
            captured_at_utc=captured,
            manual_fix=valid_fix(captured),
        )
        metadata = json.loads(result.metadata_path.read_text())
        assert metadata["mission_id"] == "mission-abc"


def test_coordinate_association(tmp_path: Path, png_factory) -> None:
    source = png_factory(tmp_path / "frame.png")
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    fix = GnssFix(
        latitude=37.1234,
        longitude=-121.5678,
        received_at_utc=captured,
        fix_quality=1,
        satellites=12,
        hdop=0.8,
    )
    result = MetadataTaggingService(make_config(tmp_path)).tag_image(
        source,
        captured_at_utc=captured,
        manual_fix=fix,
    )
    metadata = json.loads(result.metadata_path.read_text())
    assert metadata["coordinates"]["latitude"] == pytest.approx(37.1234, abs=1e-6)
    assert metadata["coordinates"]["longitude"] == pytest.approx(-121.5678, abs=1e-6)
    assert metadata["coordinates"]["valid"] is True


def test_gnss_validity_association(tmp_path: Path, png_factory) -> None:
    source = png_factory(tmp_path / "frame.png")
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    result = MetadataTaggingService(make_config(tmp_path)).tag_image(
        source,
        captured_at_utc=captured,
    )
    metadata = json.loads(result.metadata_path.read_text())
    assert metadata["coordinates"]["valid"] is False
    assert metadata["coordinates"]["latitude"] is None


def test_capture_mode_association(tmp_path: Path, png_factory) -> None:
    source = png_factory(tmp_path / "frame.png")
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    trigger_metadata = {
        "capture_mode": "distance",
        "speed_source": "gnss",
        "speed_mps": 0.5,
    }
    result = MetadataTaggingService(make_config(tmp_path)).tag_image(
        source,
        captured_at_utc=captured,
        manual_fix=valid_fix(captured),
        trigger_metadata=trigger_metadata,
    )
    metadata = json.loads(result.metadata_path.read_text())
    assert metadata["trigger"]["capture_mode"] == "distance"


def test_speed_source_association(tmp_path: Path, png_factory) -> None:
    source = png_factory(tmp_path / "frame.png")
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    trigger_metadata = {
        "capture_mode": "distance",
        "speed_source": "gnss",
        "speed_mps": 0.5,
    }
    result = MetadataTaggingService(make_config(tmp_path)).tag_image(
        source,
        captured_at_utc=captured,
        manual_fix=valid_fix(captured),
        trigger_metadata=trigger_metadata,
    )
    metadata = json.loads(result.metadata_path.read_text())
    assert metadata["trigger"]["speed_source"] == "gnss"


def test_storage_organization_by_date(tmp_path: Path, png_factory) -> None:
    source = png_factory(tmp_path / "frame.png")
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    result = MetadataTaggingService(make_config(tmp_path)).tag_image(
        source,
        captured_at_utc=captured,
        manual_fix=valid_fix(captured),
    )
    assert "2026/07/15" in result.image_path.as_posix()
    assert "2026/07/15" in result.metadata_path.as_posix()


def test_duplicate_prevention_unique_image_ids(tmp_path: Path, png_factory) -> None:
    config = make_config(tmp_path)
    service = MetadataTaggingService(config)
    image_ids = set()

    for i in range(10):
        source = png_factory(tmp_path / f"frame_{i}.png")
        captured = datetime(2026, 7, 15, 12, 0, i, tzinfo=timezone.utc)
        result = service.tag_image(
            source,
            captured_at_utc=captured,
            manual_fix=valid_fix(captured),
        )
        assert result.image_id not in image_ids
        image_ids.add(result.image_id)

    assert len(image_ids) == 10


def test_checksum_is_created(tmp_path: Path, png_factory) -> None:
    source = png_factory(tmp_path / "frame.png")
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    result = MetadataTaggingService(make_config(tmp_path)).tag_image(
        source,
        captured_at_utc=captured,
        manual_fix=valid_fix(captured),
    )
    metadata = json.loads(result.metadata_path.read_text())
    assert metadata["image"]["sha256"] is not None
    assert len(metadata["image"]["sha256"]) == 64


def test_upload_queuing_manifest_is_written(tmp_path: Path, png_factory) -> None:
    config = make_config(tmp_path, mission_id="mission-manifest-1")
    service = MetadataTaggingService(config)
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    source = png_factory(tmp_path / "frame.png")
    service.tag_image(
        source,
        captured_at_utc=captured,
        manual_fix=valid_fix(captured),
    )
    manifest = (
        tmp_path / "output" / "manifests" / "mission-manifest-1.jsonl"
    )
    assert manifest.exists()
    lines = manifest.read_text().strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["mission_id"] == "mission-manifest-1"


def test_upload_confirmation_traceable_to_input(tmp_path: Path, png_factory) -> None:
    source = png_factory(tmp_path / "frame.png")
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    result = MetadataTaggingService(make_config(tmp_path)).tag_image(
        source,
        captured_at_utc=captured,
        manual_fix=valid_fix(captured),
    )
    metadata = json.loads(result.metadata_path.read_text())
    assert metadata["image_id"] == result.image_id
    assert result.image_path.name.startswith(result.image_id)


def test_optional_row_panel_do_not_affect_completeness(
    tmp_path: Path, png_factory
) -> None:
    source = png_factory(tmp_path / "frame.png")
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    result = MetadataTaggingService(make_config(tmp_path)).tag_image(
        source,
        captured_at_utc=captured,
        manual_fix=valid_fix(captured),
    )
    assert result.status == "complete"
    metadata = json.loads(result.metadata_path.read_text())
    assert metadata["site"]["row"] is None
    assert metadata["site"]["panel"] is None
    assert not any(
        w.startswith("missing_required_fields")
        for w in metadata["warnings"]
    )


def test_no_image_receives_metadata_from_another(
    tmp_path: Path, png_factory
) -> None:
    config = make_config(tmp_path)
    service = MetadataTaggingService(config)
    results = []

    for i in range(5):
        source = png_factory(tmp_path / f"frame_{i}.png")
        captured = datetime(2026, 7, 15, 12, 0, i, tzinfo=timezone.utc)
        fix = GnssFix(
            latitude=37.0 + i * 0.001,
            longitude=-121.0,
            received_at_utc=captured,
            fix_quality=1,
            satellites=12,
            hdop=0.8,
        )
        results.append(
            service.tag_image(
                source,
                captured_at_utc=captured,
                manual_fix=fix,
            )
        )

    for i, result in enumerate(results):
        metadata = json.loads(result.metadata_path.read_text())
        expected_lat = round(37.0 + i * 0.001, 8)
        assert metadata["coordinates"]["latitude"] == pytest.approx(
            expected_lat, abs=1e-6
        )


def test_every_output_record_traceable_to_input(
    tmp_path: Path, png_factory
) -> None:
    config = make_config(tmp_path, mission_id="mission-trace-1")
    service = MetadataTaggingService(config)
    image_ids = []

    for i in range(5):
        source = png_factory(tmp_path / f"frame_{i}.png")
        captured = datetime(2026, 7, 15, 12, 0, i, tzinfo=timezone.utc)
        result = service.tag_image(
            source,
            captured_at_utc=captured,
            manual_fix=valid_fix(captured),
        )
        image_ids.append(result.image_id)

    manifest = (
        tmp_path / "output" / "manifests" / "mission-trace-1.jsonl"
    )
    manifest_ids = [
        json.loads(line)["image_id"]
        for line in manifest.read_text().strip().splitlines()
    ]

    for image_id in image_ids:
        assert image_id in manifest_ids


def test_realistic_image_dimensions_are_processed(tmp_path: Path) -> None:
    source = make_realistic_image(tmp_path / "realistic.png", size=(2448, 2048))
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    result = MetadataTaggingService(make_config(tmp_path)).tag_image(
        source,
        captured_at_utc=captured,
        manual_fix=valid_fix(captured),
    )
    metadata = json.loads(result.metadata_path.read_text())
    assert metadata["image"]["width_px"] == 2448
    assert metadata["image"]["height_px"] == 2048
    assert result.image_path.stat().st_size > 100_000


def test_1000_images_processed_no_corruption_no_loss(
    tmp_path: Path, png_factory
) -> None:
    config = make_config(tmp_path, mission_id="mission-bulk-1")
    service = MetadataTaggingService(config)
    image_ids = set()
    count = 1000

    for i in range(count):
        source = png_factory(tmp_path / f"bulk_{i}.png")
        captured = datetime(2026, 7, 15, 12, i // 60, i % 60, tzinfo=timezone.utc)
        result = service.tag_image(
            source,
            captured_at_utc=captured,
            manual_fix=valid_fix(captured),
        )
        assert result.image_path.exists(), f"Image {i} missing"
        assert result.metadata_path.exists(), f"Metadata {i} missing"
        assert result.image_id not in image_ids, f"Duplicate image ID at {i}"
        image_ids.add(result.image_id)

    assert len(image_ids) == count

    manifest = tmp_path / "output" / "manifests" / "mission-bulk-1.jsonl"
    manifest_lines = manifest.read_text().strip().splitlines()
    assert len(manifest_lines) == count

    manifest_ids = {json.loads(line)["image_id"] for line in manifest_lines}
    assert manifest_ids == image_ids


def test_processing_completes_within_timing_limits(
    tmp_path: Path, png_factory
) -> None:
    config = make_config(tmp_path)
    service = MetadataTaggingService(config)
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    source = png_factory(tmp_path / "frame.png")

    start = time.monotonic()
    service.tag_image(
        source,
        captured_at_utc=captured,
        manual_fix=valid_fix(captured),
    )
    elapsed = time.monotonic() - start

    assert elapsed < 5.0


def test_no_unexpected_duplicate_files(tmp_path: Path, png_factory) -> None:
    config = make_config(tmp_path)
    service = MetadataTaggingService(config)

    for i in range(5):
        source = png_factory(tmp_path / f"frame_{i}.png")
        captured = datetime(2026, 7, 15, 12, 0, i, tzinfo=timezone.utc)
        service.tag_image(
            source,
            captured_at_utc=captured,
            manual_fix=valid_fix(captured),
        )

    image_files = list((tmp_path / "output" / "images").rglob("*.png"))
    image_names = [f.name for f in image_files]
    assert len(image_names) == len(set(image_names))
