# Validation Procedure

## 1. Materials

The validation procedure covers the following parts of the proposed system:

- LUCID Triton camera
- Lens, polarizing filter, and IP67 lens tube assembly
- RUBIK Pi 3 edge computer
- Local SSD storage
- Camera-to-computer Gigabit Ethernet connection
- Tycon PoE injector
- Coolgear CG-PD82HVV 24 V-to-USB-C Power Delivery converter
- Image capture software
- Image metadata and geotagging software
- GNSS speed input and adaptive-capture software
- Local image storage
- Cloud upload system
- Robot 24 V power connection
- Camera mounting and mechanical interfaces

Where an existing project requirement specifies a stricter limit than the limits in this document, the existing project requirement should take priority.

---

# 2. Interface Definition

Before testing begins, every major system connection should be documented.

## 2.1 Interface Control Table

| Interface | Required information |
|---|---|
| Robot to Coolgear converter | Input voltage range, connector type, fuse, polarity, and expected current |
| Coolgear converter to RUBIK Pi 3 | USB-C PD voltage profile, current limit, cable, and maximum load |
| Robot to Tycon PoE injector | Input voltage range, connector type, fuse, polarity, and expected current |
| Tycon injector to LUCID camera | PoE standard, Ethernet pinout, cable type, and available power |
| Camera to RUBIK Pi 3 | Gigabit Ethernet, IP configuration, SDK, GenICam interface, and packet settings |
| Camera to lens assembly | Lens mount, filter attachment, lens tube, gasket, and sealing method |
| RUBIK Pi 3 to SSD | Storage interface, filesystem, mount point, power requirements, and permissions |
| RUBIK Pi 3 to cloud service | Wi-Fi, Ethernet, or cellular connection and upload protocol |
| Software to mission configuration | Existing mission-ID value, robot ID, configuration source, uniqueness check, and startup procedure |
| Software to GNSS source | Timestamp, latitude, longitude, speed, fix validity, synchronization method, and NMEA data format |
| Optional robot-speed source to RUBIK Pi 3 | Connector, electrical standard, protocol, baud rate or CAN bitrate, message ID, scaling, update rate, and timeout |
| Camera assembly to robot | Mounting points, field of view, working distance, clearance, and cable routing |
| Camera cable through robot boundary | Existing sealed opening or shared nozzle/camera penetration, waterproofing method, strain relief, owner, and inspection method |

The initial adaptive-capture implementation may use GNSS speed already decoded by the current software.

The optional robot-controller speed interface shall not be used until its electrical and communication details are confirmed.

## 2.2 Interface Review Pass Criteria

**Pass:**

- Every interface has a defined source and destination.
- Every electrical interface has a defined voltage and current.
- Every physical connection has a defined connector.
- Every communication connection in active use has a defined protocol.
- Every interface has a responsible owner.
- Required datasheets or drawings are linked.
- An interface that is not yet documented is clearly marked as unavailable and is not required for current system operation.
- The existing configuration-based mission-ID behavior is documented and retained.
- Row and panel values are documented as optional rather than required metadata.

**Fail:**

- A component depends on an undocumented voltage.
- A required connector has not been identified.
- An active communication connection uses an unconfirmed protocol.
- A required driver or software library is unknown.
- A mechanical connection has not been designed or selected.
- The system depends on an undocumented assumption.
- The software requires row or panel data even though no confirmed source exists.
- The software requires robot-controller speed data before that interface is documented.

## 2.3 Approved Capture and Storage Baseline

| Parameter | Initial value |
|---|---:|
| Required image overlap | At least 30% |
| Conservative along-track image coverage | 1.62 m |
| Distance between captures | 1.134 m |
| Adaptive-rate formula | Robot speed in m/s ÷ 1.134 m |
| Fixed-rate fallback | 0.20 images/s |
| Fixed-rate fallback interval | 5 s |
| Maximum configured capture rate | 1.00 image/s |
| Minimum capture interval | 1 s |
| Speed-data timeout | 2.5 s |
| Minimum speed treated as movement | 0.02 m/s |
| Maximum mission duration | 4.5 h |
| Provisional average stored image-record size | 5 MB |
| Maximum-rate planning mission storage | 81 GB |
| Capacity required with 20% free remaining | 101.25 GB |
| Peak planning image-data rate | 5 MB/s |
| Minimum sustained write-speed target | 10 MB/s |
| Maximum complete installed camera-system mass | Less than 1.00 kg |

