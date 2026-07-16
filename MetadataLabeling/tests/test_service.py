import json
import math
from datetime import datetime, timezone

from solar_metadata_tagger.config import GnssConfig, StorageConfig, TaggerConfig
from solar_metadata_tagger.models import GnssFix
from solar_metadata_tagger.service import MetadataTaggingService


def make_config(tmp_path, mission="mission-1") -> TaggerConfig:
    return TaggerConfig(
        robot_id="robot-1",
        mission_id=mission,
        storage=StorageConfig(root=tmp_path / "output", min_free_gb=0, emergency_free_gb=0),
        gnss=GnssConfig(max_fix_age_s=2.5),
        required_fields=("latitude", "longitude", "row", "panel"),
    )


def test_tag_image_with_manual_values(tmp_path, png_factory) -> None:
    source = png_factory(tmp_path / "frame.png")
    config = make_config(tmp_path)
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    fix = GnssFix(
        latitude=37.0,
        longitude=-121.0,
        altitude_m=10.0,
        received_at_utc=captured,
        fix_time_utc=captured,
        fix_quality=1,
        satellites=12,
        hdop=0.8,
    )
    result = MetadataTaggingService(config).tag_image(
        source, captured_at_utc=captured, manual_fix=fix, row="A", panel="001"
    )
    assert result.status == "complete"
    metadata = json.loads(result.metadata_path.read_text())
    assert metadata["schema_version"] == "2.0.0"
    assert metadata["robot_id"] == "robot-1"
    assert metadata["site"]["row"] == "A"
    assert metadata["coordinates"]["valid"] is True
    assert metadata["image"]["width_px"] == 64
    assert len(metadata["image"]["sha256"]) == 64
    assert result.image_path.exists()


def test_missing_metadata_is_quarantined_not_dropped(tmp_path, png_factory) -> None:
    source = png_factory(tmp_path / "frame.jpg")
    config = make_config(tmp_path, "mission-2")
    result = MetadataTaggingService(config).tag_image(
        source, captured_at_utc=datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    )
    assert result.status == "quarantined"
    assert result.image_path.exists()
    assert "quarantine/images" in result.image_path.as_posix()
    metadata = json.loads(result.metadata_path.read_text())
    assert metadata["coordinates"]["latitude"] is None
    assert metadata["site"]["row"] is None


def test_invalid_coordinates_can_never_be_complete(tmp_path, png_factory) -> None:
    source = png_factory(tmp_path / "frame.png")
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    fix = GnssFix(999.0, 999.0, captured, fix_time_utc=captured, fix_quality=1)
    result = MetadataTaggingService(make_config(tmp_path)).tag_image(
        source, captured_at_utc=captured, manual_fix=fix, row="A", panel="001"
    )
    metadata = json.loads(result.metadata_path.read_text())
    assert result.status == "quarantined"
    assert metadata["coordinates"]["valid"] is False
    assert metadata["coordinates"]["latitude"] is None
    assert "gnss_coordinates_invalid" in metadata["warnings"]


def test_nonfinite_coordinates_can_never_be_complete(tmp_path, png_factory) -> None:
    source = png_factory(tmp_path / "frame.png")
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    fix = GnssFix(math.nan, -121.0, captured, fix_time_utc=captured, fix_quality=1)
    result = MetadataTaggingService(make_config(tmp_path)).tag_image(
        source, captured_at_utc=captured, manual_fix=fix, row="A", panel="001"
    )
    assert result.status == "quarantined"


def test_corrupt_image_is_quarantined(tmp_path) -> None:
    source = tmp_path / "corrupt.png"
    source.write_bytes(b"not an image")
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    fix = GnssFix(37.0, -121.0, captured, fix_time_utc=captured, fix_quality=1)
    result = MetadataTaggingService(make_config(tmp_path)).tag_image(
        source, captured_at_utc=captured, manual_fix=fix, row="A", panel="001"
    )
    metadata = json.loads(result.metadata_path.read_text())
    assert result.status == "quarantined"
    assert metadata["image"]["validation_error"]["error_code"] == "IMAGE_INVALID"
