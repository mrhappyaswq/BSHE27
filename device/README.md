# ESP32 source

Only Python files in this folder are deployed. Keep host scripts in `tools/`
at the project root and tests in `tests/`.

| Path | Responsibility |
| --- | --- |
| `main.py` | Passive boot monitor |
| `config.py` | Shared UART, MAVLink IDs and mission limits |
| `banshee/flight.py` | Mission lifecycle, takeoff, waypoints and landing |
| `banshee/mavlink/vehicle.py` | Cooperative UART/MAVLink client |
| `banshee/mavlink/heartbeat.py` | Receive-only heartbeat parser |
| `banshee/vision.py` | Camera-provider registration and validation |
| `banshee/compat.py` | MicroPython/desktop timing bridge |
| `missions/` | Explicit flight entry points |
| `diagnostics/` | Telemetry and marker inspection |

The [uploader](../tools/esp32.py) preserves these package paths on the board
and installs `main.py` last. Each module uses absolute imports from the board
root. See the [mission guide](../docs/missions.md) before running a mission.
