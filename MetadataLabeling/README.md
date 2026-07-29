# Metadata Labeler

Production-oriented Python software for capturing solar-panel images, matching them to GNSS fixes, recording robot and mission identifiers, and storing durable metadata on the robot.

Optional row and panel support remains available for backward compatibility, but those values are not required by the current project baseline.

The package can be developed before the final camera arrives and then switched to the BOM hardware by changing configuration:

- `directory`: deterministic simulated-image source, including the bundled `sample_images/`
- `opencv`: ordinary USB webcam for bench work
- `lucid`: LUCID Arena SDK adapter for the Triton TRI050S-CC on the RUBIK Pi 3

## What it provides

For every capture, the system creates:

- Globally unique `image_id`
- UTC capture time and monotonic clock reading
- Capture-time-matched GNSS coordinates and fix-quality details
- Configured `robot_id`
- Existing configured `mission_id`
- Optional backward-compatible row, panel, and mission-point information
- Capture mode, speed source, speed value, speed age, and capture spacing
- LUCID camera serial, exposure, gain, frame ID, camera timestamp, pixel format, and PTP state when exposed by Arena SDK
- Image dimensions, decode validation, byte size, and SHA-256
- BOM hardware identifiers and software/host information
- Atomic image and sidecar storage
- Append-only mission manifest
- Recovery records
- Rotating JSON logs

An image cannot be marked `complete` when its image bytes are invalid, coordinates are non-finite or out of range, the GNSS fix is stale, or configured GNSS quality limits are not met.

Incomplete records are preserved in quarantine rather than silently dropped.

## Mission ID decision

The existing mission-ID implementation is intentionally retained.

The mission ID continues to come from configuration:

```json
{
  "mission_id": "mission-development"
}
```

The project does not require a new mission-ID naming format.

Before an actual mission, replace the configured value with a unique and traceable mission ID.

Do not reuse the same mission ID for a separate field run.

## Required metadata

The current required metadata fields are:

- `image_id`
- Capture timestamp
- `robot_id`
- `mission_id`
- Latitude and longitude when a valid GNSS fix is available
- GNSS validity and quality information

Row and panel are optional.

The software can still accept and store row and panel values for backward compatibility, but their absence does not make an otherwise valid record incomplete.

## Adaptive capture

The production configuration supports distance-based capture.

The RUBIK Pi uses current speed and the configured along-track image coverage to estimate distance traveled.

The initial settings are:

| Parameter | Initial value |
|---|---:|
| Along-track image coverage | 1.62 m |
| Required overlap | 30% |
| Capture spacing | 1.134 m |
| Speed timeout | 2.5 s |
| Fixed fallback interval | 5 s |
| Minimum capture interval | 1 s |
| Maximum configured capture rate | 1 image/s |
| Minimum speed treated as movement | 0.02 m/s |

The capture spacing is calculated as:

```text
Capture spacing
= Along-track coverage × (1 - Required overlap)

Capture spacing
= 1.62 m × (1 - 0.30)

Capture spacing
= 1.134 m
```

When a valid speed is available:

```text
Capture rate
= Robot speed ÷ Capture spacing
```

The scheduler estimates distance traveled using:

```text
Distance increment
= Current speed × Elapsed time
```

An image is requested whenever the accumulated distance reaches the configured capture spacing.

The current implementation uses GNSS speed decoded from NMEA RMC data.

When speed is missing or stale, the service uses the fixed fallback of one image every 5 seconds.

A future robot-controller speed provider can use the same software interface after the robot communication connection is documented.

## Output layout

```text
<storage-root>/
├── images/YYYY/MM/DD/<image_id>.<ext>
├── metadata/YYYY/MM/DD/<image_id>.json
├── quarantine/
│   ├── images/YYYY/MM/DD/<image_id>.<ext>
│   └── metadata/YYYY/MM/DD/<image_id>.json
├── manifests/<mission_id>.jsonl
├── reports/<mission_id>-summary.json
├── health/status.json
├── health/preflight.json
├── recovery/<image_id>.json
├── logs/tagger.jsonl
├── spool/
└── triggers/{incoming,processing,processed,failed}/
```

## Quick start with simulated images

```bash
cd MetadataLabeling

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

pytest

solar-tagger validate-config \
  --config config/example_config.json

solar-tagger camera-test \
  --config config/example_config.json
```

## Tag one bundled frame

```bash
solar-tagger tag \
  --config config/example_config.json \
  --image sample_images/sample_panel_01.png \
  --latitude 37.000005 \
  --longitude -121.000010 \
  --altitude-m 12.4 \
  --satellites 12 \
  --hdop 0.8
```

