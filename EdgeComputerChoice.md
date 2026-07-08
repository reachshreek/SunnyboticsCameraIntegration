# Edge Computer Choice

## Required Edge Computer Tasks

The edge computer should be able to:

- Control the industrial RGB camera
- Capture images while the robot is moving
- Add metadata to each image
- Store images locally during the mission
- Run light preprocessing or quality checks
- Prepare data for cloud upload
- Log errors and system status

Important metadata includes:

- Timestamp
- GPS coordinates
- Odometry data
- Robot ID
- Mission ID
- Row number
- Panel number
- Camera settings

---

## Edge Computer Options

| Feature | RUBIK Pi 3 | NVIDIA Jetson Orin Nano |
|---|---|---|
| Main purpose | Edge AI development board | High-performance edge AI computer |
| AI performance | 12 TOPS | Up to 67 TOPS |
| Memory | 8 GB LPDDR4x | 8 GB LPDDR5 |
| Storage support | 128 GB onboard UFS + M.2 Key M | microSD + external NVMe |
| Ethernet | 1000M Ethernet | Ethernet available on developer kit |
| USB | USB 3.0 and USB-C available | USB available on developer kit |
| Power | 12V 3A USB-C PD input | 7W–25W operating range |
| Best use case | Capture, metadata, storage, light inference, cloud upload | Heavy local AI inference |
| Project fit | Preferred first choice | Backup option |

---

## Why RUBIK Pi Is Preferred

RUBIK Pi is preferred because it better matches the actual workload of this project.

The project does not require full inference to happen on the robot, so we don't need a super strong computer. 


Main reasons for choosing RUBIK Pi:

- Enough compute for image capture and metadata handling
- 12 TOPS AI capability for light edge inference
- 8 GB RAM
- 128 GB onboard storage
- M.2 support for local SSD storage
- Gigabit Ethernet for industrial camera connection
- USB 3.0 for additional peripherals
- Lower complexity than a heavier AI platform
- Better fit for split edge/cloud inference

---

## Why Jetson Orin Nano Is Still a Backup

The Jetson Orin Nano is more powerful than the RUBIK Pi. It is a strong option if later, we push the project to do all processing on the robot.


However, for the first version of this project, the extra compute is not needed, and the Nano is too much of a heat and power sink.

The Rubik runs between 4-8W, while the Jetson runs 7-25W. The higher power draw will mitigate the operational time that the robot can do, hence why I chose the Rubik. 

Because of this, Jetson Orin Nano is kept as a backup.

---

## Camera Connection Plan

The preferred camera, **LUCID Triton TRI050S-CC**, is expected to connect through **GigE / Ethernet**.

Because the camera supports **PoE**, the system will likely need a **PoE injector** or **PoE switch**. The RUBIK Pi cannot directly do PoE.

Basic connection pathway:

```text
LUCID Triton Camera
        ↓
Ethernet Cable
        ↓
PoE Injector / PoE Switch
        ↓
RUBIK Pi 3
        ↓
Local SSD + Cloud Upload