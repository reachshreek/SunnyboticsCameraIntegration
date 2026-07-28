# Robotic Baseline

## Battery

The robot battery has the following reported characteristics:

| Parameter | Value |
|---|---:|
| Cell configuration | 7s6p |
| Cell type | 18650 lithium-ion |
| Individual cell capacity | 3200 mAh |
| Nominal battery capacity | 19.2 Ah |
| Nominal battery voltage | 25.2 V |
| Estimated battery energy | 484 Wh |
| Maximum fully charged voltage | Approximately 29.4 V |
| Reported BMS rating | 19.2 A, pending confirmation |
| Robot power-system fuse rating | 30 A |
| Battery connector listed in datasheet | XT60 |

## Measured Robot Operation

| Parameter | Measured Value |
|---|---:|
| Average operating current | 9.5–12 A |
| Voltage after approximately 90 minutes | 23.8–24.2 V |
| Current robot weight reported by mentor | 49 kg |
| Robot weight listed in datasheet | 50 kg |

The difference between the mentor-reported 49 kg weight and the datasheet-listed 50 kg weight shall be resolved before the final added-weight calculation is approved.

## Capture and Mission Planning Baseline

The image-capture system shall support distance-based capture when a valid speed value is available.

The existing mission-ID implementation shall be retained. The mission ID shall continue to be supplied through the software configuration and shall be unique and traceable for each mission. A new mission-ID naming format is not required.

### Required Metadata Sources

| Metadata field | Source |
|---|---|
| `image_id` | Generated locally by the capture software |
| `timestamp` | RUBIK Pi system time, with GNSS time available for comparison when present |
| `robot_id` | System configuration |
| `mission_id` | Existing mission configuration and mission-start process |
| `latitude` and `longitude` | NaviSys GNSS receiver |
| GNSS validity and quality | Calculated from fix age, coordinate range, fix quality, satellite count, and HDOP |

Row and panel identifiers are not required project metadata.

Existing row and panel software support may remain for backward compatibility, but missing row or panel values shall not cause an otherwise valid image record to fail.

### Capture-Spacing Baseline

The current mounting analysis gives a conservative along-track panel view from approximately 0.28 m to 1.90 m ahead of the camera.

```text
Conservative along-track coverage
= 1.90 m - 0.28 m
= 1.62 m
```

For at least 30% overlap between consecutive images:

```text
Maximum travel between captures
= Along-track coverage × (1 - Required overlap)
= 1.62 m × (1 - 0.30)
= 1.134 m
```

When valid speed data is available:

```text
Required capture rate in images per second
= Robot speed in meters per second ÷ 1.134 m
```

The initial software settings are:

| Parameter | Initial value |
|---|---:|
| Required image overlap | At least 30% |
| Conservative along-track coverage | 1.62 m |
| Maximum travel between captures | 1.134 m |
| Fixed-rate fallback | 0.20 images/s, or one image every 5 s |
| Maximum configured operational capture rate | 1.00 image/s |
| Speed-data timeout | 2.5 s |
| Minimum speed treated as movement | 0.02 m/s |

The along-track coverage value shall be replaced with a measured value after the final camera, lens, mounting height, and mounting angle are installed.

The 30% overlap requirement shall remain unless the project requirement is formally changed.

### Speed-Source Baseline

The current software already decodes GNSS speed from supported NMEA data.

The initial adaptive-capture implementation may therefore use GNSS speed without requiring a new connection to the robot controller.

A future robot-controller speed source may replace or supplement GNSS speed through the same software speed-provider interface after the electrical and communication interface is documented.

The preferred speed-source order is:

1. Validated robot-controller or wheel-speed data, when available.
2. Valid GNSS-derived speed.
3. Configured fixed-rate fallback when no valid speed is available.

### Mission-Storage Baseline

The initial storage calculation shall use:

| Parameter | Planning value |
|---|---:|
| Maximum mission duration | 4.5 h, or 16,200 s |
| Provisional average stored image-record size | 5 MB |
| Nominal fallback capture rate | 0.20 images/s |
| Maximum configured capture rate | 1.00 image/s |
| Required free-space reserve after one mission | 20% |

