# Operations Guide

## Mission-ID Behavior

The existing mission-ID implementation is retained.

The mission ID continues to be supplied through the system configuration:

```json
{
  "mission_id": "mission-development"
}
```

A new mission-ID naming format is not required.

Before each actual field mission:

- Replace the previous mission ID with a unique and traceable value.
- Do not reuse a mission ID for a separate field run.
- Confirm that the configured value is no more than 64 characters.
- Use only letters, numbers, periods, underscores, and hyphens.

## Before Each Mission

1. Set a unique `mission_id` using the existing configuration-based mission-ID implementation.
2. Confirm the correct `robot_id`.
3. Confirm the correct LUCID serial number.
4. Confirm the SSD path.
5. Confirm the configured along-track coverage.
6. Confirm the required overlap.
7. Confirm the fixed fallback interval.
8. Confirm the speed timeout.
9. Inspect:
   - Robot power connection
   - Fuse
   - Coolgear converter
   - PoE injector
   - Ethernet cables
   - USB GNSS connection
   - Camera lens tube
   - Polarizer
   - Camera mount
   - Cable routing
   - Cable strain relief
10. Confirm that the SSD is mounted:

```bash
mountpoint /opt/ssd
```

11. Confirm available storage:

```bash
df -h /opt/ssd
```

12. Run configuration validation:

```bash
solar-tagger validate-config \
  --config /etc/solar-tagger/config.json
```

13. Run the health check:

```bash
solar-tagger health-check \
  --config /etc/solar-tagger/config.json
```

14. Test the camera:

```bash
solar-tagger camera-test \
  --config /etc/solar-tagger/config.json
```

15. Monitor GNSS output:

```bash
solar-tagger gnss-monitor \
  --config /etc/solar-tagger/config.json \
  --seconds 30
```

16. Confirm:
   - The camera image is sharp.
   - Exposure is acceptable.
   - Glare is acceptable.
   - A valid GNSS coordinate is received.
   - GNSS speed appears when the receiver is moving.
   - The mission ID is correct.
   - The robot ID is correct.

17. Start the service:

```bash
sudo systemctl start solar-capture.service
```

18. Confirm service status:

```bash
sudo systemctl status solar-capture.service
```

19. Inspect the current service log:

```bash
journalctl \
  -u solar-capture.service \
  -n 100 \
  --no-pager
```

20. Inspect:

```text
/opt/ssd/sunnybotics/health/status.json
```

## Adaptive Capture Operation

The production configuration uses `distance` trigger mode.

The initial values are:

| Setting | Value |
|---|---:|
| Along-track coverage | 1.62 m |
| Required overlap | 30% |
| Capture spacing | 1.134 m |
| Speed timeout | 2.5 s |
| Fixed fallback interval | 5 s |
| Minimum capture interval | 1 s |
| Minimum movement speed | 0.02 m/s |

The scheduler estimates travel using:

```text
Distance increment
= Speed × Elapsed time
```

A new image is requested when the accumulated travel reaches the capture spacing.

The initial capture spacing is:

```text
1.62 m × 0.70 = 1.134 m
```

The initial production speed source is GNSS speed from NMEA RMC records.

When the speed sample is missing or older than the configured timeout, the service uses the fixed fallback interval.

When valid speed returns, later captures return to distance-based scheduling automatically.

## During a Mission

- The service reads GNSS data continuously.
- The service uses valid GNSS speed to estimate distance traveled.
- The service captures when estimated travel reaches the configured capture spacing.
- The service does not generate repeated distance captures while speed remains below the configured movement threshold.
- The service uses the fixed-rate fallback when speed is unavailable or stale.
- The service continues image capture when the internet connection is unavailable.
- The service continues preserving images when GNSS is unavailable.
- Missing or invalid GNSS data is clearly marked.
- Missing row or panel values do not affect required metadata completeness.
- Complete records go to `images/` and `metadata/`.
- Incomplete required records go to `quarantine/` and remain visible in the manifest.
- Logs are written as structured JSON lines in `logs/tagger.jsonl`.

Each distance-triggered metadata record includes available:

- `capture_mode`
- `speed_source`
- `speed_mps`
- `speed_sample_age_s`
- `capture_spacing_m`
- `required_overlap_fraction`
- `estimated_distance_since_previous_capture_m`

The initial image after service startup is recorded with:

```text
capture_mode = distance-initial
```

A normal adaptive capture is recorded with:

```text
capture_mode = distance
```

A fallback capture is recorded with:

```text
capture_mode = fixed-rate-fallback
```

## Monitoring During a Mission

Follow the service log:

```bash
journalctl \
  -u solar-capture.service \
  -f
```

Inspect recent structured application logs:

```bash
tail -n 100 \
  /opt/ssd/sunnybotics/logs/tagger.jsonl
```

Check available storage:

```bash
df -h /opt/ssd
```

Check mission image counts:

```bash
find \
  /opt/ssd/sunnybotics/images \
  -type f \
  | wc -l
```

Check quarantined image counts:

```bash
find \
  /opt/ssd/sunnybotics/quarantine/images \
  -type f \
  2>/dev/null \
  | wc -l
```

Do not manually delete mission images while the capture service is running.

## After a Mission

Stop the capture service:

```bash
sudo systemctl stop solar-capture.service
```

Generate the mission summary:

```bash
solar-tagger mission-summary \
  --config /etc/solar-tagger/config.json
```

Review:

- Mission summary
- Mission manifest
- Image count
- Metadata count
- Quarantine count
- Capture failures
- Tagging failures
- Camera warnings
- GNSS warnings
- Speed-source warnings
- Fallback events
- Storage warnings
- Post-mission physical condition
- Camera alignment
- Cable strain relief
- Available SSD space

The metadata-completeness result is calculated from the manifest rather than estimated manually.

Confirm that all images and metadata are readable before disconnecting or removing the SSD.

## Optional File-Trigger Operation

The original file-trigger interface remains supported.

To use it, configure:

```json
{
  "capture": {
    "trigger_mode": "file"
  }
}
```

A basic trigger file can contain:

```json
{
  "trigger_id": "mission-point-0087",
  "requested_at_utc": "2026-07-16T19:25:00Z",
  "mission_point_id": "point-0087"
}
```

Optional row and panel values may still be supplied:

```json
{
  "trigger_id": "mission-point-0087",
  "requested_at_utc": "2026-07-16T19:25:00Z",
  "mission_point_id": "point-0087",
  "row": "A",
  "panel": "017"
}
```

Row and panel are not required.

File triggers move through:

```text
incoming
    ↓
processing
    ↓
processed or failed
```

## Recovery Behavior

- Image copies use temporary files and atomic rename.
- Metadata sidecars use temporary files and atomic rename.
- Trigger-result files use temporary files and atomic rename.
- If an image is preserved but metadata commit fails, a recovery record is written under `recovery/`.
- Invalid images are not silently deleted.
- Invalid images are quarantined with their decode error.
- Low storage returns a machine-readable error.
- Normal capture stops before the emergency storage reserve is exhausted.
- The GNSS reader reconnects after serial failures.
- Missing speed activates fixed-rate fallback.
- Stale speed activates fixed-rate fallback.
- Valid speed recovery returns the scheduler to distance-based operation.
- Camera recovery closes and reopens the configured camera source after a transient capture failure.

## Common Errors

- `ARENA_SDK_MISSING`: Install the LUCID ARM64 Arena SDK and Python package.
- `CAMERA_NOT_FOUND`: Check PoE, cables, subnet, firewall, configured serial number, and camera IP.
- `GNSS_DEVICE_NOT_FOUND`: Check USB and `/dev/serial/by-id`; confirm that the service user belongs to `dialout`.
- `GNSS_NO_ACCEPTABLE_FIX`: Improve sky view or adjust validated GNSS thresholds.
- `GNSS_SERIAL_ERROR`: Check the device path, baud rate, USB connection, and permissions.
- `STORAGE_LOW`: Offload data or mount the intended NVMe SSD.
- `IMAGE_INVALID`: Inspect camera output, image format, transfer integrity, and storage.
- `CAMERA_SOURCE_EXHAUSTED`: The simulated image directory finished and looping is disabled.
- `CONFIG_INVALID`: Inspect the named configuration field and value.
- `CONFIG_NOT_FOUND`: Confirm the configuration-file path.
- `LAYOUT_NOT_FOUND`: A layout file was explicitly configured but could not be found. Set `layout_file` to `null` when row/panel layout assignment is not being used.

## Fixed-Rate Fallback Check

To verify fallback behavior:

1. Start the production service with distance triggering enabled.
2. Prevent valid speed records from reaching the speed provider.
3. Confirm that the initial image is captured.
4. Confirm that later images are generated approximately every 5 seconds.
5. Inspect metadata and confirm:

```text
capture_mode = fixed-rate-fallback
```

6. Restore valid speed data.
7. Confirm that later triggers return to:

```text
capture_mode = distance
```

## Mission-ID Check

Before enabling a field mission:

```bash
python - <<'PY'
import json

path = "/etc/solar-tagger/config.json"

with open(path, "r", encoding="utf-8") as handle:
    config = json.load(handle)

print("robot_id:", config["robot_id"])
print("mission_id:", config["mission_id"])
PY
```

Confirm that the displayed mission ID is correct and has not been used for another field run.