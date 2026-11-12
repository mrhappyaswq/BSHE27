# XIAO ESP32-S3 Sense QR camera integration

## What is implemented

The existing ESP32 WROOM-32S keeps its MicroPython MAVLink connection to the
ArduCopter flight controller. A second board, the **Seeed Studio XIAO ESP32-S3
Sense**, captures and decodes QR images onboard using the included camera.
It sends QR corners to the WROOM through a separate wired UART. This design
does not need a Raspberry Pi, laptop or Wi-Fi during flight.

The XIAO uses Arduino/C++ firmware, not the project's MicroPython image.
Current Sense kits may include an OV5640 or OV3660 camera; older OV2640 kits
are also supported by the camera driver. Buy the **Sense** kit with its
matched camera expansion board. Seeed is transitioning camera sensors, so
confirm the supplied sensor and board revision when ordering. The firmware
prints the detected sensor ID on USB. Do not substitute an arbitrary camera
ribbon cable/module based only on connector size.

See [Seeed hardware documentation](https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/)
and the [firmware setup](../firmware/xiao_qr_camera/README.md).

## Hardware and wiring

Required parts: existing WROOM-32S and ArduCopter FC, one XIAO ESP32-S3 Sense
kit with supplied camera, USB data cable, three UART wires, a rigid downward
mount, and a regulated supply. A FAT32 microSD card is optional for bench
photos; QR tracking does not require storage.

| Connection | WROOM-32S | XIAO ESP32-S3 Sense |
| --- | --- | --- |
| Camera data to WROOM | GPIO16 / UART2 RX | D6 / GPIO43 TX |
| Capture requests to camera | GPIO17 / UART2 TX | D7 / GPIO44 RX |
| Common reference | GND | GND |
| Serial settings | 115200, 8N1 | 115200, 8N1 |

The WROOM's existing FC link stays on UART1 TX33/RX32 at 57600 baud. The XIAO
camera firmware reserves D6/D7 for this connection; the Sense camera and SD
pins are listed separately in its firmware README. Defaults apply to the
existing **WROOM** board, not WROVER boards that use GPIO16/17 for PSRAM.

Signals are **3.3 V logic**. Power each board from its documented regulated
input; never connect the drone battery directly to a GPIO or 5 V pin. For
initial bench checks use separate USB power with common ground. For onboard
power, provision a regulated 5 V supply rated at least 2 A total for these
two boards, with margin, and validate voltage at the boards during capture,
SD writes and FC traffic. This is a design allowance, not measured power
consumption. Connect the XIAO's 5 V pin according to Seeed's external-power
instructions, and avoid simultaneous external 5 V/USB backfeeding. Do not
assume the FC telemetry port can power both boards.

Mount the camera pointing straight down, with **image top toward drone
forward** and **image right toward drone right**. Keep mirroring and image
rotation disabled. Align the optical center with the desired touchdown
center; an offset camera will center itself over the code, not necessarily
the aircraft's center. The current controller does not compensate offsets.

## Firmware installation

1. In VS Code install the PlatformIO IDE extension.
2. Open `firmware/xiao_qr_camera` as its own PlatformIO project.
3. Select the XIAO USB port, then **Build** and **Upload**. This flashes the
   XIAO only. Follow the firmware README for its pinned build dependencies,
   BOOT/reset procedure, camera settings and SD details.
4. On the WROOM, upload this project's `device/` Python files using the
   existing **Upload ESP32** task. Verify it targets the WROOM USB port.
5. Verify `device/config.py` against your wiring. Camera UART settings,
   payload, freshness budget, translation gains and yaw limits are grouped
   at the end. Camera firmware and WROOM must use the same target payload.

Neither firmware automatically arms the aircraft. The WROOM boot entry
point remains a passive telemetry monitor. No flight settings are changed
on the FC by the camera diagnostic.

## QR target and nonflight checks

Generate a normal, unmirrored QR code containing exactly `BSHE27-LAND`.
Use a matte, flat print with a clear white quiet zone. The printed code's
canonical top defines the desired aircraft heading. A generic QR with a
different text/URL is intentionally ignored. Multiple matching visible
codes are ambiguous and are rejected by the firmware.

Remove propellers and keep the aircraft disarmed for these checks. Run the
diagnostic on the **WROOM** (replace COM4 with its USB port):

```powershell
.\.venv\Scripts\python.exe -m mpremote connect COM4 run device/diagnostics/qr_camera.py
```

The diagnostic prints image center and clockwise yaw for ten seconds and
sends no flight commands. QVGA image center is `(160, 120)`.

| Move/rotate the visible QR | Expected diagnostic result |
| --- | --- |
| Toward image right | Center x increases |
| Toward image bottom | Center y increases |
| Rotate QR clockwise in the camera view | Positive yaw |
| Hide it, unplug camera UART, or show different payload | Absent/stale |
| Present a rotated code at 90/180 degrees | Rotation changes; corners retain QR identity |

