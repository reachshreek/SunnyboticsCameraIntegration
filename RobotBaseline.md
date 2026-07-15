
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
| SYS-002 | Each image shall include a unique ID, timestamp, robot ID, mission ID, and GNSS location when available. | Metadata inspection |
| SYS-003 | The system shall continue operating without internet access. | Offline test |
| SYS-004 | The system shall log camera, GNSS, storage, and startup errors. | Log inspection |
| SYS-005 | The system shall not interfere with normal robot operation. | Full-system test |

---

## Imaging Requirements

| ID | Requirement | Verification |
|---|---|---|
| IMG-001 | The camera shall use a global shutter and provide approximately 5 MP resolution. | Datasheet review |
| IMG-002 | Exposure, gain, and capture rate shall be adjustable. | Software test |
| IMG-003 | Images shall remain clear while the robot moves at normal speed. | Field test |
| IMG-004 | The lens, polarizer, camera angle, and mounting position shall provide clear panel coverage without blocking the image. | Image and mounting test |

---

## Data and Storage Requirements

| ID | Requirement | Verification |
|---|---|---|
| DAT-001 | Each image shall be matched to the correct metadata record. | Metadata test |
| DAT-002 | Images shall still be saved when GNSS is unavailable, with location marked as invalid. | GNSS-loss test |
| DAT-003 | Local storage shall hold at least one complete mission with 20% free space remaining. | Storage calculation |
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
| MEC-005 | The system's temperature and added weight shall remain within approved limits. | Temperature and weight test |

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
                         |
                         +------ Local SSD Storage
                         |
                         +------ Optional Internet Connection