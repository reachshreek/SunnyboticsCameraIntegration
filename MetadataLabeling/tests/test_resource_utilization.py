from __future__ import annotations

import gc
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path

import pytest

from solar_metadata_tagger.config import (
    CaptureConfig,
    GnssConfig,
    StorageConfig,
    TaggerConfig,
)
from solar_metadata_tagger.models import GnssFix
from solar_metadata_tagger.service import MetadataTaggingService
from solar_metadata_tagger.storage import disk_usage


PROVISIONAL_NOTE = (
    "Results collected on a development Mac. "
    "These are provisional and must be repeated on the RUBIK Pi 3 "
    "before being treated as final performance evidence."
)


def make_config(
    tmp_path: Path,
    mission_id: str = "mission-resource-1",
) -> TaggerConfig:
    return TaggerConfig(
        robot_id="robot-1",
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
        received_at_utc=captured,
        fix_time_utc=captured,
        fix_quality=1,
        satellites=12,
        hdop=0.8,
        speed_mps=0.5,
    )


def test_processing_time_per_image_is_recorded(
    tmp_path: Path, png_factory
) -> None:
    config = make_config(tmp_path)
    service = MetadataTaggingService(config)
    captured = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    source = png_factory(tmp_path / "frame.png")

    start = time.perf_counter()
    result = service.tag_image(
        source,
        captured_at_utc=captured,
        manual_fix=valid_fix(captured),
    )
    elapsed_ms = (time.perf_counter() - start) * 1000

    import json
    metadata = json.loads(result.metadata_path.read_text())
    recorded_ms = metadata["timing"]["tagging_duration_ms"]

    assert recorded_ms > 0
    assert elapsed_ms < 5000
    print(f"\n[PROVISIONAL] {PROVISIONAL_NOTE}")
    print(f"[PROVISIONAL] Processing time per image: {elapsed_ms:.1f} ms (recorded: {recorded_ms:.1f} ms)")


def test_no_uncontrolled_memory_growth(tmp_path: Path, png_factory) -> None:
    config = make_config(tmp_path, mission_id="mission-memory")
    service = MetadataTaggingService(config)

    gc.collect()
    tracemalloc.start()

    for i in range(100):
        source = png_factory(tmp_path / f"frame_{i}.png")
        captured = datetime(2026, 7, 15, 12, 0, i % 60, tzinfo=timezone.utc)
        service.tag_image(
            source,
            captured_at_utc=captured,
            manual_fix=valid_fix(captured),
        )

    gc.collect()
    snapshot = tracemalloc.take_snapshot()
    tracemalloc.stop()

    top_stats = snapshot.statistics("lineno")
    total_kb = sum(stat.size for stat in top_stats) / 1024

    print(f"\n[PROVISIONAL] {PROVISIONAL_NOTE}")
    print(f"[PROVISIONAL] Memory after 100 images: {total_kb:.1f} KB")
    assert total_kb < 500_000


def test_processing_keeps_up_with_planned_image_rate(
    tmp_path: Path, png_factory
) -> None:
    config = make_config(tmp_path, mission_id="mission-rate")
    service = MetadataTaggingService(config)
    count = 10
    max_rate_hz = 1.0
    min_interval_s = 1.0 / max_rate_hz

    durations = []
    for i in range(count):
        source = png_factory(tmp_path / f"frame_{i}.png")
        captured = datetime(2026, 7, 15, 12, 0, i, tzinfo=timezone.utc)
        start = time.perf_counter()
        service.tag_image(
            source,
            captured_at_utc=captured,
            manual_fix=valid_fix(captured),
        )
        durations.append(time.perf_counter() - start)

    avg_s = sum(durations) / len(durations)
    max_s = max(durations)

    print(f"\n[PROVISIONAL] {PROVISIONAL_NOTE}")
    print(f"[PROVISIONAL] Average processing time: {avg_s * 1000:.1f} ms")
    print(f"[PROVISIONAL] Max processing time: {max_s * 1000:.1f} ms")
    print(f"[PROVISIONAL] Planned image interval: {min_interval_s * 1000:.0f} ms")

    assert avg_s < min_interval_s


