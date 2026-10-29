# BM27 Banshee

ESP32 MicroPython companion code for a Pixhawk running ArduCopter.

**Start here:** [Quick setup](SETUP.md).

More detail: [board setup](docs/setup.md), [wiring](docs/hardware.md), and
[missions](docs/missions.md).

## Project map

```text
device/                 Code uploaded to the ESP32
  main.py               Passive heartbeat monitor on boot
  config.py             Board pins, UART and mission settings
  banshee/              Shared flight, MAVLink and vision code
  missions/             Hover, GPS, circle and ArUco missions
  diagnostics/          Telemetry check and marker-pose display
tools/                  Desktop upload and monitor commands
tests/                  Unit tests, reference checks and fixtures
docs/                   Setup, wiring, missions and architecture
reference/              Original desktop examples
local/                  Preserved reports, scratch work, firmware and backups
```

## Common actions in VS Code

| Action | Where |
| --- | --- |
| Upload board code | **Upload ESP32** or **Ctrl+Shift+B** |
| View the boot monitor | **ESP32 Monitor** |
| Check the UART link | **Check Pixhawk** |
| Run desktop tests | **Terminal → Run Task → BANSHEE: Run host tests** |
| Change board settings | [`device/config.py`](device/config.py) |

Uploading resets into the passive monitor. Flight missions start only through
an explicit run command. The UART defaults are UART1, TX33, RX32 and 57600 baud;
verify them against your board. ArUco missions require a camera provider.

## Guides

- [Setup and upload](docs/setup.md)
- [Wiring and configuration](docs/hardware.md)
- [Mission catalog and camera integration](docs/missions.md)
- [Code architecture](docs/architecture.md)
- [Development and tests](docs/development.md)
- [Original source and history](reference/README.md)
- Local reports, scratch files, firmware and backups remain in ignored `local/`.

The tests use simulated hardware. Physical UART, camera and flight validation
remain separate checks.
