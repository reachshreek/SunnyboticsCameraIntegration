from __future__ import annotations

import argparse
import csv
import json
import logging
import random
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent

if (HERE / "src").is_dir():
    sys.path.insert(
        0,
        str(HERE / "src"),
    )

from solar_metadata_tagger.config import (
    CameraConfig,
    GnssConfig,
    StorageConfig,
    TaggerConfig,
)
from solar_metadata_tagger.errors import (
    MetadataTaggerError,
)
from solar_metadata_tagger.models import (
    GnssFix,
    utc_iso,
)
from solar_metadata_tagger.nmea import (
    NmeaParser,
)
from solar_metadata_tagger.service import (
    MetadataTaggingService,
)


ROBOT_ID = "sunnybot-01"

MISSION_ID = (
    "p2-07-metadata-geotagging"
)

SEED = 207


# These are fixed mock coordinates with
# memorable In-N-Out location labels.
#
# The locations are shuffled using a fixed
# random seed. This gives them a randomized
# order while making every run repeatable.
#
# They are test data only and should not be
# used for navigation.
LOCATIONS = [
    (
        "Goleta, California",
        34.4429037,
        -119.7907206,
    ),
    (
        "Los Angeles, California",
        33.9537066,
        -118.3967839,
    ),
    (
        "National City, California",
        32.6596772,
        -117.1066369,
    ),
    (
        "Austin, Texas",
        30.3043639,
        -97.7154002,
    ),
    (
        "Las Vegas, Nevada",
        36.1013316,
        -115.1822285,
    ),
    (
        "Alhambra, California",
        34.1060014,
        -118.1343926,
    ),
    (
        "Hollywood, California",
        34.0982287,
        -118.3416747,
    ),
    (
        "Colorado Springs, Colorado",
        38.9902420,
        -104.7970530,
    ),
    (
        "Baldwin Park, California",
        34.0676639,
        -117.9735105,
    ),
    (
        "Keizer, Oregon",
        45.0106410,
        -122.9947200,
    ),
]


def make_fix(
    location: tuple[
        str,
        float,
        float,
    ],
    captured_at: datetime,
    *,
    offset_s: float = 0.0,
    latitude: float | None = None,
    longitude: float | None = None,
    satellites: int | None = 10,
) -> GnssFix:
    """
    Create one simulated GNSS fix.

    offset_s controls when the fix was
    received relative to image capture.

    0.0 means the fix occurred at capture.
    -5.0 means it is five seconds old.
    1.0 means it arrived one second later.
    """

    (
        _,
        default_latitude,
        default_longitude,
    ) = location

    received_at = (
        captured_at
        + timedelta(
            seconds=offset_s
        )
    )

    return GnssFix(
        latitude=(
            default_latitude
            if latitude is None
            else latitude
        ),
        longitude=(
            default_longitude
            if longitude is None
            else longitude
        ),
        received_at_utc=received_at,
        fix_time_utc=received_at,
        altitude_m=10.0,
        fix_quality=1,
        satellites=satellites,
        hdop=0.8,
        speed_mps=0.25,
        course_deg=90.0,
        source_sentence=(
            "P2-07-MOCK"
        ),
    )


def malformed_nmea_error(
    captured_at: datetime,
) -> str | None:
    """
    Send a deliberately malformed NMEA
    sentence through the real parser.

    The ZZ checksum is invalid.
    """

    sentence = (
        "$GPGGA,123519.00,"
        "4807.038,N,"
        "01131.000,E,"
        "1,08,0.9,"
        "545.4,M,"
        "46.9,M,,*ZZ"
    )

    try:
        NmeaParser().parse(
            sentence,
            captured_at,
        )

    except MetadataTaggerError as exc:
        return exc.code

    return None


