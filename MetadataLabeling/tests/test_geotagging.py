from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from solar_metadata_tagger.config import GnssConfig, StorageConfig, TaggerConfig
from solar_metadata_tagger.gnss import FixHistoryStore
from solar_metadata_tagger.models import GnssFix
from solar_metadata_tagger.service import MetadataTaggingService


def make_config(
    tmp_path: Path,
    robot_id: str = "robot-1",
    mission_id: str = "mission-gnss-1",
    max_fix_age_s: float = 2.5,
) -> TaggerConfig:
    return TaggerConfig(
        robot_id=robot_id,
        mission_id=mission_id,
        storage=StorageConfig(
            root=tmp_path / "output",
            min_free_gb=0,
            emergency_free_gb=0,
        ),
        gnss=GnssConfig(
            max_fix_age_s=max_fix_age_s,
            future_tolerance_s=0.25,
            require_fix_quality=True,
            min_satellites=4,
            max_hdop=5.0,
        ),
        required_fields=("latitude", "longitude"),
    )


def make_fix(
    at: datetime,
    lat: float = 37.0,
    lon: float = -121.0,
    speed_mps: float | None = 0.5,
    fix_quality: int = 1,
    satellites: int = 12,
    hdop: float = 0.8,
) -> GnssFix:
    return GnssFix(
        latitude=lat,
        longitude=lon,
        received_at_utc=at,
        fix_time_utc=at,
        fix_quality=fix_quality,
        satellites=satellites,
        hdop=hdop,
        speed_mps=speed_mps,
    )


def tag(
    service: MetadataTaggingService,
    source: Path,
    captured: datetime,
    fix: GnssFix | None = None,
) -> dict:
    result = service.tag_image(
        source,
        captured_at_utc=captured,
        manual_fix=fix,
    )
    return json.loads(result.metadata_path.read_text())


def test_stationary_coordinate(tmp_path: Path, png_factory) -> None:
    source = png_factory(tmp_path / "frame.png")
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    fix = make_fix(captured, lat=37.1234, lon=-121.5678)
    metadata = tag(
        MetadataTaggingService(make_config(tmp_path)),
        source,
        captured,
        fix,
    )
    assert metadata["coordinates"]["latitude"] == pytest.approx(37.1234, abs=1e-6)
    assert metadata["coordinates"]["longitude"] == pytest.approx(-121.5678, abs=1e-6)
    assert metadata["coordinates"]["valid"] is True


def test_sequence_of_changing_coordinates(tmp_path: Path, png_factory) -> None:
    config = make_config(tmp_path)
    service = MetadataTaggingService(config)
    coords = [
        (37.0, -121.0),
        (37.001, -121.001),
        (37.002, -121.002),
        (37.003, -121.003),
        (37.004, -121.004),
    ]
    for i, (lat, lon) in enumerate(coords):
        source = png_factory(tmp_path / f"frame_{i}.png")
        captured = datetime(2026, 7, 15, 12, 0, i, tzinfo=timezone.utc)
        fix = make_fix(captured, lat=lat, lon=lon)
        metadata = tag(service, source, captured, fix)
        assert metadata["coordinates"]["latitude"] == pytest.approx(lat, abs=1e-6)
        assert metadata["coordinates"]["longitude"] == pytest.approx(lon, abs=1e-6)


def test_sequence_of_changing_speeds(tmp_path: Path, png_factory) -> None:
    config = make_config(tmp_path)
    service = MetadataTaggingService(config)
    speeds = [0.0, 0.2, 0.5, 1.0, 0.3]
    for i, speed in enumerate(speeds):
        source = png_factory(tmp_path / f"frame_{i}.png")
        captured = datetime(2026, 7, 15, 12, 0, i, tzinfo=timezone.utc)
        fix = make_fix(captured, speed_mps=speed)
        metadata = tag(service, source, captured, fix)
        assert metadata["coordinates"]["speed_mps"] == pytest.approx(speed, abs=1e-3)


def test_zero_speed_is_recorded(tmp_path: Path, png_factory) -> None:
    source = png_factory(tmp_path / "frame.png")
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    fix = make_fix(captured, speed_mps=0.0)
    metadata = tag(
        MetadataTaggingService(make_config(tmp_path)),
        source,
        captured,
        fix,
    )
    assert metadata["coordinates"]["speed_mps"] == pytest.approx(0.0, abs=1e-3)
    assert metadata["coordinates"]["valid"] is True


