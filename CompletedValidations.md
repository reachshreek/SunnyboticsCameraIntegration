# Validations



---

# P2-01 - Requirements Traceability Review

## Review Criterion

Every Phase 2 requirement must have:

- At least one verification method
- At least one test or review ID
- Required evidence
- A responsible owner

## Traceability Matrix

| Requirement | Verification activity / test IDs | Required evidence | Responsible role | Traceability result |
|---|---|---|---|---|
| **SYS-001** Capture and store images while the robot operates | P2-06 synthetic pipeline; P2-13 camera acquisition; P2-14 sustained capture; P2-15 end-to-end flow; P2-21 endurance | Image count, capture log, stored files, checksums, endurance report | Software lead / Integration lead | Mapped|
| **SYS-002** Required metadata, valid-fix coordinates, GNSS quality, and continued capture without GNSS | P2-05 unit tests; P2-07 metadata/geotagging; P2-10 fault injection; P2-15; P2-21 | Known-input comparison, metadata files, GNSS-loss log, quarantine records | Software lead | Mapped|
| **SYS-003** Continue operating without internet | P2-09 upload/retry; P2-10 network failure; P2-15 offline queue; P2-21 intermittent upload | Offline capture log, local files, queue state, resumed-upload log | Software lead / Integration lead | Mapped|
| **SYS-004** Log camera, GNSS, speed, capture-mode, storage, and startup errors | P2-05; P2-10; P2-18 startup/recovery; P2-21 | Structured logs, injected-failure report, startup logs | Software lead | Mapped|
| **SYS-005** Do not interfere with normal robot operation | P2-16 power; P2-17 thermal; P2-19 fit/clearance; P2-21 endurance | Power measurements, temperature log, clearance photos, field observation | Integration lead / Electrical lead / Mechanical lead | Mapped;|
| **IMG-001** Global-shutter camera with approximately 5 MP | P2-01 datasheet review; P2-13 acquired-image inspection | Manufacturer datasheet, captured resolution record | Vision lead / Software lead | Mapped|
| **IMG-002** Adjustable exposure/gain; distance capture with 30% overlap; fixed fallback | P2-05; P2-06; P2-11 SDK review; P2-14 adaptive-capture test | Configuration, unit-test report, speed/trigger logs, camera-setting log | Software lead / Vision lead | Mapped; scheduler software evidence exists|
| **IMG-003** Clear images at normal robot speed | P2-14; P2-19; P2-21 | Motion image set and usability scoring | Vision lead | Mapped|
| **IMG-004** Lens, polarizer, angle, and mounting provide clear coverage | P2-19; P2-20 sealing inspection | Test images, focus record, glare comparison, mount measurements | Vision lead / Mechanical lead | Mapped|
| **DAT-001** Correct one-to-one image/metadata matching | P2-07; P2-15 | Manifest, metadata comparison, checksums | Software lead | Mapped|
| **DAT-002** Save images when GNSS is unavailable and mark location invalid | P2-07; P2-10; P2-21 | GNSS-loss images, metadata, logs | Software lead | Mapped|
| **DAT-003** Hold one 4.5-hour maximum-rate mission with 20% free space | P2-08; P2-21 | Capacity calculation, filesystem report, write test | Software lead / Integration lead | Mapped|
| **DAT-004** Completed files readable after shutdown or power loss | P2-10 sudden termination/write interruption; P2-18 power cycles; P2-21 | Recovery records, checksums, file-open verification | Software lead / Integration lead | Mapped|
| **ELEC-001** Operate from 23.8–29.4 VDC | P2-02; P2-12; P2-16 | Datasheets, measured input/output voltage and current | Electrical lead | Mapped|
| **ELEC-002** Dedicated fused power branch | P2-02; P2-16; wiring inspection during P2-19 | Final schematic, fuse schedule, photos, current measurements | Electrical lead | Mapped, design proposed below, approval pending |
| **ELEC-003** USB-C PD powers RUBIK Pi and PoE powers camera | P2-02; P2-12; P2-13; P2-16 | PD negotiation record, boot log, camera power/discovery log | Electrical lead / Integration lead | Mapped|
| **ELEC-004** Independent Gigabit Ethernet camera connection | P2-03; P2-13; P2-14 | Network diagram, link-speed output, discovery/stream log | Software lead / Electrical lead | Mapped|
| **MEC-001** Secure mounting with no movement | P2-19; P2-21 | Fastener inspection, before/after alignment measurements | Mechanical lead | Mapped|
| **MEC-002** Do not block brushes, tracks, sprinklers, controls, battery, or service panels | P2-19 | Clearance checklist, photos, robot movement test | Mechanical lead / Integration lead | Mapped|
| **MEC-003** Secure, insulated, fused, and protected wiring | P2-02; P2-19; P2-20 | Wiring diagram, fuse list, routing photos, strain-relief inspection | Electrical lead / Mechanical lead | Mapped|
| **MEC-004** IP67 camera target without reducing robot IP65 | P2-19 cable penetration; P2-20 sealing test | Assembly checklist, seal photos, water-test record | Mechanical lead | Mapped|
| **MEC-005** Vendor temperature limits and installed mass below 1.00 kg | P2-17; P2-19; P2-21 | Temperature logs and measured installed mass | Mechanical lead / Electrical lead | Mapped|
| **ACC-001** At least 95% of requested images captured and saved | P2-06; P2-14; P2-21 | Trigger-to-image comparison and percentage | Software lead / Integration lead | Mapped |
| **ACC-002** At least 95% complete IDs, timestamps, and metadata | P2-07; P2-15; P2-21 | Mission summary and metadata completeness percentage | Software lead | Mapped, current mission-statistics test supports calculation |
| **ACC-003** At least 80% usable images at normal speed | P2-14; P2-19; P2-21 | Defined usability rubric and reviewed image set | Vision lead | Mapped|
| **ACC-004** Zero unplanned resets or manual adjustments in one mission | P2-18; P2-21 | Power-cycle report and 4.5-hour event log | Integration lead | Mapped|
| **ACC-005** Zero water entry, loose hardware, lost completed files, or robot interference | P2-19; P2-20; P2-21 | Inspection records, checksums, endurance report | Integration lead / Mechanical lead | Mapped|


---

# P2-02 - Electrical Interface Review

## Approved Electrical Architecture

```text
Robot battery / switched accessory power
Documented operating range: 23.8–29.4 VDC
                    |
                    v
        Dedicated 5 A main fuse
        18 AWG red/black pair
        DEUTSCH DT 2-pin disconnect
                    |
                    v
        Fused accessory distribution
              |                 |
              |                 |
          3 A fuse           2 A fuse
          20 AWG             20–22 AWG
              |                 |
              v                 v
    Coolgear CG-PD82HVV    Tycon TP-DCDC-1248GD-M
       23.8–29.4 V in        23.8–29.4 V in
              |                 |
       USB-C PD 12 V/3 A     IEEE 802.3af PoE
              |                 |
              v                 v
         RUBIK Pi 3       LUCID TRI050S-CC
              |
              +-- M.2 SSD
              +-- USB GNSS receiver
```