def build_cases() -> list[
    dict[str, Any]
]:
    """
    Create the controlled P2-07 scenarios.
    """

    locations = list(
        LOCATIONS
    )

    random.Random(
        SEED
    ).shuffle(
        locations
    )

    base = datetime(
        2026,
        8,
        3,
        20,
        0,
        0,
        tzinfo=timezone.utc,
    )

    cases: list[
        dict[str, Any]
    ] = []

    missing_warnings = (
        "gnss_fix_missing_or_"
        "outside_capture_window",
        "missing_required_fields:",
    )

    invalid_coordinate_warnings = (
        "gnss_coordinates_invalid",
        "missing_required_fields:",
    )

    stale_warnings = (
        "gnss_fix_outside_window:",
        "missing_required_fields:",
    )

    def location_at(
        index: int,
    ) -> tuple[
        str,
        float,
        float,
    ]:
        return locations[
            index % len(locations)
        ]

    def add_case(
        case_id: str,
        captured_at: datetime,
        location: (
            tuple[
                str,
                float,
                float,
            ]
            | None
        ),
        fix: GnssFix | None,
        expected_status: str,
        expected_valid: bool,
        expected_fresh: bool,
        expected_quality: bool,
        expected_latitude: (
            float | None
        ),
        expected_longitude: (
            float | None
        ),
        warnings: tuple[
            str,
            ...,
        ] = (),
        row: str | None = None,
        panel: str | None = None,
        assignment: str = (
            "not-required"
        ),
        parser_error: (
            str | None
        ) = None,
        no_warnings: bool = False,
    ) -> None:
        cases.append(
            {
                "case_id": (
                    case_id
                ),
                "captured_at": (
                    captured_at
                ),
                "location": location,
                "fix": fix,
                "expected_status": (
                    expected_status
                ),
                "expected_valid": (
                    expected_valid
                ),
                "expected_fresh": (
                    expected_fresh
                ),
                "expected_quality": (
                    expected_quality
                ),
                "expected_latitude": (
                    expected_latitude
                ),
                "expected_longitude": (
                    expected_longitude
                ),
                "warnings": warnings,
                "row": row,
                "panel": panel,
                "assignment": (
                    assignment
                ),
                "parser_error": (
                    parser_error
                ),
                "no_warnings": (
                    no_warnings
                ),
            }
        )

    # -------------------------------------------------
    # Cases 1 and 2:
    # Two valid locations.
    # -------------------------------------------------

    for index in range(2):
        captured_at = (
            base
            + timedelta(
                seconds=index
            )
        )

        location = location_at(
            index
        )

        add_case(
            case_id=(
                "valid-location-"
                f"{index + 1:02d}"
            ),
            captured_at=(
                captured_at
            ),
            location=location,
            fix=make_fix(
                location,
                captured_at,
            ),
            expected_status=(
                "complete"
            ),
            expected_valid=True,
            expected_fresh=True,
            expected_quality=True,
            expected_latitude=(
                location[1]
            ),
            expected_longitude=(
                location[2]
            ),
            no_warnings=True,
        )

    # -------------------------------------------------
    # Case 3:
    # Row and panel are accepted but optional.
    # -------------------------------------------------

    captured_at = (
        base
        + timedelta(
            seconds=2
        )
    )

    location = location_at(
        2
    )

    add_case(
        case_id=(
            "optional-row-panel"
        ),
        captured_at=captured_at,
        location=location,
        fix=make_fix(
            location,
            captured_at,
        ),
        expected_status="complete",
        expected_valid=True,
        expected_fresh=True,
        expected_quality=True,
        expected_latitude=(
            location[1]
        ),
        expected_longitude=(
            location[2]
        ),
        row="TEST-ROW",
        panel="TEST-PANEL",
        assignment=(
            "manual-optional"
        ),
        no_warnings=True,
    )

    # -------------------------------------------------
    # Case 4:
    # No GNSS fix is available.
    # -------------------------------------------------

    captured_at = (
        base
        + timedelta(
            seconds=3
        )
    )

    add_case(
        case_id="missing-gnss",
        captured_at=captured_at,
        location=None,
        fix=None,
        expected_status=(
            "quarantined"
        ),
        expected_valid=False,
        expected_fresh=False,
        expected_quality=False,
        expected_latitude=None,
        expected_longitude=None,
        warnings=missing_warnings,
    )

    # -------------------------------------------------
    # Case 5:
    # Malformed NMEA checksum.
    #
    # The malformed data is rejected. The image is
    # still saved as a missing-GNSS record.
    # -------------------------------------------------

    captured_at = (
        base
        + timedelta(
            seconds=4
        )
    )

    add_case(
        case_id="malformed-nmea",
        captured_at=captured_at,
        location=None,
        fix=None,
        expected_status=(
            "quarantined"
        ),
        expected_valid=False,
        expected_fresh=False,
        expected_quality=False,
        expected_latitude=None,
        expected_longitude=None,
        warnings=missing_warnings,
        parser_error=(
            malformed_nmea_error(
                captured_at
            )
        ),
    )

    # -------------------------------------------------
    # Case 6:
    # Latitude is outside the valid range.
    # -------------------------------------------------

    captured_at = (
        base
        + timedelta(
            seconds=5
        )
    )

    location = location_at(
        3
    )

    add_case(
        case_id=(
            "invalid-latitude"
        ),
        captured_at=captured_at,
        location=location,
        fix=make_fix(
            location,
            captured_at,
            latitude=95.0,
        ),
        expected_status=(
            "quarantined"
        ),
        expected_valid=False,
        expected_fresh=True,
        expected_quality=True,
        expected_latitude=None,
        expected_longitude=None,
        warnings=(
            invalid_coordinate_warnings
        ),
    )

    # -------------------------------------------------
    # Case 7:
    # Longitude is outside the valid range.
    # -------------------------------------------------

    captured_at = (
        base
        + timedelta(
            seconds=6
        )
    )

    location = location_at(
        4
    )

    add_case(
        case_id=(
            "invalid-longitude"
        ),
        captured_at=captured_at,
        location=location,
        fix=make_fix(
            location,
            captured_at,
            longitude=-181.0,
        ),
        expected_status=(
            "quarantined"
        ),
        expected_valid=False,
        expected_fresh=True,
        expected_quality=True,
        expected_latitude=None,
        expected_longitude=None,
        warnings=(
            invalid_coordinate_warnings
        ),
    )

    # -------------------------------------------------
    # Case 8:
    # The GNSS fix is five seconds old.
    #
    # The configured maximum age is 2.5 seconds.
    # -------------------------------------------------

    captured_at = (
        base
        + timedelta(
            seconds=7
        )
    )

    location = location_at(
        5
    )

    add_case(
        case_id="stale-fix",
        captured_at=captured_at,
        location=location,
        fix=make_fix(
            location,
            captured_at,
            offset_s=-5.0,
        ),
        expected_status=(
            "quarantined"
        ),
        expected_valid=False,
        expected_fresh=False,
        expected_quality=True,
        expected_latitude=(
            location[1]
        ),
        expected_longitude=(
            location[2]
        ),
        warnings=stale_warnings,
    )

    # -------------------------------------------------
    # Case 9:
    # The fix occurs one second after capture.
    #
    # The configured future tolerance is 0.25 seconds.
    # -------------------------------------------------

    captured_at = (
        base
        + timedelta(
            seconds=8
        )
    )

    location = location_at(
        6
    )

    add_case(
        case_id=(
            "future-fix-outside-"
            "tolerance"
        ),
        captured_at=captured_at,
        location=location,
        fix=make_fix(
            location,
            captured_at,
            offset_s=1.0,
        ),
        expected_status=(
            "quarantined"
        ),
        expected_valid=False,
        expected_fresh=False,
        expected_quality=True,
        expected_latitude=(
            location[1]
        ),
        expected_longitude=(
            location[2]
        ),
        warnings=stale_warnings,
    )

    # -------------------------------------------------
    # Case 10:
    # Only two satellites are reported.
    #
    # The configured minimum is four.
    # -------------------------------------------------

    captured_at = (
        base
        + timedelta(
            seconds=9
        )
    )

    location = location_at(
        7
    )

    add_case(
        case_id=(
            "low-satellite-count"
        ),
        captured_at=captured_at,
        location=location,
        fix=make_fix(
            location,
            captured_at,
            satellites=2,
        ),
        expected_status=(
            "quarantined"
        ),
        expected_valid=False,
        expected_fresh=True,
        expected_quality=False,
        expected_latitude=(
            location[1]
        ),
        expected_longitude=(
            location[2]
        ),
        warnings=(
            "gnss_satellites_low:2",
            "missing_required_fields:",
        ),
    )

    # -------------------------------------------------
    # Cases 11 and 12:
    # Two images have exactly the same timestamp.
    #
    # Their image IDs must still be unique.
    # -------------------------------------------------

    duplicate_time = (
        base
        + timedelta(
            seconds=15
        )
    )

    for (
        suffix,
        index,
    ) in (
        ("a", 8),
        ("b", 9),
    ):
        location = location_at(
            index
        )

        add_case(
            case_id=(
                "duplicate-timestamp-"
                f"{suffix}"
            ),
            captured_at=(
                duplicate_time
            ),
            location=location,
            fix=make_fix(
                location,
                duplicate_time,
            ),
            expected_status=(
                "complete"
            ),
            expected_valid=True,
            expected_fresh=True,
            expected_quality=True,
            expected_latitude=(
                location[1]
            ),
            expected_longitude=(
                location[2]
            ),
            no_warnings=True,
        )

    # -------------------------------------------------
    # Cases 13 and 14:
    # Midnight rollover and out-of-order timestamps.
    #
    # The August 4 record is processed first.
    # The August 3 record is processed second.
    # -------------------------------------------------

    after_midnight = datetime(
        2026,
        8,
        4,
        0,
        0,
        0,
        100000,
        tzinfo=timezone.utc,
    )

    location = location_at(
        0
    )

    add_case(
        case_id=(
            "after-midnight-"
            "processed-first"
        ),
        captured_at=after_midnight,
        location=location,
        fix=make_fix(
            location,
            after_midnight,
        ),
        expected_status="complete",
        expected_valid=True,
        expected_fresh=True,
        expected_quality=True,
        expected_latitude=(
            location[1]
        ),
        expected_longitude=(
            location[2]
        ),
        no_warnings=True,
    )

    before_midnight = datetime(
        2026,
        8,
        3,
        23,
        59,
        59,
        900000,
        tzinfo=timezone.utc,
    )

    location = location_at(
        1
    )

    add_case(
        case_id=(
            "before-midnight-"
            "processed-second"
        ),
        captured_at=before_midnight,
        location=location,
        fix=make_fix(
            location,
            before_midnight,
        ),
        expected_status="complete",
        expected_valid=True,
        expected_fresh=True,
        expected_quality=True,
        expected_latitude=(
            location[1]
        ),
        expected_longitude=(
            location[2]
        ),
        no_warnings=True,
    )

    # -------------------------------------------------
    # Case 15:
    # A Pacific timestamp is converted to UTC.
    # -------------------------------------------------

    pacific = timezone(
        timedelta(
            hours=-7
        )
    )

    local_time = datetime(
        2026,
        8,
        3,
        15,
        30,
        0,
        tzinfo=pacific,
    )

    location = location_at(
        2
    )

    add_case(
        case_id=(
            "timezone-normalization"
        ),
        captured_at=local_time,
        location=location,
        fix=make_fix(
            location,
            local_time,
        ),
        expected_status="complete",
        expected_valid=True,
        expected_fresh=True,
        expected_quality=True,
        expected_latitude=(
            location[1]
        ),
        expected_longitude=(
            location[2]
        ),
        no_warnings=True,
    )

    # -------------------------------------------------
    # Cases 16 through 18:
    #
    # Valid GNSS
    # Missing GNSS
    # Valid GNSS again
    #
    # The missing record must not reuse old coordinates.
    # -------------------------------------------------

    recovery_cases = (
        (
            "recovery-valid-before-loss",
            30,
            location_at(3),
            False,
        ),
        (
            "recovery-missing",
            31,
            None,
            True,
        ),
        (
            "recovery-valid-after-loss",
            32,
            location_at(4),
            False,
        ),
    )

    for (
        case_id,
        seconds,
        location,
        is_missing,
    ) in recovery_cases:
        captured_at = (
            base
            + timedelta(
                seconds=seconds
            )
        )

        add_case(
            case_id=case_id,
            captured_at=captured_at,
            location=location,
            fix=(
                None
                if is_missing
                else make_fix(
                    location,
                    captured_at,
                )
            ),
            expected_status=(
                "quarantined"
                if is_missing
                else "complete"
            ),
            expected_valid=(
                not is_missing
            ),
            expected_fresh=(
                not is_missing
            ),
            expected_quality=(
                not is_missing
            ),
            expected_latitude=(
                None
                if is_missing
                else location[1]
            ),
            expected_longitude=(
                None
                if is_missing
                else location[2]
            ),
            warnings=(
                missing_warnings
                if is_missing
                else ()
            ),
            no_warnings=(
                not is_missing
            ),
        )

    return cases


