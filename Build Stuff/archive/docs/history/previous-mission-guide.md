# BANSHEE AVIONICS — ESP32 MicroPython port

The seven missions from the supplied MicroPython conversion are integrated
in BSHE27's `device/` directory. The existing receive-only boot
monitor and original desktop samples are preserved. The supplied source
is retained in `docs/pasted-micropython-source.txt`.

The programs run on an **ESP32 or ESP32-S3 with MicroPython**, connected by UART
to a **Pixhawk running ArduCopter**. Windows/VS Code is the editor and upload
host. DroneKit, OpenCV and NumPy are not required on the board. PX4 Offboard,
other vehicle types and MAVLink signing are not implemented by this helper.

## Files and missions

| File | Behaviour from the attachment |
| --- | --- |
| `hover.py` | Take off to 2 m, hover 5 s, land |
| `hoverGPS.py` | Take off to 10 m, hover 10 s, land |
| `moveGPS.py` | Take off to 1.5 m, fly 3 m north, hold 10 s, return, hold 10 s, land |
| `cricle.py` | Take off to 10 m, fly a 20 m radius circle, return, hold 5 s, land |
| `aruco_landing.py` | Take off to 1.5 m, hold 3 s, align with a marker, descend and land |
| `aruco_moveGPS.py` | Fly the 3 m north/return mission, then land using a marker |
| `aruco_tracker.py` | Print camera-provided marker X/Y/Z poses; no flight commands |
| `telemetry_check.py` | Check UART, heartbeat and telemetry without arming |

`cricle.py` keeps the original spelling. The circle now closes its last segment.
All flight missions use GPS-assisted GUIDED mode; `hover.py` is not an indoor
or no-GPS flight implementation. Altitudes are metres relative to autopilot
home. The point called `home` in the missions is the position captured after
takeoff, as in the attachment.

Shared modules:

- `config.py`: UART pins/baud, MAVLink IDs, limits and timeouts.
- `mavlink_minimal.py`: UART framing, CRC checks, telemetry, heartbeat, command
  acknowledgement, mode, arm, takeoff, GPS targets and body velocity.
- `mission_common.py`: takeoff, waypoint arrival, holds, landing and cleanup.
- `vision.py`: marker and pose provider integration contracts.
- `compat.py`: MicroPython timing with desktop test equivalents.

## Configure the board

Edit `device/config.py` before uploading. UART1 / TX33 / RX32 / 57600 baud
match this project's existing WROOM Dev Board 32S monitor in `device/main.py`.
Verify these against the actual wiring; other board variants may differ.
If you change UART settings, also update the constants in `device/main.py`.
Set the Pixhawk TELEM serial port to matching baud and MAVLink protocol. The
helper sends MAVLink 1 and receives unsigned MAVLink 1 or 2.

For mission communication connect ESP32 GPIO33 (TX) to Pixhawk RX,
Pixhawk TX to ESP32 GPIO32 (RX), and ground to ground. The original boot
monitor still needs only Pixhawk TX and ground for its receive-only check.
Verify the actual TELEM logic voltage and ESP32 power supply against the board
documentation before wiring. Keep props removed for initial communication and
arming tests, and configure the autopilot's link-loss failsafes before flight.

The default autopilot address is system 1 / component 1; source 245 / component
191 identifies this companion. Adjust IDs if your installation differs.
The autopilot must send `HEARTBEAT`, `SYS_STATUS`, `GPS_RAW_INT` and
`GLOBAL_POSITION_INT`. The client requests all telemetry streams at 4 Hz, but
autopilot stream settings may override that request. Prearm readiness requires
the `SYS_STATUS` prearm-check bit to be present, enabled and healthy, plus a
STANDBY heartbeat; GPS missions also require a fresh 3D fix/global position.
Autopilot arming checks remain authoritative and are never bypassed.

## Upload and run in the open BSHE27 project

Use **Upload ESP32** in the VS Code status bar, or **Ctrl+Shift+B**. The task
uploads all runtime modules from `device/`, including the existing `main.py`
and heartbeat parser, then resets the board. Boot continues to run only the
receive-only monitor. The new flight missions require an explicit run command.

Use **Terminal > Run Task > ESP32: Telemetry check** for the new five-second
connection check. It transmits a heartbeat and stream request, but never arms,
changes mode or sends movement commands. Unlike the passive boot monitor, it
requires both UART directions to work.

From the BSHE27 root, with your board's port substituted for COM4:

