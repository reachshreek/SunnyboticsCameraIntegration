# Validation Procedure

## 1. Materials

The validation procedure covers the following parts of the proposed system:

- LUCID Triton camera
- Lens, polarizing filter, and IP67 lens tube assembly
- RUBIK Pi 3 edge computer
- Local SSD storage
- Camera-to-computer Gigabit Ethernet connection
- Tycon PoE injector
- Coolgear 24 V-to-USB-C Power Delivery converter
- Image capture software
- Image metadata and geotagging software
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
| Software to location source | Timestamp, latitude, longitude, synchronization method, and data format |
| Camera assembly to robot | Mounting points, field of view, working distance, clearance, and cable routing |

## 2.2 Interface Review Pass Criteria

**Pass:**

- Every interface has a defined source and destination.
- Every electrical interface has a defined voltage and current.
- Every physical connection has a defined connector.
- Every communication connection has a defined protocol.
- Every interface has a responsible owner.
- Required datasheets or drawings are linked.

**Fail:**

- A component depends on an undocumented voltage.
- A required connector has not been identified.
- A communication protocol has not been confirmed.
- A required driver or software library is unknown.
- A mechanical connection has not been designed or selected.
- The system depends on an undocumented assumption.

---

#  Phase 2 Validation Test Matrix

| ID | Validation activity | Test stage | Tools | Responsible owner | Required evidence | Preliminary pass criteria |
|---|---|---|---|---|---|---|
| P2-01 | Requirements traceability review | Before purchase | Requirements document and traceability matrix | Systems lead | Completed requirement-to-test matrix | Every Phase 2 requirement has at least one test method and owner |
| P2-02 | Electrical interface review | Before purchase | Datasheets, wiring diagram, and power budget | Electrical lead | Approved power diagram and calculations | Every device accepts the supplied voltage and the power system has at least 20% continuous-load headroom |
| P2-03 | Network interface review | Before purchase | Datasheets, interface document, and network diagram | Software and electrical leads | Addressing and connection diagram | The camera, RUBIK Pi, injector, and internet connection have a complete network path |
| P2-04 | Software repo build | Before purchase | GitHub repo, compiler, dependency manager, and CI tools | Software lead | Build log and dependency list | A clean repo checkout builds without undocumented manual changes |
| P2-05 | Unit-test execution | Before purchase | Software test framework and CI tools | Software lead | Unit-test report | All critical capture, metadata, storage, and upload tests pass |
| P2-06 | Synthetic image pipeline test | Before purchase | Generated 5 MP images or representative sample images | Software lead | Logs, output images, checksums, and timing report | At least 1,000 images are processed with no corruption or missing output records |
| P2-07 | Metadata and geotagging validation | Before purchase | Mock GPS data and known timestamp records | Software lead | Input and output comparison file | Every image receives the correct timestamp and coordinates, and malformed data is detected |
| P2-08 | Local storage validation | Before purchase | Representative SSD or host storage and disk benchmark tools | Software lead | Throughput log, file listing, and checksums | Sustained write speed is at least twice the calculated peak image-data rate |
| P2-09 | Upload and retry validation | Before purchase | Test cloud endpoint and network simulation tools | Software lead | Server records, upload logs, and retry logs | Files upload successfully and interrupted transfers resume without data loss |
| P2-10 | Failure recovery testing | Before purchase | Fault-injection scripts | Software lead | Failure logs and recovery timeline | Camera, storage, and network failures are detected without a software crash or silent data loss |
| P2-11 | Camera SDK compatibility review | Before purchase when possible | LUCID SDK, target OS image, and ARM64 environment | Software lead | SDK installation and build report | Required SDK libraries support the target operating system and processor architecture |
| P2-12 | RUBIK Pi power-up test | After hardware arrives | Coolgear converter, USB-C power meter, and multimeter | Electrical or integration lead | Voltage, current, and startup logs | The computer boots reliably and remains stable under maximum expected software load |
| P2-13 | Camera discovery and image acquisition | After hardware arrives | LUCID camera, Tycon injector, Ethernet tools, and camera software | Software or integration lead | Discovery screenshot, acquisition log, and sample images | The camera is discovered after startup and produces correctly formatted images |
| P2-14 | Sustained camera stream test | After hardware arrives | Capture software, network monitor, and system monitor | Software lead | Frame log, packet data, and resource-use report | The required image rate is maintained for at least 3 hours without corrupted frames |
| P2-15 | End-to-end data-flow test | After hardware arrives | Complete bench system | Integration lead | Images, metadata, upload records, and checksums | Capture, metadata, storage, and upload complete with one-to-one traceability |
| P2-16 | Power consumption measurement | After hardware arrives | DC power analyzer, multimeter, or current meter | Electrical lead | Idle, capture, upload, and peak power measurements | Peak and continuous consumption remain within the approved robot power budget |
| P2-17 | Thermal validation | After hardware arrives | Temperature sensors or thermal camera | Electrical and mechanical leads | Temperature-versus-time log | Components remain below their vendor temperature limits with a preferred margin of at least 10°C |
| P2-18 | Startup and recovery test | After hardware arrives | Automated reboot or power-cycle script | Integration lead | Results from repeated power cycles | At least 20 consecutive power cycles complete without manual recovery |
| P2-19 | Mechanical fit and field-of-view test | After hardware arrives | CAD model, robot, test target, and measurement tools | Mechanical and vision leads | Photos, CAD screenshots, measurements, and test images | No interference exists and the required target area is visible |
| P2-20 | Environmental sealing inspection and test | After mechanical assembly | IP67 components, assembly checklist, and approved water-test equipment | Mechanical lead | Assembly photos and test record | All seals and gaskets are installed and no water ingress is observed |
| P2-21 | Full-system endurance test | After hardware integration | Complete system and monitoring scripts | Integration lead | 3-hour system log, image count, and error summary | No crash, corrupted files, uncontrolled heating, or unrecovered subsystem failure occurs |