The existing mission-ID implementation shall be retained.

Tests shall confirm that mission IDs are unique and traceable rather than require a new naming format.

The required project metadata fields are:

- Unique image ID
- Timestamp
- Robot ID
- Mission ID
- GNSS latitude and longitude when a valid fix is available
- GNSS validity and quality information

Row and panel values are optional.

Missing row or panel values shall not make an otherwise valid metadata record incomplete.

The initial adaptive-capture implementation shall use GNSS speed when a valid and fresh speed value is available.

When speed is missing, invalid, or stale, the software shall use the configured fixed-rate fallback.

---

# 3. Phase 2 Validation Test Matrix

| ID | Validation activity | Test stage | Tools | Responsible owner | Required evidence | Preliminary pass criteria |
|---|---|---|---|---|---|---|
| P2-01 | Requirements traceability review | Before purchase | Requirements document and traceability matrix | Systems lead | Completed requirement-to-test matrix | Every Phase 2 requirement has at least one test method and owner |
| P2-02 | Electrical interface review | Before purchase | Datasheets, wiring diagram, and power budget | Electrical lead | Approved power diagram and calculations | Every device accepts the supplied voltage and the power system has at least 20% continuous-load headroom |
| P2-03 | Network interface review | Before purchase | Datasheets, interface document, and network diagram | Software and electrical leads | Addressing and connection diagram | The camera, RUBIK Pi, injector, and internet connection have a complete network path |
| P2-04 | Software repo build | Before purchase | GitHub repo, compiler, dependency manager, and CI tools | Software lead | Build log and dependency list | A clean repo checkout builds without undocumented manual changes |
| P2-05 | Unit-test execution | Before purchase | Software test framework and CI tools | Software lead | Unit-test report | All critical capture, metadata, storage, speed-provider, and failure-recovery tests pass |
| P2-06 | Synthetic image pipeline test | Before purchase | Generated 5 MP images or representative sample images | Software lead | Logs, output images, checksums, and timing report | At least 1,000 images are processed with no corruption or missing output records, including interval, adaptive-distance, and fixed-rate-fallback operation |
| P2-07 | Metadata and geotagging validation | Before purchase | Mock GNSS data and known timestamp records | Software lead | Input and output comparison file | Every image receives the correct image ID, timestamp, robot ID, mission ID, and GNSS result; row and panel are not required; malformed or unavailable GNSS data is detected and marked invalid without losing the image |
| P2-08 | Local storage validation | Before purchase | Representative SSD or host storage and disk benchmark tools | Software lead | Throughput log, file listing, checksums, and capacity calculation | Sustained write speed is at least 10 MB/s, and one 4.5-hour maximum-rate mission fits with at least 20% free space remaining |
| P2-09 | Upload and retry validation | Before purchase | Test cloud endpoint and network simulation tools | Software lead | Server records, upload logs, and retry logs | Files upload successfully and interrupted transfers resume without data loss |
| P2-10 | Failure recovery testing | Before purchase | Fault-injection scripts | Software lead | Failure logs and recovery timeline | Camera, GNSS, speed, storage, and network failures are detected without a software crash or silent data loss |
| P2-11 | Camera SDK compatibility review | Before purchase when possible | LUCID SDK, target OS image, and ARM64 environment | Software lead | SDK installation and build report | Required SDK libraries support the target operating system and processor architecture |
| P2-12 | RUBIK Pi power-up test | After hardware arrives | Coolgear converter, USB-C power meter, and multimeter | Electrical or integration lead | Voltage, current, and startup logs | The computer boots reliably and remains stable under maximum expected software load |
| P2-13 | Camera discovery and image acquisition | After hardware arrives | LUCID camera, Tycon injector, Ethernet tools, and camera software | Software or integration lead | Discovery screenshot, acquisition log, and sample images | The camera is discovered after startup and produces correctly formatted images |
| P2-14 | Sustained camera stream and adaptive-capture test | After hardware arrives | LUCID camera, speed simulation or validated speed source, network monitor, and system monitor | Software lead | Frame log, speed log, trigger-mode log, packet data, and resource-use report | Capture spacing maintains at least 30% overlap at the tested speeds, the configured rate does not exceed 1.00 image/s, stale speed activates the 0.20 image/s fallback, and no corrupted frame is accepted |
| P2-15 | End-to-end data-flow test | After hardware arrives | Complete bench system | Integration lead | Images, metadata, upload records, and checksums | Capture, metadata, storage, and upload complete with one-to-one traceability |
| P2-16 | Power consumption measurement | After hardware arrives | DC power analyzer, multimeter, or current meter | Electrical lead | Idle, capture, upload, and peak power measurements | Peak and continuous consumption remain within the approved robot power budget |
| P2-17 | Thermal validation | After hardware arrives | Temperature sensors or thermal camera | Electrical and mechanical leads | Temperature-versus-time log | Components remain below their vendor temperature limits with a preferred margin of at least 10°C |
| P2-18 | Startup and recovery test | After hardware arrives | Automated reboot or power-cycle script | Integration lead | Results from repeated power cycles | At least 20 consecutive power cycles complete without manual recovery |
| P2-19 | Mechanical fit, field-of-view, and cable-penetration test | After hardware arrives | CAD model, robot, test target, measurement tools, and final cable route | Mechanical and vision leads | Photos, CAD screenshots, measurements, test images, and penetration inspection | No interference exists, the required target area is visible, calibrated coverage is recorded, and the camera cable route remains sealed and strain-relieved |
| P2-20 | Environmental sealing inspection and test | After mechanical assembly | IP67 components, assembly checklist, and approved water-test equipment | Mechanical lead | Assembly photos and test record | All seals and gaskets are installed and no water ingress is observed |
| P2-21 | Full-system endurance test | After hardware integration | Complete system and monitoring scripts | Integration lead | 4.5-hour system log, image count, speed-source log, fallback events, and error summary | No crash, corrupted files, uncontrolled heating, or unrecovered subsystem failure occurs during one complete 4.5-hour planning mission |

