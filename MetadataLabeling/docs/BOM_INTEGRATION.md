# BOM Integration Mapping

## Active software interfaces

### LUCID Triton TRI050S-CC

The `lucid` camera adapter uses LUCID Arena SDK and selects the camera by configured serial number. It configures GigE stream packet negotiation/resend, stream buffers, Bayer input, color conversion, exposure, gain, software triggering, optional PTP, and chunk mode. Each frame records available camera serial, model, firmware, frame ID, camera timestamp, exposure, gain, pixel format, and PTP status.

The Arena SDK is not redistributed in this repository. Install the official ARM64 Ubuntu SDK and Python package on the RUBIK Pi. The adapter fails with `ARENA_SDK_MISSING` rather than silently falling back to a different camera.

### RUBIK Pi 3

The service is pure Python 3.10+ apart from optional camera SDKs. It includes a systemd unit intended for native Ubuntu on ARM64. Health records include machine architecture, host name, process state, camera state, GNSS state, and storage usage.

### WD Blue SN5000 500GB NVMe

Robot configuration uses `/opt/ssd/sunnybotics` as the data root. All writes are atomic and data files are fsynced. Free-space thresholds stop capture before the disk is exhausted. `RequiresMountsFor=/opt/ssd` prevents the system service from writing mission data to the root filesystem when the SSD is not mounted.

### NaviSys GR-U01U

The GNSS reader consumes NMEA 0183 from a USB serial device, reconnects after errors, and stores a bounded fix history. The tagger chooses the newest fix at or before capture time; a small future tolerance handles clock/arrival jitter. Complete metadata additionally requires valid ranges and configurable fix quality, satellite count, HDOP, and age.

## Passive/mechanical BOM items

The following components do not expose a software API, but their exact configured names are stored in every metadata sidecar for traceability:

- UC080-5M / BL080C 8 mm lens;
- Edmund M22.5 polarizer;
- LUCID IP67 lens tube;
- Tycon PoE injector;
- Coolgear USB-C PD converter;
- LUCID M12-to-RJ45 and short shielded Cat6a cables.

Software cannot prove focus, polarizer orientation, sealing, cable strain relief, input voltage, or fuse selection. Those remain installation and validation checklist items.

## Network path

```text
Robot 24 V
├── Coolgear CG-PD82HVV ──USB-C PD──> RUBIK Pi 3
└── Tycon TP-DCDC-1248GD-M ──PoE──> LUCID Triton

LUCID M12 X-coded ──Cat6a/RJ45──> Tycon data/PoE path ──Cat6a──> RUBIK Pi Gigabit Ethernet
NaviSys GR-U01U ──USB serial──> RUBIK Pi
WD Blue SN5000 ──M.2 NVMe──> RUBIK Pi
```

## Commissioning checklist

1. Record the actual LUCID serial number in configuration.
2. Confirm Arena discovers the expected camera only.
3. Configure camera and Pi IPv4 addresses on the same dedicated subnet.
4. Enable jumbo frames only after end-to-end validation; auto packet size and packet resend remain enabled.
5. Run `camera-test` repeatedly and verify no incomplete/truncated images.
6. Set manual focus, iris, polarizer angle, exposure, and gain from bench data.
7. Verify NaviSys by-id path and NMEA baud rate.
8. Replace example GeoJSON with surveyed panel polygons.
9. Confirm `/opt/ssd` is mounted before service start.
10. Run a preflight health check, then a controlled mission-point trigger test.