---

# 3. Software Tests That Can Be Done Before Purchasing Hardware

A large portion of the software system can be tested before the final camera and computer hardware are purchased.

These tests should be completed as early as possible so that software problems can be identified before hardware integration.

---

## 3.1 Software Build and Dependency Validation

The software repo should be tested from a clean environment.

The validation should confirm that:

- The repo can be cloned successfully.
- The required software dependencies are documented.
- Dependency versions are recorded.
- Installation instructions are complete.
- The software builds without undocumented manual modifications.
- Configuration values are separated from the source code.
- Camera, storage, metadata, and upload modules use defined interfaces.
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

### Fail criteria

- The project only runs on one developer's computer.
- Dependencies are installed manually but not documented.
- Source files require local paths that are not included in the project.
- Credentials are hard-coded.
- Critical build errors remain unresolved.

---

## 3.2 Mock Camera Testing

A mock camera module should be created to imitate the future LUCID camera.

The mock camera should be able to:

- Return a synthetic image.
- Return a prerecorded image.
- Produce the planned image dimensions.
- Produce the planned pixel format.
- Generate frames at the planned capture rate.
- Simulate a dropped frame.
- Simulate a delayed frame.
- Simulate an incomplete frame.
- Simulate an invalid frame.
- Simulate camera disconnection.
- Simulate camera reconnection.
- Simulate a camera timeout.
- Simulate an unavailable camera during startup.

This allows the image-processing pipeline to be tested without owning the camera.

### Pass criteria

- The application can use the mock camera through the same software interface planned for the real camera.
- Valid frames are processed correctly.
- Invalid frames are rejected or clearly marked.
- Camera disconnection does not crash the full application.
- The application attempts recovery according to the defined recovery procedure.
- No invalid image is silently treated as valid.

---

## 3.3 Representative Image Pipeline Testing