---

# 4. Software Tests That Can Be Done Before Purchasing Hardware

A large portion of the software system can be tested before the final camera and computer hardware are purchased.

These tests should be completed as early as possible so that software problems can be identified before hardware integration.

---

## 4.1 Software Build and Dependency Validation

The software repo should be tested from a clean environment.

The validation should confirm that:

- The repo can be cloned successfully.
- The required software dependencies are documented.
- Dependency versions are recorded.
- Installation instructions are complete.
- The software builds without undocumented manual modifications.
- Configuration values are separated from the source code.
- Camera, storage, metadata, speed-provider, trigger, and upload modules use defined interfaces.
- The application produces useful logs.
- The application produces understandable error messages.
- The software can be configured to start automatically after boot.
- Required credentials are not stored directly in the repo.

### Pass criteria

- A clean checkout can be installed and built using the documented instructions.
- No undocumented files are required.
- No critical dependencies are missing.
- No passwords or private credentials are stored in the repo.
- The resulting application starts without an immediate error.
- The existing configuration-based mission ID is accepted without requiring a new naming format.
- Configuration validation accepts latitude and longitude as the required location fields without requiring row or panel.
- The distance trigger mode can be selected through configuration.

### Fail criteria

- The project only runs on one developer's computer.
- Dependencies are installed manually but not documented.
- Source files require local paths that are not included in the project.
- Credentials are hard-coded.
- Critical build errors remain unresolved.
- The software requires an undocumented robot-speed connection.
- The software rejects an otherwise valid configuration because row or panel values are absent.

---

## 4.2 Mock Camera and Capture-Scheduler Testing

A mock camera module should be created to imitate the future LUCID camera.

The mock camera should be able to:

- Return a synthetic image.
- Return a prerecorded image.
- Produce the planned image dimensions.
- Produce the planned pixel format.
- Generate frames using the configured fixed capture interval.
- Generate speed values that produce adaptive-distance triggers.
- Simulate a stationary robot.
- Simulate changing robot speed.
- Simulate missing speed data.
- Simulate invalid speed data.
- Simulate stale speed data.
- Confirm that stale or unavailable speed activates the one-image-every-5-seconds fallback.
- Simulate a dropped frame.
- Simulate a delayed frame.
- Simulate an incomplete frame.
- Simulate an invalid frame.
- Simulate camera disconnection.
- Simulate camera reconnection.
- Simulate a camera timeout.
- Simulate an unavailable camera during startup.

This allows the image-processing pipeline and capture scheduler to be tested without owning the camera.

### Pass criteria

- The application can use the mock camera through the same software interface planned for the real camera.
- Valid frames are processed correctly.
- Invalid frames are rejected or clearly marked.
- Camera disconnection does not crash the full application.
- The application attempts recovery according to the defined recovery procedure.
- No invalid image is silently treated as valid.
- Valid speed samples generate distance-based capture triggers.
- The capture spacing equals the configured coverage multiplied by one minus the overlap fraction.
- The initial configuration produces a 1.134 m capture spacing.
- Speed below the configured minimum movement threshold does not create repeated distance triggers.
- Missing or stale speed activates the configured fixed-rate fallback.
- The minimum capture interval prevents the configured rate from exceeding 1.00 image/s.

---

## 4.3 Representative Image Pipeline Testing

The image pipeline should be tested using synthetic or recorded images at the intended camera resolution.

The test should include:

- Image capture input
- Image naming
- Image encoding
- Image compression
- Timestamp creation
- Robot-ID association
- Existing mission-ID association
- Coordinate association
- GNSS validity association
- Capture-mode association
- Speed-source association
- Storage organization
- Duplicate prevention
- Checksum creation
- Upload queuing
- Upload confirmation
- Archival or deletion after upload

The test images should have realistic dimensions and file sizes.

Very small placeholder images should not be used as the only validation input.

### Pass criteria

- At least 1,000 images are processed.
- No output image is corrupted.
- No valid input image is lost.
- No image receives metadata from another image.
- No unexpected duplicate file is created.
- Every output record can be traced to its input.
- Processing completes within the required timing limits.
- The configured robot ID appears in every record.
- The existing configured mission ID appears in every record.
- Each image ID remains unique.
- Optional row and panel values do not affect required metadata completeness.

---

## 4.4 Metadata and Geotagging Simulation

The geotagging system should be tested using known coordinate, speed, and timestamp data.

The simulated data should include:

- A stationary coordinate
- A sequence of changing coordinates
- A sequence of changing speeds
- Zero speed
- Missing speed
- Invalid speed
- Stale speed
- Missing location data
- Delayed location data
- Invalid latitude
- Invalid longitude
- Duplicate timestamps
- Out-of-order timestamps
- Midnight date changes
- Timezone changes
- Unavailable GNSS signal
- GNSS signal recovery

### Pass criteria

- Every valid image receives the expected image ID and timestamp.
- Every image records the configured robot ID.
- Every image records the existing configured mission ID.
- The existing mission-ID implementation remains unchanged and produces unique, traceable mission records.
- Every valid GNSS fix produces the expected latitude and longitude.
- Invalid coordinates are rejected or marked invalid.
- Missing GNSS data is clearly marked.
- Missing GNSS data does not cause the captured image file to be discarded.
- Row and panel are optional and do not affect required metadata completeness.
- A valid GNSS speed value is available to the speed provider.
- Missing or stale speed activates the fixed-rate fallback.
- The software does not silently reuse an old coordinate or speed sample without recording that behavior.
- The allowed time difference between the image and GNSS record is defined.
- Out-of-order data does not cause incorrect image assignments.

### Fail criteria

- Images receive coordinates from the wrong time.
- Missing location data is recorded as valid data.
- Invalid latitude or longitude values are accepted without warning.
- Timestamps cannot be traced back to a defined time source.
- An old speed sample remains in use after the configured timeout.
- Missing row or panel values incorrectly cause the record to fail.
- A different mission-ID format is required even though the existing configured value is valid.

