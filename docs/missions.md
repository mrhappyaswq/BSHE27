# Missions and diagnostics

Upload the project first. Run one script explicitly from the project root;
substitute the board's USB COM port. Flight commands below arm and fly when
autopilot checks pass. GPS-assisted GUIDED mode and controlled hardware/SITL
validation are required.

| Script under `device/` | Behavior |
| --- | --- |
| `missions/hover.py` | 2 m takeoff, 5 s hover, land |
| `missions/hover_gps.py` | 10 m takeoff, 10 s hover, land |
| `missions/move_gps.py` | 1.5 m takeoff, 3 m north, hold 10 s, return, hold 10 s, land |
| `missions/circle.py` | 10 m takeoff, 20 m radius circle, return, hold 5 s, land |
| `missions/aruco_landing.py` | 1.5 m takeoff, hold 3 s, marker alignment and landing |
| `missions/aruco_move_gps.py` | North/return flight followed by marker alignment and landing |
| `diagnostics/telemetry.py` | Five-second UART/telemetry check; no arming or movement |
| `diagnostics/marker_tracker.py` | Print camera-provided marker poses; no flight commands |

```powershell
.\.venv\Scripts\python.exe -m mpremote connect COM4 run device/missions/hover.py
```

Altitude is in metres relative to autopilot home. The return location is
captured after takeoff. All flight scripts require GPS readiness; the short
hover is not an indoor/no-GPS implementation. Reset runs only the passive
`main.py` monitor, and importing a mission does not start it.

## Camera integration

The ESP32 code supplies a vision interface, not an OpenCV detector. A camera
or external vision processor must supply fresh target coordinates. ArUco
entry points fail before connecting or arming when no provider is registered.

Create a board-side entry script with your real camera driver:

```python
from banshee import vision
from missions import aruco_landing
from your_camera_driver import latest_marker

vision.set_marker_provider(latest_marker)
aruco_landing.main()
```

`your_camera_driver` is an integration example, not an included module. Its
nonblocking `latest_marker()` must select the desired marker ID and return
`(cx, cy, image_width, image_height)`, or `None` when missing/stale. It must
expire old packets itself. The pixel origin is top-left, image top points
forward, and image right points to vehicle right. Verify the axis signs in
`device/config.py` for the actual camera mounting.

Descent uses positive-down body NED velocity only while the marker is
centered. Marker loss sends zero velocity; a timeout requests normal LAND
while the vehicle remains armed in GUIDED. This does not guarantee landing
on the marker. Provider calls must return quickly so heartbeat processing
continues.

For the pose tracker, register `vision.set_pose_provider(provider)`, then call
`diagnostics.marker_tracker.main()`. The provider returns an iterable of
`(x, y, z)` positions in metres.

## Mission handling

Shared flight functions check telemetry freshness, command acknowledgement,
waypoint arrival and bounded timeouts. They refuse to start on an armed
vehicle, and stop guided commands if the pilot changes mode. Other errors
attempt LAND only if the vehicle remains armed and GUIDED. Link loss or power
failure still needs the autopilot's configured failsafes.

## Renamed entry points

The active scripts now use consistent names: `hoverGPS.py` → `hover_gps.py`,
`moveGPS.py` → `move_gps.py`, `cricle.py` → `circle.py`, and
`aruco_moveGPS.py` → `aruco_move_gps.py`. Their original desktop filenames
remain preserved under `reference/desktop/`.
