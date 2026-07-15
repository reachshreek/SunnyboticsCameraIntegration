## Overview


The proposed configuration uses:

- **Camera:** LUCID Triton TRI050S-CC
- **Lens:** Universe UC080-5M / BL080C, 8 mm C-mount
- **Optical filter:** Edmund Optics M22.5 × 0.50 linear polarizing filter
- **Edge computer:** RUBIK Pi 3
- **Storage:** WD Blue SN5000 2 TB NVMe SSD
- **Camera network power:** Tycon TP-DCDC-1248GD-M PoE injector
- **Location tagging:** NaviSys GR-U01U USB GNSS receiver

The camera is mounted on top of the robot, faces the **same direction as the antenna and front brushes**, and is tilted approximately **35° downward relative to the solar-panel surface**.

---

## 1. Camera orientation

The camera should be oriented as follows:

- **Forward direction:** toward the robot's front brushes
- **Yaw:** aligned with the robot centerline
- **Nominal downward pitch:** **35°**
- **Recommended adjustment range:** **30–40°**
- **Roll:** level with the solar-panel surface

The antenna remains installed on top of the robot and points in the same general forward direction as shown in the reference robot image.

A rigid but adjustable mount is recommended so the pitch angle can be tuned during field testing.

---

## 2. Mechanical size of the optical assembly

### Individual components

| Component | Approximate dimensions |
|---|---:|
| LUCID Triton camera body | 29 × 29 × 45 mm |
| UC080-5M / BL080C lens | Ø24 × 36.23 mm |
| M22.5 polarizing filter | Ø24 × 9.1 mm |

A simple arithmetic sum gives:

**Total arithmetic length:** `45 mm + 36.23 mm + 9.1 mm = 90.33 mm`

Because threaded portions overlap when assembled, the practical optical-stack length is expected to be approximately:

**Estimated practical optical-stack length:** **85–90 mm**

### Bare camera-head envelope


- Approximate assembled camera-head size: 85–90 mm long × 29 mm wide × 29 mm high

- Approximate imperial size: 3.35–3.56 in long × 1.14 in wide × 1.14 in high


## 3. Height added above the robot

With the camera mounted horizontally and tilted downward:

- Bare camera-head height: approximately **29 mm**
- Bracket and clearance: approximately **10–20 mm**
- Practical increase above the existing roof: approximately **40–50 mm**

Therefore:

**Estimated new overall robot height:** existing robot height + **40–50 mm**

This is approximately:

**Estimated added height:** **1.6–2.0 in**

The exact increase will depend on the bracket geometry and where the mounting base attaches to the robot roof.

---

## 4. Camera field of view

For the Triton camera with the 8 mm UC080-5M lens, the expected full-sensor angular field of view is approximately:

**Expected angular field of view:** **60.8° horizontal × 46.3° vertical**

Approximate diagonal field of view:

**Approximate diagonal field of view:** **72°**

The polarizing filter should not materially change the field of view, provided it does not vignette the lens.

### Visible scene dimensions

For a flat plane perpendicular to the optical axis:

`Visible width W = 2 × distance D × tan(60.8° / 2)`

`Visible height H = 2 × distance D × tan(46.3° / 2)`

where:

- `D` is distance from the camera
- `W` is visible width
- `H` is visible height

| Distance from camera | Approx. visible width | Approx. visible height |
|---:|---:|---:|
| 0.5 m | 0.59 m | 0.43 m |
| 1 m | 1.17 m | 0.86 m |
| 2 m | 2.35 m | 1.71 m |
| 3 m | 3.52 m | 2.57 m |
| 5 m | 5.87 m | 4.28 m |

At 2 m, the nominal scene coverage is approximately:

**Approximate visible area at 2 m:** **2.35 m wide × 1.71 m tall**

The actual footprint on an inclined solar panel will be trapezoidal because the camera is tilted downward rather than aimed perpendicular to the surface.

---

## 5. Recommended downward angle

A good nominal camera pitch is:

**Recommended nominal angle:** **35° downward from the solar-panel surface**

The lens has a vertical field of view of approximately 46.3°, or about 23.15° above and below the optical centerline.

At a 35° downward pitch:

- Upper image ray: approximately \(35° - 23.15° = 11.85°\) downward
- Lower image ray: approximately \(35° + 23.15° = 58.15°\) downward

This keeps the full vertical frame directed toward the panel rather than wasting image area on the sky or distant horizon.

### Estimated panel coverage

Assuming the lens center is approximately **0.40–0.45 m above the panel**, a 35° tilt gives approximately:

- **Nearest visible panel point:** 0.25–0.28 m in front of the camera
- **Farthest visible panel point:** 1.9–2.1 m in front of the camera

This provides a useful balance between:

- Seeing the panel immediately ahead of the robot
- Maintaining enough look-ahead for navigation and inspection
- Preserving useful pixel density for detecting dirt, debris, staining, or defects

### Angle comparison

| Angle | Approximate behavior |
|---:|---|
| 30° | Longer look-ahead, less close-range detail |
| **35°** | Balanced general-purpose view |
| 40° | More close-up panel coverage, less look-ahead |

The mount should therefore allow field adjustment from approximately **30° to 40°**.

---

## 6. Physical arrangement


Things on top of the robot:

- Camera body
- Lens
- Polarizing filter
- Adjustable mounting bracket
- Short camera Ethernet cable section
- Antenna in its original or equivalent roof position
- Optional protective sunshade or weather cover