---

## 4.5 Storage Capacity Simulation

The initial amount of storage required for a mission is calculated using:

```text
Mission storage
= Average stored image-record size
× Images captured per second
× Mission duration in seconds
```

Initial maximum-rate case:

```text
Mission duration
= 4.5 h × 3,600 s/h
= 16,200 s

Mission storage
= 5 MB/image × 1.00 image/s × 16,200 s
= 81 GB

Capacity required with 20% free remaining
= 81 GB ÷ 0.80
= 101.25 GB
```

Initial nominal fallback case:

```text
Mission storage
= 5 MB/image × 0.20 images/s × 16,200 s
= 16.2 GB

Capacity required with 20% free remaining
= 16.2 GB ÷ 0.80
= 20.25 GB
```

The selected 500 GB SSD exceeds the initial planning requirement.

The 5 MB stored image-record value is provisional.

It shall be replaced by measured average and high-percentile encoded image sizes from representative LUCID images.

The simulation shall account for:

- Expected image file size
- Adaptive capture frequency
- Fixed-rate fallback frequency
- Maximum configured rate of 1.00 image/s
- Mission duration of 4.5 h
- Metadata files
- Temporary files
- Log files
- Upload queue
- Storage safety margin
- Required 20% free-space reserve

The software should then be tested using enough generated files to represent at least one planned mission.

### Storage behaviors to validate

- Normal image writing
- Maximum configured image-writing rate
- Storage approaching full capacity
- Storage reaching the warning threshold
- Storage reaching the critical threshold
- SSD disconnection
- SSD reconnection
- Filesystem becoming read-only
- Corrupted write attempt
- Application restart
- Recovery of incomplete files
- Prevention of unuploaded image deletion
- Log rotation

### Pass criteria

- Sustained write speed is at least 10 MB/s.
- At least one 4.5-hour maximum-rate planning mission fits while retaining 20% free space.
- The system warns before critically low storage.
- The system does not overwrite unuploaded images.
- The system does not silently lose files when storage is full.
- The application recovers when the storage device becomes available again.
- Temporary files and logs cannot grow without a defined limit.
- Corrupted or incomplete files can be identified.

---

## 4.6 Network and Cloud Upload Simulation

The upload system should be tested before the final robot internet connection is available.

The test environment should simulate:

- A normal connection
- A slow connection
- A high-latency connection
- Complete connection loss
- Connection loss during an upload
- Connection restoration
- Server rejection
- Authentication failure
- Duplicate upload request
- Upload timeout
- Partial upload
- Incorrect server response
- Application restart during upload
- Multiple queued images

### Pass criteria

- No source image is deleted before upload is confirmed.
- Interrupted uploads are retried.
- Uploaded files match the original files.
- Failed uploads remain in the upload queue.
- Files are uploaded after network service returns.
- Duplicate upload requests do not produce uncontrolled duplicate records.
- Authentication failures are reported clearly.
- Upload credentials are not stored directly in the public source repo.
- Local capture continues while the internet connection is unavailable, provided storage remains available.

---

## 4.7 Failure-Recovery Testing

Fault-injection tests should be used to confirm that one failure does not cause the complete application to fail unexpectedly.

The following failures should be simulated:

- Camera unavailable during startup
- Camera disconnection during capture
- Invalid camera frame
- Camera timeout
- GNSS unavailable
- Invalid GNSS record
- GNSS signal loss
- Missing speed
- Invalid speed
- Stale speed
- SSD unavailable
- SSD full
- Filesystem write failure
- Internet connection unavailable
- Cloud server unavailable
- Software process restart
- Sudden application termination
- Sudden power interruption during a file write

### Pass criteria

- The application identifies the failed subsystem.
- The application records the failure.
- The application does not silently discard valid data.
- Unaffected parts of the application continue operating when appropriate.
- The application recovers automatically when recovery is possible.
- Manual recovery instructions are documented when automatic recovery is not possible.
- GNSS loss does not stop image capture.
- Missing or stale speed activates the fixed-rate fallback.
- Recovery of valid speed returns the scheduler to distance-based capture.
- No old speed sample remains active after the configured timeout.