```powershell
.\.venv\Scripts\python.exe -m mpremote connect list
.\.venv\Scripts\python.exe -m mpremote connect COM4 run device/telemetry_check.py
```

After bench checks, simulator/controlled flight validation and failsafe setup,
an explicit mission command is:

```powershell
.\.venv\Scripts\python.exe -m mpremote connect COM4 run device/hover.py
```

That command **arms, takes off and flies** when autopilot checks pass. Select
one mission per run. Importing mission modules does not start flight. VS Code's
ordinary Python Run button uses desktop Python; these programs need the board's
MicroPython runtime. The existing USB monitor must be closed before another
mpremote task opens the serial port.

## Connect ArUco vision

The attachment supplied empty marker hooks, not a detector or camera driver.
This project keeps that integration explicit: ArUco flight entry points fail
before connecting/arming until a real provider has been registered. Standard
ESP32 boards do not supply the desktop OpenCV pipeline.

Implement a nonblocking provider in your camera/vision-coprocessor driver,
upload it, then register it in a board-side entry script:

```python
import vision
from your_camera_driver import latest_marker
import aruco_landing

# latest_marker() returns (cx, cy, image_width, image_height), or None.
# It must return None for missing/stale packets and select the desired marker ID.
vision.set_marker_provider(latest_marker)
aruco_landing.main()
```

`your_camera_driver` is an integration example, not an included module.
Coordinates use a top-left pixel origin. The expected downward camera mounting
has image top pointing forward and image right pointing to vehicle right.
Verify/configure axis signs, gain, centering tolerance and speed limits in
`config.py` for your installation before flight. Descent occurs only when the
marker is centered. Positive body-NED Z is **down**; the pasted negative
descent velocity has been corrected. Loss of the marker sends zero velocity;
after the configured loss timeout the mission requests ordinary LAND while
the vehicle is still armed and GUIDED. This fallback does not guarantee
landing on a marker.

For `aruco_tracker.py`, register `vision.set_pose_provider(...)` instead; that
provider returns an iterable of `(x, y, z)` poses in metres. Detection and pose
estimation must be supplied by the camera processor. Providers must return
quickly so the cooperative client can keep processing telemetry/heartbeats.

## Changes from the pasted conversion

- Added the missing MAVLink helper, explicit UART configuration and shared
  mission functions; removed the unusable string `UART1` constructors.
- Preserved filenames, target altitudes, offsets, circle radius and hold times.
- Replaced import-time flight execution with explicit `main()` entry points.
- Kept heartbeats and telemetry processing active during waits and holds.
- Added command ACK checks, heartbeat mode/arm confirmation, stale-data checks,
  bounded waits and GPS waypoint arrival checks instead of fixed travel delays.
- Added marker validation, centering before descent, velocity limits, marker
  loss handling and the positive-down correction.
- Refuse to start on an already armed vehicle. A pilot/autopilot mode change
  stops the guided mission. Other mission errors attempt LAND only if the
  vehicle remains armed in GUIDED. Link loss, power failure, or an unresponsive
  board still require the autopilot's configured failsafes.

## Desktop tests

```powershell
python -m unittest discover -s tests -v
```

Tests use fake UARTs, a simulated clock and simulated missions. They check
framing/CRC, MAVLink 1/2 input, truncated MAVLink 2 payloads, source filtering,
ACK handling, data freshness, command encoding, mission timeouts, pilot
override and marker behavior without opening hardware.

Optional interoperability tests decode packets with the generated pymavlink
common dialect and feed its encoded packets back into the client:

```powershell
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

The reference tests skip if pymavlink is absent. It is a desktop test dependency
only. Desktop tests do not establish board compatibility or flight readiness;
UART wiring, firmware parameters, camera behavior, memory use and actual
vehicle responses still require hardware/SITL verification.

## Protocol references

- [MicroPython ESP32 UART reference](https://docs.micropython.org/en/latest/esp32/quickref.html)
- [MicroPython mpremote commands](https://docs.micropython.org/en/latest/reference/mpremote.html)
- [MAVLink framing and serialization](https://mavlink.io/en/guide/serialization.html)
- [MAVLink common messages](https://mavlink.io/en/messages/common.html)
- [ArduCopter GUIDED movement and body-NED directions](https://ardupilot.org/dev/docs/copter-commands-in-guided-mode.html)
- [ArduPilot mode commands and heartbeat confirmation](https://ardupilot.org/dev/docs/mavlink-get-set-flightmode.html)