def build_config(
    output_root: Path,
) -> TaggerConfig:
    """
    Build an isolated P2-07 configuration.
    """

    return TaggerConfig(
        robot_id=ROBOT_ID,
        mission_id=MISSION_ID,
        storage=StorageConfig(
            root=output_root,
            spool_dir=(
                output_root
                / "spool"
            ),
            quarantine_on_missing_required=True,
            compute_sha256=True,
            validate_images=True,
            preserve_source=True,
            min_free_gb=0.0,
            emergency_free_gb=0.0,
        ),
        gnss=GnssConfig(
            enabled=False,
            max_fix_age_s=2.5,
            future_tolerance_s=0.25,
            min_satellites=4,
            max_hdop=5.0,
            require_fix_quality=True,
        ),
        camera=CameraConfig(
            source="directory",
            model=(
                "P2-07 "
                "representative image"
            ),
            output_format="png",
        ),
        required_fields=(
            "latitude",
            "longitude",
        ),
        log_level="INFO",
    )


def find_image(
    requested: Path | None,
) -> Path:
    """
    Find an image to use for the test.
    """

    if requested is not None:
        image = (
            requested
            .expanduser()
            .resolve()
        )

        if image.is_file():
            return image

        raise FileNotFoundError(
            f"Image not found: {image}"
        )

    preferred = (
        HERE
        / "sample_images"
        / "sample1.png"
    )

    if preferred.is_file():
        return preferred

    search_folders = (
        "sample_images",
        "representative_dataset",
        "test_images",
    )

    image_patterns = (
        "*.png",
        "*.jpg",
        "*.jpeg",
        "*.tif",
        "*.tiff",
        "*.bmp",
    )

    for folder_name in (
        search_folders
    ):
        folder = (
            HERE
            / folder_name
        )

        if not folder.is_dir():
            continue

        for pattern in (
            image_patterns
        ):
            match = next(
                folder.rglob(
                    pattern
                ),
                None,
            )

            if match is not None:
                return match.resolve()

    raise FileNotFoundError(
        "No image was found. "
        "Run the script with:\n"
        "python .\\run_p2_07.py "
        "--image "
        "'.\\path\\to\\image.png'"
    )