---

## 4.8 Resource-Utilization Testing

Before the RUBIK Pi 3 arrives, the software should be profiled on a representative Linux or ARM64 environment.

The following measurements should be recorded:

- CPU usage
- Memory usage
- Storage write speed
- Storage usage growth
- Network bandwidth
- Processing time per image
- Image queue depth
- Upload queue depth
- Trigger-generation timing
- Speed-provider polling load
- Application startup time
- Failure-recovery time

Results collected on a different computer should be marked as **provisional**.

They should not be treated as final proof of RUBIK Pi 3 performance.

### Pass criteria

- No uncontrolled memory growth is observed.
- Processing keeps up with the planned image rate.
- The scheduler does not exceed the configured maximum capture rate.
- Image queues remain within their defined limits.
- Temporary files remain within their defined limits.
- CPU usage leaves sufficient headroom for system operation.
- Speed polling does not create excessive CPU usage.
- Results are documented clearly enough to repeat on the RUBIK Pi 3.

---

# 5. Hardware-Dependent Tests

The following tests require at least some of the selected hardware and cannot be fully completed through simulation.

---

## 5.1 Camera SDK Compatibility

The LUCID camera requires compatible software libraries, drivers, and communication support.

The test should confirm:

- The required LUCID SDK supports the target operating system.
- The SDK supports the RUBIK Pi 3 processor architecture.
- Required libraries can be installed.
- The camera can be discovered.
- Camera parameters can be read and changed.
- Images can be captured through the selected programming language.
- The application can recover after camera reconnection.

### Pass criteria

- The camera is discovered reliably.
- At least one image can be captured through the project software.
- Required camera settings can be configured.
- The application starts after a reboot without manually reinstalling the SDK.
- No unsupported processor architecture blocks the system.

---

## 5.2 USB-C Power Delivery Validation

The Coolgear CG-PD82HVV converter must correctly power the RUBIK Pi 3 from the robot's 24 V electrical system.

The test should measure:

- Input voltage
- Input current
- Negotiated USB-C PD voltage
- USB-C output current
- Startup voltage behavior
- Voltage during image processing
- Voltage during SSD writes
- Voltage during cloud upload
- Maximum observed load

The selected unit shall be checked to confirm that its model and product revision match the approved BOM record.

### Pass criteria

- The converter accepts the planned robot voltage.
- The RUBIK Pi negotiates an acceptable USB-C PD profile.
- The RUBIK Pi boots reliably.
- Output voltage remains within the acceptable range.
- No unexpected shutdown occurs during maximum expected load.
- The converter does not exceed its rated current, power, or temperature.
- The received product is the approved CG-PD82HVV model or an explicitly approved revision.

---

## 5.3 PoE Injector and Camera Power Validation

The Tycon PoE injector must provide both power and Gigabit Ethernet communication to the LUCID camera.

The test should confirm:

- Input voltage compatibility
- Output PoE standard
- Camera power requirements
- Ethernet data rate
- Cable compatibility
- Camera startup behavior
- Camera reconnection after a power cycle

### Pass criteria

- The camera powers on reliably.
- The camera is discovered through the Ethernet connection.
- The connection operates at the required Ethernet speed.
- Sustained image capture does not produce unexplained disconnections.
- The injector remains within its rated electrical and thermal limits.
- At least 20 consecutive camera power cycles succeed.

---

## 5.4 Sustained Camera Stream and Adaptive-Capture Test

The real camera should be operated continuously under the planned capture settings.

The test should record:

- Current speed input
- Speed source
- Speed-sample age
- Configured along-track coverage
- Configured overlap
- Calculated capture spacing
- Requested capture rate
- Actual image count
- Actual distance between captures
- Measured image overlap
- Fallback events
- Dropped images
- Corrupted images
- Packet loss
- CPU usage
- Memory usage
- Network usage
- SSD write speed
- Camera temperature
- RUBIK Pi temperature