## Electrical Interface Control Table

| Interface | Electrical definition | Connector / cable | Protection | Review result |
|---|---|---|---|---|
| Robot power to vision main branch | 23.8–29.4 VDC | DEUTSCH DT 2-pin; exact cavity-to-polarity assignment must be frozen | 5 A main fuse; 18 AWG | **Compatible; polarity assignment open** |
| Distribution to Coolgear CG-PD82HVV | 23.8–29.4 VDC. Coolgear technical sheet lists 22 V minimum, 55 V maximum, and nominal 24–48 V input | Coolgear Phoenix-style 2-pin terminal block | 3 A branch fuse; 20 AWG recommended | **Pass by ratings** |
| Coolgear to RUBIK Pi 3 | USB-C PD 3.0, 12 V/3 A required; converter supports a 12 V/3 A PD profile | Short USB-C to USB-C cable; screw-lock preferred | Converter internal protection plus branch fuse | **Pass by ratings** |
| Distribution to Tycon injector | 23.8–29.4 VDC within the injector's 9–36 V input range | Injector DC terminal input; use only one isolated input unless backup power is intentionally designed | 2 A branch fuse; 20–22 AWG | **Pass by ratings** |
| Tycon injector to LUCID camera | IEEE 802.3af PoE; injector listed as 48 V, 17 W model; camera typical draw 3.1 W via PoE | Shielded RJ45 PoE output to LUCID M12 X-coded Cat6a cable | Injector overcurrent/short protection plus branch fuse | **Pass with large power margin** |
| RUBIK Pi to SSD | M.2 Key M 2280, PCIe; board supplies 3.3 V to M.2 | Board-mounted M.2 connector | Included inside RUBIK Pi 12 V/3 A supply envelope | **Compatible** |
| RUBIK Pi to GNSS | USB 5 V power/data | USB connection | Included inside RUBIK Pi supply envelope; exact GNSS current should be recorded | **Compatible** |

## Power-Budget Calculation

### Rated Subsystem Envelope

Use the required RUBIK Pi input rating and the selected PoE injector's rated PoE output:

```text
RUBIK Pi branch output allowance = 12 V × 3 A = 36 W
PoE branch rated output          = 17 W
Combined rated output            = 53 W
```

At the lowest documented robot operating voltage:

```text
Ideal input current = 53 W ÷ 23.8 V = 2.23 A
20% design headroom = 2.23 A × 1.20 = 2.67 A
```

This calculation excludes converter losses because neither finalized installed-unit efficiency nor measured input current is yet available. A 5 A main accessory fuse therefore has adequate nominal room for the planned 53 W output envelope, while the final test must verify actual input current, startup transient, wire temperature, and voltage drop.

### Branch Sizing

```text
RUBIK Pi ideal input current at 23.8 V
= 36 W ÷ 23.8 V
= 1.51 A before conversion losses

Recommended branch fuse: 3 A

Tycon rated-output ideal input current at 23.8 V
= 17 W ÷ 23.8 V
= 0.71 A before conversion losses

Recommended branch fuse: 2 A
```

A 1 A PoE fuse may be unnecessarily tight after conversion losses and startup behavior. Use the currently planned 2 A option unless bench measurements justify a smaller fuse.

### Robot-Level Headroom Check

The repository records up to 12 A average robot current and a 19.2 A BMS rating that is still pending confirmation.

```text
Robot measured upper average current     = 12.00 A
Vision ideal rated-envelope current       =  2.23 A
Combined ideal current                    = 14.23 A
Provisional margin to 19.2 A rating       = 34.9%
Maximum load allowed for 20% headroom     = 19.2 A ÷ 1.20 = 16.0 A
Accessory allowance at 12 A robot current = 4.0 A
```

The planned subsystem appears capable of meeting the 20% headroom goal, but this is **not a final pass** because:

- The 19.2 A BMS rating is explicitly pending confirmation.
- The 9.5–12 A robot value is an average, not a measured peak under worst-case driving, brush, pump, and startup operation.
- Converter losses and startup transients have not been measured.
- Voltage drop at the new branch has not been measured.

```text
These are all things that can only be vaslidated with the hardware, or with access to the robot. 
```

## Other Electrical Notes


1. Locate the 5 A main fuse as close as practical to the robot power takeoff.
2. Use separate 3 A and 2 A branch fuses after distribution.
3. Use a shared robot ground return; do not use the chassis as the intended current-return path unless aprooved.
4. Use PoE only for the camera
5. Keep the unused LUCID M8 GPIO port sealed with the IP67 cap.

## P2-02 Finding

**Pass.** Component voltage and power interfaces are compatible.
---

# P2-03 - Network Interface Review

## Approved Topology

```text
LUCID Triton TRI050S-CC
1000BASE-T GigE Vision + IEEE 802.3af PoE
M12 X-coded connector
            |
            | LUCID shielded M12 X-coded to RJ45 Cat6a
            v
Tycon TP-DCDC-1248GD-M - PoE OUT
            |
      Internal injector path
            |
Tycon DATA IN
            |
            | Short shielded Cat6a RJ45 patch cable
            v
RUBIK Pi 3 RJ45 / eth0
Static, isolated camera subnet

RUBIK Pi 3 Wi-Fi / wlan0
            |
            v
Site access point / hotspot / approved robot uplink
            |
            v
Internet / cloud endpoint
```

The Tycon device is an injector/converter, not a network switch or router. It transparently inserts power into the camera cable. The RUBIK Pi has one wired Gigabit Ethernet interface, so that interface should be dedicated to the camera and internet access should use Wi-Fi or a separately approved USB/cellular interface.

## Proposed Addressing Plan

| Device/interface | Addressing | Gateway | Purpose |
|---|---|---|---|
| RUBIK Pi `eth0` | `192.168.10.1/24` static | None | Dedicated camera host interface |
| LUCID camera | `192.168.10.2/24` persistent static | `0.0.0.0` / none | Predictable discovery and acquisition |
| RUBIK Pi `wlan0` | DHCP from approved site network | DHCP-provided default gateway | Internet/cloud path |
| DNS | Supplied on `wlan0` | Through `wlan0` | Cloud name resolution only |

These addresses are a proposed project convention and may be changed if they conflict with an existing Sunnybotics subnet. The key requirement is that the camera subnet remain static, isolated, and without the system's default route.

## Network Interface Control Table

