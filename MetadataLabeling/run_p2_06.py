from __future__ import annotations

import argparse
import hashlib
import json
import logging
import shutil
import subprocess
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image

from solar_metadata_tagger.config import (
    CameraConfig,
    CaptureConfig,
    GnssConfig,
    StorageConfig,
    TaggerConfig,
)
from solar_metadata_tagger.logging_utils import configure_logging
from solar_metadata_tagger.runner import CaptureService
from solar_metadata_tagger.speed import SpeedSample


SUPPORTED_SUFFIXES = {
    ".jpg",
    ".jpeg",
    ".png",
    ".tif",
    ".tiff",
    ".bmp",
}


class ConstantSpeedProvider:
    """Provide a fresh constant speed for distance testing."""

    def __init__(self, speed_mps: float) -> None:
        self.speed_mps = speed_mps

    def sample(self) -> SpeedSample:
        return SpeedSample(
            speed_mps=self.speed_mps,
            measured_at_utc=datetime.now(timezone.utc),
            source="p2-06-constant-speed",
        )


def calculate_sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for block in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def close_validation_log_handlers() -> None:
    root_logger = logging.getLogger()

    for handler in list(root_logger.handlers):
        if (
            getattr(handler, "_solar_file", None)
            or getattr(
                handler,
                "_solar_console",
                False,
            )
        ):
            root_logger.removeHandler(handler)
            handler.close()


def get_dataset_commit(
    dataset_repo: Path,
) -> str | None:
    try:
        return subprocess.check_output(
            [
                "git",
                "-C",
                str(dataset_repo),
                "rev-parse",
                "HEAD",
            ],
            text=True,
        ).strip()
    except (
        OSError,
        subprocess.CalledProcessError,
    ):
        return None


def create_config(
    *,
    mission_id: str,
    storage_root: Path,
    image_directory: Path,
    capture: CaptureConfig,
) -> TaggerConfig:
    return TaggerConfig(
        robot_id="sunnybot-01",
        mission_id=mission_id,
        storage=StorageConfig(
            root=storage_root,
            spool_dir=storage_root / "spool",
            quarantine_on_missing_required=True,
            compute_sha256=True,
            validate_images=True,
            preserve_source=True,
            min_free_gb=2.0,
            emergency_free_gb=1.0,
        ),
        camera=CameraConfig(
            source="directory",
            model=(
                "Sunnybotics representative "
                "solar-panel dataset"
            ),
            source_directory=image_directory,
            directory_loop=True,
            output_format="jpg",
        ),
        capture=capture,
        gnss=GnssConfig(
            enabled=False,
        ),
        required_fields=(),
        log_level="INFO",
    )