def test_missing_speed_does_not_invalidate_fix(tmp_path: Path, png_factory) -> None:
    source = png_factory(tmp_path / "frame.png")
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    fix = make_fix(captured, speed_mps=None)
    metadata = tag(
        MetadataTaggingService(make_config(tmp_path)),
        source,
        captured,
        fix,
    )
    assert metadata["coordinates"]["valid"] is True
    assert metadata["coordinates"]["speed_mps"] is None


def test_missing_location_data_is_clearly_marked(tmp_path: Path, png_factory) -> None:
    source = png_factory(tmp_path / "frame.png")
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    metadata = tag(
        MetadataTaggingService(make_config(tmp_path)),
        source,
        captured,
        fix=None,
    )
    assert metadata["coordinates"]["valid"] is False
    assert metadata["coordinates"]["latitude"] is None
    assert metadata["coordinates"]["longitude"] is None
    assert any(
        "gnss_fix_missing" in w for w in metadata["warnings"]
    )


def test_missing_location_does_not_discard_image(tmp_path: Path, png_factory) -> None:
    source = png_factory(tmp_path / "frame.png")
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    result = MetadataTaggingService(make_config(tmp_path)).tag_image(
        source,
        captured_at_utc=captured,
    )
    assert result.image_path.exists()
    assert result.metadata_path.exists()


def test_delayed_location_data_outside_window_is_marked(
    tmp_path: Path, png_factory
) -> None:
    source = png_factory(tmp_path / "frame.png")
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    stale_fix = make_fix(
        captured - timedelta(seconds=10),
        lat=37.0,
        lon=-121.0,
    )
    metadata = tag(
        MetadataTaggingService(make_config(tmp_path, max_fix_age_s=2.5)),
        source,
        captured,
        stale_fix,
    )
    assert metadata["coordinates"]["fresh"] is False
    assert metadata["coordinates"]["valid"] is False
    assert any("gnss_fix_outside_window" in w for w in metadata["warnings"])


def test_invalid_latitude_is_rejected(tmp_path: Path, png_factory) -> None:
    source = png_factory(tmp_path / "frame.png")
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    bad_fix = make_fix(captured, lat=999.0, lon=-121.0)
    metadata = tag(
        MetadataTaggingService(make_config(tmp_path)),
        source,
        captured,
        bad_fix,
    )
    assert metadata["coordinates"]["valid"] is False
    assert metadata["coordinates"]["latitude"] is None
    assert any("gnss_coordinates_invalid" in w for w in metadata["warnings"])


def test_invalid_longitude_is_rejected(tmp_path: Path, png_factory) -> None:
    source = png_factory(tmp_path / "frame.png")
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    bad_fix = make_fix(captured, lat=37.0, lon=999.0)
    metadata = tag(
        MetadataTaggingService(make_config(tmp_path)),
        source,
        captured,
        bad_fix,
    )
    assert metadata["coordinates"]["valid"] is False
    assert metadata["coordinates"]["latitude"] is None
    assert any("gnss_coordinates_invalid" in w for w in metadata["warnings"])


def test_duplicate_timestamps_produce_unique_image_ids(
    tmp_path: Path, png_factory
) -> None:
    config = make_config(tmp_path)
    service = MetadataTaggingService(config)
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    fix = make_fix(captured)
    ids = set()
    for i in range(5):
        source = png_factory(tmp_path / f"frame_{i}.png")
        result = service.tag_image(
            source,
            captured_at_utc=captured,
            manual_fix=fix,
        )
        assert result.image_id not in ids
        ids.add(result.image_id)
    assert len(ids) == 5


def test_out_of_order_timestamps_do_not_cause_wrong_assignment(
    tmp_path: Path, png_factory
) -> None:
    config = make_config(tmp_path)
    service = MetadataTaggingService(config)
    t1 = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 7, 15, 12, 0, 5, tzinfo=timezone.utc)
    fix1 = make_fix(t1, lat=37.0)
    fix2 = make_fix(t2, lat=38.0)

    source2 = png_factory(tmp_path / "frame_2.png")
    meta2 = tag(service, source2, t2, fix2)

    source1 = png_factory(tmp_path / "frame_1.png")
    meta1 = tag(service, source1, t1, fix1)

    assert meta1["coordinates"]["latitude"] == pytest.approx(37.0, abs=1e-6)
    assert meta2["coordinates"]["latitude"] == pytest.approx(38.0, abs=1e-6)


