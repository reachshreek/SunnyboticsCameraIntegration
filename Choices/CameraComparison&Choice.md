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

## Weighted Camera Evaluation

The original qualitative comparison used ratings such as Excellent, Good, and Acceptable. To make the selection more objective and cost-effective, the cameras were reevaluated using a weighted decision matrix. Each criterion is assigned a weight based on its importance to the solar-panel inspection system. Each camera is then scored from 1 to 10, with higher scores representing better suitability.

Before weighted scoring, each camera must satisfy the mandatory minimum requirements of global-shutter operation, compatibility with the selected edge-computing system, and sufficient image resolution for the required field of view and defect-detection target. Cameras that do not meet a mandatory requirement may be removed from consideration regardless of their weighted score.

### Evaluation Criteria and Weights

| Criterion | Weight | Reason for Weight |
|---|:---:|---|
| **Performance** | 25% | The camera must capture sufficiently detailed, low-distortion images while the robot is moving. Resolution, sensor performance, frame rate, and global-shutter operation are considered. |
| **System Compatibility** | 20% | The camera must integrate with the RUBIK Pi, selected network and power hardware, lens, software, and data-transfer architecture. |
| **Cost** | 15% | The selected camera should meet the requirements without unnecessary expense. Required accessories and enclosure costs should also be considered. |
| **Environmental Suitability** | 15% | The camera will operate outdoors near solar panels and must be protected from dust, moisture, vibration, and temperature changes. |
| **Power Consumption** | 10% | Camera power contributes to the total load on the robot's battery and affects operating time. |
| **Size and Weight** | 5% | Smaller and lighter cameras are easier to mount and have less impact on available robot space and payload. |
| **Support and Documentation** | 5% | Datasheets, SDKs, examples, and vendor support reduce integration and maintenance risk. |
| **Availability** | 5% | The camera should be obtainable within the project schedule from a reliable supplier. |
| **Total** | **100%** | |

### Scoring Scale

| Score | Meaning |
|:---:|---|
| 10 | Best fit for the project and significantly exceeds the minimum requirement |
| 9 | Exceeds the requirement with a clear advantage |
| 8 | Fully meets the requirement and is a strong option |
| 7 | Meets the requirement with a minor disadvantage |
| 6 | Meets the minimum acceptable requirement |
| 5 | Marginal fit or requires a meaningful compromise |
| 4 | Falls below the preferred requirement or requires significant modification |
| 3 | Major limitation |
| 2 | Poor suitability |
| 1 | Does not meet the requirement |

### Example Score Assignment: LUCID Triton TRI050S-CC

The following example illustrates how individual scores were assigned using manufacturer datasheets and project requirements.

| Criterion | Score | Justification |
|---|:---:|---|
| **Performance** | **9** | The camera provides a 5.0 MP Sony IMX264 global-shutter sensor with good dynamic range and sensitivity, making it well suited for capturing sharp images of solar panels while the robot is moving. It fully meets the project's imaging requirements but is not scored as a perfect 10 because final image quality must still be verified through field testing. |
| **System Compatibility** | **10** | Supports GigE Vision, PoE, GenICam, C-mount lenses, hardware triggering, and Linux SDKs, allowing straightforward integration with the selected RUBIK Pi edge computer and industrial networking architecture. |
| **Cost** | **10** | At approximately \$550, it is the lowest-cost camera that satisfies the project's technical requirements, making it the best value among the compared options. |
| **Environmental Suitability** | **9** | The Triton family supports an IP67 configuration when paired with the proper lens tube, cables, and accessories. However, the complete camera assembly must still be verified to achieve the required environmental protection. |
| **Power Consumption** | **9** | Typical power consumption of approximately 3.1 W (PoE) is lower than many comparable industrial GigE cameras, minimizing impact on robot battery life. |
| **Size and Weight** | **9** | Compact dimensions (29 × 29 × 45 mm) and low weight (67 g) simplify integration within the robot's limited mounting space. |
| **Support and Documentation** | **8** | LUCID provides comprehensive datasheets, SDKs, and software documentation. Although well documented, its software ecosystem is slightly smaller than that of Basler. |
| **Availability** | **8** | Available from multiple industrial machine vision distributors, although supplier stock may vary depending on region and demand. |