def write_json(
    path: Path,
    payload: Any,
) -> None:
    """
    Write readable JSON evidence.
    """

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


def number_matches(
    actual: Any,
    expected: Any,
) -> bool:
    """
    Compare coordinate values.
    """

    if (
        actual is None
        or expected is None
    ):
        return (
            actual is expected
        )

    return (
        abs(
            float(actual)
            - float(expected)
        )
        <= 0.00000001
    )


def warnings_match(
    actual: list[str],
    expected_fragments: tuple[
        str,
        ...,
    ],
) -> bool:
    """
    Confirm that every expected warning
    fragment exists.
    """

    return all(
        any(
            fragment in warning
            for warning in actual
        )
        for fragment
        in expected_fragments
    )


def run_validation(
    source_image: Path,
    output_root: Path,
) -> bool:
    """
    Run every scenario and create the
    P2-07 evidence files.
    """

    # Always start with a clean folder.
    # This prevents old evidence from
    # affecting the new counts.
    if output_root.exists():
        shutil.rmtree(
            output_root
        )

    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    log_directory = (
        output_root
        / "logs"
    )

    log_directory.mkdir(
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
                log_directory
                / "p2-07.log",
                encoding="utf-8",
            ),
            logging.StreamHandler(),
        ],
        force=True,
    )

    cases = build_cases()

    service = (
        MetadataTaggingService(
            build_config(
                output_root
            )
        )
    )

    comparison: list[
        dict[str, Any]
    ] = []

    for (
        index,
        case,
    ) in enumerate(cases):
        result = service.tag_image(
            source_image,
            captured_at_utc=(
                case["captured_at"]
            ),
            captured_monotonic_ns=(
                1_000_000_000
                + index
            ),
            manual_fix=case["fix"],
            row=case["row"],
            panel=case["panel"],
            camera_metadata={
                "source": (
                    "p2-07-"
                    "representative-image"
                ),
                "sequence_index": (
                    index
                ),
            },
            trigger_metadata={
                "source": (
                    "p2-07-mock-gnss"
                ),
                "case_id": (
                    case["case_id"]
                ),
                "mock_location": (
                    case["location"][0]
                    if case["location"]
                    else None
                ),
            },
        )

        metadata = json.loads(
            result
            .metadata_path
            .read_text(
                encoding="utf-8"
            )
        )

        coordinates = metadata[
            "coordinates"
        ]

        site = metadata[
            "site"
        ]

        actual_warnings = metadata[
            "warnings"
        ]

        expected_timestamp = utc_iso(
            case["captured_at"]
        )

        expected_folder = (
            case["captured_at"]
            .astimezone(
                timezone.utc
            )
            .strftime(
                "%Y/%m/%d"
            )
        )

        checks = {
            "image_exists": (
                result
                .image_path
                .is_file()
            ),
            "metadata_exists": (
                result
                .metadata_path
                .is_file()
            ),
            "image_id_correct": (
                result.image_id.startswith(
                    f"{ROBOT_ID}--"
                    f"{MISSION_ID}--"
                )
            ),
            "timestamp_correct": (
                metadata[
                    "captured_at_utc"
                ]
                == expected_timestamp
                and metadata[
                    "timing"
                ][
                    "captured_at_utc"
                ]
                == expected_timestamp
            ),
            "robot_id_correct": (
                metadata["robot_id"]
                == ROBOT_ID
            ),
            "mission_id_correct": (
                metadata["mission_id"]
                == MISSION_ID
            ),
            "status_correct": (
                metadata["status"]
                == case[
                    "expected_status"
                ]
                and result.status
                == case[
                    "expected_status"
                ]
            ),
            "valid_correct": (
                coordinates["valid"]
                is case[
                    "expected_valid"
                ]
            ),
            "fresh_correct": (
                coordinates["fresh"]
                is case[
                    "expected_fresh"
                ]
            ),
            "quality_correct": (
                coordinates[
                    "quality_accepted"
                ]
                is case[
                    "expected_quality"
                ]
            ),
            "latitude_correct": (
                number_matches(
                    coordinates[
                        "latitude"
                    ],
                    case[
                        "expected_latitude"
                    ],
                )
            ),
            "longitude_correct": (
                number_matches(
                    coordinates[
                        "longitude"
                    ],
                    case[
                        "expected_longitude"
                    ],
                )
            ),
            "row_correct": (
                site["row"]
                == case["row"]
            ),
            "panel_correct": (
                site["panel"]
                == case["panel"]
            ),
            "row_panel_optional": (
                site["required"]
                is False
            ),
            "assignment_correct": (
                site[
                    "assignment_method"
                ]
                == case[
                    "assignment"
                ]
            ),
            "warnings_correct": (
                warnings_match(
                    actual_warnings,
                    case["warnings"],
                )
            ),
            "no_unexpected_warnings": (
                not actual_warnings
                if case[
                    "no_warnings"
                ]
                else True
            ),
            "date_folder_correct": (
                expected_folder
                in result
                .image_path
                .as_posix()
                and expected_folder
                in result
                .metadata_path
                .as_posix()
            ),
            "malformed_nmea_detected": (
                (
                    case[
                        "parser_error"
                    ]
                    == (
                        "NMEA_"
                        "CHECKSUM_INVALID"
                    )
                )
                if (
                    case["case_id"]
                    == "malformed-nmea"
                )
                else True
            ),
            "quarantine_path_correct": (
                (
                    "quarantine/images"
                    in result
                    .image_path
                    .as_posix()
                    and (
                        "quarantine/"
                        "metadata"
                    )
                    in result
                    .metadata_path
                    .as_posix()
                )
                if (
                    case[
                        "expected_status"
                    ]
                    == "quarantined"
                )
                else (
                    "quarantine/"
                    not in result
                    .image_path
                    .as_posix()
                )
            ),
        }

        comparison.append(
            {
                "case_id": (
                    case["case_id"]
                ),
                "mock_location": (
                    case["location"][0]
                    if case["location"]
                    else None
                ),
                "input": {
                    "captured_at_utc": (
                        expected_timestamp
                    ),
                    "latitude": (
                        case["fix"].latitude
                        if case["fix"]
                        else None
                    ),
                    "longitude": (
                        case["fix"].longitude
                        if case["fix"]
                        else None
                    ),
                    "received_at_utc": (
                        utc_iso(
                            case[
                                "fix"
                            ].received_at_utc
                        )
                        if case["fix"]
                        else None
                    ),
                    "satellites": (
                        case[
                            "fix"
                        ].satellites
                        if case["fix"]
                        else None
                    ),
                    "row": (
                        case["row"]
                    ),
                    "panel": (
                        case["panel"]
                    ),
                },
                "expected": {
                    "status": (
                        case[
                            "expected_status"
                        ]
                    ),
                    "valid": (
                        case[
                            "expected_valid"
                        ]
                    ),
                    "fresh": (
                        case[
                            "expected_fresh"
                        ]
                    ),
                    "quality_accepted": (
                        case[
                            "expected_quality"
                        ]
                    ),
                    "latitude": (
                        case[
                            "expected_latitude"
                        ]
                    ),
                    "longitude": (
                        case[
                            "expected_longitude"
                        ]
                    ),
                    "warning_fragments": (
                        list(
                            case[
                                "warnings"
                            ]
                        )
                    ),
                },
                "actual": {
                    "image_id": (
                        result.image_id
                    ),
                    "captured_at_utc": (
                        metadata[
                            "captured_at_utc"
                        ]
                    ),
                    "robot_id": (
                        metadata[
                            "robot_id"
                        ]
                    ),
                    "mission_id": (
                        metadata[
                            "mission_id"
                        ]
                    ),
                    "status": (
                        metadata[
                            "status"
                        ]
                    ),
                    "coordinates": (
                        coordinates
                    ),
                    "site": site,
                    "warnings": (
                        actual_warnings
                    ),
                    "image_path": str(
                        result.image_path
                    ),
                    "metadata_path": str(
                        result.metadata_path
                    ),
                    "parser_error_code": (
                        case[
                            "parser_error"
                        ]
                    ),
                },
                "checks": checks,
                "passed": all(
                    checks.values()
                ),
            }
        )

    manifest_path = (
        output_root
        / "manifests"
        / f"{MISSION_ID}.jsonl"
    )

    manifest = [
        json.loads(line)
        for line
        in manifest_path
        .read_text(
            encoding="utf-8"
        )
        .splitlines()
        if line.strip()
    ]

    image_ids = [
        item["actual"]["image_id"]
        for item in comparison
    ]

    duplicate_timestamp_ids = [
        item["actual"]["image_id"]
        for item in comparison
        if item[
            "case_id"
        ].startswith(
            "duplicate-timestamp-"
        )
    ]

    missing_recovery = next(
        item
        for item in comparison
        if (
            item["case_id"]
            == "recovery-missing"
        )
    )

    global_checks = {
        "all_cases_passed": all(
            item["passed"]
            for item in comparison
        ),
        "all_image_ids_unique": (
            len(image_ids)
            == len(
                set(image_ids)
            )
        ),
        "duplicate_timestamp_"
        "ids_unique": (
            len(
                duplicate_timestamp_ids
            )
            == 2
            and len(
                set(
                    duplicate_timestamp_ids
                )
            )
            == 2
        ),
        "manifest_count_correct": (
            len(manifest)
            == len(cases)
        ),
        "manifest_ids_correct": (
            {
                entry["image_id"]
                for entry in manifest
            }
            == set(image_ids)
        ),
        "all_images_retained": all(
            item[
                "checks"
            ][
                "image_exists"
            ]
            for item in comparison
        ),
        "all_metadata_retained": all(
            item[
                "checks"
            ][
                "metadata_exists"
            ]
            for item in comparison
        ),
        "missing_fix_did_not_"
        "reuse_coordinates": (
            missing_recovery[
                "actual"
            ][
                "coordinates"
            ][
                "latitude"
            ]
            is None
            and missing_recovery[
                "actual"
            ][
                "coordinates"
            ][
                "longitude"
            ]
            is None
        ),
        "row_and_panel_optional": all(
            item[
                "actual"
            ][
                "site"
            ][
                "required"
            ]
            is False
            for item in comparison
        ),
    }

    passed_count = sum(
        item["passed"]
        for item in comparison
    )

    overall_pass = all(
        global_checks.values()
    )

    # Save every predetermined input and
    # expected result.
    write_json(
        output_root
        / "P2-07-test-inputs.json",
        {
            "validation_id": (
                "P2-07"
            ),
            "robot_id": ROBOT_ID,
            "mission_id": (
                MISSION_ID
            ),
            "random_seed": SEED,
            "source_image": str(
                source_image
            ),
            "scenario_count": len(
                cases
            ),
            "cases": [
                {
                    "case_id": (
                        item[
                            "case_id"
                        ]
                    ),
                    "mock_location": (
                        item[
                            "mock_location"
                        ]
                    ),
                    "input": (
                        item["input"]
                    ),
                    "expected": (
                        item[
                            "expected"
                        ]
                    ),
                }
                for item
                in comparison
            ],
        },
    )

    # Save the full comparison.
    write_json(
        output_root
        / "P2-07-comparison.json",
        comparison,
    )

    # Save a spreadsheet-friendly CSV.
    csv_path = (
        output_root
        / "P2-07-comparison.csv"
    )

    with csv_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        fields = [
            "case_id",
            "mock_location",
            "expected_status",
            "actual_status",
            "expected_valid",
            "actual_valid",
            "expected_latitude",
            "actual_latitude",
            "expected_longitude",
            "actual_longitude",
            "image_exists",
            "metadata_exists",
            "warnings",
            "passed",
        ]

        writer = csv.DictWriter(
            file,
            fieldnames=fields,
        )

        writer.writeheader()

        for item in comparison:
            writer.writerow(
                {
                    "case_id": (
                        item[
                            "case_id"
                        ]
                    ),
                    "mock_location": (
                        item[
                            "mock_location"
                        ]
                    ),
                    "expected_status": (
                        item[
                            "expected"
                        ][
                            "status"
                        ]
                    ),
                    "actual_status": (
                        item[
                            "actual"
                        ][
                            "status"
                        ]
                    ),
                    "expected_valid": (
                        item[
                            "expected"
                        ][
                            "valid"
                        ]
                    ),
                    "actual_valid": (
                        item[
                            "actual"
                        ][
                            "coordinates"
                        ][
                            "valid"
                        ]
                    ),
                    "expected_latitude": (
                        item[
                            "expected"
                        ][
                            "latitude"
                        ]
                    ),
                    "actual_latitude": (
                        item[
                            "actual"
                        ][
                            "coordinates"
                        ][
                            "latitude"
                        ]
                    ),
                    "expected_longitude": (
                        item[
                            "expected"
                        ][
                            "longitude"
                        ]
                    ),
                    "actual_longitude": (
                        item[
                            "actual"
                        ][
                            "coordinates"
                        ][
                            "longitude"
                        ]
                    ),
                    "image_exists": (
                        item[
                            "checks"
                        ][
                            "image_exists"
                        ]
                    ),
                    "metadata_exists": (
                        item[
                            "checks"
                        ][
                            "metadata_exists"
                        ]
                    ),
                    "warnings": (
                        " | ".join(
                            item[
                                "actual"
                            ][
                                "warnings"
                            ]
                        )
                    ),
                    "passed": (
                        item[
                            "passed"
                        ]
                    ),
                }
            )

    report = {
        "validation_id": "P2-07",
        "title": (
            "Metadata and "
            "Geotagging Validation"
        ),
        "result": (
            "PASS"
            if overall_pass
            else "FAIL"
        ),
        "passed": overall_pass,
        "executed_at_utc": (
            utc_iso(
                datetime.now(
                    timezone.utc
                )
            )
        ),
        "robot_id": ROBOT_ID,
        "mission_id": MISSION_ID,
        "source_image": str(
            source_image
        ),
        "scenario_count": len(
            cases
        ),
        "passed_scenarios": (
            passed_count
        ),
        "failed_scenarios": (
            len(cases)
            - passed_count
        ),
        "unique_image_ids": len(
            set(image_ids)
        ),
        "manifest_entries": len(
            manifest
        ),
        "global_checks": (
            global_checks
        ),
        "failed_case_ids": [
            item["case_id"]
            for item in comparison
            if not item["passed"]
        ],
        "evidence_files": [
            "P2-07-test-inputs.json",
            "P2-07-comparison.json",
            "P2-07-comparison.csv",
            "P2-07-final-report.json",
            "logs/p2-07.log",
            (
                "manifests/"
                f"{MISSION_ID}.jsonl"
            ),
        ],
    }

    write_json(
        output_root
        / "P2-07-final-report.json",
        report,
    )

    print()

    print(
        "=" * 64
    )

    print(
        "P2-07 METADATA AND "
        "GEOTAGGING VALIDATION"
    )

    print(
        "=" * 64
    )

    print(
        "Result:             "
        f"{report['result']}"
    )

    print(
        "Scenarios:          "
        f"{passed_count}/"
        f"{len(cases)} passed"
    )

    print(
        "Unique image IDs:   "
        f"{len(set(image_ids))}/"
        f"{len(image_ids)}"
    )

    print(
        "Manifest entries:   "
        f"{len(manifest)}/"
        f"{len(cases)}"
    )

    print(
        "Evidence folder:    "
        f"{output_root}"
    )

    print(
        "=" * 64
    )

    return overall_pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run P2-07 using "
            "controlled mock GNSS data."
        )
    )

    parser.add_argument(
        "--image",
        type=Path,
        default=None,
        help=(
            "Representative image to use "
            "for every test case."
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=(
            HERE.parent
            / "ValidationEvidence"
            / "P2-07"
        ),
        help=(
            "Evidence output directory."
        ),
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        image = find_image(
            args.image
        )

        passed = run_validation(
            image,
            args.output
            .expanduser()
            .resolve(),
        )

    except Exception:
        logging.exception(
            "P2-07 validation "
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