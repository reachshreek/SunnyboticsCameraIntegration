## Camera Comparison Matrix

> Note: Field of view is lens-dependent for these industrial cameras. The camera body determines the sensor, shutter type, interface, and ruggedness, while the selected lens determines the actual field of view.

### Table 1: Core Camera Specifications

| # | Camera | Resolution | Shutter Type | Field of View | Interface | Lens Mount | Operating Temperature |
|---:|---|---|---|---|---|---|---|
| 1 | **LUCID Triton TRI050S-CC** | 2448 × 2048, 5.0 MP | Global shutter | Lens-dependent. Uses C-mount lenses, so FOV changes based on focal length. | GigE / PoE | C-mount | -20°C to +55°C |
| 2 | **Teledyne FLIR Blackfly S BFS-PGE-50S5C-C** | 2448 × 2048, 5.0 MP | Global shutter | Lens-dependent. Uses C-mount lenses. | GigE / PoE | C-mount | 0°C to +50°C |
| 3 | **Basler ace 2 Pro a2A2448-23gcPRO** | 2448 × 2048 default, 5.0 MP | Global shutter | Lens-dependent. Uses C-mount lenses. | GigE / PoE or 12–24 VDC | C-mount | -10°C to +50°C |
| 4 | **Allied Vision Alvium 1800 U-507c** | 2464 × 2056, 5.1 MP | Global shutter | Lens-dependent. Uses C-mount lenses. | USB 3.0 | C-mount | +5°C to +65°C housing temperature |
| 5 | **IDS uEye+ FA GV-5040FA-C-HQ** | 1456 × 1088, 1.58 MP | Global shutter | Lens-dependent. Uses C-mount lenses. | GigE / PoE | C-mount | 0°C to +55°C |

  ### Table 2: Ruggedness, Power, Cost, and Integration

| # | Camera | IP Rating | Dust / Water / Vibration Suitability | Trigger / Sync Support | Technical Specs | Approx. Cost | Enclosure Needed? | Integration Risk | Why It Is a Good Option |
|---:|---|---|---|---|---|---:|---|---|---|
| 1 | **LUCID Triton TRI050S-CC** | IP67 when used with proper IP67 lens tube and cables | Strong option for dust and splash protection. Good fit for field robotics if sealed correctly. | Hardware trigger, software trigger, and PTP / IEEE 1588 support | 67 g; 29 × 29 × 45 mm; 12–24 VDC or PoE; about 2.5 W external / 3.1 W PoE | ~$550 | Partial. It can be IP67 with correct accessories, but still needs a secure robot mount and cable protection. | Low to medium | Best overall balance of ruggedness, global shutter, PoE, compact size, and cost. |
| 2 | **Teledyne FLIR Blackfly S BFS-PGE-50S5C-C** | Not IP-rated by default | Good industrial camera, but not sealed for outdoor dust or water exposure by itself. | Hardware trigger or software trigger | 36 g; 29 × 29 × 30 mm; about 3 W; compact industrial body | ~$880 | Yes. Needs a sealed protective enclosure for field use. | Medium | Strong image quality, good SDK support, and reliable machine-vision performance. |
| 3 | **Basler ace 2 Pro a2A2448-23gcPRO** | IP30 | Not suitable for direct dust or water exposure. Needs external enclosure and strong mounting. | Hardware trigger, software trigger, or free run | 100 g; 55.5 × 29 × 29 mm; PoE or 12–24 VDC; about 2.9 W GPIO / 4.2 W PoE | ~$829–$1,155 | Yes. Needs a sealed enclosure for outdoor robot use. | Medium | Reliable industrial camera ecosystem with strong documentation and vendor support. |
| 4 | **Allied Vision Alvium 1800 U-507c** | Not IP-rated by default | Good compact embedded camera, but needs protection from dust, water, and brush-area debris. | Hardware trigger through GPIO or software trigger | Around 60–65 g; 38 × 29 × 29 mm; USB power or external 5 V; about 2.0 W | ~$945 | Yes. Needs a sealed enclosure for field use. | Medium to high | Good embedded/robotics option, especially if the edge computer is USB-based. |
| 5 | **IDS uEye+ FA GV-5040FA-C-HQ** | IP65 / IP67 style rugged housing; IDS also lists strong IP protection for the FA family | Best rugged physical option for dust and water. Designed for harsh industrial environments. | Hardware trigger or software trigger | 173 g; 41 × 53 × 42.7 mm; PoE or 12–24 VDC; about 1.4–3.1 W | ~$775 | Usually no full enclosure needed if paired with compatible IP-rated lens/accessories, but still needs a protective robot mount. | Low for environment, medium for resolution | Very rugged, but lower resolution may be a limitation for detailed panel analysis. |


---

## Evaluation Criteria

| Criterion | What It Means |
|---|---|
| **Performance** | Image quality, resolution, shutter type, and ability to capture usable images while the robot is moving. |
| **Cost** | Approximate purchase cost and whether the option is realistic for approval. |
| **Availability** | Whether the camera appears easy to purchase within the project timeline. |
| **Support / Documentation** | Quality of datasheets, SDKs, examples, and vendor support. |
| **Power Consumption** | How much power the camera needs and how easy it is to power from the robot. |
| **Ease of Integration** | How easy the camera is to connect to the edge computer, mount, protect, and use in software. |

---

## Camera System Options

