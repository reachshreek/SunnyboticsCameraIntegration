# BOM Integration Mapping

## Active Software Interfaces

### LUCID Triton TRI050S-CC

The `lucid` camera adapter uses the LUCID Arena SDK and selects the camera by configured serial number.

It configures:

- Gigabit Ethernet stream packet negotiation
- Packet resend
- Stream buffers
- Bayer input
- Color conversion
- Exposure
- Gain
- Software triggering
- Optional PTP
- Chunk mode

Each frame records available:

- Camera serial number
- Camera model
- Firmware version
- Frame ID
- Camera timestamp
- Exposure
- Gain
- Pixel format
- PTP status

The Arena SDK is not redistributed in this repository.

Install the official ARM64 Ubuntu SDK and Python package on the RUBIK Pi.

The adapter fails with `ARENA_SDK_MISSING` rather than silently falling back to a different camera.

### RUBIK Pi 3

The service is pure Python 3.10+ apart from optional camera SDKs.

It includes a systemd unit intended for native Ubuntu on ARM64.

The RUBIK Pi performs:

- Camera control
- Image capture
- Image validation
- Metadata generation
- Mission-ID recording
- Robot-ID recording
- GNSS matching
- Speed-based capture scheduling
- Local storage
- Health reporting
- Failure logging

The existing configuration-based mission-ID implementation is retained.

A new mission-ID naming format is not required.

Each field mission shall still use a unique and traceable configured mission ID.

### WD Blue SN5000 500GB NVMe

The robot configuration uses `/opt/ssd/sunnybotics` as the data root.

All image, metadata, manifest, recovery, and report writes use the local SSD.

Data files are written using atomic operations and filesystem synchronization where implemented.

Free-space thresholds stop normal capture before the disk reaches the emergency reserve.

The production configuration initially reserves:

- `110 GB` as the normal minimum-free threshold
- `20 GB` as the emergency-free threshold

These values are based on the preliminary maximum-rate mission requirement of approximately `101.25 GB`, including the requirement to finish with 20% free space.

`RequiresMountsFor=/opt/ssd` prevents the system service from writing mission data to the root filesystem when the SSD is not mounted.

### NaviSys GR-U01U

The GNSS reader consumes NMEA 0183 from a USB serial device.

It:

- Reconnects after serial failures
- Stores a bounded fix history
- Decodes latitude and longitude
- Decodes GNSS time
- Records fix quality
- Records satellite count
- Records HDOP
- Decodes speed from RMC records
- Records course when available

The metadata tagger chooses the newest acceptable fix at or before capture time.

A small future tolerance handles clock and serial-arrival jitter.

Complete location metadata additionally requires:

- Valid latitude and longitude ranges
- An acceptable fix age
- An acceptable fix-quality result
- The configured minimum satellite count, when reported
- An acceptable HDOP, when reported

Image capture continues when GNSS is unavailable.

The image is preserved, while its location is marked invalid and the record may be quarantined according to configuration.

### Adaptive Capture Speed Provider

The current software already decodes GNSS speed into `speed_mps`.

The distance-based trigger uses that speed to estimate robot travel.

The initial calculation is:

```text
Along-track camera coverage = 1.62 m
Required overlap = 30%

Capture spacing
= 1.62 m × (1 - 0.30)
= 1.134 m
```

The scheduler accumulates distance using:

```text
Distance increment
= Current speed × Elapsed time
```

A new image is requested when accumulated travel reaches the configured capture spacing.

Initial capture settings are:

| Setting | Value |
|---|---:|
| Along-track coverage | 1.62 m |
| Required overlap | 30% |
| Capture spacing | 1.134 m |
| Speed timeout | 2.5 s |
| Speed polling interval | 0.1 s |
| Fixed fallback interval | 5 s |
| Minimum capture interval | 1 s |
| Minimum movement speed | 0.02 m/s |

The speed provider uses the newest applicable GNSS RMC speed record.

A later GGA position sentence does not refresh the age of the previous RMC speed measurement.

When no valid fresh speed is available, the trigger provider uses the fixed fallback interval.

The speed-provider interface is intentionally independent of the capture scheduler.

A future robot-controller speed provider may be added after the connector, electrical standard, protocol, message identifier, scaling, and update rate are confirmed.

### Mission and Metadata Configuration

The current software continues to obtain `robot_id` and `mission_id` from configuration.

Example:

```json
{
  "robot_id": "sunnybot-01",
  "mission_id": "mission-development"
}
```

The mission ID is included in:

- Every metadata sidecar
- Every mission manifest filename
- Every mission summary filename
- Every generated image ID