Test speeds should include:

- Zero speed
- Low operating speed
- Nominal operating speed
- Highest expected operating speed
- Changing speed
- Missing speed
- Stale speed
- Speed recovery

### Pass criteria

- At each tested speed, the calculated capture rate equals speed divided by the calibrated capture spacing, subject to the configured maximum of 1.00 image/s.
- Consecutive images maintain at least 30% measured along-track overlap within the tested operating range.
- Valid speed data uses adaptive distance-based capture.
- Missing, invalid, or stale speed data activates the configured 0.20 image/s fallback.
- Zero or near-zero speed does not create repeated distance-based images.
- The configured rate does not exceed 1.00 image/s.
- No corrupted image is accepted as valid.
- Dropped images remain within the project requirement.
- The application does not crash.
- Memory use remains stable.
- Temperatures remain below vendor limits.
- The test runs continuously for at least 3 hours.

---

## 5.5 End-to-End Data Flow Test

The complete bench system should validate the following sequence:

1. A valid speed or fallback state is selected.
2. The capture scheduler requests an image.
3. The camera captures an image.
4. The software receives the image.
5. A timestamp is assigned.
6. The configured robot ID is assigned.
7. The existing configured mission ID is assigned.
8. Location metadata and GNSS validity are assigned.
9. Capture mode and speed-source metadata are assigned.
10. The image is written to the SSD.
11. A checksum is created.
12. The image enters the upload queue.
13. The image is uploaded.
14. The cloud service confirms receipt.
15. The uploaded file is compared with the local file.
16. The local record is updated to show successful upload.

### Pass criteria

- Every captured image has one matching metadata record.
- Every metadata record includes the correct robot ID and mission ID.
- The existing mission-ID format remains accepted.
- Every stored image has a valid checksum.
- Every uploaded image matches the stored image.
- No image is deleted before upload confirmation.
- No image is uploaded without a traceable local record.
- Failed uploads remain queued.
- Every file can be traced through the complete pipeline.
- Optional row and panel fields do not affect required metadata completeness.
- Capture-mode and speed-source information is traceable for adaptive and fallback captures.

---

## 5.6 Power Consumption Test

Power consumption should be measured during:

- System idle
- RUBIK Pi startup
- Camera startup
- Normal image capture
- Maximum configured capture rate
- SSD write
- Cloud upload
- Simultaneous capture, storage, and upload
- GNSS operation
- Recovery after a failure
- Maximum expected processing load

The total continuous system load should include:

- RUBIK Pi 3
- SSD
- Camera
- GNSS receiver
- PoE conversion losses
- USB-C PD conversion losses
- Network hardware
- Any additional supporting electronics

### Pass criteria

- Continuous power remains within the approved robot power budget.
- Peak power does not cause a system reset.
- Wiring and connectors remain within their current ratings.
- The selected fuse protects the wiring and components.
- The preferred continuous-load power margin is at least 20%.

---

## 5.7 Thermal Validation

Temperature should be measured during simultaneous:

- Camera operation
- Image processing
- SSD writing
- Cloud upload
- Maximum configured capture activity
- Maximum expected ambient temperature
- Direct sunlight conditions, when appropriate

### Measurement locations

- LUCID camera body
- RUBIK Pi processor
- SSD
- Coolgear converter
- Tycon PoE injector
- Internal enclosure air
- External enclosure surface

### Pass criteria

- Every component remains below its vendor temperature limit.
- A preferred margin of at least 10°C remains below each maximum temperature.
- Temperature stabilizes rather than increasing continuously.
- No thermal throttling prevents the required system performance.
- No shutdown or communication loss occurs because of temperature.

---

## 5.8 Startup and Power-Cycle Test

The complete system should be power-cycled repeatedly.

Each cycle should confirm:

1. Power is applied.
2. The RUBIK Pi boots.
3. The SSD mounts.
4. The camera receives PoE.
5. The camera is discovered.
6. The GNSS reader starts.
7. The capture application starts.
8. The existing configured mission ID is loaded.
9. A test image is captured.
10. The image is stored.
11. The upload system starts or enters its offline queue state.

