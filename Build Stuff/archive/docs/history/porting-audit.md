# Audit of the two original branches

The desktop-source findings below still apply to the preserved samples.
The newer MicroPython conversion has now been integrated separately in
`device/`; see [its setup guide](../missions.md).

Neither `Michael` nor `precision_landing` is a MicroPython ESP32 project.
Their `.py` files in `reference/desktop/` use CPython packages and operating-system
services intended for a PC or Raspberry Pi. They are examples to review, not
scripts to flash to the board.

| Original dependency / feature | ESP32 MicroPython assessment | Sensible destination |
| --- | --- | --- |
| `dronekit` (`Vehicle`, arm, GUIDED, takeoff, goto) | CPython package; no direct MicroPython drop-in | Pi/PC, or rewrite selected features with MAVLink |
| `pymavlink` | CPython package; no direct drop-in | Pi/PC; on ESP32 use a small protocol implementation for selected messages |
| `cv2`, `cv2.aruco`, `solvePnP`, USB camera | Desktop OpenCV pipeline; not runnable as written on WROOM ESP32 | Pi/PC with camera, or a major redesign on more capable hardware |
| `numpy` | Desktop array library; existing scripts depend on it | Pi/PC; basic arithmetic can be rewritten on ESP32 |
| `serial.tools.list_ports`, `/dev/serial/by-id`, `glob`, `os.path.realpath` | Host serial-device discovery | Replace with fixed `machine.UART` GPIO assignment |
| `cv.imshow`, `cv.waitKey` | Requires a desktop UI | Keep for bench tests on Pi/PC |
| `time`, `math`, coordinate offsets | Most operations portable with minor edits | ESP32, if mission logic is separately designed and tested |
| `camera.yaml` | Calibration data, not executable code | Keep alongside Pi/PC vision code |

`precision_landing.py` sends MAVLink `LANDING_TARGET` using OpenCV detection
and camera calibration. An ESP32 could relay or generate a chosen MAVLink
message after another device supplies validated target coordinates, but the
camera detector and pose estimation cannot be copied to this WROOM board.
The newer MicroPython implementations in `device/` add a minimal MAVLink
client and marker-provider-based guided landing; they do not implement
the original OpenCV detector or the LANDING_TARGET precision-landing
pipeline. The passive monitor consumes signatures without authenticating
them, while the new control helper rejects signed MAVLink telemetry.

Existing source issues worth fixing **on the original CPython side** before a
flight test:

- `precision_landing.py` reads calibration key `dist_coeffs`; `camera.yaml`
  stores it as `distortion_coefficients`. That makes the loaded distortion
  matrix empty and breaks pose estimation.
- `precision_landing.py` uses `/dev/ttyA0` for the Pi UART; verify whether the
  intended device is `/dev/ttyAMA0` or another port on that Pi.
- `aruco_landing.py` uses `glob` without importing it, and calls takeoff with
  no active `vehicle` created in the live code path.
- `aruco_moveGPS.py` and `moveGPS.py` refer to `serial.tools.list_ports`
  without importing `serial`.
- `moveGPS.py` dedents the return and land sequence outside its
  `if __name__ == "__main__"` guard; importing the file runs code using
  variables created only inside that guard.
- The ArUco scripts use differing OpenCV ArUco APIs; pin a working OpenCV
  version and test with a camera before relying on them.
- Most motion scripts wait indefinitely without command timeouts or a
  demonstrated lost-link response. Flight use needs explicit failsafe design.

The calibration mismatch and the desktop dependencies are facts from the
preserved files, not claims that the ESP32 starter has corrected them.