| Interface | Physical layer | Protocol / configuration | Review result |
|---|---|---|---|
| LUCID camera to Tycon PoE OUT | 1000BASE-T over Cat5e or better; selected cable is shielded Cat6a with M12 X-coded camera end | GigE Vision / GenICam, IEEE 802.3af PoE | **Pass** |
| Tycon DATA IN to RUBIK Pi | Shielded RJ45 Cat6a, Gigabit | Transparent Ethernet; no switch configuration | **Pass** |
| RUBIK Pi camera NIC | 1000M Ethernet | Static IPv4; no DHCP; no default gateway | **Pass** |
| Camera IP | Persistent static IPv4 | Configure through Arena SDK `IpConfigUtility`; record camera MAC and serial number | **Pass** |
| Camera packet behavior | Start with standard MTU 1500; retain packet resend and 10% link-throughput reserve | Optional jumbo-frame commissioning only after the RUBIK Pi NIC and injector path are validated | **Safe baseline** |
| RUBIK Pi internet path | Wi-Fi 5 available on board | DHCP/default route on `wlan0`; local capture must not depend on connection | **Transport path available** |
| Cloud application path | Internet uplink from `wlan0` | Recommended HTTPS/TLS upload with authenticated endpoint and retry queue | **Pass** |

## Routing and Firewall Requirements

1. Put the default route on `wlan0`, never on the camera-only `eth0` interface.
2. Do not bridge `eth0` and `wlan0`.
3. Do not enable IP forwarding unless a later reviewed design explicitly requires it.
4. Permit camera discovery, control, and stream traffic only on `eth0`.
5. Permit outbound authenticated cloud traffic on `wlan0`.
6. Keep capture and local storage operational when `wlan0` is absent.
7. Store no cloud credentials in the public repository.

## Packet-Size Decision

LUCID recommends jumbo frames up to approximately 9000 bytes when every link supports them, primarily to improve high-bandwidth performance and reduce CPU load. This project is configured for a maximum of only one captured image per second, so standard 1500-byte Ethernet frames are an acceptable commissioning baseline and avoid depending on undocumented jumbo-frame behavior in the injector path.

Commissioning sequence:

1. Establish stable discovery and capture with MTU 1500.
2. Confirm `1000baseT/Full` link on the RUBIK Pi.
3. Record dropped/resend packet counts.
4. Only then test MTU 9000 on both the RUBIK Pi NIC and camera.
5. Retain jumbo frames only if the complete path passes without fragmentation, discovery failure, or packet loss.

## Repository/Network Implementation Gap

The current source manifest contains camera, storage, trigger, metadata, GNSS, health, and service modules, but no dedicated uploader module. The configuration also does not define a cloud endpoint, authentication method, retry policy, or upload protocol. Therefore:

- The physical camera network path is complete.
- The independent wired camera connection requirement is traceable and technically valid.
- Offline capture is architecturally supported.
- The cloud leg is not yet sufficiently defined to claim a complete end-to-end network implementation.

## P2-03 Finding

**Conditional pass.** The camera, injector, and RUBIK Pi form a complete compatible Gigabit path, and the static addressing plan above resolves the previously undefined IP configuration. Final approval requires:

1. Confirming the final camera subnet does not conflict with Sunnybotics networks.
2. Recording the camera MAC address and serial number.
3. Testing link speed, discovery, packet loss, and optional jumbo frames on hardware.
4. Selecting the real internet uplink used on the robot.
5. Defining and implementing the cloud endpoint, authentication, upload protocol, and retry behavior.

---

---

# P2-04 - Software Repository Build Validation

## Validation Objective

Confirm that the software repository can be installed and started from a clean development environment without undocumented files, dependencies, or manual source-code changes.

## Environment

| Item                | Value                                      |
| ------------------- | ------------------------------------------ |
| Repository          | `reachshreek/SunnyboticsCameraIntegration` |
| Branch              | `main`                                     |
| Software directory  | `MetadataLabeling/`                        |
| Operating system    | Windows                                    |
| Python version      | Python 3.14.4                              |
| Environment type    | Python virtual environment                 |
| Dependency manager  | `pip`                                      |
| Build configuration | `pyproject.toml`                           |

## Procedure Performed

The following general procedure was completed:

1. Opened the repository from the local development environment.
2. Entered the `MetadataLabeling` directory.
3. Created an isolated Python virtual environment named `.venv`.
4. Activated the virtual environment.
5. Updated `pip`.
6. Installed the project and its development dependencies from `pyproject.toml`.
7. Confirmed that the `solar-tagger` command was installed.
8. Confirmed that pytest could discover the project configuration and test directory.
9. Confirmed that no undocumented source-code changes were required to install the software.

The primary setup commands were:

```powershell
cd MetadataLabeling

py -m venv .venv

.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip

python -m pip install -e ".[dev]"
```

PowerShell script execution was temporarily enabled for the current terminal session when required:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

## Dependencies Installed

The project dependencies were installed using the package definitions in `pyproject.toml`.

The main runtime dependencies include:

* Pillow
* pyserial

The development dependencies include:

* pytest

The project was installed in editable mode so the installed package uses the current repository source code.

## Results

* The virtual environment was created successfully.
* The virtual environment activated successfully.
* The project dependencies installed successfully.
* The project package installed successfully.
* The `pyproject.toml` configuration was recognized.
* Pytest found the configured `tests` directory.
* The software did not require undocumented local files.
* The source code did not require manual modification to complete installation.
* No missing critical dependency prevented the project from running.

## Required Evidence

The following evidence was produced or observed:

* Successful virtual-environment creation
* Successful dependency-installation output
* Installed package and dependency list
* Recognized `pyproject.toml` configuration
* Successful pytest test discovery
* Repository commit showing completion of P2-04

## Limitations

This validation confirms the software build and dependency process on the Windows development computer.

It does not yet confirm:

* Installation on the RUBIK Pi 3
* ARM64 compatibility
* LUCID Arena SDK installation
* Communication with the physical LUCID camera
* Communication with the physical GNSS receiver
* Automatic startup through the final Linux system service

Those items are addressed by later hardware and compatibility validations.

## P2-04 Finding

**Pass.**

The software repository can be installed in a clean Python virtual environment using the documented project configuration and dependency manager. No undocumented source-code changes were required.

---

# P2-05 - Unit-Test Execution

## Validation Objective

Confirm that all current critical unit tests for capture, metadata, GNSS, speed handling, trigger scheduling, storage behavior, and failure handling pass successfully.

## Test Environment

| Item                        | Value                                       |
| --------------------------- | ------------------------------------------- |
| Operating system            | Windows                                     |
| Platform reported by pytest | `win32`                                     |
| Python version              | Python 3.14.4                               |
| pytest version              | 8.4.2                                       |
| pluggy version              | 1.6.0                                       |
| Python executable           | `MetadataLabeling/.venv/Scripts/python.exe` |
| Project root                | `MetadataLabeling/`                         |
| Configuration file          | `pyproject.toml`                            |
| Test directory              | `tests/`                                    |
| Tests collected             | 28                                          |

## Procedure Performed

The complete unit-test suite was executed from the activated virtual environment.