def validate_scenario(
    *,
    root: Path,
    mission_id: str,
    expected_images: int,
    expected_modes: Counter[str | None],
) -> dict[str, Any]:
    errors: list[str] = []

    report_path = (
        root
        / "reports"
        / f"{mission_id}-summary.json"
    )

    manifest_path = (
        root
        / "manifests"
        / f"{mission_id}.jsonl"
    )

    if not report_path.is_file():
        raise RuntimeError(
            "Mission report was not created: "
            f"{report_path}"
        )

    if not manifest_path.is_file():
        raise RuntimeError(
            "Mission manifest was not created: "
            f"{manifest_path}"
        )

    mission_report = json.loads(
        report_path.read_text(
            encoding="utf-8"
        )
    )

    manifest_entries = [
        json.loads(line)
        for line in manifest_path.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]

    image_files = sorted(
        path
        for path in (
            root / "images"
        ).rglob("*")
        if path.is_file()
    )

    metadata_files = sorted(
        (
            root / "metadata"
        ).rglob("*.json")
    )

    if (
        mission_report["capture_attempts"]
        != expected_images
    ):
        errors.append(
            "Unexpected capture-attempt count: "
            f"{mission_report['capture_attempts']}"
        )

    if (
        mission_report["images_written"]
        != expected_images
    ):
        errors.append(
            "Unexpected images-written count: "
            f"{mission_report['images_written']}"
        )

    if (
        mission_report[
            "complete_metadata_images"
        ]
        != expected_images
    ):
        errors.append(
            "Not all images produced complete "
            "records: "
            f"{mission_report['complete_metadata_images']}"
        )

    if (
        mission_report["capture_failures"]
        != 0
    ):
        errors.append(
            "Capture failures occurred: "
            f"{mission_report['capture_failures']}"
        )

    if (
        mission_report["tagging_failures"]
        != 0
    ):
        errors.append(
            "Tagging failures occurred: "
            f"{mission_report['tagging_failures']}"
        )

    if (
        len(manifest_entries)
        != expected_images
    ):
        errors.append(
            "Manifest count does not match "
            "expected count: "
            f"{len(manifest_entries)}"
        )

    if len(image_files) != expected_images:
        errors.append(
            "Output-image count does not match "
            "expected count: "
            f"{len(image_files)}"
        )

    if (
        len(metadata_files)
        != expected_images
    ):
        errors.append(
            "Metadata-file count does not match "
            "expected count: "
            f"{len(metadata_files)}"
        )

    image_ids = [
        entry["image_id"]
        for entry in manifest_entries
    ]

    if (
        len(set(image_ids))
        != expected_images
    ):
        errors.append(
            "One or more image IDs are duplicated."
        )

    metadata_by_id: dict[str, Path] = {}

    for metadata_path in metadata_files:
        payload = json.loads(
            metadata_path.read_text(
                encoding="utf-8"
            )
        )

        metadata_by_id[
            payload["image_id"]
        ] = metadata_path

    observed_modes: Counter[
        str | None
    ] = Counter()

    source_paths: Counter[str] = Counter()
    tagging_times: list[float] = []

    for entry in manifest_entries:
        image_id = entry["image_id"]

        if (
            entry["robot_id"]
            != "sunnybot-01"
        ):
            errors.append(
                f"{image_id}: incorrect robot ID"
            )

        if (
            entry["mission_id"]
            != mission_id
        ):
            errors.append(
                f"{image_id}: incorrect mission ID"
            )

        if image_id not in metadata_by_id:
            errors.append(
                f"{image_id}: metadata sidecar "
                "is missing"
            )

        relative_image_path = Path(
            entry["image"][
                "relative_path"
            ]
        )

        output_image = (
            root
            / relative_image_path
        )

        if not output_image.is_file():
            errors.append(
                f"{image_id}: output image "
                "is missing"
            )
            continue

        try:
            with Image.open(
                output_image
            ) as image:
                image.verify()

        except Exception as exc:
            errors.append(
                f"{image_id}: image validation "
                f"failed: {exc}"
            )
            continue

        expected_checksum = (
            entry["image"]["sha256"]
        )

        actual_checksum = (
            calculate_sha256(
                output_image
            )
        )

        if (
            actual_checksum
            != expected_checksum
        ):
            errors.append(
                f"{image_id}: checksum mismatch"
            )

        source_path = entry.get(
            "camera",
            {},
        ).get(
            "source_path"
        )

        if source_path:
            source_paths[
                str(source_path)
            ] += 1

        capture_mode = entry.get(
            "trigger",
            {},
        ).get(
            "capture_mode"
        )

        observed_modes[
            capture_mode
        ] += 1

        tagging_duration = entry.get(
            "timing",
            {},
        ).get(
            "tagging_duration_ms"
        )

        if isinstance(
            tagging_duration,
            (int, float),
        ):
            tagging_times.append(
                float(tagging_duration)
            )

    if observed_modes != expected_modes:
        errors.append(
            "Capture-mode counts are incorrect. "
            f"Expected {dict(expected_modes)}, "
            f"observed {dict(observed_modes)}"
        )

    summary = {
        "mission_id": mission_id,
        "expected_images": expected_images,
        "manifest_records": (
            len(manifest_entries)
        ),
        "output_images": len(image_files),
        "metadata_files": (
            len(metadata_files)
        ),
        "unique_image_ids": (
            len(set(image_ids))
        ),
        "unique_source_images_used": (
            len(source_paths)
        ),
        "maximum_source_reuse_count": (
            max(source_paths.values())
            if source_paths
            else 0
        ),
        "capture_modes": {
            str(key): value
            for key, value
            in observed_modes.items()
        },
        "mean_tagging_duration_ms": (
            round(
                sum(tagging_times)
                / len(tagging_times),
                3,
            )
            if tagging_times
            else None
        ),
        "maximum_tagging_duration_ms": (
            round(
                max(tagging_times),
                3,
            )
            if tagging_times
            else None
        ),
        "capture_failures": (
            mission_report[
                "capture_failures"
            ]
        ),
        "tagging_failures": (
            mission_report[
                "tagging_failures"
            ]
        ),
        "errors": errors,
        "passed": not errors,
    }

    verification_path = (
        root
        / "reports"
        / (
            f"{mission_id}"
            "-verification.json"
        )
    )

    verification_path.write_text(
        json.dumps(
            summary,
            indent=2,
        ),
        encoding="utf-8",
    )

    return summary


