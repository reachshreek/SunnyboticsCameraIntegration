# Metadata Labeler

Production-oriented Python software for capturing solar-panel images, matching them to GNSS fixes, assigning row/panel identifiers, and storing durable metadata on the robot.

The package can be developed before the final camera arrives and then switched to the BOM hardware by changing configuration:

- `directory`: deterministic simulated-image source, including the bundled `sample_images/`;
- `opencv`: ordinary USB webcam for bench work;
- `lucid`: LUCID Arena SDK adapter for the Triton TRI050S-CC on the RUBIK Pi 3.

## What it provides

For every capture, the system creates:

- globally unique `image_id`;
- UTC capture time and monotonic clock reading;
- capture-time-matched GNSS coordinates and fix-quality details;
- `robot_id`, `mission_id`, row, panel, and mission-point trigger information;
- LUCID camera serial, exposure, gain, frame ID, camera timestamp, pixel format, and PTP state when exposed by Arena SDK;
- image dimensions, decode validation, byte size, and SHA-256;
- BOM hardware identifiers and software/host information;
- atomic image/sidecar storage, append-only mission manifest, recovery records, and rotating JSON logs.

An image cannot be marked `complete` when its image bytes are invalid, coordinates are non-finite/out of range, the GNSS fix is stale, or configured GNSS quality limits are not met. Incomplete records are preserved in quarantine rather than silently dropped.

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
cd solar_metadata_tagger
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
pytest

solar-tagger validate-config --config config/example_config.json
solar-tagger camera-test --config config/example_config.json
```

Tag one bundled frame with complete manual metadata:

```bash
solar-tagger tag \
  --config config/example_config.json \
  --image sample_images/sample_panel_01.png \
  --latitude 37.000005 \
  --longitude -121.000010 \
  --altitude-m 12.4 \
  --satellites 12 \
  --hdop 0.8 \
  --row A \
  --panel 001
```

Run one simulated unattended capture:

```bash
solar-tagger run-service --config config/example_config.json
solar-tagger mission-summary --config config/example_config.json
```

Because the development config has GNSS disabled, an unattended simulated frame is intentionally quarantined unless the layout/location is supplied through another integration. This demonstrates safe failure rather than creating false complete metadata.

## USB webcam bench mode

```bash
python -m pip install -e ".[webcam,dev]"
solar-tagger camera-test --config config/usb_webcam_config.json
solar-tagger run-service --config config/usb_webcam_config.json
```

## NaviSys GR-U01U GNSS test

```bash
solar-tagger gnss-monitor \
  --config config/usb_webcam_config.json \
  --seconds 30
```

The reader prefers stable paths in `/dev/serial/by-id/`, then checks `/dev/ttyACM*` and `/dev/ttyUSB*`. Set an explicit by-id path in the robot configuration after the receiver is connected.

## Mission-point trigger interface

The robot mission controller can request a capture without importing Python. Configure `capture.trigger_mode` as `file`, then atomically place JSON into the trigger `incoming/` directory:

```json
{
  "trigger_id": "mission-42-point-0087",
  "requested_at_utc": "2026-07-16T19:25:00Z",
  "mission_point_id": "point-0087",
  "row": "A",
  "panel": "017"
}
```

A helper command is included:

```bash
solar-tagger create-trigger \
  --config /etc/solar-tagger/config.json \
  --trigger-id mission-42-point-0087 \
  --mission-point-id point-0087 \
  --row A \
  --panel 017
```

The trigger moves through `incoming`, `processing`, and then `processed` or `failed`, with the result or machine-readable error attached. This provides an auditable boundary to the robot mission software.

## LUCID Triton on RUBIK Pi 3

1. Install Ubuntu and mount the WD Blue SN5000 at `/opt/ssd`.
2. Install the ARM64 Arena SDK and its `arena_api` Python package from LUCID.
3. Connect the Triton through the Tycon PoE injector and Gigabit Ethernet path.
4. Copy `config/rubik_pi_lucid_config.json` to `/etc/solar-tagger/config.json`.
5. Replace the mission ID, camera serial, and site-layout path.
6. Run `solar-tagger health-check` and `solar-tagger camera-test` before enabling the service.

See:

- `docs/BOM_INTEGRATION.md`
- `docs/RUBIK_PI_DEPLOYMENT.md`
- `docs/OPERATIONS.md`
- `deploy/systemd/solar-capture.service`

## Key commands

```text
validate-config  Validate and summarize all settings
camera-test      Open the configured source and capture a frame
GNSS-monitor     Stream decoded NaviSys fixes
tag               Tag an existing image
run-service       Run unattended capture and tagging
health-check      Check storage, camera, and GNSS visibility
create-trigger    Request a file-triggered mission capture
mission-summary   Calculate metadata-completeness statistics
```

## Important field-test limits

The LUCID adapter follows the Arena SDK integration boundary and is ready for ARM64 deployment, but it still must be tested with the actual camera, firmware, network, PoE injector, NaviSys receiver, and final mounting geometry. Exposure, polarizer angle, focus, shutter speed, GNSS thresholds, site polygons, and trigger timing are commissioning values, not universal defaults.
