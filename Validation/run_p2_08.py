from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import math
import os
import platform
import shutil
import socket
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
VALIDATION_ID = "P2-08"

MISSION_HOURS = 4.5
MAX_CAPTURE_RATE_HZ = 1.0
AVERAGE_RECORD_MB = 5.0
REQUIRED_FREE_PERCENT = 20.0
MINIMUM_WRITE_MBPS = 10.0

MB = 1_000_000
GB = 1_000_000_000
READ_CHUNK_BYTES = 1024 * 1024
HEADER_BYTES = 256


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def to_mb(
    byte_count: int | float,
) -> float:
    return round(
        float(byte_count) / MB,
        3,
    )


def to_gb(
    byte_count: int | float,
) -> float:
    return round(
        float(byte_count) / GB,
        3,
    )


def write_json(
    path: Path,
    payload: Any,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
    fieldnames: list[str],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)


def disk_snapshot(
    path: Path,
) -> dict[str, Any]:
    usage = shutil.disk_usage(
        path
    )

    return {
        "captured_at_utc": (
            utc_now()
        ),
        "path": str(
            path.resolve()
        ),
        "volume_root": (
            path.resolve().anchor
            or "/"
        ),
        "total_bytes": (
            usage.total
        ),
        "used_bytes": (
            usage.used
        ),
        "free_bytes": (
            usage.free
        ),
        "total_gb": to_gb(
            usage.total
        ),
        "used_gb": to_gb(
            usage.used
        ),
        "free_gb": to_gb(
            usage.free
        ),
    }


def make_planning_calculation(
) -> dict[str, Any]:
    mission_seconds = int(
        MISSION_HOURS
        * 60
        * 60
    )

    maximum_images = int(
        mission_seconds
        * MAX_CAPTURE_RATE_HZ
    )

    record_bytes = int(
        AVERAGE_RECORD_MB
        * MB
    )

    mission_bytes = (
        maximum_images
        * record_bytes
    )

    required_capacity_bytes = (
        math.ceil(
            mission_bytes
            / (
                1.0
                - REQUIRED_FREE_PERCENT
                / 100.0
            )
        )
    )

    return {
        "mission_hours": (
            MISSION_HOURS
        ),
        "mission_seconds": (
            mission_seconds
        ),
        "maximum_capture_rate_hz": (
            MAX_CAPTURE_RATE_HZ
        ),
        "maximum_image_count": (
            maximum_images
        ),
        "average_image_record_mb": (
            AVERAGE_RECORD_MB
        ),
        "average_image_record_bytes": (
            record_bytes
        ),
        "mission_storage_bytes": (
            mission_bytes
        ),
        "mission_storage_gb": (
            to_gb(
                mission_bytes
            )
        ),
        "required_free_percent": (
            REQUIRED_FREE_PERCENT
        ),
        "minimum_total_capacity_bytes": (
            required_capacity_bytes
        ),
        "minimum_total_capacity_gb": (
            to_gb(
                required_capacity_bytes
            )
        ),
        "peak_planning_data_rate_mbps": (
            AVERAGE_RECORD_MB
            * MAX_CAPTURE_RATE_HZ
        ),
        "minimum_sustained_write_mbps": (
            MINIMUM_WRITE_MBPS
        ),
    }


def make_header(
    index: int,
    expected_bytes: int,
) -> bytes:
    text = (
        f"P2-08 FILE {index:06d} "
        f"EXPECTED_BYTES={expected_bytes} "
        f"CREATED_UTC={utc_now()}"
    ).encode(
        "utf-8"
    )

    size = min(
        HEADER_BYTES,
        expected_bytes,
    )

    return text[
        :size
    ].ljust(
        size,
        b"\0",
    )


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open(
        "rb"
    ) as file:
        for block in iter(
            lambda: file.read(
                READ_CHUNK_BYTES
            ),
            b"",
        ):
            digest.update(
                block
            )

    return digest.hexdigest()


