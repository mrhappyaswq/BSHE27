# C++ migration feature audit

Reviewed the tracked `device/` application and diagnostics, both Arduino projects, desktop mission examples, VS Code tasks, and the newer GOOUUU configuration, camera dashboard, telemetry and LED sources preserved under `local/board-app-backup-20261119` and `local/s3-migration-stage`. The local backups establish the single-board GOOUUU wiring and recent color camera behavior; they are preserved as local evidence.

| Feature found | Active C++ replacement |
| --- | --- |
| MicroPython boot routing | Arduino setup/loop; passive boot only |
| Separate WROOM plus XIAO camera | One GOOUUU N16R8 with onboard sensor-JPEG camera |
| Camera webpage and mobile access | Self-contained responsive page on local AP, no external assets |
| Live JPEG video, stop/start, snapshot | Color QVGA multipart stream on port 81; snapshot on port 80 |
| Passive Pixhawk UART heartbeat monitor | CRC-validated MAVLink 1/2, target source/autopilot filtering, byte/heartbeat/error counters |
| Dashboard telemetry | Link, armed/mode, position freshness, altitude, GPS, battery, vision backend, mission state and errors |
| MAVLink flight client | C++ UART client, bounded polling, unsigned framing, stream requests, companion heartbeat during explicit sessions, command ACKs |
| Mode, arm, takeoff, GPS setpoints, body velocity and yaw | C++ GUIDED/LAND state machine; same frames and velocity masks |
| Hover 10 m / 10 s and hover GPS 2 m / 5 s | `run hover`, `run hover_gps` |
| Fly 3 m north, return, land | `run move_gps` |
| 20 m circle at 10 m altitude | `run circle`, 36 segments, closed circle, return to origin |
| QR payload/corners and yaw alignment | Removed from the active firmware at user request; quirc excluded from the build |
| QR preflight and landing | Removed; the command is rejected before flight |
| ArUco landing and GPS-return landing | `run aruco_landing`, `run aruco_move_gps`; real external detector sends USB serial center observations |
| ArUco detection / metric pose tracker | Previously external hooks, not an installed onboard decoder; C++ center input supported, metric pose display not ported |
| Bench photo saving | HTTP JPEG download; optional external SPI SD and `photo` command; disabled until storage wiring is confirmed |
| Status LED | GPIO48 RGB pulses for waiting, linked, mission and fault; fewer patterns than legacy diagnostic library |
| Serial diagnostics and upload | PlatformIO monitor/build/upload and C++ `status`, `telemetry`, `photo` commands |
| Wi-Fi tuning / phone transfer experiments | Stable local AP and ordinary browser JPEG download; experimental radio stress scripts remain in `local/` |
| Host test suite | New tests run the actual C++ parser/client/state machine with simulated UART/time and independent pymavlink packets; Python tests remain legacy |

The application files were written for this migration. The pinned Arduino/Espressif libraries are reused; the preserved ISC-licensed quirc source is now excluded. The firmware was subsequently uploaded to the connected ESP32-S3 on COM4; passive startup was confirmed over serial. No old repository files were deleted, and the preexisting camera edits were preserved. Root setup docs and VS Code defaults now select C++.

Outstanding hardware validation: correct board/PSRAM detection, camera sensor/color/orientation, Pixhawk port configuration and UART exchange, timing under camera/Wi-Fi load, external SD wiring, SITL mission behavior, and controlled flight. ArUco decoding still requires an external detector. External marker landing height thresholds use relative home altitude and require matching terrain assumptions. MAVLink signing is unsupported and rejected.

## Camera transport follow-up

The dashboard now compares completed onboard pipeline FPS with actual browser decoded-frame FPS over Wi-Fi and native USB. Native USB Serial/JTAG serves a read-only framed JPEG protocol, while CH340 remains the TTL console. A single frame producer shares immutable JPEGs across viewers. Added a local Edge/Chrome viewer, download endpoint, VS Code launch task, binary-header tests and simulated browser transport tests. The camera board's live serial readings confirmed approximately 7.4 processed FPS; transfer benchmarks are separate from that onboard measurement.
