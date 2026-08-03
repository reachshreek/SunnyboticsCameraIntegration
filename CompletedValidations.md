# Phase 2 Validation

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