```powershell
python -m pytest -v `
    --junitxml=..\ValidationEvidence\P2-05\pytest-results.xml `
    2>&1 |
    Tee-Object ..\ValidationEvidence\P2-05\pytest-output.txt
```

Pytest automatically loaded the project configuration from `pyproject.toml` and collected tests from the `tests` directory.

## Test Coverage

The executed suite included tests for:

| Area                   | Test coverage                                                                                         |
| ---------------------- | ----------------------------------------------------------------------------------------------------- |
| Simulated camera       | Directory-camera image ordering                                                                       |
| Command-line interface | Structured handling of invalid timestamps                                                             |
| GNSS history           | Closest-fix selection and future-fix tolerance                                                        |
| Image IDs              | Uniqueness and sortable prefixes                                                                      |
| Site layout            | Polygon-based location assignment                                                                     |
| Mission statistics     | Metadata-completeness calculations                                                                    |
| NMEA parsing           | GGA and RMC sentence parsing                                                                          |
| Metadata service       | IDs, timestamps, mission IDs, coordinates, optional fields, quarantine behavior, and image validation |
| Speed provider         | Fresh, missing, stale, and invalid speed samples                                                      |
| Capture scheduling     | Distance capture, fallback capture, overlap spacing, and stationary behavior                          |
| Trigger handling       | File-trigger claiming, completion, and optional row/panel values                                      |

## Initial Test Result

The first complete execution produced:

```text
28 tests collected
26 passed
2 failed
```

The two failures were investigated rather than being ignored.

### Issue 1: Incorrect Manifest Test Path

The mission-manifest test calculated the expected manifest path from the metadata file using an incorrect number of parent-directory operations.

The software correctly wrote the manifest under:

```text
output/manifests/<mission_id>.jsonl
```

The test incorrectly checked under:

```text
output/metadata/manifests/<mission_id>.jsonl
```

The test was corrected to calculate the expected path from the configured storage root.

### Issue 2: Speed-Sample Timestamp Ordering

The distance-trigger test exposed a timing-order issue.

The scheduler recorded the comparison time immediately before requesting the current speed sample. The test speed provider then created a sample with a timestamp slightly later than the comparison time.

This produced a very small negative calculated age, causing the valid speed sample to be treated as unavailable. The scheduler then used fixed-rate fallback instead of distance-based capture.

The scheduler was corrected so that the comparison time is recorded after obtaining the speed sample.

## Corrective Verification

After both corrections, the two previously failing tests were rerun individually and passed.

The complete unit-test suite was then executed again.

## Final Test Result

```text
28 passed
0 failed
```

All collected unit tests passed.

## Final Coverage Result

| Required P2-05 area                     | Result   |
| --------------------------------------- | -------- |
| Capture tests                           | **Pass** |
| Metadata tests                          | **Pass** |
| GNSS tests                              | **Pass** |
| Speed-provider tests                    | **Pass** |
| Trigger-scheduler tests                 | **Pass** |
| Basic storage and manifest tests        | **Pass** |
| Invalid-data and quarantine tests       | **Pass** |
| Current software failure-handling tests | **Pass** |

## Evidence

The validation evidence includes:

```text
ValidationEvidence/
└── P2-05/
    ├── collected-tests.txt
    ├── pytest-output.txt
    └── pytest-results.xml
```

The evidence records:

* The tests collected by pytest
* Individual test results
* The final pass/fail summary
* Machine-readable JUnit XML results
* The Python and pytest environment used for the validation

## Remaining Limitations

P2-05 validates the current unit-test suite, but it does not replace later integration and fault-injection testing.

Additional later validations are still required for:

* Actual SSD write performance
* Full-disk behavior
* Sudden power loss
* Interrupted metadata writes
* Physical camera disconnection
* Physical GNSS disconnection
* Network interruption
* Cloud-upload retries
* Full-system recovery
* Long-duration operation

These behaviors are addressed by P2-08, P2-09, P2-10, P2-18, and P2-21.

## P2-05 Finding

**Pass.**

All 28 collected unit tests passed after correcting one invalid test-path assertion and one genuine speed-sample timestamp-ordering defect.

The final test result was:

```text
28 passed
0 failed
```

The software currently satisfies the P2-05 unit-test execution requirement.
---
---

# P2-06 - Synthetic Image Pipeline Test

## Validation Objective

Confirm that the local image-processing pipeline can process at least 1,000 representative solar-panel image captures without:

- Corrupted output images
- Missing image files
- Missing metadata records
- Duplicate image IDs
- Incorrect image-to-metadata associations
- Capture failures
- Tagging failures

The validation also confirms operation in:

- Interval capture mode
- Adaptive-distance capture mode
- Fixed-rate-fallback capture mode

## Test Environment

| Item | Value |
|---|---|
| Validation ID | `P2-06` |
| Test date | August 3, 2026 |
| Operating system | Windows |
| Software directory | `MetadataLabeling/` |
| Python environment | Project `.venv` virtual environment |
| Camera source | Directory-based simulated camera |
| Physical camera required | No |
| Physical GNSS required | No |
| Evidence directory | `ValidationEvidence/P2-06/` |

## Representative Image Dataset

The validation used representative solar-panel images from:

```text
roboticsSunnyApp/sunnybotics-solar-panel-challenge
```

The dataset commit used was:

```text
a9d9350b4432819e02b5ae4258986e860e1dcabe
```

The repository contained images of both clean and damaged solar panels.

| Dataset item | Count |
|---|---:|
| Total image files | 129 |
| Supported JPG/JPEG images used | 119 |
| Unsupported HEIC images excluded | 10 |

The existing directory-camera simulator supports:

```text
.jpg
.jpeg
.png
.tif
.tiff
.bmp
```

The ten HEIC images were ignored because HEIC is not currently supported by the directory-camera simulator.

The 119 supported images were looped repeatedly until the software completed 1,000 simulated capture events.

The original dataset images were preserved and were not modified or deleted.

## Test Architecture

The physical LUCID camera was replaced with the existing directory-camera simulator.

For each simulated capture, the software:

1. Selected the next supported solar-panel image.
2. Generated a capture trigger.
3. Created a unique image ID.
4. Copied the image into the validation output directory.
5. Created a matching JSON metadata file.
6. Added the record to the mission manifest.
7. Calculated and recorded a SHA-256 checksum.
8. Recorded the capture mode.
9. Recorded image-processing timing.
10. Verified that the saved image could be opened successfully.
11. Recalculated the SHA-256 checksum.
12. Compared the recalculated checksum with the recorded checksum.
13. Confirmed that the image had one matching metadata record.

## Capture Scenarios

| Scenario | Captures | Trigger behavior |
|---|---:|---|
| Interval capture | 500 | One capture generated every one second |
| Adaptive-distance capture | 400 | Simulated speed generated a capture after each estimated 1.134 m |
| Fixed-rate fallback | 100 | Missing speed generated captures using the five-second fallback interval |
| **Total** | **1,000** | All required P2-06 capture modes were exercised |