### Pass criteria

- At least 20 consecutive power cycles complete successfully.
- No manual software restart is required.
- No manual camera reconnection is required.
- The SSD mounts correctly.
- The existing mission-ID configuration loads correctly.
- No corrupted system configuration is created.
- The application records startup failures clearly.

---

## 5.9 Mechanical Fit and Field-of-View Validation

The camera assembly should be installed on the robot or a representative mounting structure.

The test should confirm:

- Camera mount fit
- Screw and fastener compatibility
- Camera clearance
- Lens tube clearance
- Cable bend radius
- Cable routing
- Shared sealed cable-penetration condition, when used
- Cable strain relief
- Robot movement clearance
- Camera field of view
- Working distance
- Image focus
- Visibility of the required solar-panel area
- Mount adjustment range
- Repeatability after removal and reinstallation
- Nearest usable panel point
- Farthest usable panel point
- Measured along-track coverage
- Calculated capture spacing for 30% overlap

### Pass criteria

- The assembly does not interfere with robot movement.
- Cables are not pinched, stretched, or sharply bent.
- The target area is visible at the required working distance.
- The image can be focused correctly.
- The mount does not visibly shift during normal robot motion.
- The camera can be removed and reinstalled without unacceptable alignment change.
- The actual along-track coverage is measured and recorded.
- The software configuration is updated with the measured coverage.
- The resulting capture spacing preserves at least 30% overlap.
- A separate unsealed chassis opening is not created.
- Any shared cable penetration remains sealed and includes strain relief.

---

## 5.10 Environmental Sealing Validation

The IP67 camera configuration should be inspected before environmental testing.

The inspection should confirm:

- Correct lens tube
- Correct camera gasket
- Correct sealing surface
- Correct cable and connector
- Proper connector engagement
- Correct fastener torque, where specified
- No damaged O-rings
- No missing seals
- No trapped wires
- No visible gap in the sealing surfaces

A controlled water test should only be performed using an approved procedure that does not endanger personnel or other electronics.

### Pass criteria

- All required sealing parts are installed.
- Sealing surfaces are clean and undamaged.
- Connectors are fully engaged.
- No water is observed inside the protected camera assembly after the approved test.
- The camera remains operational after the test.

---

## 5.11 Full-System Endurance Test

The complete system should operate for at least 4.5 continuous hours, representing one complete planning mission.

The test should include:

- Adaptive image capture
- Fixed-rate fallback operation
- Metadata creation
- Existing mission-ID recording
- GNSS location recording
- Speed-source recording
- Local storage
- Intermittent upload
- Simulated network loss
- Network recovery
- Temperature monitoring
- CPU and memory monitoring
- Storage monitoring
- Error monitoring

### Pass criteria

- The application does not crash.
- No stored file is corrupted.
- No uncontrolled memory growth occurs.
- No uncontrolled storage growth occurs.
- No component exceeds its temperature limit.
- Network loss does not stop local image capture.
- Queued uploads resume after network recovery.
- No unrecovered subsystem failure occurs.
- Valid speed uses distance-based capture.
- Missing or stale speed activates the fixed-rate fallback.
- GNSS loss does not cause captured image files to be discarded.
- Every image records the correct existing configured mission ID.
- The final image count matches the capture-trigger log within the approved dropped-image limit.
- The complete installed camera system remains below 1.00 kg.

---

## 6. Immediate Priorities/Risks

The recommended order of work is:

1. Complete the requirements traceability matrix.
2. Freeze the electrical and network interface diagrams.
3. Verify LUCID SDK and ARM64 compatibility.
4. Create the mock camera interface.
5. Complete the GNSS and speed-provider simulation.
6. Complete adaptive-distance and fixed-fallback trigger testing.
7. Complete synthetic image-pipeline testing.
8. Complete storage-capacity and write-speed testing.
9. Complete upload interruption and retry testing.
10. Complete failure-recovery testing.
11. Record all results using the standard test template.
12. Prepare the hardware-dependent procedures before purchasing parts.
13. Assign an actual named owner to every remaining test and risk.