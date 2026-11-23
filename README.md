# BSHE27 — GOOUUU ESP32-S3

The active firmware is now **C++ for one GOOUUU ESP32-S3-CAM N16R8**, connected directly to an ArduCopter Pixhawk. No MicroPython runtime or XIAO coprocessor is required.

Start with the [C++ firmware guide](firmware/goouuu_esp32_s3/README.md) for wiring, build/upload, Wi-Fi, telemetry and missions.

For a fresh clone, open this branch's `BSHE27.code-workspace` and install the recommended PlatformIO IDE extension. All application source and the USB viewer live in this checkout; no adjacent project or developer-specific tool paths are required. See [setup](SETUP.md).

In VS Code, **Ctrl+Shift+B** runs **GOOUUU: Build and upload C++**. Disconnect the USB viewer first. Use **GOOUUU: Build** for compilation only and **GOOUUU: Monitor** for the console from Terminal → Run Task. Boot starts the camera dashboard and passive Pixhawk listener. Missions require explicit serial commands.

Join Wi-Fi **BSHE27-Camera**, password **password**, then open **http://192.168.4.1/** for a telemetry-only latency test, heartbeat freshness, optional camera video, one-shot snapshots, and percentage/multiplier comparisons of latency and payload size. For continuous wired viewing without Wi-Fi, connect the **OTG USB-C** port and run **GOOUUU: Open USB camera**, then click **Connect USB** in Edge/Chrome and select the Espressif device. The viewer shows live FPS, transfer timing, frame count and stale-video warnings.

| Location | Purpose |
| --- | --- |
| `firmware/goouuu_esp32_s3/` | Active C++ application, settings, missions and host tests |
| [Feature migration audit](docs/cpp-migration.md) | Previous features, replacement behavior and limits |
| `device/`, `tools/esp32.py`, `tests/` | Preserved legacy MicroPython code and tests |
| `firmware/camera_web/`, `firmware/xiao_qr_camera/` | Preserved earlier C++ experiments |
| `reference/`, `docs/history/`, `local/` | Original examples, older documentation and local backups |

Older architecture, mission and hardware guides describe the legacy system; the active firmware guide supersedes their board pins and upload instructions. Existing uncommitted camera changes have been retained. The default VS Code tasks use the new C++ firmware; older tasks are labeled Legacy.

The new firmware has build and simulated C++ protocol/mission checks. The C++ firmware was uploaded to COM4 and its passive serial status was confirmed. Physical Pixhawk communication, camera timing and flight still require validation.
