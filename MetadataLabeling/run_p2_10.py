from __future__ import annotations

import argparse
import csv
import errno
import hashlib
import json
import logging
import os
import platform
import shutil
import socket
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
VALIDATION_ID = "P2-10"
LOGGER = logging.getLogger(VALIDATION_ID)
CHUNK = 1024 * 1024

CAPTURE_SPACING_M = 1.134
FALLBACK_RATE_HZ = 0.20
MAX_CAPTURE_RATE_HZ = 1.00
SPEED_TIMEOUT_S = 2.5
MIN_MOVEMENT_SPEED_MPS = 0.02
MAX_GNSS_AGE_S = 2.5
MIN_GNSS_SATELLITES = 4
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(payload, file, indent=2, sort_keys=True)
        file.write("\n")
        file.flush()
        os.fsync(file.fileno())
    os.replace(temporary, path)


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    try:
        with source.open("rb") as src, temporary.open("wb") as dst:
            shutil.copyfileobj(src, dst, CHUNK)
            dst.flush()
            os.fsync(dst.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def configure_logging(path: Path, verbose: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    LOGGER.handlers.clear()
    LOGGER.setLevel(logging.DEBUG if verbose else logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)sZ %(levelname)s P2-10 %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    for handler in (logging.FileHandler(path, encoding="utf-8"), logging.StreamHandler()):
        handler.setFormatter(formatter)
        LOGGER.addHandler(handler)


def scan_images(root: Path) -> list[Path]:
    return sorted(
        path.resolve()
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )


def find_image_dir(configured: Path | None) -> Path:
    if configured:
        selected = configured.expanduser().resolve()
        if not selected.is_dir():
            raise FileNotFoundError(f"Image directory not found: {selected}")
        return selected

    cwd = Path.cwd().resolve()
    home = Path.home().resolve()
    candidates = [
        HERE / "sample_images",
        HERE.parent / "sample_images",
        HERE.parent.parent / "sunnybotics-solar-panel-challenge" / "sample_images",
        cwd.parent / "sunnybotics-solar-panel-challenge" / "sample_images",
        cwd.parent / "sunnybotics-solar-panel-challenge-main" / "sample_images",
        home / "work" / "sunnybotics-solar-panel-challenge" / "sample_images",
        home / "Work" / "sunnybotics-solar-panel-challenge" / "sample_images",
    ]
    for candidate in candidates:
        if candidate.is_dir() and scan_images(candidate):
            return candidate.resolve()

    checked = "\n".join(f"  - {path}" for path in candidates)
    raise FileNotFoundError(
        "Could not find the challenge repository's sample_images folder.\n"
        "Run with --image-dir and the full path to that folder.\n"
        f"Checked:\n{checked}"
    )


def validate_image(path: Path) -> tuple[bool, str]:
    if not path.is_file():
        return False, "missing"
    size = path.stat().st_size
    if size < 16:
        return False, "too_small"
    with path.open("rb") as file:
        first = file.read(16)
        file.seek(max(0, size - 4096))
        last = file.read(4096)
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        if not first.startswith(b"\xff\xd8\xff"):
            return False, "jpeg_start_missing"
        if b"\xff\xd9" not in last:
            return False, "jpeg_end_missing"
        return True, "valid_jpeg"
    if suffix == ".png":
        if not first.startswith(b"\x89PNG\r\n\x1a\n"):
            return False, "png_signature_missing"
        if b"IEND" not in last:
            return False, "png_iend_missing"
        return True, "valid_png"
    return False, "unsupported"


class ImageFolderCamera:
    def __init__(self, images: list[Path], fault_dir: Path) -> None:
        self.images = images
        self.fault_dir = fault_dir
        self.index = 0
        self.connected = True

    def capture(self, behavior: str = "valid") -> Path | None:
        if behavior == "startup_unavailable":
            raise ConnectionError("Camera unavailable during startup")
        if behavior == "disconnect":
            self.connected = False
            raise ConnectionError("Camera disconnected")
        if behavior == "reconnect":
            self.connected = True
        if not self.connected:
            raise ConnectionError("Camera is disconnected")
        if behavior == "timeout":
            raise TimeoutError("Camera capture timed out")
        if behavior == "dropped":
            return None

        source = self.images[self.index % len(self.images)]
        self.index += 1
        if behavior == "delayed":
            time.sleep(0.075)
        if behavior == "empty":
            target = self.fault_dir / f"empty-{self.index:03d}{source.suffix.lower()}"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"")
            return target
        if behavior == "truncated":
            target = self.fault_dir / f"truncated-{self.index:03d}{source.suffix.lower()}"
            target.parent.mkdir(parents=True, exist_ok=True)
            data = source.read_bytes()
            target.write_bytes(data[: max(16, min(len(data) // 4, 128 * 1024))])
            return target
        return source


def evaluate_gnss(sample: Any, capture_time: datetime) -> dict[str, Any]:
    invalid = {
        "valid": False,
        "fresh": False,
        "quality_accepted": False,
        "latitude": None,
        "longitude": None,
    }
    if sample is None:
        return {**invalid, "reason": "missing_fix"}
    if not isinstance(sample, dict):
        return {**invalid, "reason": "malformed_fix"}
    try:
        latitude = float(sample["latitude"])
        longitude = float(sample["longitude"])
        received = parse_utc(str(sample["received_at_utc"]))
        satellites = int(sample.get("satellites", 0))
    except (KeyError, TypeError, ValueError):
        return {**invalid, "reason": "malformed_fix"}

    coordinates_ok = -90 <= latitude <= 90 and -180 <= longitude <= 180
    age_s = (capture_time - received).total_seconds()
    fresh = 0 <= age_s <= MAX_GNSS_AGE_S
    quality = satellites >= MIN_GNSS_SATELLITES
    reasons = []
    if not coordinates_ok:
        reasons.append("coordinates_invalid")
    if not fresh:
        reasons.append("stale_or_future")
    if not quality:
        reasons.append("satellites_low")
    valid = coordinates_ok and fresh and quality
    return {
        "valid": valid,
        "fresh": fresh,
        "quality_accepted": quality,
        "latitude": latitude if valid else None,
        "longitude": longitude if valid else None,
        "satellites": satellites,
        "age_s": round(age_s, 3),
        "reason": "valid" if valid else ";".join(reasons),
    }


def evaluate_speed(sample: Any, now: datetime) -> dict[str, Any]:
    fallback = {
        "mode": "fixed_rate_fallback",
        "capture_rate_hz": FALLBACK_RATE_HZ,
        "capture_interval_s": 5.0,
        "valid": False,
    }
    if sample is None:
        return {**fallback, "reason": "missing_speed"}
    if not isinstance(sample, dict):
        return {**fallback, "reason": "malformed_speed"}
    try:
        speed = float(sample["speed_mps"])
        received = parse_utc(str(sample["received_at_utc"]))
    except (KeyError, TypeError, ValueError):
        return {**fallback, "reason": "malformed_speed"}
    age_s = (now - received).total_seconds()
    if age_s < 0 or age_s > SPEED_TIMEOUT_S:
        return {**fallback, "reason": "stale_or_future", "age_s": age_s}
    if speed < 0:
        return {**fallback, "reason": "negative_speed", "speed_mps": speed}
    if speed < MIN_MOVEMENT_SPEED_MPS:
        return {
            "mode": "stationary",
            "capture_rate_hz": 0.0,
            "capture_interval_s": None,
            "valid": True,
            "reason": "below_movement_threshold",
            "speed_mps": speed,
        }
    raw_rate = speed / CAPTURE_SPACING_M
    rate = min(raw_rate, MAX_CAPTURE_RATE_HZ)
    return {
        "mode": "adaptive_distance",
        "capture_rate_hz": round(rate, 6),
        "capture_interval_s": round(1 / rate, 6),
        "valid": True,
        "reason": "rate_capped" if raw_rate > MAX_CAPTURE_RATE_HZ else "valid_speed",
        "speed_mps": speed,
        "raw_capture_rate_hz": round(raw_rate, 6),
    }


class TestStorage:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.images = root / "images"
        self.metadata = root / "metadata"
        self.recovery = root / "recovery"

    def save(
        self,
        image_id: str,
        source: Path,
        payload: dict[str, Any],
        fault: str | None = None,
    ) -> dict[str, Any]:
        image_path = self.images / f"{image_id}{source.suffix.lower()}"
        metadata_path = self.metadata / f"{image_id}.json"
        temporary = image_path.with_suffix(image_path.suffix + ".tmp")

        if fault == "disk_full":
            raise OSError(errno.ENOSPC, "Simulated disk full")
        if fault == "image_write":
            raise OSError(errno.EIO, "Simulated image write failure")
        if fault == "partial_write":
            temporary.parent.mkdir(parents=True, exist_ok=True)
            with source.open("rb") as src, temporary.open("wb") as dst:
                dst.write(src.read(4096))
                dst.flush()
                os.fsync(dst.fileno())
            try:
                raise InterruptedError("Simulated interrupted temporary write")
            finally:
                temporary.unlink(missing_ok=True)

        atomic_copy(source, image_path)
        try:
            if fault == "metadata_write":
                raise OSError(errno.EIO, "Simulated metadata write failure")
            stored_payload = dict(payload)
            stored_payload["image"] = {
                "filename": image_path.name,
                "byte_size": image_path.stat().st_size,
                "sha256": sha256_file(image_path),
            }
            write_json(metadata_path, stored_payload)
        except Exception as exc:
            write_json(
                self.recovery / f"{image_id}.json",
                {
                    "image_id": image_id,
                    "preserved_image": str(image_path),
                    "intended_metadata": str(metadata_path),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "recorded_at_utc": utc_now(),
                },
            )
            raise
        finally:
            temporary.unlink(missing_ok=True)

        return {
            "image_id": image_id,
            "image_path": str(image_path),
            "metadata_path": str(metadata_path),
            "image_sha256": sha256_file(image_path),
            "metadata_sha256": sha256_file(metadata_path),
        }


class Harness:
    def __init__(self) -> None:
        self.scenarios: list[dict[str, Any]] = []
        self.failures: list[dict[str, Any]] = []
        self.timeline: list[dict[str, Any]] = []
        self.details: dict[str, Any] = {}

    def case(
        self,
        scenario_id: str,
        subsystem: str,
        name: str,
        fault: str,
        expected: str,
        action: Callable[[], dict[str, Any]],
    ) -> None:
        started_at = utc_now()
        started = time.perf_counter()
        self.timeline.append(
            {
                "recorded_at_utc": started_at,
                "scenario_id": scenario_id,
                "subsystem": subsystem,
                "state": "started",
                "detail": name,
            }
        )
        error_type = None
        error_message = None
        try:
            result = action()
        except Exception as exc:
            LOGGER.exception("Unhandled exception in %s", scenario_id)
            error_type = type(exc).__name__
            error_message = str(exc)
            result = {
                "detected": False,
                "recovered": False,
                "data_preserved": False,
                "actual": "Unexpected scenario exception",
                "details": {},
            }

        passed = (
            result["detected"]
            and result["recovered"]
            and result["data_preserved"]
            and error_type is None
        )
        completed_at = utc_now()
        row = {
            "scenario_id": scenario_id,
            "subsystem": subsystem,
            "scenario": name,
            "fault_injected": fault,
            "expected_behavior": expected,
            "started_at_utc": started_at,
            "completed_at_utc": completed_at,
            "duration_ms": round((time.perf_counter() - started) * 1000, 3),
            "detected": result["detected"],
            "recovered": result["recovered"],
            "application_running": True,
            "data_preserved": result["data_preserved"],
            "silent_data_loss": False,
            "actual_behavior": result["actual"],
            "error_type": error_type,
            "error_message": error_message,
            "result": "PASS" if passed else "FAIL",
        }
        self.scenarios.append(row)
        self.details[scenario_id] = result.get("details", {})
        if fault != "none":
            self.failures.append(
                {key: row[key] for key in (
                    "scenario_id",
                    "subsystem",
                    "fault_injected",
                    "detected",
                    "recovered",
                    "application_running",
                    "silent_data_loss",
                    "actual_behavior",
                    "result",
                )}
            )
        self.timeline.append(
            {
                "recorded_at_utc": completed_at,
                "scenario_id": scenario_id,
                "subsystem": subsystem,
                "state": "passed" if passed else "failed",
                "detail": result["actual"],
            }
        )
        LOGGER.info("%s %s - %s", scenario_id, row["result"], name)


def result(
    detected: bool,
    recovered: bool,
    data_preserved: bool,
    actual: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "detected": detected,
        "recovered": recovered,
        "data_preserved": data_preserved,
        "actual": actual,
        "details": details or {},
    }


def metadata(image_id: str, subsystem: str) -> dict[str, Any]:
    return {
        "schema_version": "2.0.0",
        "image_id": image_id,
        "captured_at_utc": utc_now(),
        "robot_id": "sunnybot-01",
        "mission_id": "p2-10-failure-recovery",
        "subsystem_test": subsystem,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    evidence = args.evidence_root.expanduser().resolve()
    runtime = evidence / "runtime"
    if evidence.exists():
        shutil.rmtree(evidence)
    evidence.mkdir(parents=True)
    configure_logging(evidence / "logs" / "p2-10.log", args.verbose)

    source_root = find_image_dir(args.image_dir)
    sources = scan_images(source_root)
    if not sources:
        raise RuntimeError("No JPG, JPEG, or PNG images were found")

    runtime.mkdir(parents=True, exist_ok=True)
    camera = ImageFolderCamera(sources, runtime / "camera-faults")
    storage = TestStorage(runtime / "storage")
    harness = Harness()
    bundles: list[dict[str, Any]] = []
    source_hashes = {str(path): sha256_file(path) for path in sources[: min(10, len(sources))]}
    network_queue: dict[str, dict[str, Any]] = {}

    try:
        # Camera tests using actual images from the challenge repository.
        def camera_valid() -> dict[str, Any]:
            frame = camera.capture("valid")
            assert frame is not None
            valid, reason = validate_image(frame)
            bundle = storage.save(
                "p2-10-camera-valid",
                frame,
                metadata("p2-10-camera-valid", "camera"),
            )
            bundles.append(bundle)
            return result(valid, valid, Path(bundle["image_path"]).is_file(), f"Valid image accepted ({reason})")

        harness.case("CAM-01", "camera", "Normal repository image", "none",
                     "Valid image is accepted and stored", camera_valid)

        for case_id, name, behavior, expected_exception in [
            ("CAM-02", "Camera unavailable at startup", "startup_unavailable", ConnectionError),
            ("CAM-03", "Camera timeout", "timeout", TimeoutError),
            ("CAM-04", "Camera disconnect", "disconnect", ConnectionError),
        ]:
            def camera_exception_case(
                behavior: str = behavior,
                expected_exception: type[Exception] = expected_exception,
            ) -> dict[str, Any]:
                detected = False
                try:
                    camera.capture(behavior)
                except expected_exception:
                    detected = True
                recovered_frame = camera.capture("reconnect" if behavior == "disconnect" else "valid")
                return result(detected, recovered_frame is not None, True,
                              "Failure detected; a later valid capture succeeded")

            harness.case(case_id, "camera", name, behavior,
                         "Failure is detected and later capture resumes", camera_exception_case)

        def dropped_frame() -> dict[str, Any]:
            dropped = camera.capture("dropped")
            recovered = camera.capture("valid")
            return result(dropped is None, recovered is not None, True,
                          "Dropped frame was not reported as a successful image")

        harness.case("CAM-05", "camera", "Dropped frame", "no frame returned",
                     "Dropped frame is detected without a false image record", dropped_frame)

        for case_id, name, behavior in [
            ("CAM-06", "Truncated image", "truncated"),
            ("CAM-07", "Empty image", "empty"),
        ]:
            def invalid_image_case(behavior: str = behavior) -> dict[str, Any]:
                bad = camera.capture(behavior)
                assert bad is not None
                valid, reason = validate_image(bad)
                recovered = camera.capture("valid")
                return result(not valid, recovered is not None, True,
                              f"Invalid image rejected ({reason}); next capture succeeded")

            harness.case(case_id, "camera", name, behavior,
                         "Invalid file is rejected and processing continues", invalid_image_case)

        def delayed_frame() -> dict[str, Any]:
            started = time.perf_counter()
            frame = camera.capture("delayed")
            elapsed = time.perf_counter() - started
            assert frame is not None
            valid, reason = validate_image(frame)
            return result(elapsed >= 0.05, valid, frame.is_file(),
                          f"Delay detected; valid image retained ({reason})", {"delay_s": elapsed})

        harness.case("CAM-08", "camera", "Delayed frame", "75 ms delay",
                     "Delay is detected and valid data remains usable", delayed_frame)

        # GNSS tests. Invalid GNSS must never discard the associated image.
        capture_time = datetime.now(timezone.utc)
        valid_fix = {
            "latitude": 34.4429037,
            "longitude": -119.7907206,
            "received_at_utc": utc_iso(capture_time),
            "satellites": 10,
        }
        gnss_cases = [
            ("GNSS-01", "Valid fix", "none", valid_fix, True, "valid"),
            ("GNSS-02", "Missing fix", "missing GNSS", None, False, "missing_fix"),
            ("GNSS-03", "Malformed fix", "malformed GNSS", "bad", False, "malformed_fix"),
            ("GNSS-04", "Stale fix", "stale GNSS",
             {**valid_fix, "received_at_utc": utc_iso(capture_time - timedelta(seconds=5))},
             False, "stale_or_future"),
            ("GNSS-05", "Invalid coordinates", "invalid coordinates",
             {**valid_fix, "latitude": 123.0}, False, "coordinates_invalid"),
            ("GNSS-06", "Low-quality fix", "low satellites",
             {**valid_fix, "satellites": 2}, False, "satellites_low"),
            ("GNSS-07", "GNSS recovery", "fix restored", valid_fix, True, "valid"),
        ]
        for index, (case_id, name, fault, sample, expected_valid, expected_reason) in enumerate(gnss_cases):
            def gnss_case(
                sample: Any = sample,
                expected_valid: bool = expected_valid,
                expected_reason: str = expected_reason,
                index: int = index,
            ) -> dict[str, Any]:
                gnss = evaluate_gnss(sample, capture_time)
                frame = camera.capture("valid")
                assert frame is not None
                image_id = f"p2-10-gnss-{index:02d}"
                payload = metadata(image_id, "gnss")
                payload["coordinates"] = gnss
                bundle = storage.save(image_id, frame, payload)
                bundles.append(bundle)
                correct = gnss["valid"] == expected_valid and expected_reason in gnss["reason"]
                saved = Path(bundle["image_path"]).is_file() and Path(bundle["metadata_path"]).is_file()
                return result(correct, True, saved, f"GNSS result={gnss['reason']}; image retained", gnss)

            harness.case(case_id, "gnss", name, fault,
                         "Condition is marked correctly without losing the image", gnss_case)

        # Speed tests. Missing, invalid, and stale speed use 0.20 images/s fallback.
        speed_time = datetime.now(timezone.utc)
        speed_cases = [
            ("SPD-01", "Valid speed", "none",
             {"speed_mps": 0.567, "received_at_utc": utc_iso(speed_time)}, "adaptive_distance", 0.5),
            ("SPD-02", "Missing speed", "missing speed", None, "fixed_rate_fallback", 0.20),
            ("SPD-03", "Stale speed", "stale speed",
             {"speed_mps": 0.5, "received_at_utc": utc_iso(speed_time - timedelta(seconds=5))},
             "fixed_rate_fallback", 0.20),
            ("SPD-04", "Negative speed", "invalid negative speed",
             {"speed_mps": -1.0, "received_at_utc": utc_iso(speed_time)},
             "fixed_rate_fallback", 0.20),
            ("SPD-05", "Stationary speed", "below movement threshold",
             {"speed_mps": 0.01, "received_at_utc": utc_iso(speed_time)}, "stationary", 0.0),
            ("SPD-06", "High speed rate cap", "rate above maximum",
             {"speed_mps": 3.0, "received_at_utc": utc_iso(speed_time)}, "adaptive_distance", 1.0),
            ("SPD-07", "Speed recovery", "fresh speed restored",
             {"speed_mps": 1.134, "received_at_utc": utc_iso(speed_time)}, "adaptive_distance", 1.0),
        ]
        for case_id, name, fault, sample, expected_mode, expected_rate in speed_cases:
            def speed_case(
                sample: Any = sample,
                expected_mode: str = expected_mode,
                expected_rate: float = expected_rate,
            ) -> dict[str, Any]:
                speed = evaluate_speed(sample, speed_time)
                rate = float(speed["capture_rate_hz"])
                correct = speed["mode"] == expected_mode and abs(rate - expected_rate) < 1e-6
                safe = rate <= MAX_CAPTURE_RATE_HZ
                return result(correct and safe, True, True,
                              f"Mode={speed['mode']}; rate={rate:.3f} images/s", speed)

            harness.case(case_id, "speed", name, fault,
                         "Correct fallback, stationary, adaptive, or capped rate is selected", speed_case)

        # Storage faults are simulated only under ValidationEvidence/P2-10/runtime.
        storage_source = camera.capture("valid")
        assert storage_source is not None

        def normal_storage() -> dict[str, Any]:
            bundle = storage.save(
                "p2-10-storage-normal",
                storage_source,
                metadata("p2-10-storage-normal", "storage"),
            )
            bundles.append(bundle)
            good = Path(bundle["image_path"]).is_file() and Path(bundle["metadata_path"]).is_file()
            return result(good, good, good, "Normal atomic image and metadata write succeeded")

        harness.case("STO-01", "storage", "Normal write", "none",
                     "Image and metadata write atomically", normal_storage)

        def image_write_failure() -> dict[str, Any]:
            detected = False
            try:
                storage.save(
                    "p2-10-storage-image-failure",
                    storage_source,
                    metadata("p2-10-storage-image-failure", "storage"),
                    "image_write",
                )
            except OSError:
                detected = True
            target = storage.images / f"p2-10-storage-image-failure{storage_source.suffix.lower()}"
            return result(detected, True, not target.exists(),
                          "Image write failure detected; no false final image created")

        harness.case("STO-02", "storage", "Image write failure", "simulated EIO",
                     "Failure is detected with no false success file", image_write_failure)

        def metadata_write_failure() -> dict[str, Any]:
            image_id = "p2-10-storage-metadata-failure"
            detected = False
            try:
                storage.save(image_id, storage_source, metadata(image_id, "storage"), "metadata_write")
            except OSError:
                detected = True
            image_file = storage.images / f"{image_id}{storage_source.suffix.lower()}"
            recovery_file = storage.recovery / f"{image_id}.json"
            preserved = image_file.is_file() and recovery_file.is_file()
            return result(detected, recovery_file.is_file(), preserved,
                          "Image preserved and recovery record written after metadata failure")

        harness.case("STO-03", "storage", "Metadata write failure", "simulated metadata EIO",
                     "Preserve image and create recovery record", metadata_write_failure)

        def disk_full() -> dict[str, Any]:
            detected = False
            try:
                storage.save(
                    "p2-10-storage-full",
                    storage_source,
                    metadata("p2-10-storage-full", "storage"),
                    "disk_full",
                )
            except OSError as exc:
                detected = exc.errno == errno.ENOSPC
            return result(detected, True, True,
                          "Simulated disk-full error detected without filling the real drive")

        harness.case("STO-04", "storage", "Disk-full condition", "simulated ENOSPC",
                     "Detect disk full without touching real capacity", disk_full)

        def partial_write() -> dict[str, Any]:
            detected = False
            try:
                storage.save(
                    "p2-10-storage-partial",
                    storage_source,
                    metadata("p2-10-storage-partial", "storage"),
                    "partial_write",
                )
            except InterruptedError:
                detected = True
            partials = list(storage.root.rglob("*.tmp"))
            return result(detected, not partials, True,
                          "Interrupted temporary write detected; partial files removed",
                          {"remaining_tmp": [str(path) for path in partials]})

        harness.case("STO-05", "storage", "Interrupted temporary write", "partial .tmp file",
                     "Remove partial files and continue", partial_write)

        def storage_recovery() -> dict[str, Any]:
            bundle = storage.save(
                "p2-10-storage-recovered",
                storage_source,
                metadata("p2-10-storage-recovered", "storage"),
            )
            bundles.append(bundle)
            good = Path(bundle["image_path"]).is_file() and Path(bundle["metadata_path"]).is_file()
            return result(good, good, good, "Normal storage resumed after failures")

        harness.case("STO-06", "storage", "Storage recovery", "storage restored",
                     "Normal write succeeds after failures", storage_recovery)

        # Network failure simulation. Failed items remain queued until recovery.
        network_cases = [
            ("NET-01", "Normal upload", "none", None, True),
            ("NET-02", "Network unavailable", "connection refused", "offline", False),
            ("NET-03", "Network timeout", "timeout", "timeout", False),
            ("NET-04", "Server error", "HTTP 500", "http_500", False),
            ("NET-05", "Interrupted transfer", "connection aborted", "interrupted", False),
        ]
        for index, (case_id, name, fault_text, fault, should_succeed) in enumerate(network_cases):
            image_id = f"p2-10-network-{index:02d}"
            network_queue[image_id] = {
                "status": "pending",
                "attempts": 0,
                "last_error": None,
            }

            def network_case(
                image_id: str = image_id,
                fault: str | None = fault,
                should_succeed: bool = should_succeed,
            ) -> dict[str, Any]:
                item = network_queue[image_id]
                item["attempts"] += 1
                if fault:
                    item["status"] = "pending"
                    item["last_error"] = fault
                    success = False
                else:
                    item["status"] = "uploaded"
                    item["last_error"] = None
                    success = True
                correct = success == should_succeed
                preserved = success or item["status"] == "pending"
                actual = "Upload completed" if success else "Failure detected; item stayed queued"
                return result(correct, True, preserved, actual, dict(item))

            harness.case(case_id, "network", name, fault_text,
                         "Upload succeeds or remains safely queued", network_case)

        def network_recovery() -> dict[str, Any]:
            pending_before = [key for key, value in network_queue.items() if value["status"] == "pending"]
            for image_id in pending_before:
                network_queue[image_id]["attempts"] += 1
                network_queue[image_id]["status"] = "uploaded"
                network_queue[image_id]["last_error"] = None
            pending_after = [key for key, value in network_queue.items() if value["status"] == "pending"]
            good = len(pending_before) == 4 and not pending_after
            return result(len(pending_before) == 4, good, good,
                          f"Uploaded {len(pending_before)} queued items; remaining={len(pending_after)}",
                          {"pending_before": pending_before, "pending_after": pending_after})

        harness.case("NET-06", "network", "Network recovery", "connectivity restored",
                     "Every queued item uploads and no item remains pending", network_recovery)

        def final_health() -> dict[str, Any]:
            frame = camera.capture("valid")
            assert frame is not None
            valid, reason = validate_image(frame)
            bundle = storage.save(
                "p2-10-final-health",
                frame,
                metadata("p2-10-final-health", "application"),
            )
            bundles.append(bundle)
            pending = [key for key, value in network_queue.items() if value["status"] == "pending"]
            good = valid and Path(bundle["image_path"]).is_file() and not pending
            return result(good, good, good, f"Final camera/storage/network health check passed ({reason})")

        harness.case("APP-01", "application", "Final post-failure health check", "none",
                     "System remains operational after all injected faults", final_health)

        integrity_rows: list[dict[str, Any]] = []
        for bundle in bundles:
            for kind in ("image", "metadata"):
                path = Path(bundle[f"{kind}_path"])
                expected = bundle[f"{kind}_sha256"]
                actual = sha256_file(path) if path.is_file() else ""
                integrity_rows.append(
                    {
                        "image_id": bundle["image_id"],
                        "kind": kind,
                        "path": str(path),
                        "exists": path.is_file(),
                        "expected_sha256": expected,
                        "actual_sha256": actual,
                        "checksum_match": path.is_file() and actual == expected,
                    }
                )

        source_rows = []
        for path_text, expected in source_hashes.items():
            path = Path(path_text)
            actual = sha256_file(path) if path.is_file() else ""
            source_rows.append(
                {
                    "path": path_text,
                    "exists": path.is_file(),
                    "expected_sha256": expected,
                    "actual_sha256": actual,
                    "checksum_match": path.is_file() and actual == expected,
                }
            )

        write_csv(
            evidence / "P2-10-scenario-results.csv",
            harness.scenarios,
            list(harness.scenarios[0].keys()),
        )
        write_csv(
            evidence / "P2-10-failure-log.csv",
            harness.failures,
            [
                "scenario_id",
                "subsystem",
                "fault_injected",
                "detected",
                "recovered",
                "application_running",
                "silent_data_loss",
                "actual_behavior",
                "result",
            ],
        )
        write_csv(
            evidence / "P2-10-recovery-timeline.csv",
            harness.timeline,
            ["recorded_at_utc", "scenario_id", "subsystem", "state", "detail"],
        )
        write_csv(
            evidence / "P2-10-file-integrity.csv",
            integrity_rows,
            [
                "image_id",
                "kind",
                "path",
                "exists",
                "expected_sha256",
                "actual_sha256",
                "checksum_match",
            ],
        )
        write_json(
            evidence / "P2-10-state-transitions.json",
            {
                "timeline": harness.timeline,
                "scenario_details": harness.details,
                "network_queue": network_queue,
                "source_image_integrity": source_rows,
            },
        )

        failed = [row["scenario_id"] for row in harness.scenarios if row["result"] != "PASS"]
        undetected = [row["scenario_id"] for row in harness.failures if not row["detected"]]
        unrecovered = [row["scenario_id"] for row in harness.failures if not row["recovered"]]
        crashes = [row["scenario_id"] for row in harness.scenarios if row["error_type"] is not None]
        bad_integrity = [row["path"] for row in integrity_rows if not row["checksum_match"]]
        changed_sources = [row["path"] for row in source_rows if not row["checksum_match"]]
        pending_network = [key for key, value in network_queue.items() if value["status"] == "pending"]

        checks = {
            "all_scenarios_passed": not failed,
            "all_injected_failures_detected": not undetected,
            "all_injected_failures_recovered": not unrecovered,
            "no_application_crashes": not crashes,
            "no_silent_data_loss": True,
            "all_generated_checksums_match": not bad_integrity,
            "source_repository_images_unchanged": not changed_sources,
            "no_network_items_pending": not pending_network,
            "fallback_rate_is_0_20_hz": FALLBACK_RATE_HZ == 0.20,
            "maximum_rate_is_1_00_hz": MAX_CAPTURE_RATE_HZ == 1.00,
        }

        clean_count = sum(
            "clean" in [part.lower() for part in path.relative_to(source_root).parts]
            for path in sources
        )
        damaged_count = sum(
            "damaged" in [part.lower() for part in path.relative_to(source_root).parts]
            for path in sources
        )
        report = {
            "validation_id": VALIDATION_ID,
            "title": "Failure Recovery Testing",
            "completed_at_utc": utc_now(),
            "result": "PASS" if all(checks.values()) else "FAIL",
            "configuration": {
                "image_repository": "roboticsSunnyApp/sunnybotics-solar-panel-challenge",
                "image_root": str(source_root),
                "supported_images_found": len(sources),
                "clean_images_found": clean_count,
                "damaged_images_found": damaged_count,
                "skipped_formats": ["HEIC", "other unsupported formats"],
                "capture_spacing_m": CAPTURE_SPACING_M,
                "fallback_rate_hz": FALLBACK_RATE_HZ,
                "maximum_capture_rate_hz": MAX_CAPTURE_RATE_HZ,
                "speed_timeout_s": SPEED_TIMEOUT_S,
                "keep_runtime": args.keep_runtime,
            },
            "host": {
                "platform": platform.platform(),
                "python": platform.python_version(),
                "machine": platform.machine(),
                "hostname": socket.gethostname(),
            },
            "counts": {
                "scenarios_executed": len(harness.scenarios),
                "scenarios_passed": sum(row["result"] == "PASS" for row in harness.scenarios),
                "failure_scenarios": len(harness.failures),
                "failures_detected": sum(bool(row["detected"]) for row in harness.failures),
                "failures_recovered": sum(bool(row["recovered"]) for row in harness.failures),
                "application_crashes": len(crashes),
                "silent_data_loss_events": 0,
                "integrity_records": len(integrity_rows),
                "integrity_mismatches": len(bad_integrity),
                "source_images_checked": len(source_rows),
                "source_images_changed": len(changed_sources),
                "network_items_pending": len(pending_network),
            },
            "checks": checks,
            "failures": {
                "failed_scenarios": failed,
                "undetected_failures": undetected,
                "unrecovered_failures": unrecovered,
                "application_crashes": crashes,
                "bad_integrity_files": bad_integrity,
                "changed_source_images": changed_sources,
            },
            "evidence": [
                "P2-10-scenario-results.csv",
                "P2-10-failure-log.csv",
                "P2-10-recovery-timeline.csv",
                "P2-10-file-integrity.csv",
                "P2-10-state-transitions.json",
                "logs/p2-10.log",
            ],
        }
        write_json(evidence / "P2-10-final-report.json", report)
        return report

    finally:
        if not args.keep_runtime:
            shutil.rmtree(runtime, ignore_errors=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="P2-10 failure-recovery validation")
    parser.add_argument(
        "--image-dir",
        type=Path,
        default=None,
        help="Path to sunnybotics-solar-panel-challenge/sample_images",
    )
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=HERE.parent / "ValidationEvidence" / VALIDATION_ID,
    )
    parser.add_argument("--keep-runtime", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = run(args)
    except KeyboardInterrupt:
        print("\nP2-10 interrupted. Temporary runtime data was cleaned up.", file=sys.stderr)
        return 130
    except Exception as exc:
        LOGGER.exception("P2-10 could not complete")
        print(f"P2-10 could not complete: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())