def run_scenario(
    *,
    evidence_root: Path,
    image_directory: Path,
    name: str,
    image_count: int,
    capture: CaptureConfig,
    speed_provider: (
        ConstantSpeedProvider
        | None
    ),
    expected_modes: (
        Counter[str | None]
    ),
) -> dict[str, Any]:
    mission_id = f"p2-06-{name}"

    scenario_root = (
        evidence_root
        / name
    )

    if scenario_root.exists():
        shutil.rmtree(
            scenario_root
        )

    scenario_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    config = create_config(
        mission_id=mission_id,
        storage_root=scenario_root,
        image_directory=image_directory,
        capture=capture,
    )

    close_validation_log_handlers()

    configure_logging(
        scenario_root / "logs",
        "INFO",
        console=False,
    )

    print(
        f"Running {name}: "
        f"{image_count} images..."
    )

    started = time.perf_counter()

    try:
        return_code = CaptureService(
            config,
            speed_provider=speed_provider,
        ).run()

    finally:
        elapsed_seconds = (
            time.perf_counter()
            - started
        )

        close_validation_log_handlers()

    if return_code != 0:
        raise RuntimeError(
            f"{name} returned exit code "
            f"{return_code}"
        )

    result = validate_scenario(
        root=scenario_root,
        mission_id=mission_id,
        expected_images=image_count,
        expected_modes=expected_modes,
    )

    result["elapsed_seconds"] = round(
        elapsed_seconds,
        3,
    )

    result[
        "average_total_seconds_per_image"
    ] = round(
        elapsed_seconds / image_count,
        6,
    )

    result_path = (
        scenario_root
        / "reports"
        / (
            f"{mission_id}"
            "-verification.json"
        )
    )

    result_path.write_text(
        json.dumps(
            result,
            indent=2,
        ),
        encoding="utf-8",
    )

    if not result["passed"]:
        raise RuntimeError(
            f"{name} validation failed. "
            f"See {result_path}"
        )

    print(
        f"{name}: PASS "
        f"({image_count} images)"
    )

    return result


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--dataset-repo",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=Path(
            "../ValidationEvidence/P2-06"
        ),
    )

    args = parser.parse_args()

    dataset_repo = (
        args.dataset_repo
        .expanduser()
        .resolve()
    )

    image_directory = (
        dataset_repo
        / "sample_images"
    )

    evidence_root = (
        args.evidence_root
        .expanduser()
        .resolve()
    )

    if not image_directory.is_dir():
        raise FileNotFoundError(
            "The dataset sample_images "
            "directory was not found: "
            f"{image_directory}"
        )

    source_images = sorted(
        path
        for path in image_directory.rglob("*")
        if (
            path.is_file()
            and path.suffix.lower()
            in SUPPORTED_SUFFIXES
        )
    )

    if not source_images:
        raise RuntimeError(
            "No supported source images "
            "were found."
        )

    evidence_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataset_summary = {
        "repository": (
            "roboticsSunnyApp/"
            "sunnybotics-solar-panel-challenge"
        ),
        "repository_path": str(
            dataset_repo
        ),
        "commit": get_dataset_commit(
            dataset_repo
        ),
        "supported_source_images": (
            len(source_images)
        ),
        "total_supported_source_bytes": sum(
            path.stat().st_size
            for path in source_images
        ),
        "suffix_counts": dict(
            Counter(
                path.suffix.lower()
                for path in source_images
            )
        ),
        "category_counts": {
            "clean": sum(
                "clean" in path.parts
                for path in source_images
            ),
            "damaged": sum(
                "damaged" in path.parts
                for path in source_images
            ),
        },
    }

    (
        evidence_root
        / "dataset-summary.json"
    ).write_text(
        json.dumps(
            dataset_summary,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        "Supported source images found:",
        len(source_images),
    )

    interval_result = run_scenario(
        evidence_root=evidence_root,
        image_directory=image_directory,
        name="interval",
        image_count=500,
        capture=CaptureConfig(
            trigger_mode="interval",
            interval_s=1.0,
            max_images=500,
            continue_on_error=False,
            health_interval_s=5.0,
        ),
        speed_provider=None,
        expected_modes=Counter(
            {
                None: 500,
            }
        ),
    )

    adaptive_result = run_scenario(
        evidence_root=evidence_root,
        image_directory=image_directory,
        name="adaptive-distance",
        image_count=400,
        capture=CaptureConfig(
            trigger_mode="distance",
            max_images=400,
            continue_on_error=False,
            health_interval_s=5.0,
            along_track_coverage_m=1.62,
            required_overlap_fraction=0.30,
            speed_timeout_s=2.5,
            speed_poll_s=0.05,
            fallback_interval_s=5.0,
            min_capture_interval_s=1.0,
            min_moving_speed_mps=0.02,
        ),
        speed_provider=(
            ConstantSpeedProvider(
                speed_mps=1.134,
            )
        ),
        expected_modes=Counter(
            {
                "distance-initial": 1,
                "distance": 399,
            }
        ),
    )

    fallback_result = run_scenario(
        evidence_root=evidence_root,
        image_directory=image_directory,
        name="fixed-rate-fallback",
        image_count=100,
        capture=CaptureConfig(
            trigger_mode="distance",
            max_images=100,
            continue_on_error=False,
            health_interval_s=5.0,
            along_track_coverage_m=1.62,
            required_overlap_fraction=0.30,
            speed_timeout_s=2.5,
            speed_poll_s=0.05,
            fallback_interval_s=5.0,
            min_capture_interval_s=1.0,
            min_moving_speed_mps=0.02,
        ),
        speed_provider=None,
        expected_modes=Counter(
            {
                "distance-initial": 1,
                "fixed-rate-fallback": 99,
            }
        ),
    )

    combined = {
        "validation": "P2-06",
        "total_expected_images": 1000,
        "total_output_images": sum(
            result["output_images"]
            for result in (
                interval_result,
                adaptive_result,
                fallback_result,
            )
        ),
        "total_metadata_files": sum(
            result["metadata_files"]
            for result in (
                interval_result,
                adaptive_result,
                fallback_result,
            )
        ),
        "total_unique_image_ids": sum(
            result["unique_image_ids"]
            for result in (
                interval_result,
                adaptive_result,
                fallback_result,
            )
        ),
        "scenarios": {
            "interval": interval_result,
            "adaptive-distance": (
                adaptive_result
            ),
            "fixed-rate-fallback": (
                fallback_result
            ),
        },
    }

    combined["passed"] = (
        combined[
            "total_output_images"
        ]
        == 1000
        and combined[
            "total_metadata_files"
        ]
        == 1000
        and combined[
            "total_unique_image_ids"
        ]
        == 1000
        and all(
            result["passed"]
            for result in combined[
                "scenarios"
            ].values()
        )
    )

    combined_path = (
        evidence_root
        / "P2-06-final-report.json"
    )

    combined_path.write_text(
        json.dumps(
            combined,
            indent=2,
        ),
        encoding="utf-8",
    )

    if not combined["passed"]:
        raise RuntimeError(
            "P2-06 failed. See "
            f"{combined_path}"
        )

    print()
    print("P2-06: PASS")
    print(
        "1,000 images processed "
        "successfully."
    )
    print(
        f"Evidence: {evidence_root}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())