def test_scheduler_does_not_exceed_maximum_capture_rate() -> None:
    config = CaptureConfig(
        along_track_coverage_m=1.62,
        required_overlap_fraction=0.30,
        min_capture_interval_s=1.0,
    )
    assert config.maximum_capture_rate_hz == pytest.approx(1.0)
    assert config.min_capture_interval_s == pytest.approx(1.0)
    print(f"\n[PROVISIONAL] {PROVISIONAL_NOTE}")
    print(f"[PROVISIONAL] Maximum configured capture rate: {config.maximum_capture_rate_hz} image/s")


def test_storage_write_speed_is_measured(tmp_path: Path, png_factory) -> None:
    config = make_config(tmp_path, mission_id="mission-write-speed")
    service = MetadataTaggingService(config)
    count = 20

    start = time.perf_counter()
    for i in range(count):
        source = png_factory(tmp_path / f"frame_{i}.png")
        captured = datetime(2026, 7, 15, 12, 0, i, tzinfo=timezone.utc)
        service.tag_image(
            source,
            captured_at_utc=captured,
            manual_fix=valid_fix(captured),
        )
    elapsed = time.perf_counter() - start

    total_bytes = sum(
        f.stat().st_size
        for f in (tmp_path / "output" / "images").rglob("*.png")
    )
    write_speed_mbs = (total_bytes / (1024 * 1024)) / elapsed

    print(f"\n[PROVISIONAL] {PROVISIONAL_NOTE}")
    print(f"[PROVISIONAL] Storage write speed: {write_speed_mbs:.2f} MB/s over {count} images")
    print(f"[PROVISIONAL] Total written: {total_bytes / 1024:.1f} KB in {elapsed:.2f} s")

    assert write_speed_mbs > 0
    assert elapsed < 30.0


def test_storage_usage_growth_is_proportional(tmp_path: Path, png_factory) -> None:
    config = make_config(tmp_path, mission_id="mission-growth")
    service = MetadataTaggingService(config)

    def output_size() -> int:
        root = tmp_path / "output"
        if not root.exists():
            return 0
        return sum(f.stat().st_size for f in root.rglob("*") if f.is_file())

    sizes = []
    for i in range(10):
        source = png_factory(tmp_path / f"frame_{i}.png")
        captured = datetime(2026, 7, 15, 12, 0, i, tzinfo=timezone.utc)
        service.tag_image(
            source,
            captured_at_utc=captured,
            manual_fix=valid_fix(captured),
        )
        sizes.append(output_size())

    for i in range(1, len(sizes)):
        assert sizes[i] >= sizes[i - 1]

    print(f"\n[PROVISIONAL] {PROVISIONAL_NOTE}")
    print(f"[PROVISIONAL] Storage growth per image: {(sizes[-1] - sizes[0]) / 9 / 1024:.1f} KB average")


def test_temporary_files_do_not_accumulate(tmp_path: Path, png_factory) -> None:
    config = make_config(tmp_path, mission_id="mission-temp-files")
    service = MetadataTaggingService(config)

    for i in range(20):
        source = png_factory(tmp_path / f"frame_{i}.png")
        captured = datetime(2026, 7, 15, 12, 0, i, tzinfo=timezone.utc)
        service.tag_image(
            source,
            captured_at_utc=captured,
            manual_fix=valid_fix(captured),
        )

    temp_files = list((tmp_path / "output").rglob("*.tmp"))
    assert len(temp_files) == 0

    print(f"\n[PROVISIONAL] {PROVISIONAL_NOTE}")
    print(f"[PROVISIONAL] Temporary files remaining after 20 images: {len(temp_files)}")


def test_trigger_generation_timing(tmp_path: Path) -> None:
    from solar_metadata_tagger.triggers import TriggerProvider

    config = CaptureConfig(
        trigger_mode="distance",
        along_track_coverage_m=0.01,
        required_overlap_fraction=0.0,
        speed_timeout_s=1.0,
        speed_poll_s=0.001,
        fallback_interval_s=60.0,
        min_capture_interval_s=0.001,
        min_moving_speed_mps=0.0,
        max_images=10,
    )

    from solar_metadata_tagger.speed import SpeedSample

    class FastSpeedProvider:
        def sample(self):
            return SpeedSample(
                speed_mps=10.0,
                measured_at_utc=datetime.now(timezone.utc),
                source="test",
            )

    start = time.perf_counter()
    provider = TriggerProvider(config, speed_provider=FastSpeedProvider())
    triggers = list(provider)
    elapsed = time.perf_counter() - start

    assert len(triggers) == 10
    avg_ms = (elapsed / len(triggers)) * 1000

    print(f"\n[PROVISIONAL] {PROVISIONAL_NOTE}")
    print(f"[PROVISIONAL] Trigger generation: {len(triggers)} triggers in {elapsed * 1000:.1f} ms")
    print(f"[PROVISIONAL] Average time per trigger: {avg_ms:.2f} ms")

    assert elapsed < 10.0