The image pipeline should be tested using synthetic or recorded images at the intended camera resolution.

The test should include:

- Image capture input
- Image naming
- Image encoding
- Image compression
- Timestamp creation
- Coordinate association
- Storage organization
- Duplicate prevention
- Checksum creation
- Upload queuing
- Upload confirmation
- Archival or deletion after upload

The test images should have realistic dimensions and file sizes. Very small placeholder images should not be used as the only validation input.
### Pass criteria

- At least 1,000 images are processed.
- No output image is corrupted.
- No valid input image is lost.
- No image receives metadata from another image.
- No unexpected duplicate file is created.
- Every output record can be traced to its input.
- Processing completes within the required timing limits.

---

## 3.4 Metadata and Geotagging Simulation

The geotagging system should be tested using known coordinate and timestamp data.

The simulated data should include:

- A stationary coordinate
- A sequence of changing coordinates
- Missing location data
- Delayed location data
- Invalid latitude
- Invalid longitude
- Duplicate timestamps
- Out-of-order timestamps
- Midnight date changes
- Timezone changes
- Unavailable GPS signal
- GPS signal recovery

### Pass criteria

- Every valid image receives the expected timestamp.
- Every valid image receives the expected coordinates.
- Invalid coordinates are rejected or marked invalid.
- Missing data is clearly marked.
- The software does not silently reuse an old coordinate without documenting that behavior.
- The allowed time difference between the image and location record is defined.
- Out-of-order data does not cause incorrect image assignments.

### Fail criteria

- Images receive coordinates from the wrong time.
- Missing location data is recorded as valid data.
- Invalid latitude or longitude values are accepted without warning.
- Timestamps cannot be traced back to a defined time source.

---

## 3.5 Storage Capacity Simulation

The amount of storage required for a mission:

Mission storage = Average image size × Images captured per second × Mission duration in seconds

The calculation should account for:

- Expected image file size
- Capture frequency
- Mission duration
- Metadata files
- Temporary files
- Log files
- Upload queue
- Storage safety margin

The software should then be tested using enough generated files to represent at least one planned mission.

### Storage behaviors to validate

- Normal image writing
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

- Sustained write speed is at least twice the calculated peak image-data rate.
- The system warns before critically low storage.
- The system does not overwrite unuploaded images.
- The system does not silently lose files when storage is full.
- The application recovers when the storage device becomes available again.
- Temporary files and logs cannot grow without a defined limit.
- Corrupted or incomplete files can be identified.

---

## 3.6 Network and Cloud Upload Simulation

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

## 3.7 Failure-Recovery Testing

Fault-injection tests should be used to confirm that one failure does not cause the complete application to fail unexpectedly.

The following failures should be simulated:

- Camera unavailable during startup
- Camera disconnection during capture
- Invalid camera frame
- Camera timeout
- SSD unavailable
- SSD full
- Filesystem write failure
- Internet connection unavailable
- Cloud server unavailable
- Invalid GPS record
- GPS signal loss
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

---

## 3.8 Resource-Utilization Testing

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
- Application startup time
- Failure-recovery time

Results collected on a different computer should be marked as **provisional**.

They should not be treated as final proof of RUBIK Pi 3 performance.

### Pass criteria

- No uncontrolled memory growth is observed.
- Processing keeps up with the planned image rate.
- Image queues remain within their defined limits.
- Temporary files remain within their defined limits.
- CPU usage leaves sufficient headroom for system operation.
- Results are documented clearly enough to repeat on the RUBIK Pi 3.

---

# 4. Hardware-Dependent Tests

The following tests require at least some of the selected hardware and cannot be fully completed through simulation.

---

## 4.1 Camera SDK Compatibility

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

## 4.2 USB-C Power Delivery Validation

The Coolgear converter must correctly power the RUBIK Pi 3 from the robot's 24 V electrical system.

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

### Pass criteria