Nominal fallback case:

```text
Images per mission
= 0.20 images/s × 16,200 s
= 3,240 images

Mission storage
= 3,240 images × 5 MB
= 16.2 GB

Capacity needed while retaining 20% free space
= 16.2 GB ÷ 0.80
= 20.25 GB
```

Maximum configured-rate case:

```text
Images per mission
= 1.00 image/s × 16,200 s
= 16,200 images

Mission storage
= 16,200 images × 5 MB
= 81 GB

Capacity needed while retaining 20% free space
= 81 GB ÷ 0.80
= 101.25 GB
```

The selected 500 GB SSD exceeds both initial planning cases.

The 5 MB value is provisional and shall be replaced by measured representative image sizes during validation.

The initial peak image-data rate is:

```text
Peak image-data rate
= 5 MB/image × 1.00 image/s
= 5 MB/s
```

The storage-throughput acceptance target shall therefore be at least:

```text
Required sustained write speed
= 2 × 5 MB/s
= 10 MB/s
```

## Existing Interfaces

The robot does not provide an external USB or Ethernet port.

Available internal communication connections include:

- ESP32 connection on the control board.
- RX, TX, and GND communication pins.
- DB25 communication port on the 50 A motor drivers.
- CAN and RS-232 communication capability on the 50 A motor drivers.
- 2×2 Molex communication connector on the 30 A driver.
- CAN and RS-232 communication capability on the 30 A driver.

The protocol, pinout, signal voltage, baud rate, CAN bitrate, and message format have not yet been provided.

The image-capture software shall not assume a robot-controller speed protocol until the interface is documented.

A later CAN, RS-232, or UART robot-speed provider may replace or supplement the GNSS speed provider without changing the capture-scheduling logic, but only after the following information is confirmed:

- Connector and pinout
- Signal voltage or electrical standard
- Grounding requirements
- Communication protocol
- Baud rate or CAN bitrate
- Message identifier
- Speed scaling and units
- Expected update rate
- Invalid-data behavior
- Timeout behavior

## Environmental Characteristics

The JC600 datasheet provides the following information:

| Parameter | Value |
|---|---:|
| Robot protection rating | IP65 |
| Nominal robot voltage | 24 V |
| Listed output current | 30 A |
| Listed robot weight | 50 kg |
| Approximate dimensions | 1.4 × 0.4 × 1.3 m |
| Number of sprinklers | 10 |
| Water-system pressure | 3 bar |
| Water consumption | 0.5 L/m² |
| Primary use | Photovoltaic-panel cleaning |

The datasheet does not identify which listed dimension corresponds to length, width, or height.

---

# System Requirements

## Functional Requirements

| ID | Requirement | Verification |
|---|---|---|
| SYS-001 | The system shall capture and store images while the robot is operating. | Field test |
| SYS-002 | Each image shall include a unique ID, timestamp, robot ID, mission ID, and GNSS latitude and longitude when a valid fix is available. GNSS validity and quality shall be recorded, and image capture shall continue when GNSS is unavailable. | Metadata inspection and GNSS-loss test |
| SYS-003 | The system shall continue operating without internet access. | Offline test |
| SYS-004 | The system shall log camera, GNSS, speed-source, capture-mode, storage, and startup errors. | Log inspection |
| SYS-005 | The system shall not interfere with normal robot operation. | Full-system test |

---

## Imaging Requirements

| ID | Requirement | Verification |
|---|---|---|
| IMG-001 | The camera shall use a global shutter and provide approximately 5 MP resolution. | Datasheet review |
| IMG-002 | Exposure, gain, and capture timing shall be adjustable. When valid speed data is available, capture timing shall be distance-based and shall target at least 30% overlap using the calibrated along-track image coverage. When speed is unavailable or stale, the software shall use the configured fixed-rate fallback. | Software and field test |
| IMG-003 | Images shall remain clear while the robot moves at normal speed. | Field test |
| IMG-004 | The lens, polarizer, camera angle, and mounting position shall provide clear panel coverage without blocking the image. | Image and mounting test |