Optional backward-compatible row and panel values may still be supplied:

```bash
solar-tagger tag \
  --config config/example_config.json \
  --image sample_images/sample_panel_01.png \
  --latitude 37.000005 \
  --longitude -121.000010 \
  --row A \
  --panel 001
```

They are not required for current metadata completeness.

## Run one simulated unattended capture

```bash
solar-tagger run-service \
  --config config/example_config.json

solar-tagger mission-summary \
  --config config/example_config.json
```

Because the development configuration has GNSS disabled, an unattended simulated frame is intentionally quarantined unless location is supplied through another integration.

This demonstrates safe failure rather than creating false complete metadata.

## USB webcam bench mode

```bash
python -m pip install -e ".[webcam,dev]"

solar-tagger camera-test \
  --config config/usb_webcam_config.json

solar-tagger run-service \
  --config config/usb_webcam_config.json
```

## NaviSys GR-U01U GNSS test

```bash
solar-tagger gnss-monitor \
  --config config/usb_webcam_config.json \
  --seconds 30
```

The reader prefers stable paths in `/dev/serial/by-id/`, then checks `/dev/ttyACM*` and `/dev/ttyUSB*`.

Set an explicit by-ID path in the robot configuration after the receiver is connected.

The adaptive scheduler uses speed from valid NMEA RMC records.

A later GGA position record does not refresh the RMC speed timestamp.

## Distance-trigger production mode

The production configuration uses:

```json
{
  "capture": {
    "trigger_mode": "distance",
    "along_track_coverage_m": 1.62,
    "required_overlap_fraction": 0.30,
    "speed_timeout_s": 2.5,
    "speed_poll_s": 0.1,
    "fallback_interval_s": 5.0,
    "min_capture_interval_s": 1.0,
    "min_moving_speed_mps": 0.02
  }
}
```

The initial `1.62 m` coverage is a design value.

Replace it with the measured installed coverage after the final camera position and angle are verified.

## Optional mission-point trigger interface

The existing file-trigger interface remains available.

Configure `capture.trigger_mode` as `file`, then atomically place JSON into the trigger `incoming/` directory:

```json
{
  "trigger_id": "mission-42-point-0087",
  "requested_at_utc": "2026-07-16T19:25:00Z",
  "mission_point_id": "point-0087"
}
```

Optional row and panel values are still accepted:

```json
{
  "trigger_id": "mission-42-point-0087",
  "requested_at_utc": "2026-07-16T19:25:00Z",
  "mission_point_id": "point-0087",
  "row": "A",
  "panel": "017"
}
```

The trigger moves through `incoming`, `processing`, and then `processed` or `failed`, with the result or machine-readable error attached.

## LUCID Triton on RUBIK Pi 3

1. Install Ubuntu and mount the WD Blue SN5000 at `/opt/ssd`.
2. Install the ARM64 Arena SDK and its `arena_api` Python package from LUCID.
3. Connect the Triton through the Tycon PoE injector and Gigabit Ethernet path.
4. Copy `config/rubik_pi_lucid_config.json` to `/etc/solar-tagger/config.json`.
5. Replace the mission ID and camera serial number.
6. Confirm the GNSS serial-device path.
7. Run the health and camera tests before enabling the service.
8. Measure the installed along-track camera coverage and update `along_track_coverage_m`.

See:

- `docs/BOM_INTEGRATION.md`
- `docs/RUBIK_PI_DEPLOYMENT.md`
- `docs/OPERATIONS.md`
- `deploy/systemd/solar-capture.service`

## Key commands

```text
validate-config   Validate and summarize all settings
camera-test       Open the configured source and capture a frame
gnss-monitor      Stream decoded NaviSys fixes
tag               Tag an existing image
run-service       Run unattended capture and tagging
health-check      Check storage, camera, and GNSS visibility
create-trigger    Request a file-triggered mission capture
mission-summary   Calculate metadata-completeness statistics
```

## Important field-test limits

The LUCID adapter follows the Arena SDK integration boundary and is prepared for ARM64 deployment, but it still must be tested with the actual camera, firmware, network, PoE injector, NaviSys receiver, SSD, and final mounting geometry.

The following values remain commissioning values:

- Exposure
- Gain
- Focus
- Iris
- Polarizer angle
- Shutter speed
- GNSS quality thresholds
- Actual image size
- Actual along-track image coverage
- Speed timeout
- Minimum movement speed
- Capture spacing
- Trigger timing

The existing mission-ID behavior is not a commissioning value and should remain unchanged unless a separate project requirement calls for a new format.