### Weighted Decision Matrix

| Camera | Performance 25% | Compatibility 20% | Cost 15% | Environmental 15% | Power 10% | Size and Weight 5% | Support 5% | Availability 5% | **Weighted Score** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **LUCID Triton TRI050S-CC** | 9 | 9 | 10 | 10 | 9 | 9 | 8 | 8 | **9.25** |
| **Teledyne FLIR Blackfly S BFS-PGE-50S5C-C** | 9 | 9 | 6 | 6 | 9 | 10 | 10 | 7 | **8.10** |
| **Basler ace 2 Pro a2A2448-23gcPRO** | 9 | 9 | 5 | 5 | 8 | 8 | 10 | 8 | **7.65** |
| **Allied Vision Alvium 1800 U-507c** | 9 | 6 | 5 | 5 | 10 | 9 | 8 | 9 | **7.25** |
| **IDS uEye+ FA GV-5040FA-C-HQ** | 5 | 9 | 7 | 10 | 10 | 6 | 8 | 7 | **7.65** |

The weighted score is calculated using:

`Weighted Score = Σ(Camera Score × Criterion Weight)`

For example, the LUCID Triton score is calculated as:

`(9 × 0.25) + (10 × 0.20) + (10 × 0.15) + (9 × 0.15) + (9 × 0.10) + (9 × 0.05) + (8 × 0.05) + (8 × 0.05) = 9.25`

### Score Justification

| Camera | Score Justification |
|---|---|
| **LUCID Triton TRI050S-CC** | Receives the highest score because it combines 5 MP global-shutter imaging, GigE/PoE compatibility, low power consumption, compact dimensions, relatively low cost, and an available IP67 sealing approach. It still requires the correct IP67 lens tube, cables, and mounting hardware. |
| **Teledyne FLIR Blackfly S BFS-PGE-50S5C-C** | Provides strong imaging performance, compact size, GigE/PoE connectivity, and excellent software support. Its higher cost and lack of an IP-rated body reduce its score because a separate sealed enclosure is required. |
| **Basler ace 2 Pro a2A2448-23gcPRO** | Provides strong imaging performance, documentation, and industrial software support. However, it is more expensive, slightly larger and heavier, and only IP30, requiring a complete protective enclosure. |
| **Allied Vision Alvium 1800 U-507c** | Offers strong 5.1 MP performance, low power consumption, compact dimensions, and good availability. Its USB3 interface is less desirable than GigE/PoE for long or vibration-prone robot cable routing, and it requires a sealed enclosure. |
| **IDS uEye+ FA GV-5040FA-C-HQ** | Scores very highly in ruggedness, power consumption, and GigE/PoE compatibility. However, its 1.58 MP resolution provides substantially less image detail than the approximately 5 MP alternatives and may not satisfy the final ground-sampling-distance requirement. |

## Final Camera Selection

The **LUCID Triton TRI050S-CC** received the highest weighted score and remains the recommended camera. Its main advantages are its combination of 5 MP global-shutter imaging, GigE/PoE integration, compact size, low power use, lower purchase cost, and ability to support an IP67 installation with the proper accessories.

The recommendation remains conditional on completing the following verification:

- Confirm that the calculated field of view and ground sampling distance satisfy the minimum defect-detection requirement.
- Confirm compatibility between the selected lens and polarizer thread.
- Define the complete IP67 sealing arrangement, including the lens tube or enclosure, cables, connectors, and polarizer location.
- Confirm camera compatibility with the RUBIK Pi software and network configuration.

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