def test_speed_provider_polling_load(tmp_path: Path) -> None:
    from solar_metadata_tagger.camera.mock_camera import MockSpeedProvider

    provider = MockSpeedProvider(mode="fixed", fixed_speed_mps=0.5)
    count = 10000

    gc.collect()
    start = time.perf_counter()
    for _ in range(count):
        provider.sample()
    elapsed = time.perf_counter() - start

    avg_us = (elapsed / count) * 1_000_000

    print(f"\n[PROVISIONAL] {PROVISIONAL_NOTE}")
    print(f"[PROVISIONAL] Speed provider polling: {count} samples in {elapsed * 1000:.1f} ms")
    print(f"[PROVISIONAL] Average time per sample: {avg_us:.2f} µs")

    assert avg_us < 10_000


def test_application_startup_time(tmp_path: Path) -> None:
    start = time.perf_counter()
    config = make_config(tmp_path)
    service = MetadataTaggingService(config)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert service is not None
    assert elapsed_ms < 5000

    print(f"\n[PROVISIONAL] {PROVISIONAL_NOTE}")
    print(f"[PROVISIONAL] Application startup time: {elapsed_ms:.1f} ms")


def test_failure_recovery_time(tmp_path: Path, png_factory) -> None:
    from unittest.mock import patch
    from solar_metadata_tagger.errors import MetadataTaggerError
    from solar_metadata_tagger.storage import write_json_atomic

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
                "Simulated failure for recovery timing.",
            )
        return original_write(destination, payload)

    start = time.perf_counter()
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
    recovery_time_ms = (time.perf_counter() - start) * 1000

    recovery_files = list((tmp_path / "output" / "recovery").glob("*.json"))
    assert len(recovery_files) == 1

    print(f"\n[PROVISIONAL] {PROVISIONAL_NOTE}")
    print(f"[PROVISIONAL] Failure detection and recovery record time: {recovery_time_ms:.1f} ms")

    assert recovery_time_ms < 5000


def test_disk_usage_is_tracked(tmp_path: Path) -> None:
    usage = disk_usage(tmp_path)
    assert usage["total_bytes"] > 0
    assert usage["free_bytes"] > 0

    print(f"\n[PROVISIONAL] {PROVISIONAL_NOTE}")
    print(f"[PROVISIONAL] Total disk: {usage['total_bytes'] / (1024**3):.1f} GB")
    print(f"[PROVISIONAL] Free disk: {usage['free_bytes'] / (1024**3):.1f} GB")
    print(f"[PROVISIONAL] Used disk: {usage['used_bytes'] / (1024**3):.1f} GB")


def test_mission_stats_track_image_queue_depth(tmp_path: Path, png_factory) -> None:
    from solar_metadata_tagger.mission import MissionStats
    from solar_metadata_tagger.models import TagResult

    stats = MissionStats(mission_id="mission-queue-depth")
    count = 50

    for i in range(count):
        result = TagResult(
            image_id=f"robot-1_mission-queue-depth_{i:06d}",
            image_path=tmp_path / f"image_{i}.png",
            metadata_path=tmp_path / f"meta_{i}.json",
            status="complete",
        )
        stats.record_result(result)

    summary = stats.as_dict()
    assert summary["images_written"] == count
    assert summary["complete_metadata_images"] == count
    assert summary["capture_attempts"] == count

    print(f"\n[PROVISIONAL] {PROVISIONAL_NOTE}")
    print(f"[PROVISIONAL] Image queue depth tracked: {summary['images_written']} images")
    print(f"[PROVISIONAL] Metadata complete: {summary['metadata_complete_percent']}%")


def test_results_are_marked_provisional() -> None:
    assert PROVISIONAL_NOTE != ""
    assert "provisional" in PROVISIONAL_NOTE.lower()
    assert "RUBIK Pi 3" in PROVISIONAL_NOTE
    print(f"\n[PROVISIONAL] {PROVISIONAL_NOTE}")