def run_validation(
    target: Path,
    evidence_root: Path,
    test_gb: float,
    file_size_mb: float,
    device_label: str,
    safety_gb: float,
    keep_payload: bool,
) -> bool:
    if test_gb <= 0:
        raise ValueError(
            "--test-gb must be "
            "greater than 0"
        )

    if file_size_mb <= 0:
        raise ValueError(
            "--file-size-mb must be "
            "greater than 0"
        )

    if safety_gb < 0:
        raise ValueError(
            "--safety-gb cannot "
            "be negative"
        )

    target = (
        target
        .expanduser()
        .resolve()
    )

    evidence_root = (
        evidence_root
        .expanduser()
        .resolve()
    )

    target.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Start with clean evidence so that
    # an earlier run cannot affect the
    # new validation result.
    if evidence_root.exists():
        shutil.rmtree(
            evidence_root
        )

    evidence_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    (
        evidence_root
        / "logs"
    ).mkdir(
        parents=True,
        exist_ok=True,
    )

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s "
            "%(levelname)s "
            "%(name)s "
            "%(message)s"
        ),
        handlers=[
            logging.FileHandler(
                evidence_root
                / "logs"
                / "p2-08.log",
                encoding="utf-8",
            ),
            logging.StreamHandler(),
        ],
        force=True,
    )

    logger = logging.getLogger(
        "p2-08"
    )

    payload_root = (
        target
        / "p2-08-payload"
    )

    if payload_root.exists():
        shutil.rmtree(
            payload_root
        )

    payload_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    planning = (
        make_planning_calculation()
    )

    before = disk_snapshot(
        target
    )

    test_bytes = int(
        test_gb
        * GB
    )

    nominal_file_bytes = int(
        file_size_mb
        * MB
    )

    safety_bytes = int(
        safety_gb
        * GB
    )

    file_count = math.ceil(
        test_bytes
        / nominal_file_bytes
    )

    mission_bytes = int(
        planning[
            "mission_storage_bytes"
        ]
    )

    minimum_capacity_bytes = int(
        planning[
            "minimum_total_capacity_bytes"
        ]
    )

    required_reserve_bytes = (
        math.ceil(
            before[
                "total_bytes"
            ]
            * REQUIRED_FREE_PERCENT
            / 100.0
        )
    )

    projected_free_after_mission = (
        before[
            "free_bytes"
        ]
        - mission_bytes
    )

    capacity_checks = {
        "mission_storage_is_81_gb": (
            mission_bytes
            == 81_000_000_000
        ),
        "minimum_capacity_is_101_25_gb": (
            minimum_capacity_bytes
            == 101_250_000_000
        ),
        "tested_volume_meets_minimum_capacity": (
            before[
                "total_bytes"
            ]
            >= minimum_capacity_bytes
        ),
        "tested_volume_leaves_20_percent_free": (
            projected_free_after_mission
            >= required_reserve_bytes
        ),
        "enough_space_for_benchmark": (
            before[
                "free_bytes"
            ]
            >= (
                test_bytes
                + safety_bytes
            )
        ),
    }

    system_info = {
        "validation_id": (
            VALIDATION_ID
        ),
        "device_label": (
            device_label
        ),
        "host": {
            "hostname": (
                socket.gethostname()
            ),
            "platform": (
                platform.platform()
            ),
            "operating_system": (
                platform.system()
            ),
            "release": (
                platform.release()
            ),
            "machine": (
                platform.machine()
            ),
            "processor": (
                platform.processor()
            ),
            "python_version": (
                platform.python_version()
            ),
        },
        "target": str(
            target
        ),
        "payload_root": str(
            payload_root
        ),
        "evidence_root": str(
            evidence_root
        ),
        "disk_before_test": (
            before
        ),
        "benchmark_request": {
            "test_bytes": (
                test_bytes
            ),
            "test_gb": (
                to_gb(
                    test_bytes
                )
            ),
            "file_size_bytes": (
                nominal_file_bytes
            ),
            "file_size_mb": (
                to_mb(
                    nominal_file_bytes
                )
            ),
            "expected_file_count": (
                file_count
            ),
            "safety_gb": (
                safety_gb
            ),
            "fsync_after_each_file": (
                True
            ),
        },
    }

    write_json(
        evidence_root
        / "P2-08-system-info.json",
        system_info,
    )

    capacity_report = {
        "validation_id": (
            VALIDATION_ID
        ),
        "planning": planning,
        "tested_volume": {
            "total_bytes": (
                before[
                    "total_bytes"
                ]
            ),
            "total_gb": (
                before[
                    "total_gb"
                ]
            ),
            "free_bytes_before_test": (
                before[
                    "free_bytes"
                ]
            ),
            "free_gb_before_test": (
                before[
                    "free_gb"
                ]
            ),
            "required_reserve_bytes": (
                required_reserve_bytes
            ),
            "required_reserve_gb": (
                to_gb(
                    required_reserve_bytes
                )
            ),
            "projected_free_after_mission_bytes": (
                projected_free_after_mission
            ),
            "projected_free_after_mission_gb": (
                to_gb(
                    projected_free_after_mission
                )
            ),
        },
        "checks": (
            capacity_checks
        ),
    }

    write_json(
        evidence_root
        / "P2-08-capacity-calculation.json",
        capacity_report,
    )

    if not capacity_checks[
        "enough_space_for_benchmark"
    ]:
        report = {
            "validation_id": (
                VALIDATION_ID
            ),
            "title": (
                "Local Storage Validation"
            ),
            "result": "FAIL",
            "passed": False,
            "executed_at_utc": (
                utc_now()
            ),
            "failure_reason": (
                "Not enough free space "
                "for the requested benchmark "
                "plus safety margin."
            ),
            "global_checks": (
                capacity_checks
            ),
        }

        write_json(
            evidence_root
            / "P2-08-final-report.json",
            report,
        )

        shutil.rmtree(
            payload_root,
            ignore_errors=True,
        )

        return False

    # Create one random template in memory.
    # Every output file gets a unique header.
    template = os.urandom(
        nominal_file_bytes
    )

    template_view = memoryview(
        template
    )

    write_rows: list[
        dict[str, Any]
    ] = []

    total_written = 0
    remaining = test_bytes

    write_started_utc = (
        utc_now()
    )

    write_started = (
        time.perf_counter()
    )

    logger.info(
        "Writing %.3f GB as %s files",
        to_gb(
            test_bytes
        ),
        file_count,
    )

    for index in range(
        1,
        file_count + 1,
    ):
        expected_bytes = min(
            nominal_file_bytes,
            remaining,
        )

        remaining -= (
            expected_bytes
        )

        filename = (
            "p2-08-storage-"
            f"{index:06d}.bin"
        )

        path = (
            payload_root
            / filename
        )

        header = make_header(
            index,
            expected_bytes,
        )

        body = template_view[
            len(header):
            expected_bytes
        ]

        expected_digest = (
            hashlib.sha256()
        )

        expected_digest.update(
            header
        )

        expected_digest.update(
            body
        )

        started_utc = (
            utc_now()
        )

        started = (
            time.perf_counter()
        )

        # buffering=0 plus fsync forces each
        # completed file through the operating
        # system's storage path before it is
        # counted as written.
        with path.open(
            "wb",
            buffering=0,
        ) as file:
            file.write(
                header
            )

            if body:
                file.write(
                    body
                )

            file.flush()

            os.fsync(
                file.fileno()
            )

        elapsed = (
            time.perf_counter()
            - started
        )

        actual_bytes = (
            path.stat().st_size
        )

        total_written += (
            actual_bytes
        )

        write_rows.append(
            {
                "index": (
                    index
                ),
                "filename": (
                    filename
                ),
                "relative_path": str(
                    path.relative_to(
                        target
                    )
                ),
                "write_started_utc": (
                    started_utc
                ),
                "write_completed_utc": (
                    utc_now()
                ),
                "expected_bytes": (
                    expected_bytes
                ),
                "actual_bytes": (
                    actual_bytes
                ),
                "size_matches": (
                    actual_bytes
                    == expected_bytes
                ),
                "write_duration_s": (
                    round(
                        elapsed,
                        6,
                    )
                ),
                "file_write_mbps": (
                    round(
                        actual_bytes
                        / elapsed
                        / MB,
                        3,
                    )
                    if elapsed > 0
                    else 0.0
                ),
                "expected_sha256": (
                    expected_digest
                    .hexdigest()
                ),
            }
        )

        if (
            index == 1
            or index % 100 == 0
            or index == file_count
        ):
            logger.info(
                "Write progress: %s/%s",
                index,
                file_count,
            )

    write_elapsed = (
        time.perf_counter()
        - write_started
    )

    sustained_mbps = (
        total_written
        / write_elapsed
        / MB
        if write_elapsed > 0
        else 0.0
    )

    after_write = (
        disk_snapshot(
            target
        )
    )

    write_csv(
        evidence_root
        / "P2-08-throughput-log.csv",
        write_rows,
        [
            "index",
            "filename",
            "relative_path",
            "write_started_utc",
            "write_completed_utc",
            "expected_bytes",
            "actual_bytes",
            "size_matches",
            "write_duration_s",
            "file_write_mbps",
            "expected_sha256",
        ],
    )

    throughput_summary = {
        "validation_id": (
            VALIDATION_ID
        ),
        "write_started_utc": (
            write_started_utc
        ),
        "write_completed_utc": (
            utc_now()
        ),
        "requested_test_bytes": (
            test_bytes
        ),
        "requested_test_gb": (
            to_gb(
                test_bytes
            )
        ),
        "total_bytes_written": (
            total_written
        ),
        "total_gb_written": (
            to_gb(
                total_written
            )
        ),
        "expected_file_count": (
            file_count
        ),
        "written_file_count": (
            len(
                write_rows
            )
        ),
        "write_elapsed_seconds": (
            round(
                write_elapsed,
                6,
            )
        ),
        "overall_sustained_write_mbps": (
            round(
                sustained_mbps,
                3,
            )
        ),
        "minimum_required_write_mbps": (
            MINIMUM_WRITE_MBPS
        ),
        "throughput_pass": (
            sustained_mbps
            >= MINIMUM_WRITE_MBPS
        ),
        "fsync_after_each_file": (
            True
        ),
        "disk_after_write": (
            after_write
        ),
    }

    write_json(
        evidence_root
        / "P2-08-throughput-summary.json",
        throughput_summary,
    )

    logger.info(
        "Write phase completed "
        "at %.3f MB/s",
        sustained_mbps,
    )

    verify_rows: list[
        dict[str, Any]
    ] = []

    missing_files: list[str] = []
    unreadable_files: list[str] = []
    size_mismatches: list[str] = []
    checksum_mismatches: list[str] = []
    duplicate_filenames: list[str] = []

    seen_names: set[str] = set()

    verify_started_utc = (
        utc_now()
    )

    verify_started = (
        time.perf_counter()
    )

    for row in write_rows:
        filename = str(
            row[
                "filename"
            ]
        )

        path = (
            payload_root
            / filename
        )

        duplicate = (
            filename
            in seen_names
        )

        if duplicate:
            duplicate_filenames.append(
                filename
            )

        seen_names.add(
            filename
        )

        exists = (
            path.is_file()
        )

        readable = False

        actual_bytes: (
            int
            | None
        ) = None

        actual_sha256: (
            str
            | None
        ) = None

        read_duration_s: (
            float
            | None
        ) = None

        if not exists:
            missing_files.append(
                filename
            )

        else:
            actual_bytes = (
                path.stat().st_size
            )

            if (
                actual_bytes
                != row[
                    "expected_bytes"
                ]
            ):
                size_mismatches.append(
                    filename
                )

            started = (
                time.perf_counter()
            )

            try:
                actual_sha256 = (
                    sha256_file(
                        path
                    )
                )

                readable = True

            except OSError:
                unreadable_files.append(
                    filename
                )

            read_duration_s = (
                time.perf_counter()
                - started
            )

            if (
                readable
                and actual_sha256
                != row[
                    "expected_sha256"
                ]
            ):
                checksum_mismatches.append(
                    filename
                )

        verify_rows.append(
            {
                "index": (
                    row[
                        "index"
                    ]
                ),
                "filename": (
                    filename
                ),
                "relative_path": (
                    row[
                        "relative_path"
                    ]
                ),
                "exists": (
                    exists
                ),
                "readable": (
                    readable
                ),
                "expected_bytes": (
                    row[
                        "expected_bytes"
                    ]
                ),
                "actual_bytes": (
                    actual_bytes
                ),
                "size_matches": (
                    exists
                    and actual_bytes
                    == row[
                        "expected_bytes"
                    ]
                ),
                "expected_sha256": (
                    row[
                        "expected_sha256"
                    ]
                ),
                "actual_sha256": (
                    actual_sha256
                ),
                "checksum_matches": (
                    readable
                    and actual_sha256
                    == row[
                        "expected_sha256"
                    ]
                ),
                "duplicate_filename": (
                    duplicate
                ),
                "read_duration_s": (
                    round(
                        read_duration_s,
                        6,
                    )
                    if (
                        read_duration_s
                        is not None
                    )
                    else None
                ),
            }
        )

    verify_elapsed = (
        time.perf_counter()
        - verify_started
    )

    write_csv(
        evidence_root
        / "P2-08-file-list.csv",
        verify_rows,
        [
            "index",
            "filename",
            "relative_path",
            "exists",
            "readable",
            "expected_bytes",
            "actual_bytes",
            "size_matches",
            "expected_sha256",
            "actual_sha256",
            "checksum_matches",
            "duplicate_filename",
            "read_duration_s",
        ],
    )

    checksum_report = {
        "validation_id": (
            VALIDATION_ID
        ),
        "verification_started_utc": (
            verify_started_utc
        ),
        "verification_completed_utc": (
            utc_now()
        ),
        "verification_elapsed_seconds": (
            round(
                verify_elapsed,
                6,
            )
        ),
        "expected_file_count": (
            file_count
        ),
        "verified_file_count": (
            len(
                verify_rows
            )
        ),
        "existing_file_count": (
            sum(
                bool(
                    row[
                        "exists"
                    ]
                )
                for row
                in verify_rows
            )
        ),
        "readable_file_count": (
            sum(
                bool(
                    row[
                        "readable"
                    ]
                )
                for row
                in verify_rows
            )
        ),
        "size_match_count": (
            sum(
                bool(
                    row[
                        "size_matches"
                    ]
                )
                for row
                in verify_rows
            )
        ),
        "checksum_match_count": (
            sum(
                bool(
                    row[
                        "checksum_matches"
                    ]
                )
                for row
                in verify_rows
            )
        ),
        "missing_files": (
            missing_files
        ),
        "unreadable_files": (
            unreadable_files
        ),
        "size_mismatches": (
            size_mismatches
        ),
        "checksum_mismatches": (
            checksum_mismatches
        ),
        "duplicate_filenames": (
            duplicate_filenames
        ),
        "passed": not any(
            (
                missing_files,
                unreadable_files,
                size_mismatches,
                checksum_mismatches,
                duplicate_filenames,
            )
        ),
    }

    write_json(
        evidence_root
        / "P2-08-checksum-verification.json",
        checksum_report,
    )

    cleanup_ok = True

    cleanup_error: (
        str
        | None
    ) = None

    # Normal runs delete the temporary
    # multi-gigabyte payload here.
    if not keep_payload:
        try:
            shutil.rmtree(
                payload_root
            )

        except OSError as exc:
            cleanup_ok = False
            cleanup_error = str(
                exc
            )

    after_cleanup = (
        disk_snapshot(
            target
        )
    )

    global_checks = {
        **capacity_checks,
        "all_expected_files_written": (
            len(
                write_rows
            )
            == file_count
            and total_written
            == test_bytes
            and all(
                bool(
                    row[
                        "size_matches"
                    ]
                )
                for row
                in write_rows
            )
        ),
        "sustained_write_speed_at_least_10_mbps": (
            sustained_mbps
            >= MINIMUM_WRITE_MBPS
        ),
        "all_files_exist_and_are_readable": (
            not missing_files
            and not unreadable_files
        ),
        "all_file_sizes_match": (
            not size_mismatches
        ),
        "all_checksums_match": (
            not checksum_mismatches
        ),
        "no_duplicate_filenames": (
            not duplicate_filenames
        ),
        "temporary_payload_cleanup_ok": (
            cleanup_ok
        ),
    }

    overall_pass = all(
        global_checks.values()
    )

    final_report = {
        "validation_id": (
            VALIDATION_ID
        ),
        "title": (
            "Local Storage Validation"
        ),
        "result": (
            "PASS"
            if overall_pass
            else "FAIL"
        ),
        "passed": (
            overall_pass
        ),
        "executed_at_utc": (
            utc_now()
        ),
        "device_label": (
            device_label
        ),
        "test_type": (
            "Representative "
            "local-storage benchmark"
        ),
        "target": str(
            target
        ),
        "payload_retained": (
            keep_payload
        ),
        "cleanup_error": (
            cleanup_error
        ),
        "planning": (
            planning
        ),
        "benchmark": {
            "requested_test_gb": (
                to_gb(
                    test_bytes
                )
            ),
            "file_size_mb": (
                to_mb(
                    nominal_file_bytes
                )
            ),
            "expected_file_count": (
                file_count
            ),
            "written_file_count": (
                len(
                    write_rows
                )
            ),
            "verified_file_count": (
                len(
                    verify_rows
                )
            ),
            "overall_sustained_write_mbps": (
                round(
                    sustained_mbps,
                    3,
                )
            ),
            "minimum_required_write_mbps": (
                MINIMUM_WRITE_MBPS
            ),
            "checksum_match_count": (
                checksum_report[
                    "checksum_match_count"
                ]
            ),
            "size_match_count": (
                checksum_report[
                    "size_match_count"
                ]
            ),
        },
        "capacity": {
            "tested_volume_total_gb": (
                before[
                    "total_gb"
                ]
            ),
            "tested_volume_free_gb_before_test": (
                before[
                    "free_gb"
                ]
            ),
            "mission_storage_gb": (
                planning[
                    "mission_storage_gb"
                ]
            ),
            "minimum_total_capacity_gb": (
                planning[
                    "minimum_total_capacity_gb"
                ]
            ),
            "required_reserve_gb": (
                to_gb(
                    required_reserve_bytes
                )
            ),
            "projected_free_after_mission_gb": (
                to_gb(
                    projected_free_after_mission
                )
            ),
        },
        "disk_snapshots": {
            "before_test": (
                before
            ),
            "after_write": (
                after_write
            ),
            "after_cleanup": (
                after_cleanup
            ),
        },
        "global_checks": (
            global_checks
        ),
        "failed_checks": [
            name
            for name, passed
            in global_checks.items()
            if not passed
        ],
        "evidence_files": [
            "P2-08-system-info.json",
            "P2-08-capacity-calculation.json",
            "P2-08-throughput-summary.json",
            "P2-08-throughput-log.csv",
            "P2-08-file-list.csv",
            "P2-08-checksum-verification.json",
            "P2-08-final-report.json",
            "logs/p2-08.log",
        ],
    }

    write_json(
        evidence_root
        / "P2-08-final-report.json",
        final_report,
    )

    print()
    print(
        "=" * 68
    )
    print(
        "P2-08 LOCAL STORAGE VALIDATION"
    )
    print(
        "=" * 68
    )
    print(
        "Result:                    "
        f"{final_report['result']}"
    )
    print(
        "Benchmark data written:    "
        f"{to_gb(total_written):.3f} GB"
    )
    print(
        "Files written:             "
        f"{len(write_rows)}/"
        f"{file_count}"
    )
    print(
        "Sustained write speed:     "
        f"{sustained_mbps:.3f} MB/s"
    )
    print(
        "Minimum required speed:    "
        f"{MINIMUM_WRITE_MBPS:.3f} MB/s"
    )
    print(
        "Checksum matches:          "
        f"{checksum_report['checksum_match_count']}/"
        f"{file_count}"
    )
    print(
        "Mission storage required:  "
        f"{planning['mission_storage_gb']:.3f} GB"
    )
    print(
        "Minimum usable capacity:   "
        f"{planning['minimum_total_capacity_gb']:.3f} GB"
    )
    print(
        "20% free-space check:      "
        + (
            "PASS"
            if capacity_checks[
                "tested_volume_leaves_20_percent_free"
            ]
            else "FAIL"
        )
    )
    print(
        "Evidence folder:           "
        f"{evidence_root}"
    )
    print(
        "=" * 68
    )

    return overall_pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run P2-08 local-storage "
            "throughput, integrity, and "
            "capacity validation."
        )
    )

    parser.add_argument(
        "--target",
        required=True,
        type=Path,
        help=(
            "Directory on the volume "
            "to test, for example "
            "C:\\P2-08-storage-test."
        ),
    )

    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=(
            HERE.parent
            / "ValidationEvidence"
            / "P2-08"
        ),
        help=(
            "Directory where reports "
            "and logs will be saved."
        ),
    )

    parser.add_argument(
        "--test-gb",
        type=float,
        default=10.0,
        help=(
            "Temporary data to write "
            "in decimal GB. Default: 10."
        ),
    )

    parser.add_argument(
        "--file-size-mb",
        type=float,
        default=5.0,
        help=(
            "Nominal file size in decimal "
            "MB. Default: 5."
        ),
    )

    parser.add_argument(
        "--device-label",
        default=(
            "Representative host storage"
        ),
        help=(
            "Human-readable name for "
            "the tested storage device."
        ),
    )

    parser.add_argument(
        "--safety-gb",
        type=float,
        default=1.0,
        help=(
            "Extra free-space margin "
            "required before testing. "
            "Default: 1 GB."
        ),
    )

    parser.add_argument(
        "--keep-payload",
        action="store_true",
        help=(
            "Keep the temporary benchmark "
            "files after verification."
        ),
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        passed = run_validation(
            target=(
                args.target
            ),
            evidence_root=(
                args.evidence_root
            ),
            test_gb=(
                args.test_gb
            ),
            file_size_mb=(
                args.file_size_mb
            ),
            device_label=(
                args.device_label
            ),
            safety_gb=(
                args.safety_gb
            ),
            keep_payload=(
                args.keep_payload
            ),
        )

    except Exception:
        logging.exception(
            "P2-08 validation "
            "could not complete"
        )

        return 2

    return (
        0
        if passed
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )