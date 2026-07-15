
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

## General Functional Requirements

| ID | Requirement | Verification |
|---|---|---|
| SYS-001 | The subsystem shall capture images of photovoltaic panels while the robot is operating. | Field test |
| SYS-002 | The subsystem shall associate each captured image with a capture timestamp. | File inspection |
| SYS-003 | The subsystem shall associate each captured image with GNSS location information when a valid GNSS fix is available. | Field test and metadata inspection |
| SYS-004 | The subsystem shall save captured images to local nonvolatile storage. | Functional test |
| SYS-005 | The subsystem shall operate without requiring a continuous internet connection. | Offline field test |
| SYS-006 | The loss of an internet or cloud connection shall not stop local image capture or local storage. | Network-disconnection test |
| SYS-007 | The subsystem shall start image-capture operation without requiring access to the robot's existing USB or Ethernet interfaces. | Inspection and functional test |
| SYS-008 | The subsystem shall not interfere with the robot's drive motors, brush motors, water system, control board, or normal operator controls. | Full-system field test |
| SYS-009 | The subsystem shall retain all locally stored images after an unexpected loss of robot power, except for a file actively being written at the time of power loss. | Power-interruption test |
| SYS-010 | The subsystem shall provide a method to retrieve stored images after a mission. | Demonstration |
| SYS-011 | The subsystem shall provide a visible or software-readable indication of normal operation, capture failure, storage failure, or loss of GNSS fix. | Functional test |
| SYS-012 | The subsystem shall require no physical adjustment during a normal cleaning mission after initial setup. | Pilot mission |

---

## Imaging Requirements

| ID | Requirement | Verification |
|---|---|---|
| IMG-001 | The camera shall use a global shutter to reduce motion distortion during robot movement. | Datasheet inspection |
| IMG-002 | The camera shall provide a minimum resolution of approximately 5 megapixels. | Datasheet inspection and image inspection |
| IMG-003 | The camera shall be capable of capturing images at the required rate while the robot is moving at its normal cleaning speed. | Field test |
| IMG-004 | The final image-capture rate shall be selected using the robot speed, camera field of view, and required overlap between consecutive images. | Calculation and field test |
| IMG-005 | The camera exposure time shall be configurable to reduce motion blur in outdoor operation. | Software inspection and field test |
| IMG-006 | The camera gain shall be configurable to accommodate changes in solar illumination. | Software inspection |
| IMG-007 | The system shall retain the original full-resolution image unless an approved compression or resizing method is documented. | File inspection |
| IMG-008 | Images shall be sufficiently sharp to support the intended panel-inspection or documentation task. | Image-quality test |
| IMG-009 | The camera mount shall allow the camera viewing angle to be adjusted during installation. | Inspection |
| IMG-010 | The final camera angle shall be mechanically locked after calibration. | Inspection and vibration test |
| IMG-011 | The selected lens shall provide adequate coverage of the target panel area at the installed camera-to-panel distance. | Field-of-view calculation and test image |
| IMG-012 | The polarizing filter shall be rotatable during setup. | Inspection |
| IMG-013 | The polarizing filter shall be lockable after its glare-reduction position is selected. | Inspection |
| IMG-014 | The optical system shall minimize glare and reflected sunlight from photovoltaic-panel glass. | Outdoor image test |
| IMG-015 | The lens, filter, and lens-tube assembly shall not visibly obstruct the image. | Image inspection |
| IMG-016 | The image system shall maintain focus throughout a complete test mission. | Before-and-after image comparison |

---

## Geotagging and Time Requirements

| ID | Requirement | Verification |
|---|---|---|
| GEO-001 | Each captured image shall have a unique filename or unique identifier. | File inspection |
| GEO-002 | Each image record shall contain a timestamp with a resolution of at least one second. | Metadata inspection |
| GEO-003 | Each image record shall contain latitude and longitude when a valid GNSS fix is available. | Metadata inspection |
| GEO-004 | The system shall record whether the GNSS fix was valid at the time of capture. | Metadata inspection |
| GEO-005 | The system shall not generate false coordinates when no valid GNSS fix is available. | GNSS-loss test |
| GEO-006 | When GNSS is unavailable, the image shall still be saved with its timestamp and a missing- or invalid-location status. | GNSS-loss test |
| GEO-007 | Camera time, computer time, and GNSS time shall be synchronized closely enough to associate each image with the correct location sample. | Timestamp comparison |
| GEO-008 | The selected time-synchronization tolerance shall be documented after the image rate and robot speed are finalized. | Design review |
| GEO-009 | Location and timestamp data shall be stored either in the image metadata, in an associated data file, or in both. | File inspection |
| GEO-010 | The metadata format shall allow each data record to be matched unambiguously to its corresponding image. | Data-validation script |