def test_midnight_date_change(tmp_path: Path, png_factory) -> None:
    source = png_factory(tmp_path / "frame.png")
    midnight = datetime(2026, 7, 16, 0, 0, 0, tzinfo=timezone.utc)
    fix = make_fix(midnight)
    result = MetadataTaggingService(make_config(tmp_path)).tag_image(
        source,
        captured_at_utc=midnight,
        manual_fix=fix,
    )
    assert result.image_path.exists()
    metadata = json.loads(result.metadata_path.read_text())
    assert "2026-07-16" in metadata["captured_at_utc"]
    assert "2026/07/16" in result.image_path.as_posix()


def test_timezone_offset_stored_as_utc(tmp_path: Path, png_factory) -> None:
    source = png_factory(tmp_path / "frame.png")
    from datetime import timezone as tz
    offset = tz(timedelta(hours=5, minutes=30))
    captured_local = datetime(2026, 7, 15, 17, 30, 0, tzinfo=offset)
    captured_utc = captured_local.astimezone(timezone.utc)
    fix = make_fix(captured_utc)
    result = MetadataTaggingService(make_config(tmp_path)).tag_image(
        source,
        captured_at_utc=captured_local,
        manual_fix=fix,
    )
    metadata = json.loads(result.metadata_path.read_text())
    assert metadata["captured_at_utc"] == "2026-07-15T12:00:00.000Z"


def test_unavailable_gnss_signal_does_not_crash(tmp_path: Path, png_factory) -> None:
    source = png_factory(tmp_path / "frame.png")
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    result = MetadataTaggingService(make_config(tmp_path)).tag_image(
        source,
        captured_at_utc=captured,
    )
    assert result.image_path.exists()
    metadata = json.loads(result.metadata_path.read_text())
    assert metadata["coordinates"]["valid"] is False


def test_gnss_signal_recovery_uses_new_fix(tmp_path: Path, png_factory) -> None:
    config = make_config(tmp_path)
    service = MetadataTaggingService(config)
    captured_no_fix = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    captured_with_fix = datetime(2026, 7, 15, 12, 0, 5, tzinfo=timezone.utc)

    source1 = png_factory(tmp_path / "frame_1.png")
    meta1 = tag(service, source1, captured_no_fix, fix=None)
    assert meta1["coordinates"]["valid"] is False

    source2 = png_factory(tmp_path / "frame_2.png")
    recovery_fix = make_fix(captured_with_fix, lat=37.5, lon=-121.5)
    meta2 = tag(service, source2, captured_with_fix, recovery_fix)
    assert meta2["coordinates"]["valid"] is True
    assert meta2["coordinates"]["latitude"] == pytest.approx(37.5, abs=1e-6)


def test_valid_image_id_and_timestamp_for_every_valid_image(
    tmp_path: Path, png_factory
) -> None:
    config = make_config(tmp_path)
    service = MetadataTaggingService(config)
    for i in range(5):
        captured = datetime(2026, 7, 15, 12, 0, i, tzinfo=timezone.utc)
        source = png_factory(tmp_path / f"frame_{i}.png")
        fix = make_fix(captured)
        result = service.tag_image(
            source,
            captured_at_utc=captured,
            manual_fix=fix,
        )
        metadata = json.loads(result.metadata_path.read_text())
        assert result.image_id in metadata["image_id"]
        assert metadata["captured_at_utc"].endswith("Z")


def test_robot_id_in_every_record(tmp_path: Path, png_factory) -> None:
    config = make_config(tmp_path, robot_id="robot-gnss-test")
    service = MetadataTaggingService(config)
    for i in range(5):
        source = png_factory(tmp_path / f"frame_{i}.png")
        captured = datetime(2026, 7, 15, 12, 0, i, tzinfo=timezone.utc)
        metadata = tag(service, source, captured, make_fix(captured))
        assert metadata["robot_id"] == "robot-gnss-test"


def test_mission_id_in_every_record(tmp_path: Path, png_factory) -> None:
    config = make_config(tmp_path, mission_id="mission-gnss-verify")
    service = MetadataTaggingService(config)
    for i in range(5):
        source = png_factory(tmp_path / f"frame_{i}.png")
        captured = datetime(2026, 7, 15, 12, 0, i, tzinfo=timezone.utc)
        metadata = tag(service, source, captured, make_fix(captured))
        assert metadata["mission_id"] == "mission-gnss-verify"