## Interval-Capture Scenario

The interval scenario generated:

```text
500 captures
```

The scheduler generated one capture request every second.

This mode did not use robot speed or estimated distance.

The interval scenario verified repeated operation of:

- Timed capture triggering
- Image selection
- Image copying
- Image validation
- Metadata generation
- Manifest generation
- Checksum generation
- Mission reporting

## Adaptive-Distance Scenario

The adaptive-distance scenario generated:

```text
400 captures
```

The configured image coverage was:

```text
1.62 meters
```

The required image overlap was:

```text
30%
```

The resulting capture spacing was:

```text
1.62 m × (1 - 0.30) = 1.134 m
```

The test supplied a simulated constant speed of:

```text
1.134 meters per second
```

The software estimated distance using:

```text
Estimated distance = speed × elapsed time
```

At the simulated speed:

```text
1.134 m/s × 1 second = 1.134 m
```

The scheduler therefore generated an adaptive-distance capture approximately once every second.

The expected adaptive-distance trigger records were:

```text
1 distance-initial capture
399 distance captures
```

The repository images themselves did not contain distance information.

The image dataset acted only as the simulated camera input. The speed and distance calculations were produced independently by the trigger scheduler.

This scenario verified that:

- A valid speed sample was accepted.
- Speed was integrated over elapsed time.
- A capture was triggered after the estimated distance reached 1.134 m.
- The correct capture mode was recorded in the metadata.
- Every adaptive trigger produced a valid image and metadata record.

This scenario did not validate the physical distance between the original dataset images.

## Fixed-Rate-Fallback Scenario

The fixed-rate-fallback scenario generated:

```text
100 captures
```

No valid speed provider was supplied.

The scheduler first generated one initial distance-mode capture and then switched to the configured fallback interval:

```text
5 seconds
```

The expected fallback trigger records were:

```text
1 distance-initial capture
99 fixed-rate-fallback captures
```

This scenario verified that the system continues capturing images when speed information is:

- Missing
- Unavailable
- Invalid
- Too old to be considered fresh

Instead of stopping capture completely, the system used the slower fixed-rate fallback.

## Automated Verification Checks

The validation script checked the following conditions:

- The expected number of capture events occurred.
- The expected number of output images was written.
- The expected number of metadata JSON files was written.
- The expected number of manifest records was written.
- Every image ID was unique.
- Every output image had one matching metadata record.
- Every metadata record contained the correct robot ID.
- Every metadata record contained the correct mission ID.
- Every output image could be opened successfully.
- Every recorded SHA-256 checksum matched the saved image.
- No unexpected duplicate output filename was created.
- No capture failure occurred.
- No tagging failure occurred.
- Each scenario contained the expected capture modes.
- Processing time was recorded.
- Every output image remained traceable to a source dataset image.

## Final Results

| Result | Value |
|---|---:|
| Total simulated captures | 1,000 |
| Total output images | 1,000 |
| Total metadata JSON files | 1,000 |
| Total unique image IDs | 1,000 |
| Missing output images | 0 |
| Missing metadata records | 0 |
| Corrupted output images | 0 |
| SHA-256 checksum mismatches | 0 |
| Duplicate image IDs | 0 |
| Capture failures | 0 |
| Tagging failures | 0 |
| Interval scenario | **Pass** |
| Adaptive-distance scenario | **Pass** |
| Fixed-rate-fallback scenario | **Pass** |
| Overall P2-06 result | **Pass** |

The final console output was:

```text
interval: PASS (500 images)
adaptive-distance: PASS (400 images)
fixed-rate-fallback: PASS (100 images)

P2-06: PASS
1,000 images processed successfully.
```

## Evidence

The P2-06 evidence is stored under:

```text
ValidationEvidence/
└── P2-06/
    ├── dataset-summary.json
    ├── P2-06-final-report.json
    ├── interval/
    │   ├── images/
    │   ├── metadata/
    │   ├── manifests/
    │   ├── reports/
    │   └── logs/
    ├── adaptive-distance/
    │   ├── images/
    │   ├── metadata/
    │   ├── manifests/
    │   ├── reports/
    │   └── logs/
    └── fixed-rate-fallback/
        ├── images/
        ├── metadata/
        ├── manifests/
        ├── reports/
        └── logs/
```

The primary overall report is:

```text
ValidationEvidence/P2-06/P2-06-final-report.json
```

The dataset summary is:

```text
ValidationEvidence/P2-06/dataset-summary.json
```

The individual image metadata files are stored under:

```text
ValidationEvidence/P2-06/interval/metadata/
ValidationEvidence/P2-06/adaptive-distance/metadata/
ValidationEvidence/P2-06/fixed-rate-fallback/metadata/
```

The mission manifests are stored at:

```text
ValidationEvidence/P2-06/interval/manifests/p2-06-interval.jsonl
ValidationEvidence/P2-06/adaptive-distance/manifests/p2-06-adaptive-distance.jsonl
ValidationEvidence/P2-06/fixed-rate-fallback/manifests/p2-06-fixed-rate-fallback.jsonl
```

The individual verification reports are stored under:

```text
ValidationEvidence/P2-06/interval/reports/
ValidationEvidence/P2-06/adaptive-distance/reports/
ValidationEvidence/P2-06/fixed-rate-fallback/reports/
```

## P2-06 Finding

**Pass.**

The local image-processing pipeline successfully processed 1,000 representative solar-panel image captures across interval, adaptive-distance, and fixed-rate-fallback operation.

All 1,000 output images were readable and traceable to matching metadata records.

All image IDs were unique, all recorded SHA-256 checksums matched the saved files, and no capture failures, tagging failures, missing records, duplicate IDs, or corrupted outputs were detected.

---

---

# P2-07 - Metadata and Geotagging Validation

## Validation Criterion

Every captured image must receive:

- A unique image ID
- The correct UTC capture timestamp
- The correct robot ID
- The correct mission ID
- A valid GNSS result when acceptable GNSS data is available
- An invalid GNSS result when GNSS data is missing, malformed, stale, outside the permitted timing window, or otherwise unacceptable

Row and panel values are optional.

Missing or invalid GNSS data must not cause the corresponding image or metadata record to be lost.

## Test Configuration

| Item | Test value |
|---|---|
| Robot ID | `sunnybot-01` |
| Mission ID | `p2-07-metadata-geotagging` |
| Test method | Controlled mock GNSS data and predetermined timestamps |
| Representative image | `MetadataLabeling/sample_images/Sample1.jpg` |
| Scenario count | 18 |
| Maximum accepted GNSS age | 2.5 seconds |
| Future-fix tolerance | 0.25 seconds |
| Minimum accepted satellites | 4 |
| Real GNSS receiver required | No |
| Validation runner | `MetadataLabeling/run_p2_07.py` |