Required current project metadata consists of:

- Image ID
- Timestamp
- Robot ID
- Mission ID
- GNSS latitude and longitude when a valid fix is available
- GNSS validity and quality information

Row and panel values remain supported as optional fields for backward compatibility.

They are not required for a record to be complete.

## Passive and Mechanical BOM Items

The following components do not expose a software API, but their configured names are stored in every metadata sidecar for traceability:

- UC080-5M / BL080C 8 mm lens
- Edmund M22.5 polarizer
- LUCID IP67 lens tube
- Tycon PoE injector
- Coolgear CG-PD82HVV USB-C PD converter
- LUCID M12-to-RJ45 cable
- Short shielded Cat6a Ethernet cable
- GNSS receiver
- Power connector
- Fuses
- Power wiring
- Wiring-protection hardware

Software cannot prove:

- Focus
- Polarizer orientation
- Lens-tube sealing
- Cable strain relief
- Input voltage
- Fuse selection
- Connector engagement
- Mount strength
- Final installed mass

Those remain installation and validation checklist items.

## Coolgear Converter Decision

The selected converter is the:

**Coolgear CG-PD82HVV ChargeIT Mini 82 W USB-C PD converter**

It replaces references to the previously considered CG-PD100C.

The selected converter supports the planned robot-input range and the required RUBIK Pi USB-C PD profile.

Coolgear lists the selected CG-PD82HVV at the same nominal item weight as the previously considered CG-PD100C.

The converter change therefore does not increase the converter-weight allowance used in the system weight calculation.

The CG-PD82HVV remains a development product.

Before purchase and installation:

1. Confirm availability.
2. Confirm the current product revision.
3. Confirm the input-voltage range.
4. Confirm the available 12 V / 3 A USB-C PD profile.
5. Confirm connector and cable requirements.
6. Validate the received unit under the expected RUBIK Pi load.

## Network and Power Path

```text
Robot 24 V Power
│
├── Dedicated fused branch
│   │
│   ├── Coolgear CG-PD82HVV
│   │       │
│   │       └── USB-C PD ──> RUBIK Pi 3
│   │
│   └── Tycon TP-DCDC-1248GD-M
│           │
│           └── PoE ──> LUCID Triton
│
└── Existing Robot Loads
```

```text
LUCID Triton
    │
    └── M12 X-coded Cat6a cable
            │
            v
Tycon PoE Injector
            │
            └── Short shielded Cat6a cable
                    │
                    v
                RUBIK Pi 3
```

```text
NaviSys GR-U01U
    │
    └── USB Serial ──> RUBIK Pi 3
                           │
                           ├── Latitude and longitude
                           ├── GNSS time
                           ├── Fix quality
                           ├── Satellite count
                           ├── HDOP
                           └── GNSS speed
```

```text
WD Blue SN5000
    │
    └── M.2 NVMe ──> RUBIK Pi 3
```

## Camera Cable Routing

If the camera is integrated into the same existing external structure as the nozzle, the camera wiring should use the same approved sealed penetration and waterproofing method.

A separate unsealed opening should not be created.

The cable installation should include:

- Connector clearance
- Acceptable cable bend radius
- Strain relief
- Abrasion protection
- Separation from moving parts
- Inspection of the shared penetration after installation

## Commissioning Checklist

1. Record the actual LUCID serial number in configuration.
2. Set a unique mission ID using the existing configuration-based implementation.
3. Confirm the configured robot ID.
4. Confirm Arena discovers the expected camera only.
5. Configure camera and Pi IPv4 addresses on the same dedicated subnet.
6. Enable jumbo frames only after end-to-end validation.
7. Keep automatic packet-size negotiation and packet resend enabled during initial testing.
8. Run `camera-test` repeatedly and verify that no incomplete or truncated images are accepted.
9. Set manual focus, iris, polarizer angle, exposure, and gain from bench data.
10. Verify the NaviSys by-ID serial path.
11. Verify the NMEA baud rate.
12. Confirm that valid RMC records include speed.
13. Confirm that stale speed activates fixed-rate fallback.
14. Measure the installed nearest and farthest usable panel points.
15. Update `capture.along_track_coverage_m` using the measured coverage.
16. Confirm that the calculated capture spacing preserves at least 30% overlap.
17. Confirm `/opt/ssd` is mounted before service start.
18. Confirm at least the configured free-space reserve is available.
19. Inspect the final cable route and strain relief.
20. Run the preflight health check.
21. Run a controlled adaptive-capture test.
22. Run a controlled fixed-fallback test.
23. Weigh the complete installed system and confirm that it is less than 1.00 kg.