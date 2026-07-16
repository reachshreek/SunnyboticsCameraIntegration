# Operations Guide

## Before each mission

1. Create a unique `mission_id`; never reuse one for a separate field run.
2. Confirm the correct robot ID, LUCID serial, site layout, and SSD path.
3. Inspect power, PoE, Ethernet, USB GNSS, lens tube, polarizer, and mount.
4. Run:

```bash
solar-tagger validate-config --config /etc/solar-tagger/config.json
solar-tagger health-check --config /etc/solar-tagger/config.json
solar-tagger camera-test --config /etc/solar-tagger/config.json
solar-tagger gnss-monitor --config /etc/solar-tagger/config.json --seconds 30
```

5. Confirm camera-test image sharpness/exposure and a valid GNSS fix.
6. Start the service and inspect `health/status.json`.

## During a mission

- Robot software creates mission-point trigger JSON files.
- The service captures one image per accepted trigger.
- Complete records go to `images/` and `metadata/`.
- Missing/invalid records go to `quarantine/` and remain visible in the manifest.
- Trigger outcomes are written to `triggers/processed/` or `triggers/failed/`.
- Logs are structured JSON lines in `logs/tagger.jsonl`.

## After a mission

```bash
solar-tagger mission-summary --config /etc/solar-tagger/config.json
sudo systemctl stop solar-capture.service
```

Review the report, quarantine, failed triggers, camera/GNSS warnings, and the post-mission physical inspection. The metadata goal is computed from the manifest rather than estimated manually.

## Recovery behavior

- Image copy, sidecar writes, and trigger result writes use temporary files plus atomic rename.
- If the image is preserved but metadata commit fails, a record is written under `recovery/`.
- Invalid images are not deleted; they are quarantined with their decode error.
- Low storage returns a machine-readable error and stops normal capture before emergency exhaustion.
- The GNSS reader reconnects after serial failures and exposes its latest error in health status.

## Common errors

- `ARENA_SDK_MISSING`: install the LUCID ARM64 Arena SDK/Python package.
- `CAMERA_NOT_FOUND`: check PoE, cables, subnet, firewall, and camera IP.
- `GNSS_DEVICE_NOT_FOUND`: check USB and `/dev/serial/by-id`; add the service user to `dialout`.
- `GNSS_NO_ACCEPTABLE_FIX`: improve sky view or adjust thresholds only with validation evidence.
- `STORAGE_LOW`: offload data or install/mount the intended NVMe SSD.
- `LAYOUT_NOT_FOUND`: deploy the surveyed site GeoJSON.
- `CAMERA_SOURCE_EXHAUSTED`: simulated directory finished and looping is disabled.