Check detection at the intended starting height, throughout descent, under
real light, vibration and tilt. A larger marker helps distant detection but
can leave the field of view near the ground. No marker size or maximum
acquisition height has been validated yet. The sensor's maximum megapixel
resolution does not determine the QR detection rate.

The WROOM rejects a capture older than **350 ms from the scan request**,
including acquisition, decoding and UART transmission. This is a configured
budget, not a measured frame rate. If the diagnostic stays absent, check
payload, wiring, focus, field of view and USB error output before changing
the budget. Measure end-to-end latency and missed detections on the actual
hardware; no detection or landing performance is promised by compilation.
The pinned driver does not command OV5640 autofocus; verify the supplied
lens produces sharp images at all intended distances.

To save a **bench-only QVGA grayscale JPEG** on the XIAO microSD, use a new
camera session:

```powershell
.\.venv\Scripts\python.exe -m mpremote connect COM4 exec "from diagnostics.qr_camera import photo; photo()"
```

The returned `/photos/...jpg` path is on the XIAO card, not the WROOM or PC.
Power down before removing the card and read it with a card reader. Firmware
chooses a new filename instead of overwriting old photos, and reports card,
capture and write errors. This is not automatic mission-waypoint photography.
The blocking photo helper must not be used during flight; QR scans use the
nonblocking UART client instead. Photos currently have no GPS/time metadata.

## QR landing mission

The new mission is separate from the existing ArUco examples:

```powershell
.\.venv\Scripts\python.exe -m mpremote connect COM4 run device/missions/qr_landing.py
```

**That explicit command arms and flies** once camera preflight and existing
autopilot checks pass. First validate the control behavior in SITL with
synthetic target input, then validate the physical camera separately. A
camera photographs its real surroundings, not the simulated ground. Do not
treat passing host tests as SITL or physical flight validation.

The mission first requires three distinct fresh matching QR captures while disarmed, then runs
the existing GPS/prearm checks, takes off to 1.5 m and uses GUIDED body
velocity plus yaw-rate commands. It moves toward the QR center and rotates
toward its canonical top. Descent starts only after centering within 10
pixels and heading within 5 degrees for at least 500 ms across at least
three distinct captures. Gains and tolerances are configurable. Missing or
stale detections cancel translation, descent and rotation commands; a pilot
mode change interrupts the mission.

This controller **does not use `LANDING_TARGET` or configure `PLND_*`**. It
uses the existing GUIDED mission architecture, extended with yaw rate.
[ArduPilot documents this velocity/yaw-rate command interface](https://ardupilot.org/dev/docs/copter-commands-in-guided-mode.html).

## Limits and failure behavior

- QR corners provide image-plane center and approximate rotation. This is
  not calibrated 3D pose estimation; tilt, lens distortion, vibration and
  rolling shutter affect results. There is no validated centimeter-level
  touchdown or heading accuracy.
- Altitude currently comes from FC height **relative to home**, not measured
  height above the QR. Initial tests require a stationary pad at home
  elevation and a validated altitude estimate. A rangefinder and calibrated
  camera geometry are recommended for a later precision-touchdown design.
- Once aligned at or below `LANDING_ALTITUDE` (0.2 m by default), control
  switches to ordinary LAND. QR translation/heading corrections end at that
  handoff; drift or heading changes afterward are not corrected here.
- After prolonged marker loss (5 s) or mission timeout (60 s), the existing
  mission runner attempts **ordinary LAND** if still armed in GUIDED. That
  can land away from the QR. Pilot overrides are respected. Configure and
  validate FC link-loss failsafes separately.
- Automatic waypoint photography, high-resolution color photos, metric pose
  estimation, automatic focus control and ground-station video are outside
  this implementation.

## Software verification

Run the host tests described in [development](development.md). New tests
exercise CRC framing, fragmentation, wrong-target rejection, late/stale
images, UART recovery, canonical corner geometry, photo failures, yaw
encoding, alignment gating and marker loss. Build the separate XIAO firmware
with PlatformIO. Neither check flashes a board or validates flight hardware.

Wire protocol: UTF-8 JSON followed by `*HHHH\n`, where `HHHH` is uppercase
CRC-16/CCITT-FALSE over JSON bytes (polynomial 0x1021, initial 0xFFFF).
Requests contain `v=1`, randomized/incrementing `id`, and `op=scan|photo`.
Responses echo the request ID. QR corners are canonical top-left, top-right,
bottom-right, bottom-left; they are **never sorted by screen position**.
The client has only one request outstanding and expires images using its
own request time, preventing a delayed UART reply from refreshing old data.
