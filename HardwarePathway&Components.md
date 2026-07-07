# Camera System Hardware Pathway

## 1. Purpose

The goal of this camera system is to allow a Sunnybotics robot to capture useful, georeferenced images of solar panels during real field missions.

The system must work without manual intervention during a mission and must produce images that are clear enough for the existing analysis pipeline. Because the robot operates outdoors and near the cleaning mechanism, the hardware must survive heat, vibration, dust, and possible water splashes.

This document explains the proposed hardware pathway, why each major component is needed, and what the overall system looks like.

---

## 2. Main Hardware Pathway

The proposed hardware pathway is:

```mermaid
flowchart LR
    A[Solar Panel / Target Area] --> B[Industrial RGB Camera]
    B --> C[Fixed Lens + Protective Window / Optional Polarizer]
    C --> D[Sealed Camera Enclosure]
    D --> E[Edge Computer]
    E --> F[Local Storage]
    E --> G[Robot GPS / Odometry Metadata]
    F --> H[Analysis Pipeline / Data Export]

    I[Robot Power System] --> J[Protected DC-DC Converter]
    J --> E
    J --> B