---

##  Data Storage and Upload Requirements

| ID | Requirement | Verification |
|---|---|---|
| DAT-001 | The subsystem shall provide sufficient local storage for at least one complete approved robot mission. | Storage calculation and field test |
| DAT-002 | The storage-capacity calculation shall include image size, image rate, mission duration, metadata, logs, and reserve capacity. | Calculation review |
| DAT-003 | At least 20% of the local storage capacity should remain unused during the maximum planned mission. | Storage inspection |
| DAT-004 | The system shall detect when available storage falls below an approved threshold. | Functional test |
| DAT-005 | The system shall stop image capture safely or issue a clear fault condition before storage is completely exhausted. | Storage-full test |
| DAT-006 | Image files shall remain readable after normal shutdown. | File inspection |
| DAT-007 | Image files shall remain readable after an unexpected power interruption, except for a file actively being written. | Power-interruption test |
| DAT-008 | The system shall maintain a log of startup, shutdown, capture errors, GNSS errors, and storage errors. | Log inspection |
| DAT-009 | Cloud upload shall be treated as an additional function and shall not be required for local image capture. | Offline test |
| DAT-010 | When a network connection is available, the system should support transfer of images to an approved external server or cloud service. | Upload demonstration |
| DAT-011 | A failed upload shall not delete the local image copy. | Network-failure test |
| DAT-012 | Uploaded files shall be checked to confirm that the transferred file matches the locally stored file. | Checksum or file-comparison test |

---

##  Electrical Requirements

| ID | Requirement | Verification |
|---|---|---|
| ELEC-001 | The subsystem shall operate from the robot's nominal 24 V electrical system. | Functional test |
| ELEC-002 | Every component connected directly to the unregulated battery bus shall tolerate at least 30 VDC at its input. | Datasheet inspection |
| ELEC-003 | The subsystem shall operate over the measured robot voltage range of at least 23.8–29.4 VDC. | Bench power-supply test |
| ELEC-004 | The subsystem shall not rely on the robot's regulated 5 V control-board output for primary power. | Wiring inspection |
| ELEC-005 | The subsystem shall use a dedicated fused accessory-power branch. | Wiring inspection |
| ELEC-006 | The accessory fuse shall be located as close as practical to the battery-bus takeoff point. | Wiring inspection |
| ELEC-007 | The accessory fuse rating shall be selected from the maximum continuous load, converter inrush current, wire rating, and connector rating. | Electrical calculation |
| ELEC-008 | The subsystem shall not be connected to an existing motor-output circuit. | Wiring inspection |
| ELEC-009 | The subsystem shall not obtain power from motor phase connections U, V, or W. | Wiring inspection |
| ELEC-010 | The subsystem shall not obtain power from encoder, Hall-sensor, CAN, RS-232, RX, TX, or control-signal wiring. | Wiring inspection |
| ELEC-011 | The accessory branch should be connected downstream of the robot's main switch or power relay so that the subsystem turns off with the robot. | Wiring inspection and shutdown test |
| ELEC-012 | The final battery-bus takeoff location shall be approved by Sunnybotics before installation. | Design approval |
| ELEC-013 | The subsystem wiring shall not bypass the existing robot fuse and switching architecture without written approval. | Wiring inspection |
| ELEC-014 | All subsystem power wiring shall have sufficient current capacity for the maximum expected load. | Wire-ampacity calculation |
| ELEC-015 | Wiring shall include protection against abrasion, movement, and strain. | Inspection |
| ELEC-016 | Power connectors shall be keyed or otherwise protected against reverse-polarity connection. | Inspection |
| ELEC-017 | The PoE injector shall provide the voltage and power required by the LUCID camera. | Datasheet inspection and functional test |
| ELEC-018 | The USB-C converter shall support the Power Delivery profile required by the RUBIK Pi 3. | Datasheet inspection and functional test |
| ELEC-019 | The PoE injector and USB-C converter input ratings shall include the battery's approximately 29.4 V fully charged condition. | Datasheet inspection |
| ELEC-020 | The complete subsystem's maximum continuous input current shall be calculated before the final fuse is selected. | Electrical calculation |
| ELEC-021 | The subsystem shall not cause the total robot current to exceed the battery, BMS, fuse, relay, wiring, or connector limits. | Current measurement |
| ELEC-022 | The reported 19.2 A BMS rating shall be confirmed as either a current rating or a reference to the battery's 19.2 Ah capacity. | Mentor or manufacturer confirmation |
| ELEC-023 | The system shall be tested for startup inrush current. | Current measurement |
| ELEC-024 | The system shall shut down without producing an unsafe condition when robot power is removed. | Shutdown test |
| ELEC-025 | Grounds shall be connected according to an approved wiring plan that avoids unintended current paths or communication-ground damage. | Design review and inspection |

