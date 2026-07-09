# Camera System Hardware Pathway

## 1. Purpose

The main idea is to have the whole system work well in pretty serious weather conditions like high heat (100+F), dust, etc. 

We will be splititng the full inference into partly on the edge computer and partly on the cloud
  


---

## 2. Proposed Hardware Components

The proposed camera system would be made of the following main hardware components:

- **Industrial RGB Camera**
  - Captures visible images of the solar panels.
  - Should be rugged enough for outdoor use.
  - Preferably should use a global shutter to reduce motion distortion while the robot is moving.

- **Fixed Lens**
  - Controls the field of view and image sharpness.
  - A fixed lens is preferred over autofocus because it is more reliable in vibration, glare, and dust.
  - The lens should be chosen based on the final camera mounting distance from the panel.


- **Polarizing Filter**
  - Helps reduce glare from the glass surface of the solar panels.
  - Should be tested because it may reduce brightness and require exposure adjustments.

- **Sealed Protective Enclosure**
  - Protects the camera from dust, heat, vibration, and water splashes.
  - Should have an appropriate IP rating, likely IP65 or higher depending on splash exposure.
  - Should allow the camera to be securely mounted and still have a clear view of the panel.

- **Edge Computer**
  - Controls the camera and handles image capture.
  - Adds metadata such as timestamp, robot ID, mission ID, GPS coordinates, row, and panel number.
  - Stores images locally and prepares them for the analysis pipeline.

- **Local SSD Storage**
  - Stores images during the mission.
  - Prevents data loss if the robot does not have a stable internet connection.
  - Should have enough capacity for at least one full mission.

- **Robot GPS/Odometry Connection**
  - Provides location and movement information for each image.
  - Allows every image to be georeferenced.
  - Helps connect each image to the correct row, panel, and mission.

- **DC-DC Converter**
  - Converts robot power into the voltage needed by the camera and edge computer.
  - Protects the system from power instability.
  - Should include proper fusing or electrical protection.

- **Rugged Cables and Connectors**
  - Connect the camera, edge computer, power system, and robot data interfaces.
  - Should be vibration-resistant and protected from water, dust, and moving parts.
  - Locking connectors are preferred so cables do not disconnect during robot movement.

- **Mechanical Mounting Bracket**
  - Holds the camera in the correct position and angle.
  - Should be rigid enough to reduce vibration.
  - Should allow adjustment during testing before the final mounting angle is chosen.

- **Cable Routing and Protection**
  - Keeps wires away from the brush, wheels, moving parts, and sharp edges.
  - Prevents cable damage during field operation.
  - Should be planned as part of the final installation design.

---
## 3. Main Hardware Pathway

The proposed hardware pathway is:

```mermaid
flowchart LR
    A[Solar Panel / Target Area] --> B[Industrial RGB Camera]
    B --> C[Lens + Polarized Filter]
    C --> D[Sealed Camera Enclosure]
    D --> E[Edge Computer]
    E --> F[Local Storage]
    E --> G[Robot GPS / Odometry Metadata]
    F --> H[Upload]

    I[Robot Power System] --> J[Protected DC-DC Converter]
    J --> E
    J --> B
```
---

## 4. Proposed Items

- **Camera: *LUCID Triton TRI050S-CC***
  - Justification written in `CameraChoice.md`.
- **Edge Computer: *RUBIK Pi 3***
  - Justification written in `EdgeComputerChoice.md`.
- **Local Storage: *WD Blue SN5000 2TB NVMe M.2 2280 SSD***
  - Fits the RUBIK Pi 3 system because it uses the required **M.2 2280 NVMe** 
  - The **2TB capacity** gives the system plenty of room for for lots of storage incase theres no wifi or ocnnection possible.
  - will integrate into the system very easily. 
- **Lens: *LUCID / Universe NF120-5M-C 12mm C-Mount 5MP 2/3" Lens* - ~$260**
  - Compatible with the LUCID Triton TRI050S-CC because it uses a C-mount and supports 2/3" sensors.
  - Rated for 5MP imaging, matching the 5MP resolution of the selected Triton camera.
  - The 12mm focal length provides a big field of view for the  vision system without being wide or distorted.
  - Manual focus and manual iris are suitable for a fixed-mounted machine vision setup where the camera-to-object distance will not constantly change.
  - Compact and lightweight, making it easy to mechanically integrate with the camera enclosure or mounting system.
  - Listed by LUCID as compatible with Triton camera models, reducing integration risk.
- **Optical Filter: *Edmund Optics M22.5 × 0.50 Machine Vision Mounted Linear Glass Polarizing Filter***
  - Recommended because the target surface is **solar panels in direct sunlight**, which can create strong glare and reflections from the glass surface.
  - Helps reduce specular glare and bright hot spots, allowing the camera to capture the actual solar panel surface more clearly.
  - Fits the camera lens, which uses an **M22.5 × 0.5mm** filter thread.
  - The rotating mount allows the filter angle to be adjusted during setup for maximum glare reduction.
  - The locking thumbscrew helps keep the polarizer orientation fixed after adjustment, which is useful for a mounted field system.
  - Improves image consistency and contrast, which helps the computer vision system avoid being confused by sunlight reflections.