def test_existing_mission_id_produces_unique_traceable_records(
    tmp_path: Path, png_factory
) -> None:
    mission_id = "existing-mission-format-b"
    config = make_config(tmp_path, mission_id=mission_id)
    service = MetadataTaggingService(config)
    ids = []
    for i in range(5):
        source = png_factory(tmp_path / f"frame_{i}.png")
        captured = datetime(2026, 7, 15, 12, 0, i, tzinfo=timezone.utc)
        result = service.tag_image(
            source,
            captured_at_utc=captured,
            manual_fix=make_fix(captured),
        )
        ids.append(result.image_id)
    assert len(ids) == len(set(ids))
    manifest = tmp_path / "output" / "manifests" / f"{mission_id}.jsonl"
    assert manifest.exists()
    manifest_ids = [
        json.loads(line)["image_id"]
        for line in manifest.read_text().strip().splitlines()
    ]
    for image_id in ids:
        assert image_id in manifest_ids


def test_valid_gnss_fix_produces_expected_lat_lon(
    tmp_path: Path, png_factory
) -> None:
    source = png_factory(tmp_path / "frame.png")
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    fix = make_fix(captured, lat=36.9876, lon=-122.1234)
    metadata = tag(
        MetadataTaggingService(make_config(tmp_path)),
        source,
        captured,
        fix,
    )
    assert metadata["coordinates"]["latitude"] == pytest.approx(36.9876, abs=1e-6)
    assert metadata["coordinates"]["longitude"] == pytest.approx(-122.1234, abs=1e-6)


def test_row_and_panel_optional_do_not_affect_completeness(
    tmp_path: Path, png_factory
) -> None:
    source = png_factory(tmp_path / "frame.png")
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    metadata = tag(
        MetadataTaggingService(make_config(tmp_path)),
        source,
        captured,
        make_fix(captured),
    )
    assert metadata["status"] == "complete"
    assert metadata["site"]["row"] is None
    assert metadata["site"]["panel"] is None
    assert not any(
        w.startswith("missing_required_fields") for w in metadata["warnings"]
    )


def test_fix_age_window_is_defined_and_enforced(
    tmp_path: Path, png_factory
) -> None:
    source = png_factory(tmp_path / "frame.png")
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    just_inside = make_fix(captured - timedelta(seconds=2.4))
    just_outside = make_fix(captured - timedelta(seconds=2.6))

    meta_inside = tag(
        MetadataTaggingService(make_config(tmp_path, max_fix_age_s=2.5)),
        source,
        captured,
        just_inside,
    )
    assert meta_inside["coordinates"]["fresh"] is True

    source2 = png_factory(tmp_path / "frame2.png")
    meta_outside = tag(
        MetadataTaggingService(make_config(tmp_path / "b", max_fix_age_s=2.5)),
        source2,
        captured,
        just_outside,
    )
    assert meta_outside["coordinates"]["fresh"] is False


def test_stale_fix_does_not_silently_appear_as_valid(
    tmp_path: Path, png_factory
) -> None:
    source = png_factory(tmp_path / "frame.png")
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    stale_fix = make_fix(captured - timedelta(seconds=10))
    metadata = tag(
        MetadataTaggingService(make_config(tmp_path, max_fix_age_s=2.5)),
        source,
        captured,
        stale_fix,
    )
    assert metadata["coordinates"]["valid"] is False
    assert any("gnss_fix_outside_window" in w for w in metadata["warnings"])


def test_gnss_speed_available_from_valid_fix(tmp_path: Path, png_factory) -> None:
    source = png_factory(tmp_path / "frame.png")
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    fix = make_fix(captured, speed_mps=0.75)
    metadata = tag(
        MetadataTaggingService(make_config(tmp_path)),
        source,
        captured,
        fix,
    )
    assert metadata["coordinates"]["speed_mps"] == pytest.approx(0.75, abs=1e-3)


def test_fix_store_selects_closest_fix_for_capture() -> None:
    capture = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    store = FixHistoryStore()
    store.update(make_fix(capture - timedelta(seconds=2), lat=1.0))
    store.update(make_fix(capture - timedelta(milliseconds=100), lat=2.0))
    store.update(make_fix(capture + timedelta(milliseconds=50), lat=3.0))
    selected = store.select_for_capture(capture, max_age_s=3.0, future_tolerance_s=0.25)
    assert selected is not None
    assert selected.latitude == pytest.approx(2.0)


def test_fix_store_rejects_future_fix_beyond_tolerance() -> None:
    capture = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    store = FixHistoryStore()
    store.update(make_fix(capture + timedelta(milliseconds=300), lat=1.0))
    selected = store.select_for_capture(capture, max_age_s=2.5, future_tolerance_s=0.25)
    assert selected is None


def test_fix_store_returns_none_when_empty() -> None:
    store = FixHistoryStore()
    capture = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    assert store.select_for_capture(capture, max_age_s=2.5, future_tolerance_s=0.25) is None