Things inside the robot

- RUBIK Pi 3
- NVMe SSD
- USB-C power converter
- PoE injector
- Fuse block
- Power switch
- Wiring distribution
- GNSS receiver electronics, unless its antenna requires external placement

Keeping the heavy and heat-generating electronics inside the robot minimizes rooftop weight and prevents them from increasing the camera assembly height.

---

## 7. Power and data architecture

A practical connection sequence is:

```text
Robot DC Power
    │
    ├── Fuse / optional fused distribution block
    │
    ├── USB-C PD converter ──> RUBIK Pi 3
    │                           │
    │                           ├── NVMe SSD
    │                           ├── USB GNSS receiver
    │                           └── Ethernet
    │
    └── Tycon DC-DC PoE injector
                                │
                                └── M12-to-RJ45 cable ──> LUCID Triton camera
```

The camera receives both power and Ethernet communication through the PoE path.

The RUBIK Pi communicates with the camera over Gigabit Ethernet and stores captured images or video on the NVMe SSD. GNSS data can be associated with each image to support location-based inspection records.

---

## 8. Mounting recommendations

The camera mount should include:

1. **30–40° pitch adjustment**
2. A positive locking method so vibration cannot change the angle
3. Corrosion-resistant fasteners
4. Cable strain relief
5. Space for the rear M12 connector and cable bend
6. A rigid connection to the robot chassis
7. Optional vibration-damping material that does not allow excessive camera motion
8. A small sunshade or lens hood if it does not enter the field of view
9. Access to the lens focus and aperture controls
10. A repeatable alignment reference for yaw and pitch

The optical axis should be centered laterally when possible. If an offset is necessary to retain the antenna, that offset should be recorded in the software calibration.

---

## 10. Polarizer setup

The linear polarizing filter can reduce glare reflected by the solar-panel glass.

During setup:

1. Place the robot on a representative solar panel under direct sunlight.
2. View the live camera feed.
3. Rotate the polarizer slowly.
4. Select the orientation that minimizes glare without making the panel image excessively dark.
5. Lock the filter orientation so vibration cannot rotate it.

The optimum polarizer orientation will vary with sun position, robot direction, panel angle, and surface reflections.

---

## 11. Final design recommendation

Use the following as the initial design baseline:

| Parameter | Recommended value |
|---|---:|
| Camera direction | Forward, toward front brushes |
| Nominal downward angle | **35°** |
| Adjustable pitch range | **30–40°** |
| Added roof height | **40–50 mm** |
| Optical-stack length | **85–90 mm** |
| Preliminary keep-out envelope | **100 × 40 × 50 mm** |
| Horizontal field of view | **60.8°** |
| Vertical field of view | **46.3°** |
| Approx. coverage at 2 m | **2.35 m × 1.71 m** |

The 35° setting is a practical starting point, not a fixed final requirement. The bracket should retain enough adjustment for testing on actual solar panels.

---

![Sunnybotics Robot camera setup overview](img\cameraview.jpg)

> The illustration is a concept visualization

## Sources

- [LUCID Triton TRI050S-CC - Edmund Optics](https://www.edmundoptics.com/p/lucid-vision-labs-tritontrade-tri050s-cc-sony-imx264-50mp-color-camera/41821/)
- [LUCID Triton TRI050S-CC - Graftek Imaging](https://graftek.com/product/tri050s-cc/)
- [LUCID Triton 5 MP product page](https://thinklucid.com/product/triton-5-mp-imx264/)
- [LUCID Universe UC080-5M 8 mm lens](https://thinklucid.com/product/universe-compact-c-mount-5mp-8mm-f-2-0/)
- [UC080-5M lens - IMVision](https://www.imvision.com.mx/en/shop/uc080-5m-universe-bl080c-c-mount-lens-8mm-23-5mp-149086)
- [Edmund M22.5 linear polarizing filter](https://www.edmundoptics.com/p/m225-x-050-machine-vision-mounted-linear-glass-polarizing-filter/48695/)
- [RUBIK Pi](https://rubikpi.ai/)
- [RUBIK Pi - Thundercomm](https://www.thundercomm.com/product/rubik-pi/)
- [WD Blue SN5000 NVMe SSD](https://www.sandisk.com/products/ssd/internal-ssd/wd-blue-sn5000-nvme-ssd)
- [Coolgear ChargeIt! 100 W USB-C charger](https://www.coolgear.com/product/chargeit-100-watt-usb-type-c-charger)
- [Tycon TP-DCDC-1248GD-M PoE injector](https://www.tyconsystems.com/products/tp-dcdc-1248gd-m/6026428000003330297)
- [Tycon PoE injector datasheet](https://tsi.tyconsystems.com/doc/SpecSheets/TP-DCDC_Gigabit_POE_Inserter-Converter_Spec_Sheet.pdf)
- [LUCID M12-to-RJ45 Cat6a cable](https://thinklucid.com/product/m12-to-rj45-ip67-cat6a-cable-2m-dark-green/)
- [NaviSys GR-U01U - GPSWebShop](https://gpswebshop.com/products/navisys-gr-u01-industrial-grade-usb-gnss-receiver-1-5m-accuracy-18hz-update-rate-ultra-low-power-consumption-ipx7-waterproof-fully-emi-shielded-operating-temperatures-from-40-c-to-85-c)
- [NaviSys GR-U01 manufacturer page](https://www.navisys.com.tw/productdetail?class=GPS&name=GRU01)