## Mock GNSS Inputs

Known coordinates associated with multiple In-N-Out location labels were used as recognizable mock GNSS inputs.

The location order was randomized with the fixed seed `207`, making the test repeatable while still exercising multiple coordinate values.

The location names were included only as test labels. The validation result was determined from the expected latitude, longitude, timestamp, freshness, and quality values.

## Validation Scenarios

| Scenario | Expected behavior |
|---|---|
| Two valid GNSS locations | Coordinates accepted and metadata marked complete |
| Optional row and panel | Values accepted but not required |
| Missing GNSS fix | Coordinates marked invalid and image retained |
| Malformed NMEA checksum | Malformed input detected and image retained |
| Invalid latitude | Coordinates rejected and image quarantined |
| Invalid longitude | Coordinates rejected and image quarantined |
| Stale GNSS fix | Fix rejected because it exceeded the 2.5-second maximum age |
| Future-dated GNSS fix | Fix rejected because it exceeded the 0.25-second future tolerance |
| Low satellite count | Fix rejected because only two satellites were reported |
| Duplicate timestamps | Both images received unique image IDs |
| Midnight rollover | Images stored under the correct UTC date folders |
| Out-of-order timestamps | Records stored according to capture time rather than processing order |
| Timezone normalization | Timezone-aware input converted correctly to UTC |
| GNSS loss and recovery | Valid fix, missing fix, and valid recovered fix handled correctly |
| Missing-fix coordinate reuse | Previous coordinates were not silently reused |

## Supporting Unit Tests

The following test files were run:

```text
tests/test_ids.py
tests/test_gnss_history.py
tests/test_nmea.py
tests/test_service.py
```

Test result:

```text
12 passed in 0.39 seconds
```

## Validation Results

| Result | Recorded value |
|---|---:|
| Overall result | **PASS** |
| Scenarios executed | 18 |
| Scenarios passed | 18 |
| Scenarios failed | 0 |
| Unique image IDs | 18 |
| Manifest entries | 18 |
| Supporting unit tests passed | 12 |
| Failed case IDs | None |

## Global Checks

| Check | Result |
|---|---|
| All validation cases passed | **Pass** |
| All image IDs were unique | **Pass** |
| All images were retained | **Pass** |
| All metadata records were retained | **Pass** |
| Duplicate timestamps produced unique IDs | **Pass** |
| Manifest record count was correct | **Pass** |
| Manifest image IDs matched generated image IDs | **Pass** |
| Missing GNSS did not reuse previous coordinates | **Pass** |
| Row and panel remained optional | **Pass** |

## Invalid-GNSS Handling

Records with missing or unacceptable GNSS data were placed in the quarantine directories:

```text
ValidationEvidence/P2-07/quarantine/images/
ValidationEvidence/P2-07/quarantine/metadata/
```

Quarantine preserved the image and metadata while clearly indicating that the required valid latitude and longitude were unavailable.

Valid records were stored under:

```text
ValidationEvidence/P2-07/images/
ValidationEvidence/P2-07/metadata/
```

## Evidence

- `MetadataLabeling/run_p2_07.py`
- `ValidationEvidence/P2-07/P2-07-test-inputs.json`
- `ValidationEvidence/P2-07/P2-07-comparison.json`
- `ValidationEvidence/P2-07/P2-07-comparison.csv`
- `ValidationEvidence/P2-07/P2-07-final-report.json`
- `ValidationEvidence/P2-07/pytest-output.txt`
- `ValidationEvidence/P2-07/logs/p2-07.log`
- `ValidationEvidence/P2-07/manifests/p2-07-metadata-geotagging.jsonl`
- Generated normal image and metadata records
- Generated quarantined image and metadata records

## P2-07 Finding

**Pass.**

All 18 controlled metadata and geotagging scenarios passed. Every generated image received a unique image ID, correct timestamp, robot ID, and mission ID.

Valid mock GNSS fixes produced the expected coordinates. Missing, malformed, stale, future-dated, low-satellite, and invalid-coordinate inputs were detected and marked invalid without losing the associated image or metadata.

Duplicate timestamps still produced unique image IDs, missing GNSS did not silently reuse previous coordinates, timezone and midnight handling were correct, and row and panel remained optional.

P2-07 is complete.

---

# P2-08 - Local Storage Validation

## Validation Criterion

The local-storage system must:

- Sustain a write speed of at least 10 MB/s
- Successfully write and retain representative image-sized files
- Preserve file integrity
- Produce no missing or duplicate files
- Support one 4.5-hour maximum-rate mission
- Retain at least 20% free capacity after the planned mission
- Produce a throughput log, file listing, checksums, and capacity calculation

Because the selected 500 GB SSD was not physically available, the pre-purchase validation used:

1. Actual host-storage measurements for write speed and file integrity
2. A clearly identified 500 GB planned-capacity simulation for the selected SSD

The physical performance of the final SSD must be confirmed after the hardware is available.

## Test Configuration

| Item | Test value |
|---|---|
| Validation runner | `MetadataLabeling/run_p2_08.py` |
| Throughput test device | Windows host `C:` storage |
| Planned storage device | 500 GB SSD |
| Temporary benchmark size | 10 GB |
| Representative file size | 5 MB |
| Number of temporary files | 2,000 |
| Minimum required write speed | 10 MB/s |
| Mission duration | 4.5 hours |
| Maximum capture rate | 1 image/second |
| Planned average image-record size | 5 MB |
| Maximum mission image count | 16,200 |
| Planned mission storage | 81 GB |
| Required remaining capacity | 20% |
| Planned-capacity simulation | 500 GB |
| Temporary payload retained | No |

## Mission-Capacity Calculation

The maximum mission duration is:

```text
4.5 hours × 60 minutes/hour × 60 seconds/minute
= 16,200 seconds
```

At the maximum capture rate:

```text
16,200 seconds × 1 image/second
= 16,200 image records
```

Using the provisional average record size:

```text
16,200 image records × 5 MB/record
= 81,000 MB
= 81 GB
```

The minimum completely available capacity required to store 81 GB while retaining 20% free is:

```text
81 GB ÷ 0.80
= 101.25 GB
```

The selected 500 GB planned SSD exceeds the minimum capacity requirement.

## Planned 500 GB Capacity Simulation

For the planned 500 GB SSD:

```text
Planned capacity = 500 GB
Mission storage  = 81 GB
```

Projected remaining capacity after one maximum-rate mission:

```text
500 GB - 81 GB
= 419 GB remaining
```

Required 20% reserve:

```text
500 GB × 0.20
= 100 GB required reserve
```

Capacity comparison:

```text
419 GB remaining ≥ 100 GB required
```

**Planned-capacity result: Pass**

The planned drive would retain approximately:

```text
419 GB ÷ 500 GB × 100
= 83.8% free
```