---

## Network and Communication Requirements

| ID | Requirement | Verification |
|---|---|---|
| COM-001 | The camera subsystem shall provide its own Ethernet connection because the robot does not provide an Ethernet port. | Inspection |
| COM-002 | The camera shall communicate with the RUBIK Pi 3 over Gigabit Ethernet. | Network test |
| COM-003 | The PoE injector shall pass both camera power and Ethernet data. | Functional test |
| COM-004 | The local camera network shall operate without depending on the robot control board. | Independent operation test |
| COM-005 | The image subsystem shall not be connected directly to an unknown RX, TX, CAN, or RS-232 signal. | Wiring inspection |
| COM-006 | Any connection to a true RS-232 interface shall use a compatible RS-232 transceiver or adapter. | Inspection and datasheet review |
| COM-007 | A logic-level UART connection shall not be assumed to be compatible with RS-232. | Design review |
| COM-008 | Any connection to a CAN bus shall use a compatible CAN transceiver or CAN adapter. | Inspection |
| COM-009 | The existing CAN bus shall not be modified until its bitrate, termination, pinout, and message format are known. | Design approval |
| COM-010 | The existing RS-232 interface shall not be used until its pinout, baud rate, voltage levels, and protocol are known. | Design approval |
| COM-011 | An independent GNSS receiver shall be used for the initial implementation unless an approved robot-position interface becomes available. | Inspection |
| COM-012 | The subsystem shall not transmit commands to the robot's motor drivers during the initial image-system implementation. | Software and network inspection |
| COM-013 | Any future robot-data connection shall initially be read-only unless Sunnybotics approves command transmission. | Design review |

---

## Mechanical and Mounting Requirements

| ID | Requirement | Verification |
|---|---|---|
| MEC-001 | The camera, lens, filter, and lens-tube assembly shall be mounted securely to the robot. | Inspection |
| MEC-002 | The camera mount shall not loosen during a complete cleaning mission. | Field test |
| MEC-003 | The mount shall prevent camera-angle movement caused by vibration, cable forces, or accidental contact. | Vibration and field test |
| MEC-004 | The mount shall allow initial adjustment of camera position and viewing angle. | Inspection |
| MEC-005 | Adjustment points shall be mechanically lockable. | Inspection |
| MEC-006 | The camera assembly shall not interfere with the brushes, brush supports, tracks, motors, sprinklers, operator controls, or service panels. | Clearance inspection |
| MEC-007 | The camera assembly shall remain within the approved robot envelope. | Dimensional inspection |
| MEC-008 | The camera assembly shall not create a snag point for cables, vegetation, panel edges, or maintenance equipment. | Inspection |
| MEC-009 | The mount shall be made from corrosion-resistant material or receive an appropriate corrosion-resistant finish. | Material inspection |
| MEC-010 | Exposed fasteners shall resist loosening during vibration. | Inspection |
| MEC-011 | Appropriate locking nuts, thread-locking methods, or mechanical retainers shall be used where required. | Inspection |
| MEC-012 | Cable weight and motion shall not be supported by the camera connectors. | Inspection |
| MEC-013 | All external cables shall include strain relief. | Inspection |
| MEC-014 | Cables shall be routed away from tracks, brushes, rotating shafts, sharp edges, and hot surfaces. | Inspection |
| MEC-015 | The added subsystem weight shall be documented. | Weight measurement |
| MEC-016 | The subsystem's center-of-mass effect shall be reviewed before final installation. | Mechanical review |
| MEC-017 | The final installation shall not make the robot unstable during normal movement, turning, transport, or panel operation. | Stability test |
| MEC-018 | The maximum allowable added mass shall be approved by Sunnybotics. | Mentor approval |
| MEC-019 | The mount shall permit removal of the camera for maintenance without requiring disassembly of unrelated robot systems. | Maintenance demonstration |

---

## Environmental Requirements