---

## Data and Storage Requirements

| ID | Requirement | Verification |
|---|---|---|
| DAT-001 | Each image shall be matched to the correct metadata record. | Metadata test |
| DAT-002 | Images shall still be saved when GNSS is unavailable, with location marked as invalid. | GNSS-loss test |
| DAT-003 | Local storage shall hold at least one 4.5-hour mission at the maximum configured capture rate with 20% free space remaining. The initial planning case is 1.00 image/s at 5 MB per stored image record, requiring at least 101.25 GB before replacement by measured image-size data. | Storage calculation and storage test |
| DAT-004 | Completed image files shall remain readable after shutdown or unexpected power loss. | Power-loss test |

---

## Electrical and Communication Requirements

| ID | Requirement | Verification |
|---|---|---|
| ELEC-001 | The system shall operate from the robot's 23.8–29.4 VDC power range. | Bench test |
| ELEC-002 | The system shall use a dedicated fused power branch approved by Sunnybotics. | Wiring inspection |
| ELEC-003 | The power converter shall provide the required USB-C PD power to the RUBIK Pi, and the PoE injector shall power the LUCID camera. | Functional test |
| ELEC-004 | The camera shall communicate with the RUBIK Pi over an independent Gigabit Ethernet connection. | Network test |

---

## Mechanical, Environmental, and Safety Requirements

| ID | Requirement | Verification |
|---|---|---|
| MEC-001 | The camera and electronics shall be mounted securely and shall not move during operation. | Inspection and field test |
| MEC-002 | The installation shall not block the robot's brushes, tracks, sprinklers, controls, battery, or service panels. | Clearance inspection |
| MEC-003 | Cables and battery-voltage wiring shall be secured, insulated, fused, and protected from water, vibration, abrasion, and moving parts. | Safety inspection |
| MEC-004 | The exposed camera assembly shall target IP67 protection without reducing the robot's existing IP65 protection. | Documentation and water test |
| MEC-005 | Component temperatures shall remain below approved vendor limits, and the complete installed camera system shall add less than 1.00 kg to the robot. | Temperature and measured-weight test |

### Camera Cable Penetration Condition

If the camera is integrated into the same existing external structure as the nozzle, the camera wiring shall use the same approved sealed penetration and waterproofing method.

A separate unsealed chassis opening shall not be created.

The shared penetration shall include appropriate cable strain relief and shall be inspected to confirm that adding the camera wiring does not reduce the robot's existing IP65 protection.

---

# Performance and Acceptance Requirements

| ID | Requirement | Acceptance Threshold | Verification |
|---|---|---:|---|
| ACC-001 | Images successfully captured and saved | At least 95% | Capture-log comparison |
| ACC-002 | Images with complete IDs, timestamps, and metadata | At least 95% | Metadata test |
| ACC-003 | Images usable at normal robot speed | At least 80% | Image review |
| ACC-004 | Unplanned resets or manual adjustments during one mission | 0 | Field observation |
| ACC-005 | Water entry, loose hardware, lost completed files, or interference with the robot | 0 occurrences | Inspection and system test |

# Preliminary System Connection Diagram

```text
7s6p Robot Battery
Nominal: 25.2 V
Maximum: approximately 29.4 V
        |
        v
Existing Robot Power Board
Main switch / relay
        |
        +---------------- Existing Robot Loads
        |
        +---------------- New Dedicated Accessory Fuse
                              |
                              v
                     Accessory Power Distribution
                         |                 |
                         |                 |
                         v                 v
                USB-C PD Converter    PoE Injector
                         |                 |
                         v                 v
                    RUBIK Pi 3       LUCID Camera
                         |
                         +------ Ethernet Data ------+
                         |
                         +------ GNSS Receiver
                         |           |
                         |           +------ Position
                         |           +------ Time
                         |           +------ Speed
                         |
                         +------ Local SSD Storage
                         |
                         +------ Optional Future Robot-Speed Interface
                         |
                         +------ Optional Internet Connection
```