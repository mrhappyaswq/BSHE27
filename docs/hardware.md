# Wiring and configuration

The configured board is a WROOM Dev Board 32S. Its shared settings live in
[`device/config.py`](../device/config.py); the boot monitor and mission client
both import this file.

| Setting | Current value |
| --- | --- |
| UART | 1 |
| ESP32 RX | GPIO32 ← Pixhawk TELEM TX |
| ESP32 TX | GPIO33 → Pixhawk TELEM RX |
| Baud | 57600 |
| Ground | ESP32 and Pixhawk share ground |
| Autopilot address | System 1, component 1 |
| Companion address | System 245, component 191 |

The passive boot monitor needs only the receive signal and ground. The mission
client and telemetry check need both UART directions. Verify the exact TELEM
pinout, signal voltage and regulated ESP32 power supply against your boards;
do not connect 5 V logic to ESP32 GPIO. Keep props removed for bench checks.

Set the selected Pixhawk port to MAVLink with matching baud. The helper
transmits MAVLink 1 and receives unsigned MAVLink 1 or 2. It implements
ArduCopter GUIDED/LAND, with command acknowledgements and heartbeat checks.
PX4 Offboard and MAVLink signing are not implemented by this client.

`HEARTBEAT`, `SYS_STATUS`, `GPS_RAW_INT` and `GLOBAL_POSITION_INT` must be sent.
The client requests all telemetry streams at 4 Hz; autopilot settings may
override the request. Readiness requires a STANDBY heartbeat, the enabled and
healthy prearm-check bit, and fresh 3D GPS/global position. Autopilot checks
remain authoritative. Configure its link-loss failsafes before flight.

Camera orientation, gains, descent limits and timeouts also live in
`device/config.py`. See [camera integration](missions.md#camera-integration).