- The converter accepts the planned robot voltage.
- The RUBIK Pi negotiates an acceptable USB-C PD profile.
- The RUBIK Pi boots reliably.
- Output voltage remains within the acceptable range.
- No unexpected shutdown occurs during maximum expected load.
- The converter does not exceed its rated current, power, or temperature.

---

## 4.3 PoE Injector and Camera Power Validation

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

## 4.4 Sustained Camera Stream Test

The real camera should be operated continuously under the planned capture settings.

The test should record:

- Requested frame or capture rate
- Actual image count
- Dropped images
- Corrupted images
- Packet loss
- CPU usage
- Memory usage
- Network usage
- SSD write speed
- Camera temperature
- RUBIK Pi temperature

### Pass criteria

- The required image rate is maintained.
- No corrupted image is accepted as valid.
- Dropped images remain within the project requirement.
- The application does not crash.
- Memory use remains stable.
- Temperatures remain below vendor limits.
- The test runs continuously for at least 3 hours.

---

## 4.5 End-to-End Data Flow Test

The complete bench system should validate the following sequence:

1. The camera captures an image.
2. The software receives the image.
3. A timestamp is assigned.
4. Location metadata is assigned.
5. The image is written to the SSD.
4. A checksum is created.
7. The image enters the upload queue.
8. The image is uploaded.
9. The cloud service confirms receipt.
10. The uploaded file is compared with the local file.
11. The local record is updated to show successful upload.

### Pass criteria

- Every captured image has one matching metadata record.
- Every stored image has a valid checksum.
- Every uploaded image matches the stored image.
- No image is deleted before upload confirmation.
- No image is uploaded without a traceable local record.
- Failed uploads remain queued.
- Every file can be traced through the complete pipeline.

---

## 4.6 Power Consumption Test

Power consumption should be measured during:

- System idle
- RUBIK Pi startup
- Camera startup
- Normal image capture
- SSD write
- Cloud upload
- Simultaneous capture, storage, and upload
- Recovery after a failure
- Maximum expected processing load

The total continuous system load should include:

- RUBIK Pi 3
- SSD
- Camera
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

## 4.7 Thermal Validation

Temperature should be measured during simultaneous:

- Camera operation
- Image processing
- SSD writing
- Cloud upload
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

## 4.8 Startup and Power-Cycle Test

The complete system should be power-cycled repeatedly.

Each cycle should confirm:

1. Power is applied.
2. The RUBIK Pi boots.
3. The SSD mounts.
4. The camera receives PoE.
5. The camera is discovered.
4. The capture application starts.
7. A test image is captured.
8. The image is stored.
9. The upload system starts or enters its offline queue state.

### Pass criteria

- At least 5 consecutive power cycles complete successfully.
- No manual software restart is required.
- No manual camera reconnection is required.
- The SSD mounts correctly.
- No corrupted system configuration is created.
- The application records startup failures clearly.

---

## 4.9 Mechanical Fit and Field-of-View Validation

The camera assembly should be installed on the robot or a representative mounting structure.

The test should confirm:

- Camera mount fit
- Screw and fastener compatibility
- Camera clearance
- Lens tube clearance
- Cable bend radius
- Cable routing
- Robot movement clearance
- Camera field of view
- Working distance
- Image focus
- Visibility of the required solar-panel area
- Mount adjustment range
- Repeatability after removal and reinstallation

### Pass criteria

- The assembly does not interfere with robot movement.
- Cables are not pinched, stretched, or sharply bent.
- The target area is visible at the required working distance.
- The image can be focused correctly.
- The mount does not visibly shift during normal robot motion.
- The camera can be removed and reinstalled without unacceptable alignment change.

---

## 4.10 Environmental Sealing Validation

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

## 4.11 Full-System Endurance Test

The complete system should operate for at least 3 continuous hours or for the full expected mission duration, whichever requirement is longer.

The test should include:

- Continuous image capture
- Metadata creation
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
- The final image count matches the expected image count within the approved dropped-image limit.

---