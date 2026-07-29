# RUBIK Pi 3 Deployment

## Recommended Filesystem Layout

```text
/opt/solar-metadata-tagger/       Application and virtual environment
/opt/ssd/                         WD Blue SN5000 mount point
/opt/ssd/sunnybotics/             Mission data
/etc/solar-tagger/config.json     Robot configuration
```

A site-layout file is optional.

It is only needed when optional row and panel assignment from surveyed polygons is deliberately enabled.

The production GNSS-only metadata configuration uses:

```json
{
  "layout_file": null
}
```

## SSD Mounting

The NVMe SSD may require explicit mounting.

Add the SSD to `/etc/fstab` using its UUID and verify the mount before enabling the service.

List disks:

```bash
lsblk -f
```

Find the SSD UUID:

```bash
sudo blkid
```

Create the mount point:

```bash
sudo mkdir -p /opt/ssd
```

Verify the final configuration:

```bash
mountpoint /opt/ssd
df -h /opt/ssd
```

The systemd service uses `RequiresMountsFor=/opt/ssd`.

This prevents mission files from being written to the RUBIK Pi root filesystem when the intended SSD is unavailable.

## Install

The included installer creates:

- The `solarbot` service account
- The application directory
- The Python virtual environment
- The configuration directory
- The mission-data directory
- The systemd unit

It intentionally does not partition or format the SSD.

From the `MetadataLabeling` directory:

```bash
sudo deploy/scripts/install_rubik_pi.sh
```

## LUCID Arena SDK

Install the LUCID Arena SDK separately.

The SDK is not redistributed in this repository.

Ensure that `arena_api` imports inside the service virtual environment:

```bash
sudo -u solarbot \
  /opt/solar-metadata-tagger/.venv/bin/python \
  -c 'import arena_api; print("Arena OK")'
```

A failed import must be corrected before enabling the production capture service.

## Production Configuration

The installer copies the production template to:

```text
/etc/solar-tagger/config.json
```

The installer does not overwrite an existing configuration file.

After installation, edit the configuration:

```bash
sudo nano /etc/solar-tagger/config.json
```

At minimum, confirm:

- `robot_id`
- `mission_id`
- LUCID camera serial number
- GNSS serial-device path
- SSD path
- Along-track image coverage
- Required overlap
- Speed timeout
- Fallback interval
- Minimum capture interval
- Minimum movement speed
- Storage thresholds

The existing mission-ID implementation remains configuration based.

Do not introduce a separate mission-ID generator unless a later project requirement explicitly calls for one.

## Initial Production Capture Settings

The template contains:

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

These produce an initial spacing of:

```text
1.62 m × 0.70 = 1.134 m
```

The `1.62 m` coverage is preliminary.

After mounting the camera:

1. Measure the nearest usable panel point.
2. Measure the farthest usable panel point.
3. Subtract the nearest distance from the farthest distance.
4. Set the result as `along_track_coverage_m`.
5. Keep `required_overlap_fraction` at `0.30` unless the requirement is formally changed.

## Validate the Configuration

Run:

```bash
sudo -u solarbot \
  /opt/solar-metadata-tagger/.venv/bin/solar-tagger \
  validate-config \
  --config /etc/solar-tagger/config.json
```

Run the preflight check:

```bash
sudo -u solarbot \
  /opt/solar-metadata-tagger/.venv/bin/solar-tagger \
  health-check \
  --config /etc/solar-tagger/config.json
```

Run a camera test:

```bash
sudo -u solarbot \
  /opt/solar-metadata-tagger/.venv/bin/solar-tagger \
  camera-test \
  --config /etc/solar-tagger/config.json
```

Monitor GNSS:

```bash
sudo -u solarbot \
  /opt/solar-metadata-tagger/.venv/bin/solar-tagger \
  gnss-monitor \
  --config /etc/solar-tagger/config.json \
  --seconds 30
```

## Enable the Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now solar-capture.service
sudo systemctl status solar-capture.service
```

Follow logs:

```bash
journalctl \
  -u solar-capture.service \
  -f
```

## Permissions

The `solarbot` account needs:

- Read/write access to `/opt/ssd/sunnybotics`
- Membership in `dialout` for the NaviSys serial device
- Network access to the dedicated Gigabit Ethernet camera interface
- Read access to Arena SDK libraries
- Execute access to Arena SDK dependencies
- Read access to `/etc/solar-tagger/config.json`

Confirm group membership:

```bash
id solarbot
```

Confirm mission-data permissions:

```bash
sudo -u solarbot \
  test -w /opt/ssd/sunnybotics
```

Confirm configuration access:

```bash
sudo -u solarbot \
  test -r /etc/solar-tagger/config.json
```

Avoid running the capture service as root.

## Updating the Application

Stop the service before updating:

```bash
sudo systemctl stop solar-capture.service
```

From the updated source checkout:

```bash
sudo deploy/scripts/install_rubik_pi.sh
```

The installer preserves an existing `/etc/solar-tagger/config.json`.

Compare the preserved configuration with the new template after software changes:

```bash
diff \
  -u \
  /etc/solar-tagger/config.json \
  /opt/solar-metadata-tagger/config/rubik_pi_lucid_config.json
```

Manually add newly required configuration fields when appropriate.

Validate the final configuration before restarting:

```bash
sudo -u solarbot \
  /opt/solar-metadata-tagger/.venv/bin/solar-tagger \
  validate-config \
  --config /etc/solar-tagger/config.json
```

Restart:

```bash
sudo systemctl restart solar-capture.service
```

## Deployment Acceptance Checks

Before field operation, confirm:

- The SSD is mounted at `/opt/ssd`.
- The service is writing to `/opt/ssd/sunnybotics`.
- The Arena SDK imports successfully.
- The expected LUCID camera is discovered.
- The camera serial number matches configuration.
- The GNSS receiver is visible.
- GNSS position data is decoded.
- GNSS RMC speed is decoded when moving.
- The configured mission ID is unique.
- The configured robot ID is correct.
- Row and panel are not required.
- The distance trigger produces adaptive captures.
- Missing speed produces fixed-rate fallback captures.
- Stored metadata records capture mode and speed information.
- The installed camera coverage is measured and entered into configuration.
- The complete installed system weighs less than 1.00 kg.