| ID | Requirement | Verification |
|---|---|---|
| ENV-001 | The exposed camera assembly shall target an IP67 environmental-protection level. | Component documentation and inspection |
| ENV-002 | The IP67 camera configuration shall include the approved LUCID lens tube and compatible seals. | Inspection |
| ENV-003 | The camera's external Ethernet connection shall use a weather-resistant sealing method compatible with the camera. | Inspection |
| ENV-004 | The lens, polarizer, and lens tube shall be protected against water spray and dust. | Water and dust inspection |
| ENV-005 | External cable entries shall be sealed and strain relieved. | Inspection |
| ENV-006 | Installation of the subsystem shall not reduce the robot's existing IP65 protection. | Inspection |
| ENV-007 | No new unsealed opening shall be made in the electronics compartment. | Inspection |
| ENV-008 | Any required chassis penetration shall use an approved sealed gland, bulkhead connector, or equivalent method. | Inspection |
| ENV-009 | The subsystem shall tolerate direct sunlight during outdoor operation. | Field test |
| ENV-010 | The subsystem shall tolerate vibration produced by the tracks, drive motors, brush motors, and panel contact. | Field and vibration test |
| ENV-011 | The subsystem shall tolerate exposure to dust associated with outdoor solar-panel cleaning. | Field test |
| ENV-012 | The subsystem shall tolerate water spray associated with the JC600 sprinkler system. | Controlled water test |
| ENV-013 | The camera lens surface shall remain accessible for inspection and cleaning. | Maintenance inspection |
| ENV-014 | Materials exposed outside the chassis shall resist corrosion from water and outdoor exposure. | Material inspection |
| ENV-015 | Internal subsystem components shall remain within their manufacturer-specified operating-temperature ranges. | Temperature measurement |
| ENV-016 | Internal chassis temperature shall be measured during representative peak-work-hour operation before final environmental approval. | Instrumented field test |
| ENV-017 | The final temperature requirement shall include the highest measured chassis temperature plus an approved design margin. | Thermal review |
| ENV-018 | The system shall not shut down, reset, or corrupt data during the approved environmental test. | Field test |

---

## Safety and Maintainability Requirements

| ID | Requirement | Verification |
|---|---|---|
| SAF-001 | The subsystem installation shall not expose uninsulated battery-voltage conductors. | Inspection |
| SAF-002 | All battery-connected wiring shall be protected against accidental short circuits. | Inspection |
| SAF-003 | The subsystem shall have a documented safe method of electrical disconnection. | Inspection |
| SAF-004 | Maintenance shall be performed only when robot power is disconnected unless a live test is specifically required. | Procedure review |
| SAF-005 | The subsystem shall not prevent access to the robot's emergency controls, main switch, battery connector, or fuses. | Inspection |
| SAF-006 | The subsystem shall not interfere with removal or replacement of the robot battery. | Maintenance demonstration |
| SAF-007 | Components shall be mounted so that normal robot vibration cannot cause contact with live terminals. | Inspection |
| SAF-008 | Cable routing shall not create a trip, entanglement, cutting, or pinch hazard. | Inspection |
| SAF-009 | Power and communication cables shall be labeled at both ends. | Inspection |
| SAF-010 | The accessory fuse rating and purpose shall be labeled. | Inspection |
| SAF-011 | The system wiring diagram shall be updated to include the image subsystem before final installation approval. | Document review |
| SAF-012 | Any modification to the Sunnybotics power or control system shall receive approval before implementation. | Approval record |
| SAF-013 | The system shall allow camera, storage, converter, and network components to be replaced without modifying the motor-driver wiring. | Maintenance inspection |

---

# Performance and Acceptance Requirements

The following thresholds are proposed and shall be confirmed during design review.

| ID | Requirement | Proposed Acceptance Threshold | Verification |
|---|---|---:|---|
| ACC-001 | Images successfully captured and saved | At least 95% of commanded captures | Capture-log comparison |
| ACC-002 | Images with complete timestamp metadata | At least 95% | Metadata-validation script |
| ACC-003 | Images with valid location metadata when GNSS coverage is available | At least 95% | Metadata-validation script |
| ACC-004 | Images judged usable at nominal robot speed | At least 80% | Image-quality review |
| ACC-005 | Unplanned system resets during one complete mission | 0 | Field-test log |
| ACC-006 | Manual intervention during one complete pilot mission | 0 interventions after startup | Field observation |
| ACC-007 | Loose fasteners or mount movement after one complete mission | 0 | Before-and-after inspection |
| ACC-008 | Water entry into sealed camera connections | 0 visible water entry | Water test |
| ACC-009 | Lost image files after normal shutdown | 0 | File-count comparison |
| ACC-010 | Damage to existing robot wiring or functions | 0 | Robot functional test |
| ACC-011 | Camera-angle change during one mission | No measurable movement beyond the approved tolerance | Mechanical measurement |
| ACC-012 | Component temperature limit violations | 0 | Temperature log |
| ACC-013 | Interference with brushes, tracks, sprinklers, or robot controls | 0 occurrences | Field observation |---

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