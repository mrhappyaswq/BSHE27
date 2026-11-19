# BSHE27

**One ESP32-S3-CAM running MicroPython, connected to the Pixhawk.**
The S3 replaces the WROOM and uses its own camera. No second ESP32 or XIAO
is required. The Pixhawk still runs ArduCopter and controls the aircraft.

## Files

- **Code/** — the Python and webpage files uploaded to the S3.
- **Build Stuff/** — uploader, tests, dependencies list, old work and backups.
- **Guides/** — setup, LED meanings and the code map.

Open [Code Map](Code%20Map.md) for the function guide and block diagram.
The hidden `.venv` Python runtime and `.vscode` integration stay at the project
root so the current tools and running sessions keep working. You do not need
to edit those folders.

## Set up once

1. Open **BSHE27.code-workspace** in VS Code. Connect the board's **TTL USB-C**
   port with a USB data cable. Close Thonny or other serial monitors.
2. In the VS Code terminal:

   ```powershell
   py -3 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install mpremote esptool
   ```

   Skip creating `.venv` if it already exists. VS Code tasks use this environment.
3. Install MicroPython for **ESP32-S3**, not the old ESP32/WROOM image.
   For the N16R8 module, choose **Octal-SPIRAM / spiram-oct**. The official
   [S3 firmware page](https://micropython.org/download/ESP32_GENERIC_S3/)
   describes installation. A full S3 `.bin` is flashed at **0x0**, not 0x1000.
   Flashing firmware erases existing board files; uploading Python files does not
   replace the firmware.
4. **For camera capture/preview**, use an S3 firmware with the
   [MicroPython Camera API](https://github.com/cnadler86/micropython-camera-API/releases)
   (`from camera import Camera`). Choose a generic S3 build with octal PSRAM
   support matching your module. The project supplies camera pins explicitly.
   Plain official firmware is sufficient for MAVLink missions but does not
   supply this camera API. An old `camera.init()`-only build is not compatible
   with this adapter. No Arduino/PlatformIO project is required to run these
   Python files.

## Upload and use

- **Ctrl+Shift+B** uploads `Code/` and restarts into the Wi-Fi/camera app.
- **Terminal → Run Task → S3: Monitor** opens USB output; press RESET to see boot.
- **S3: Check Pixhawk** checks telemetry without arming or moving the aircraft.
- **S3: Camera preview** starts the MicroPython webpage. Join **BSHE27-Camera**,
  password from **Code/config.py → WIFI_PASSWORD**, then open **http://192.168.4.1/**. Use one viewer.
  It serves continuous MJPEG on `/stream`; `/capture` provides a still JPEG.
- **S3: Check landing QR** requires the local decoder described below.

Upload before running apps. Close an open serial monitor with **Ctrl+]** before
starting another task. Stop a running app with Ctrl+C; reset starts the Wi-Fi/camera app again. The dashboard runs video and passive telemetry together. Flight missions
require an explicit start. Wi-Fi settings are in `Code/config.py`.

The tasks use automatic port selection. If multiple boards are connected, set
their `--port` argument in `.vscode/tasks.json` to the S3 port (currently COM4).
The uploader checks that the runtime is an S3 and checks Python syntax before
copying. It transfers temporary files, verifies every file's size and SHA-256,
then installs them with `main.py` last and resets the board. A failed transfer
leaves installed files intact. Power loss during the final installation can
still leave mixed versions; rerun Upload if that happens.

```powershell
.\.venv\Scripts\python.exe "Build Stuff/tools/board.py" list
.\.venv\Scripts\python.exe "Build Stuff/tools/board.py" upload --port COM4
.\.venv\Scripts\python.exe "Build Stuff/tools/board.py" monitor --port COM4
```

The ordinary VS Code Python Run button executes desktop Python. Use the tasks
above for the microcontroller. The optional Task Buttons extension adds toolbar
shortcuts; the built-in task menu works without it.

### Wi-Fi network missing?

After uploading, power-up/reset automatically starts **BSHE27-Camera**.
To start it manually, choose **Terminal → Run Task → S3: Camera preview**.
The app broadcasts a visible 2.4 GHz hotspot on channel 1; password from **Code/config.py → WIFI_PASSWORD**.
Keep the app running and accept "no internet" when joining. Open
**http://192.168.4.1/**. Stopping the app turns the hotspot off; reset automatically starts it again.

The hotspot and HTTP listener start before camera initialization. The page can
show "Starting camera" and a camera fault leaves Wi-Fi diagnostics available.
Standard MicroPython
does not include the required `camera.Camera` driver; the error page explains
this rather than silently hiding the network. A live image still requires
the camera-enabled firmware described above.

**Keep the supplied external antenna connected on this board.** On 2026-11-19,
connecting it restored the phone connection and camera image after partial page
loads, timeouts and repeated reconnects. Seeing the Wi-Fi network or joining it
was not enough to establish a reliable image transfer.

The actual antenna-selector position was not inspected. The seller's
[antenna-selection diagram](https://m.media-amazon.com/images/S/aplus-media-library-service-media/df52a0c5-26a3-43b3-b6da-83622d624860.__CR0,0,970,600_PT0_SX970_V1___.jpg)
illustrates the physical selection; software cannot switch that resistor.

## Pixhawk wiring

Default board: **GOOUUU ESP32-S3-CAM N16R8**, with the onboard camera pin map
in the [board manual, page 4](https://m.media-amazon.com/images/I/D1Q5qrL0OoL.pdf).
Confirm the module marking and board layout before wiring.

| Pixhawk | S3-CAM header |
| --- | --- |
| TELEM TX | GPIO42 (S3 RX) |
| TELEM RX | GPIO41 (S3 TX) |
| GND | GND |

Use **57600 baud**, MAVLink and ArduCopter; match the selected TELEM port's
parameters in Mission Planner. GPIO41/42 must be free of external OLED/JTAG
connections. GPIO43/44 are kept for the TTL USB console; camera and N16R8 memory
pins are reserved. Both UART assignments are checked in `config.py`.
UART signals are 3.3 V; do not put 5 V on GPIO. For the first receive-only boot
check, leave the S3 TX wire disconnected. Power the board through USB for bench
testing and remove propellers.

## Missions and camera limits

Reset/upload never starts a mission. To deliberately run one after bench/SITL
validation, interrupt the monitor with Ctrl+C at the MicroPython REPL, then use
`from missions import hover; hover.main()` (which can arm and take off).
Other modules are `hover_gps`, `move_gps`, `circle`, `aruco_landing`,
`aruco_move_gps`, and `qr_landing`. Their parameters are in the mission files
and `config.py`. Pilot mode changes and disarm stop guided mission commands.

**QR landing is not ready out of the box:** camera-enabled MicroPython supplies
images, not QR detection. The old native XIAO decoder is preserved in
`Build Stuff/archive/cpp/xiao_qr_camera/`; it no longer communicates with the active code.
To enable local QR detection, supply an importable MicroPython decoder module,
set `QR_DECODER_MODULE` in `config.py`, and implement:

```python
def decode(grayscale_image, width, height):
    # Return actual detections; [] means no QR.
    # Each result: {"payload": "...", "corners": [[x,y], ...]}.
    # Corners must follow QR-grid TL/TR/BR/BL order, not screen sorting.
    ...
```

The decoder must run locally, return promptly within the 350 ms capture/decode
budget, and use the supplied 320x240 grayscale frame. Missing decoding support
fails before connecting/arming. Duplicated targets, invalid geometry and stale
frames cannot authorize descent. The target payload is `BSHE27-LAND`.
Image top must point toward the vehicle nose and image right toward its right.
ArUco missions similarly require an onboard provider registered through
`banshee.vision`; none is bundled. Neither QR nor ArUco flight is hardware
validated. No detector is simulated in the board application.

## Debugging

Color names are colored text in **Markdown Preview** (VS Code: **Ctrl+Shift+V**).

The RGB indicator uses counted, single-color blinks followed by a dark pause.
See the [LED guide](LED%20Guide.md) for the complete table. BOOT mutes/resumes it.

## Check the software

Use **Terminal → Run Task → BSHE27: Run tests**, or:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s "Build Stuff/tests" -t "Build Stuff" -v
```

Optional MAVLink interoperability checks use `Build Stuff/requirements-dev.txt`. Host tests
do not verify physical wiring, a live feed, or flight. No firmware or mission
is uploaded as part of those checks.


## Current camera setup (verified on the board)

The board now runs Camera API v0.6.2 / MicroPython v1.27.0 with octal PSRAM.
Its **OV3660** works in RGB565 capture mode with the native `jpeg.Encoder`;
direct sensor JPEG mode fails with this driver release. `CAMERA_CAPTURE_MODE`,
`CAMERA_RGB565_FORMAT`, and JPEG quality are in **Code/config.py**.

Reset starts the Wi-Fi camera page automatically. Connect to **BSHE27-Camera**
using the configured password, then open **http://192.168.4.1/** and refresh an
older tab. The page starts `/stream` automatically. Only one live viewer can
stream at a time; a new stream releases the previous viewer. Close other live
tabs so their automatic reconnects do not keep replacing your stream.

Use **JPEG detail (35–90)** and **frame-rate limit (1–15 FPS)** on the page, then
click **Apply**. Lower detail makes smaller files and can improve speed; higher
detail preserves more image information. Lowering the FPS ceiling saves transfer
work. Resolution stays **320 × 240** and actual speed depends on lighting, camera
capture and Wi-Fi. Changes last until reset; edit `CAMERA_JPEG_QUALITY` (35 by
default) and `CAMERA_FPS_LIMIT` (1 by default) in `Code/config.py` for boot defaults.

Press **BOOT briefly after startup** to mute the RGB LED; press it again to
resume the current status. The webpage still shows subsystem health while the
indicator is muted. Reset restores `RGB_ENABLED`. Hold BOOT during reset only
when you want download mode; RESET itself restarts the board.

Raw color capture, JPEG conversion, `/capture`, and consecutive MJPEG frames
were tested on the physical board. The previous full 16 MB flash is saved in
**Build Stuff/local/board-backups/**, including the original firmware and files.

## Camera and Pixhawk together

The default `BOOT_APP = "camera"` now starts one dashboard with video and
receive-only Pixhawk heartbeat monitoring together. Join the same hotspot and
refresh http://192.168.4.1/. Pixhawk TX connects to S3 GPIO42 RX; connect a common
ground. Baud rate is 57600. UART1 uses an 8192-byte receive buffer to tolerate
native camera capture while the cooperative monitor polls every 20 ms.

The dashboard shows connected/waiting/lost/error, armed state, numeric custom
mode, heartbeat age and UART counters. Armed/mode values become unknown after
the heartbeat expires; video continues. No Pixhawk is required to use video.
The dashboard sends no flight commands or stream requests; configure the
Pixhawk telemetry port to output MAVLink heartbeats at the matching baud rate.

Manual missions still own UART and camera exclusively: stop the running app
through the serial REPL before running a mission, and reset to restore the
dashboard. QR/ArUco still require their documented decoder/provider.

### Live view recovery

The webpage requests complete JPEG frames and displays each decoded image. It reconnects
if the connection closes or no decoded frame reaches the page for eight seconds,
even when board counters keep advancing. Status requests time out after five
seconds and never overlap; reconnect delays range from one to five seconds.
Live view resumes when the board becomes reachable; clicking Stop deliberately
pauses it until Start is clicked. Refresh an older tab after uploading web changes.

The server retries a transient camera capture twice before ending that stream.
An MJPEG frame has five seconds to finish writing before the viewer is released;
this deadline covers every chunk together. Network
disconnects are recorded separately from camera errors in `/status`; the RGB
returns to its underlying connection state until streaming resumes.

On 2026-11-19, the updated app passed 650 real OV3660 frames over 134 seconds
using on-board TCP loopback, with concurrent status, snapshots and the passive
UART monitor. Quality changes, viewer replacement, stalled-viewer release and
recovery also passed. Browser controls were checked with simulated camera
responses. These checks do not establish browser-over-Wi-Fi endurance or verify
a physical BOOT-button press; those remain hands-on checks.

Phone connection: join BSHE27-Camera and accept staying connected without internet.
Open **http://192.168.4.1/** explicitly. Local DNS and common phone hotspot probes
now point at the dashboard. Camera initialization waits for the first camera/status request
so camera capture does not consume memory bandwidth before the page is requested.
HTTPS-only browser settings and a VPN can still prevent local HTTP access.

The browser preview now requests complete JPEG frames from `/capture`, taking turns
with status requests so video cannot occupy a permanent browser connection.
Each JPEG request has a ten-second client deadline; status keeps its five-second
deadline. The `/stream` MJPEG API remains available for other viewers.
Preview frames also activate the blue live-view indicator, returning to the
underlying Wi-Fi state within three seconds after frames stop.

Normal reset now starts with JPEG quality 35 and a 1 FPS ceiling. The previous
75/10 defaults reconnected even with the antenna attached. The compatibility
profile uses Wi-Fi b/g, disables radio power-save and paces small TCP packets.
The Wi-Fi password and WPA2 protection are unchanged. Increase image quality
or frame rate from the page gradually once the connection stays stable.