after one 81 GB mission when beginning empty.

## Representative Throughput Test

The benchmark created:

```text
10 GB ÷ 5 MB/file
= 2,000 temporary files
```

For every file, the validation runner:

- Generated a unique filename
- Wrote the expected number of bytes
- Flushed the file through the operating-system storage path
- Recorded the write duration
- Calculated the expected SHA-256 checksum
- Reopened the completed file
- Confirmed that the file was readable
- Confirmed that its size was correct
- Recalculated its SHA-256 checksum
- Compared the expected and actual checksums

The temporary 10 GB payload was deleted after verification.

## Throughput Results

| Result | Recorded value |
|---|---:|
| Benchmark data written | 10.000 GB |
| Expected files | 2,000 |
| Files written | 2,000 |
| Files verified | 2,000 |
| Sustained write speed | 280.818 MB/s |
| Minimum required write speed | 10.000 MB/s |
| Write-speed margin | 28.08 times the requirement |
| Checksum matches | 2,000 of 2,000 |
| File-size matches | 2,000 of 2,000 |
| Missing files | 0 |
| Unreadable files | 0 |
| Duplicate filenames | 0 |
| Temporary payload cleanup | Successful |

## Validation Checks

| Check | Result |
|---|---|
| Mission storage calculated as 81 GB | **Pass** |
| Minimum total capacity calculated as 101.25 GB | **Pass** |
| Planned 500 GB device exceeds minimum capacity | **Pass** |
| Planned device retains at least 20% free capacity | **Pass** |
| Enough host-storage space existed for the benchmark | **Pass** |
| All 2,000 expected files were written | **Pass** |
| Sustained write speed was at least 10 MB/s | **Pass** |
| All files existed and were readable | **Pass** |
| All file sizes matched | **Pass** |
| All SHA-256 checksums matched | **Pass** |
| No duplicate filenames were created | **Pass** |
| Temporary 10 GB payload was deleted | **Pass** |

## Interpretation of the Pre-Purchase Result

The actual host-storage test demonstrated that the software and storage workflow can:

- Write representative 5 MB records at substantially more than 10 MB/s
- Create 2,000 separate files without a missing output
- Read every written file successfully
- Detect file corruption using SHA-256 checksums
- Preserve correct file sizes
- Avoid duplicate filenames
- Remove the temporary benchmark payload after verification

The capacity simulation demonstrated that the planned 500 GB SSD has sufficient nominal capacity for the 81 GB planning mission while leaving more than the required 20% free.

The host `C:` drive was used only to measure throughput and integrity. Its actual current free-space condition was not represented as the capacity of the planned SSD.



## Evidence

- `MetadataLabeling/run_p2_08.py`
- `ValidationEvidence/P2-08/P2-08-system-info.json`
- `ValidationEvidence/P2-08/P2-08-capacity-calculation.json`
- `ValidationEvidence/P2-08/P2-08-throughput-summary.json`
- `ValidationEvidence/P2-08/P2-08-throughput-log.csv`
- `ValidationEvidence/P2-08/P2-08-file-list.csv`
- `ValidationEvidence/P2-08/P2-08-checksum-verification.json`
- `ValidationEvidence/P2-08/P2-08-final-report.json`
- `ValidationEvidence/P2-08/logs/p2-08.log`

## P2-08 Finding

**Pass**

The representative host-storage benchmark wrote and verified all 2,000 temporary 5 MB files. The measured sustained write speed was 280.818 MB/s, exceeding the 10 MB/s requirement by approximately 28 times.

All file sizes and SHA-256 checksums matched. No file was missing, unreadable, corrupted, or duplicated. The temporary 10 GB payload was successfully removed after verification.

The planned 500 GB SSD capacity calculation also passed. One maximum-rate 4.5-hour mission requires 81 GB, and the planned drive would retain 419 GB, or approximately 83.8% of its nominal capacity, after storing that mission when beginning empty.

P2-08 is complete as a before-purchase storage validation. Actual performance and formatted capacity of the selected SSD must be confirmed after hardware acquisition.

# P2-09 - Upload Interruption and Retry Validation

## Validation Criterion

The upload system must continue operating when internet connectivity is unavailable.

The system must:

* Continue capturing and storing images while the upload server is unavailable
* Preserve each image and matching metadata file locally
* Add each unuploaded bundle to a persistent upload queue
* Record unsuccessful upload attempts
* Preserve the queue across an application restart
* Resume uploading automatically after connectivity is restored
* Recover from temporary server errors
* Recover from an interrupted file transfer
* Prevent duplicate final server records when a successful response is lost
* Verify that uploaded files match the original local files
* Finish with no missing, corrupted, duplicated, or pending bundles

## Test Configuration

| Item                             | Test value                                                         |
| -------------------------------- | ------------------------------------------------------------------ |
| Validation runner                | `MetadataLabeling/run_p2_09.py`                                    |
| Robot ID                         | `sunnybot-01`                                                      |
| Mission ID                       | `p2-09-upload-retry`                                               |
| Representative image             | `MetadataLabeling/sample_images/Sample1.jpg`                       |
| Representative image size        | 7,366,471 bytes                                                    |
| Representative image SHA-256     | `af2704412ba0ac4bf826943a6c9b3a24ed949f1c6adb82ac92e3e8f559578b0c` |
| Initial online captures          | 20                                                                 |
| Captures during outage           | 40                                                                 |
| Captures after recovery          | 40                                                                 |
| Total image and metadata bundles | 100                                                                |
| Persistent queue                 | SQLite                                                             |
| Mock server type                 | Local HTTP server                                                  |
| Runtime cleanup                  | Enabled                                                            |
| Host operating system            | Windows 11                                                         |
| Python version                   | 3.14.4                                                             |
| Final hardware required          | No                                                                 |

## Test Architecture

The validation used the following workflow:

```text
Representative image capture
        ↓
Local image and metadata storage
        ↓
Persistent SQLite upload queue
        ↓
Local mock HTTP upload server
        ↓
Simulated connection failures
        ↓
Automatic retry and recovery
        ↓
Checksum and receipt verification
```

Each captured bundle contained:

* One representative image
* One matching metadata JSON file
* A unique image ID
* An image SHA-256 checksum
* A metadata SHA-256 checksum
* A persistent upload-queue record

## Validation Procedure

### Phase 1 - Normal Online Operation

The mock upload server was started.

The validation runner created 20 image and metadata bundles.

For each bundle, the software:

1. Copied the representative image into local storage
2. Created a matching metadata record
3. Calculated image and metadata SHA-256 checksums
4. Added the bundle to the persistent upload queue
5. Uploaded the image and metadata to the mock server
6. Received a server receipt
7. Marked the queue item as uploaded

All 20 initial bundles uploaded successfully.

### Phase 2 - Simulated Internet Outage

The mock server was stopped to simulate unavailable internet connectivity.