| # | Option | Camera | Optics | Compute | Notes |
|---:|---|---|---|---|---|
| 1 | **LUCID Triton System** | LUCID Triton TRI050S-CC | C-mount low-distortion lens | RUBIK Pi / Jetson / industrial mini PC | PoE/GigE, IP67-capable |
| 2 | **FLIR Blackfly S System** | Teledyne FLIR Blackfly S BFS-PGE-50S5C-C | C-mount low-distortion lens | RUBIK Pi / Jetson / industrial mini PC | PoE/GigE, enclosure needed |
| 3 | **Basler ace 2 Pro System** | Basler ace 2 Pro a2A2448-23gcPRO | C-mount low-distortion lens | RUBIK Pi / Jetson / industrial mini PC | PoE/GigE, enclosure needed |
| 4 | **Allied Vision Alvium System** | Allied Vision Alvium 1800 U-507c | C-mount low-distortion lens | RUBIK Pi / Jetson / USB3 mini PC | USB3, enclosure needed |
| 5 | **IDS uEye+ FA System** | IDS uEye+ FA GV-5040FA-C-HQ | IP-rated C-mount lens/accessory set | RUBIK Pi / Jetson / industrial mini PC | PoE/GigE, very rugged |

---

## Basic Specification Matrix

| # | Camera | Resolution | Shutter | Interface | IP Rating | Power | Approx. Cost |
|---:|---|---|---|---|---|---|---:|
| 1 | **LUCID Triton TRI050S-CC** | 2448 × 2048, 5.0 MP | Global | GigE / PoE | IP67 with proper accessories | ~3.1 W PoE | ~$550 |
| 2 | **FLIR Blackfly S BFS-PGE-50S5C-C** | 2448 × 2048, 5.0 MP | Global | GigE / PoE | Not IP-rated by default | ~3 W | ~$880 |
| 3 | **Basler ace 2 Pro a2A2448-23gcPRO** | 2448 × 2048, 5.0 MP | Global | GigE / PoE | IP30 | ~3–4 W | ~$829–$1,155 |
| 4 | **Allied Vision Alvium 1800 U-507c** | 2464 × 2056, 5.1 MP | Global | USB3 | Not IP-rated by default | ~2 W | ~$945 |
| 5 | **IDS uEye+ FA GV-5040FA-C-HQ** | 1456 × 1088, 1.58 MP | Global | GigE / PoE | IP65 / IP67 family | ~1.4–3.1 W | ~$775 |

---

## Comparison Matrix

| Option | Performance | Cost | Availability | Support / Docs | Power | Ease of Integration | Overall Evaluation |
|---|---|---|---|---|---|---|---|
| **LUCID Triton System** | Excellent | Excellent | Good | Good | Good | Excellent | Best overall balance of ruggedness, image quality, PoE/GigE integration, and cost. |
| **FLIR Blackfly S System** | Good | Acceptable | Acceptable | Excellent | Good | Good | Strong camera and SDK support, but needs a separate enclosure for field use. |
| **Basler ace 2 Pro System** | Good | Acceptable | Good | Excellent | Good | Good | Reliable industrial option with strong documentation, but IP30 rating means enclosure is required. |
| **Allied Vision Alvium System** | Good | Acceptable | Excellent | Good | Excellent | Acceptable | Good low-power USB3 option, but USB3 is less ideal than PoE/GigE for rugged robot cable routing. |
| **IDS uEye+ FA System** | Acceptable | Good | Acceptable | Good | Excellent | Good | Very rugged physically, but lower resolution may limit image detail for solar panel analysis. |

---

## Short Justification

| Option | Justification |
|---|---|
| **LUCID Triton System** | Best overall choice because it has 5 MP resolution, global shutter, PoE/GigE, low power, compact size, and IP67 capability with the correct accessories. |
| **FLIR Blackfly S System** | Strong industrial camera with good image quality and excellent software support, but it is not sealed for dust or water by default. |
| **Basler ace 2 Pro System** | Strong vendor ecosystem and documentation, but it needs a protective enclosure because the camera itself is only IP30. |
| **Allied Vision Alvium System** | Good low-power option for USB3-based compute, but USB3 may be less rugged than PoE/GigE for a vibrating robot. |
| **IDS uEye+ FA System** | Best physical ruggedness option, but the lower 1.58 MP resolution may not provide enough detail depending on the analysis pipeline. |

---

## Final Ranking

| Rank | Camera System | Reason |
|---:|---|---|
| 1 | **LUCID Triton System** | Best overall balance of image quality, ruggedness, PoE/GigE integration, and cost. |
| 2 | **Basler ace 2 Pro System** | Strong industrial camera with excellent documentation and support. |
| 3 | **FLIR Blackfly S System** | Very strong camera and SDK support, but enclosure requirement increases integration effort. |
| 4 | **Allied Vision Alvium System** | Good low-power embedded option, but USB3 is less ideal for rugged robot use. |
| 5 | **IDS uEye+ FA System** | Very rugged, but lower resolution makes it a riskier choice for detailed panel imagery. |

---

## Initial Recommendation

The recommended baseline option is:

**LUCID Triton TRI050S-CC + C-mount low-distortion lens + RUBIK Pi or similar edge computer + local SSD storage**

This option is recommended because it provides the best balance of:

- Image quality
- Global shutter performance
- Ruggedness
- PoE/GigE integration
- Cost
- Low integration risk

---

## Sources

| Source | Link |
|---|---|
| LUCID Triton TRI050S-CC | https://thinklucid.com/product/triton-5-mp-imx264/ |
| Teledyne FLIR Blackfly S | https://softwareservices.flir.com/BFS-PGE-50S5/latest/Model/spec.html |
| Basler ace 2 Pro | https://www.baslerweb.com/en/shop/a2a2448-23gcpro/ |
| Allied Vision Alvium U-507c | https://www.alliedvision.com/en/products/area-scan-cameras/alvium/alvium-u/view/1133 |
| IDS GV-5040FA-C-HQ | https://en.ids-imaging.com/store/gv-5040fa-rev-1-2.html |
| Example C-mount lens | https://www.1stvision.com/lens/spec/CBC-/M1228-MPX |