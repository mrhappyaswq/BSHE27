# Wiring and configuration

Target: **GOOUUU ESP32-S3-CAM N16R8** with onboard camera, connected to a Pixhawk running **ArduCopter**. Settings live in [settings.h](../Code/Board%20Settings/settings.h).

| Connection / setting | Value |
| --- | --- |
| Pixhawk TELEM TX to GOOUUU RX | GPIO42 |
| Pixhawk TELEM RX from GOOUUU TX | GPIO41 |
| Ground | Shared between boards |
| UART | UART1, 57600 baud, 8N1, 3.3 V logic |
| Autopilot address | System 1, component 1 |
| Companion address | System 245, component 191 |
| RGB status LED | GPIO48 |
| Console/upload connection | TTL / USB-to-UART bridge, 115200 baud |
| Native video connection | OTG USB-C, GPIO19/20 |

Configure the selected Pixhawk TELEM port for MAVLink with matching baud. Boot is receive-only. The serial `telemetry` command requests 4 Hz streams when linked and idle. Mission readiness requires fresh heartbeat, position, GPS and system-health information; receiving a heartbeat alone is insufficient.

Verify TELEM pinout and power against the actual hardware. Do not connect a Pixhawk power pin to an ESP32 GPIO. Keep propellers removed for bench checks. Physical Pixhawk exchange and flight behavior still need validation.

Camera sensor pins are defined in `Code/Camera/camera_service.cpp`. Exposure and image defaults live in `Code/Board Settings/settings.h`; simulated-altitude profiles are in `Code/Camera/altitude_profile.h`. ArUco marker dimensions, camera calibration and mounting settings are in `Code/ArUco/aruco_config.h` and require real measurements.

External SPI microSD is optional and disabled by default. Its configured pins are SCK38, MISO39, MOSI40 and CS21; verify wiring before enabling it. See the [firmware guide](Camera%20Guide.md) for the full camera pin table, USB behavior and storage details.