The validation runner continued operating and created 40 additional image and metadata bundles.

During the outage:

* All 40 images were saved locally
* All 40 metadata files were saved locally
* All 40 bundles were added to the persistent queue
* Upload attempts failed as expected
* Failed attempts were logged
* No local image or metadata file was deleted
* Capture continued without depending on the upload connection

The queue contained all 40 offline bundles.

### Phase 3 - Application Restart Simulation

One pending queue item was deliberately placed into the `in_progress` state.

The SQLite database was then closed and reopened to simulate an application restart.

After the restart:

* The persistent queue remained available
* All 40 offline bundles remained pending
* The interrupted `in_progress` item was returned safely to the `pending` state
* No bundle was lost

### Phase 4 - Connectivity Recovery

The mock server was restarted using the same local endpoint.

The upload worker resumed processing the persistent queue.

All pending bundles were eventually uploaded successfully.

### Phase 5 - Controlled Failure Scenarios

Three controlled failure conditions were included.

#### Temporary HTTP 500 Errors

Bundle:

```text
sunnybot-01_p2-09_000021
```

received temporary HTTP 500 server errors.

The queue retained the bundle and retried it until the upload succeeded.

#### Interrupted Mid-Upload Transfer

Bundle:

```text
sunnybot-01_p2-09_000022
```

experienced a simulated connection interruption during the image upload.

The incomplete transfer was not accepted as a complete server file.

The bundle remained queued and was successfully retransmitted.

#### Lost Successful Server Response

Bundle:

```text
sunnybot-01_p2-09_000023
```

was stored successfully by the server, but the successful response was deliberately lost.

The uploader retried the same image ID.

The server recognized that the bundle had already been committed and returned an idempotent success instead of creating a duplicate final record.

### Phase 6 - Post-Recovery Capture

After all offline bundles had been recovered, the system created and uploaded another 40 image and metadata bundles.

This confirmed that normal capture and upload operation continued after recovery.

## Results

| Result                                  | Recorded value |
| --------------------------------------- | -------------: |
| Total bundles generated                 |            100 |
| Bundles captured during outage          |             40 |
| Bundles pending before offline attempts |             40 |
| Bundles pending after restart           |             40 |
| Total upload attempts                   |            109 |
| Failed upload attempts recovered        |              9 |
| Queue items uploaded successfully       |            100 |
| Queue items pending at completion       |              0 |
| Server receipts                         |            100 |
| Server files checked                    |            200 |
| Missing local files                     |              0 |
| Local checksum mismatches               |              0 |
| Server checksum mismatches              |              0 |
| Duplicate final receipts                |              0 |

## Validation Checks

| Check                                                   | Result   |
| ------------------------------------------------------- | -------- |
| All 100 expected bundles were generated                 | **Pass** |
| Capture continued while the server was unavailable      | **Pass** |
| All 40 offline bundles entered the persistent queue     | **Pass** |
| Failed upload attempts were recorded                    | **Pass** |
| Local files survived the outage                         | **Pass** |
| The queue survived the simulated restart                | **Pass** |
| The interrupted queue item recovered after restart      | **Pass** |
| The queue drained after connectivity returned           | **Pass** |
| No item remained in the `in_progress` state             | **Pass** |
| All 100 queue items were marked uploaded                | **Pass** |
| All local files still existed after recovery            | **Pass** |
| All local checksums matched                             | **Pass** |
| The server produced one receipt per bundle              | **Pass** |
| All server receipts existed                             | **Pass** |
| All server checksums matched                            | **Pass** |
| Temporary HTTP 500 errors were recovered                | **Pass** |
| The interrupted mid-upload transfer was recovered       | **Pass** |
| The lost successful response was recovered idempotently | **Pass** |
| No duplicate final receipt was created                  | **Pass** |

## File-Integrity Verification

A SHA-256 checksum was calculated for every local image and metadata file before upload.

The mock server independently calculated the checksum of each received file.

The final comparison verified:

```text
Local image checksum      = Uploaded image checksum
Local metadata checksum   = Uploaded metadata checksum
```

A total of 200 uploaded files were checked:

```text
100 image files
100 metadata files
```

All 200 server-side files matched their expected checksums.

## Persistent Queue Verification

The SQLite upload queue stored:

* Image ID
* Local image path
* Local metadata path
* Image checksum
* Metadata checksum
* Upload status
* Attempt count
* Last attempt time
* Next retry time
* Last error
* Upload receipt

The queue used the following states:

```text
pending
in_progress
uploaded
```

At the end of the validation:

```text
Uploaded:    100
Pending:       0
In progress:   0
```

## Runtime Cleanup

The validation was run with:

```text
keep_runtime = false
```

After the test completed successfully, the temporary runtime directory was removed automatically.

The deleted runtime data included:

* Temporary local image copies
* Temporary mock-server image copies
* Temporary metadata copies
* Temporary server receipts
* Partial transfer files

The smaller permanent validation evidence was retained.

## Evidence

* `MetadataLabeling/run_p2_09.py`
* `ValidationEvidence/P2-09/P2-09-upload-queue.sqlite3`
* `ValidationEvidence/P2-09/P2-09-queue-before-outage.json`
* `ValidationEvidence/P2-09/P2-09-queue-during-outage.json`
* `ValidationEvidence/P2-09/P2-09-queue-after-recovery.json`
* `ValidationEvidence/P2-09/P2-09-capture-log.csv`
* `ValidationEvidence/P2-09/P2-09-upload-attempts.csv`
* `ValidationEvidence/P2-09/P2-09-local-files-during-outage.csv`
* `ValidationEvidence/P2-09/P2-09-local-file-inventory.csv`
* `ValidationEvidence/P2-09/P2-09-checksum-comparison.csv`
* `ValidationEvidence/P2-09/P2-09-server-request-log.csv`
* `ValidationEvidence/P2-09/P2-09-server-receipts.json`
* `ValidationEvidence/P2-09/P2-09-final-report.json`
* `ValidationEvidence/P2-09/logs/p2-09.log`

## P2-09 Finding

**Pass**

The system continued capturing and storing image and metadata bundles while the mock upload server was unavailable.

All 40 bundles captured during the outage were preserved locally and retained in the persistent SQLite upload queue. The queue remained intact across a simulated application restart, including recovery of an interrupted `in_progress` item.

After connectivity was restored, all pending bundles uploaded successfully. The uploader also recovered from temporary HTTP 500 errors, an interrupted mid-upload transfer, and a lost successful server response.

All 100 image and metadata bundles produced server receipts. All 200 uploaded files matched their expected SHA-256 checksums. No local file was missing or corrupted, no duplicate final server record was created, and no queue item remained pending at completion.

P2-09 is complete as a pre-hardware upload interruption and retry validation. The final production upload endpoint, authentication method, real network hardware, and real cloud-server compatibility must be confirmed after those interfaces are available.
