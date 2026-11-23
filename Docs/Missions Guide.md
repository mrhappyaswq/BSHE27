# Missions and diagnostics

Open **GOOUUU: Monitor** at 115200 baud. Commands are entered on the TTL console, followed by Enter. No mission runs on reset, upload, Wi-Fi connection or webpage access. The native USB camera protocol does not start flight missions.

| Command | Behavior |
| --- | --- |
| `status` | Report link, mission, camera, USB, exposure and Wi-Fi state |
| `telemetry` | Request 4 Hz Pixhawk telemetry when linked and idle |
| `photo` | Save a JPEG to configured external SD; requires idle/disarmed state and enabled storage |
| `run hover` | Take off to 10 m, hold 10 s, LAND |
| `run hover_gps` | Take off to 2 m, hold 5 s, LAND |
| `run move_gps` | Take off to 1.5 m, fly 3 m north, hold, return, hold, LAND |
| `run circle` | Take off to 10 m, follow a 20 m radius circle in 36 segments, return, hold, LAND |
| `run aruco_landing` | External detector preflight, take off to 1.5 m, center and descend |
| `run aruco_move_gps` | External detector preflight, GPS out-and-back, center and descend |
| `abort` | Request LAND while the mission still owns armed GUIDED flight; otherwise stop without changing pilot mode |

Mission logic is in [mission.h](../Code/Flight%20Missions/mission.h). All missions require fresh disarmed ArduCopter heartbeats, prearm health, 3D GPS and position telemetry. They are not indoor/no-GPS implementations. Commands require acknowledgments and relevant state confirmation. Physical UART, SITL and controlled flight validation remain necessary.

## Marker input

The onboard ArUco detector is a bench preview and does not feed flight missions. The ArUco missions require a separate provider to send the following line to the TTL console at least 10 times per second:

```text
marker cx cy width height
```

Supply the selected marker's center and image dimensions. Input must be finite and inside the image; observations expire after 350 ms. The mission uses center alignment, not the preview's metric pose or proposed velocities. The provider needs an independent camera feed because browser video delivery is paused during missions. Verify camera axes and movement signs before integration.

See the [firmware guide](Camera%20Guide.md) for timeouts, link-loss behavior, mission ownership and landing limitations. Laptop diagnostics for USB video, camera controls and Wi-Fi telemetry are in `Helpers/`; they are separate from flight missions.
