# GOOUUU ESP32-S3 C++ firmware

Active target: one GOOUUU ESP32-S3-CAM N16R8 (16 MB flash, 8 MB OPI PSRAM), with its onboard camera and a Pixhawk running **ArduCopter**. The application is Arduino C++; it does not require MicroPython or a second ESP32.

## Build and upload

Install PlatformIO IDE in VS Code. Open the repository workspace. **Ctrl+Shift+B** runs **GOOUUU: Build and upload C++**. Disconnect the USB viewer first. Use **GOOUUU: Build** from Run Task for compilation without uploading. **Terminal → Run Task → GOOUUU: Upload** replaces the program on the board; **GOOUUU: Monitor** opens the 115200 baud serial console. The default console uses the board's USB-to-UART bridge, GPIO43/44. Native USB CDC is not enabled in this profile.

The tasks use the PlatformIO extension's native task provider, which finds/manages its installed Core. No `.platformio` executable path is embedded in the project. The root workspace uses `.` so clones can have any directory name. The first build downloads the toolchain versions pinned in `platformio.ini`; generated `.pio` and editor/debug files stay outside Git.

From a terminal with PlatformIO on PATH:

```text
pio run -d firmware/goouuu_esp32_s3
pio run -d firmware/goouuu_esp32_s3 -t upload
pio device monitor -b 115200
```

If automatic upload cannot reset the board, hold BOOT, tap RESET, release BOOT and retry. Select the actual board port if multiple serial devices are connected. Uploading is a separate action from building. This firmware was uploaded successfully to the connected ESP32-S3 on COM4, and its passive status response was confirmed.

## Wiring and settings

Edit `include/settings.h` for the UART IDs, baud rate, Wi-Fi credentials, orientation and optional storage. Camera pins are in `src/camera_service.cpp` and match the GOOUUU manual used by the existing camera firmware.

| Connection | GOOUUU pin |
| --- | --- |
| Pixhawk TELEM TX → companion RX | GPIO42 |
| Pixhawk TELEM RX ← companion TX | GPIO41 |
| Ground | GND, shared with Pixhawk |
| Camera D0…D7 | 11, 9, 8, 10, 12, 18, 17, 16 |
| Camera SDA / SCL / XCLK | 4 / 5 / 15 |
| Camera VSYNC / HREF / PCLK | 6 / 7 / 13 |
| RGB status LED | GPIO48 |

UART is 57600 baud, 8N1, 3.3 V logic. Cross TX/RX and use a common ground; do not put a Pixhawk power pin on an ESP32 GPIO. Configure the selected ArduCopter TELEM port for MAVLink 1 or unsigned MAVLink 2 and matching baud. This is a GUIDED/LAND companion, not a PX4 Offboard implementation. Signed MAVLink packets are rejected and counted; signing is not implemented.

External SPI microSD is optional and **disabled by default** because the GOOUUU card wiring has not been established. `SdEnabled` and `SdSck/SdMiso/SdMosi/SdCs` configure an external module (defaults 38/39/40/21). These are not XIAO expansion-board pins. `photo` saves and verifies a JPEG under `/photos/`; it refuses while armed or running a mission.

## Dashboard and diagnostics

Join **BSHE27-Camera**, password **password**, then open **http://192.168.4.1/**. No internet is needed. The page starts with lightweight telemetry only. **Start video** enables optional QVGA video, and **Get latest snapshot** makes a single JPEG request. It also shows FC/ESP32 freshness and request latency comparisons. `/status` works without a Pixhawk. Camera startup failures are reported without disabling telemetry or the hotspot. Video delivery is paused during missions; the sensor JPEG capture pipeline continues. Restart Wi-Fi video afterward with Start video.

At boot the Pixhawk UART is receive-only. `telemetry` explicitly requests 4 Hz streams; alternatively configure telemetry streams in ArduCopter. `status` prints the current link, mode, altitude and mission state. LED pulses: amber waiting, green connected, blue mission, red camera fault or lost heartbeat. Diagnostics never arm a vehicle.

## Wi-Fi telemetry latency test

Join **BSHE27-Camera** (password **password**) and open **http://192.168.4.1/**. Stay connected/use the network even if the device warns that it has no internet. The page automatically polls **`/telemetry`**, with no automatic JPEG downloads and no automatic camera-control requests. Default poll interval is 500 ms; choose 250 ms, 1 s or 2 s. There is at most one telemetry request in flight, a 3-second deadline, automatic retry, and a Stop button. The ESP32 samples its FC/parser state every 250 ms. No flight commands or FC stream-configuration commands are sent by this test.

The panel distinguishes laptop-to-ESP32 reachability from the FC link. It shows last ESP32 reply age, last received FC heartbeat age/count, numeric flight mode, armed state, altitude, battery, GPS fix/satellite count, UART bytes/CRC failures, board uptime and free heap/PSRAM. FC state is unknown before the first valid target heartbeat or after heartbeat loss (5 seconds). Battery/position/GPS readings also expire independently (3 seconds). Stale telemetry source snapshots or missing Wi-Fi replies clear current FC values rather than presenting old readings as live. Receiving heartbeat alone does not guarantee other MAVLink streams are configured; use the existing serial `telemetry` command or configure stream rates on the FC if those values are absent.

**Get latest snapshot** fetches one complete JPEG and displays it separately, without starting video. **Start video** streams distinct framed JPEGs until stopped. The UI sends both image modes to port **81**, while small telemetry requests use port **80**, so a blocked image handler does not occupy the telemetry HTTP server. Camera acquisition still runs onboard with video downloads off; this test isolates network payload, not camera power consumption.

The **Wi-Fi comparison** section reports successful/failed/timed-out requests, success percentage, mean and 95th-percentile RTT, average response-body bytes, and both percentage/multiplier comparisons against telemetry. Statistics retain the most recent 100 successful requests per mode; counts continue until **Reset measurements**. RTT is browser request start through full response-body receipt, before JSON parsing/JPEG decode. It includes server waiting and TCP/HTTP overhead and is not one-way RF latency, raw packet loss, or complete FC-to-screen latency. Heartbeat age starts at ESP32 reception. No synchronized FC/laptop clock is assumed.

For a controlled test: leave video off and collect telemetry samples; take several snapshots; then start video and observe telemetry RTT, timeouts and freshness under load. Reset before comparing separate conditions and repeat at the intended distance and representative interference. The page shows current load. Do not infer flight reliability from a short successful test.

`WifiCompatibility=true` in `include/settings.h` selects 802.11b/g rather than 802.11n for the small-message test; Wi-Fi power saving is disabled and HTTP sockets use TCP_NODELAY. These settings are an interoperability baseline, not proof that radio dropouts are fixed. The TTL console's `status` also shows AP client count, radio protocol mask and HTTP telemetry request/send-result counters. A successful server send result means data was accepted by the TCP stack, not independently confirmed at the browser. A firmware upload restarts the AP: reconnect and refresh the page afterward.

## Wired laptop viewing and speed measurements

The native USB-C socket uses the ESP32-S3 USB Serial/JTAG peripheral (GPIO19 D− / GPIO20 D+). The existing TTL/CH340 USB socket remains the UART console/upload connection. Native USB uses a separate binary protocol for video and camera exposure/gain settings; it cannot issue flight commands. It does not turn the board into a UVC webcam for Camera/Zoom.

1. Plug a data-capable cable from the laptop into the board's **OTG USB-C** socket (native USB, not TTL).
2. In VS Code use **GOOUUU: Open USB camera**, or click the **USB camera** toolbar button. This opens the local viewer in Edge. You can also download the same HTML from the Wi-Fi dashboard's **Download offline USB viewer** link.
3. Click **Connect USB** and choose **USB JTAG/serial debug unit**, the Espressif device. The USB viewer works without joining the camera hotspot. Use Edge or Chrome on the desktop; the unencrypted Wi-Fi page itself may not have permission for Web Serial.

The local viewer opens with the USB video enlarged and the optional Wi-Fi comparison hidden. It continuously requests fresh frames until **Disconnect USB** is clicked. **Full screen** enlarges the video; **Save JPEG** saves the latest picture. The session line shows received frame count and elapsed time, and warns when the displayed picture has stopped updating. Automatic recovery handles transient transfer failures. Close the viewer before uploading firmware or running the USB checker.

For a repeatable hardware check (requires Python and pyserial):

```text
python tools/check_usb_camera.py --seconds 60 --report local/usb-video-soak.json --snapshot local/usb-camera-first.jpg
```

The checker automatically selects a single Espressif native USB port; use `--port COM10` (or the current Windows port) if necessary. It checks distinct frame IDs, dimensions, JPEG boundaries and complete transfers, and reports measured FPS, request times and board frame age. It also counts JPEGs divisible by the 64-byte USB packet size, which exercise end-of-transfer handling. It does not measure CPU utilization or fully decode JPEGs. The TTL console's `status` command also reports native USB readiness, received request bytes, bytes written to the transmit FIFO and send failures. Bytes written do not by themselves prove laptop delivery.

If only CH340 appears, check the other socket and the cable's data capability. Close any serial monitor that owns the native port. The browser asks for 115200 as the required serial API setting, but native USB is not throttled to the CH340 UART's 115200-bit/s wire rate. The TTL console is not a video endpoint. At its current 115200 baud, 8N1 framing limits useful bytes to about 11,520/s before video protocol overhead; a 10 KiB JPEG alone takes about 0.89 s. USB can remove that serial bottleneck, but total FPS remains limited by camera acquisition and transport.

| Display | What is actually measured |
| --- | --- |
| Board processed FPS | Completed sensor JPEG frames per elapsed board second, updated in roughly one-second windows; not the sensor's theoretical FPS |
| ESP32 JPEG encoding | Zero: the sensor supplies JPEG directly. Sensor compression time is included in camera acquisition, not separately timed |
| JPEG size | Compressed bytes per received frame; depends on scene and sensor quality |
| Capture wait ms | Time blocked in the camera driver's frame getter; not sensor exposure duration |
| Browser displayed FPS | Distinct frame IDs decoded into the preview over the last two seconds |
| Request → decoded image | Laptop/browser clock interval from the frame request through receive and JPEG decode; includes waiting for a new board frame |
| Received JPEG data | JPEG bytes over a two-second browser window, in decimal kB/s; excludes USB/HTTP framing |
| Frame age when sent | Board clock interval from exposure timestamp to response creation; excludes subsequent transfer/display time |

Both transports read the same immutable JPEG cache. One worker receives sensor JPEGs, copies each into an immutable PSRAM cache and immediately returns the driver buffer. No RGB conversion, software JPEG encoding or image recognition runs. There is no fixed worker pacing delay. Requests wait for a new frame ID for at most one second. The legacy MJPEG `/stream` endpoint remains available; the instrumented browser viewer uses `/frame` on port 81. Each `/frame` response contains the same 48-byte BSC1 header and JPEG body as native USB. `/capture` returns a plain JPEG, `/viewer` downloads the offline page, and `/status.camera` reports onboard measurements.

Edit `data/viewer.html` and run `python tools/sync_camera_viewer.py` from the repository root before building. The generated `include/dashboard_page.h` is committed for builds without a desktop Python dependency. Browser tests check both copies match. Run `test/browser/viewer.cjs` with Node and Playwright available (`PLAYWRIGHT_MODULE` may specify the module path). Tests simulate transports; a successful build or test does not establish actual USB throughput.

## Fast sensor JPEG preview

The OV3660 captures 320x240 JPEG directly (`PIXFORMAT_JPEG`) with two continuous driver buffers. This avoids the previous approximately 70 ms software JPEG encoder, approximately 44 ms QR processing and 20 ms fixed delay. The worker only copies compressed bytes into PSRAM; `/status.camera.prepare_ms` reports this copy/release time. `jpeg_ms` is zero because no ESP32 JPEG encoding runs. This does not mean sensor compression has zero latency.

`include/settings.h` sets `JpegQuality=20`. The sensor scale is 0..63: increasing the number reduces image quality and usually frame size/transfer time; lowering it increases quality and bytes. This is a different scale from the removed software encoder's quality 75. Resolution remains QVGA for speed. No ArUco detector or pose calculation has been added. The vendored legacy quirc files remain preserved but are excluded from the build.

Hardware verification on 2026-11-22: 1,666 complete frames in 60.05 seconds, **27.74 received FPS** and 27.75 mean board FPS, with zero partial/invalid frames. Mean request time was 36.02 ms; mean frame age when sent was 39.01 ms. This test had no artificial reader pauses. The earlier software-encoding/QR baseline received 7.41 FPS. A live serial sample measured 0 ms ESP32 JPEG encoding and 0.026 ms JPEG copy/release time. These are scene-dependent measurements, not sensor maximums or CPU utilization percentages. Reports: `local/usb-sensor-jpeg-final.json` and `local/sensor-jpeg-status.txt`.

## Live exposure and gain

Reload the local USB viewer after updating firmware. Under **Exposure and gain**, connect USB, choose an exposure in milliseconds and gain in multiples, then **Apply manual**. The **0.5 ms**, **1 ms** and **2 ms** presets apply the gain currently shown (initially 4x). **Restore auto** restores both automatic exposure and automatic gain. Boot defaults to auto; settings are not persisted. Night-mode frame extension stays disabled in both modes. No clock or frame-rate overclock is applied.

Readback updates about once per second while USB viewing (on Wi-Fi, click **Read exposure over Wi-Fi**) and shows mode, actual register-derived exposure, gain and calculated frame period alongside live FPS. The exposure conversion reads OV3660 PLL and horizontal/vertical timing registers; it does not treat the driver's row count as microseconds. Manual requests allow 0.1–20 ms, additionally bounded to four rows below the frame period, and 1–15.5x gain. Actual exposure is rounded to whole sensor rows. These are register-derived times, not an independently measured optical shutter duration.

Controls work over USB without Wi-Fi. The Wi-Fi page uses GET/POST `/camera-control`; POST is seven bytes: mode (0 auto, 1 manual), little-endian exposure microseconds (uint32), gain times 16 (uint16). Native USB accepts `S` for status and `C` followed by the same seven bytes to apply settings. The response is `BSS1`, uint32 JSON length, then UTF-8 JSON. The viewer serializes settings and video requests so their responses cannot overlap. Invalid requests return `ok:false`; mode changes are refused during an active mission. The video `F` request and BSC1 format are unchanged.

Shorter exposure can darken indoor images; gain brightens them but increases noise. Try presets in representative light and compare motion sharpness. Automatic mode provides an immediate recovery if a manual setting becomes too dark. ArUco and distance estimation remain absent.

The live board passed `python tools/check_camera_controls.py --port COM10`: requested 0.5/1/2 ms exposures read back as 0.506/1.012/1.978 ms with 46 microseconds per row. Manual gain read back as requested, three invalid requests were rejected without changing the prior settings, video continued in every mode, and automatic exposure/gain were restored. The test writes `local/camera-controls-hardware.json`. Register-derived frame period was 36.018 ms; this is distinct from exposure and from an optical timing measurement.

## Explicit missions

Type one command followed by Enter in the serial monitor. No mission runs on reset, upload, webpage access or Wi-Fi connection.

| Command | Behavior |
| --- | --- |
| `run hover` | Take off to 10 m, hold 10 s, LAND |
| `run hover_gps` | Take off to 2 m, hold 5 s, LAND |
| `run move_gps` | Take off to 1.5 m, 3 m north, hold 10 s, return, hold 10 s, LAND |
| `run circle` | Take off to 10 m, follow 36 segments around a 20 m radius circle centered on takeoff, return, hold 5 s, LAND |
| `run aruco_landing` | External detector preflight, take off to 1.5 m, center and descend |
| `run aruco_move_gps` | External detector preflight, GPS out-and-back, center and descend |
| `abort` | Request LAND if mission still owns armed GUIDED flight; otherwise stop without changing pilot mode |

All missions require fresh disarmed ArduCopter heartbeats, prearm health, a 3D GPS fix and position telemetry. Mode/arm/takeoff commands require accepted acknowledgements and mode/arm confirmation. Pilot/autopilot mode changes stop mission commands. Stale positions, marker loss and bounded mission timeouts request LAND only while the companion still owns GUIDED flight. Link loss stops commands; recovery then depends on configured autopilot failsafes. There is no force arming or automatic restart.

QR detection and the QR landing command have been removed. ArUco detection and distance estimation are not installed. The existing external-marker missions still require a real provider before preflight can pass.

ArUco detection was an external provider in the original code and remains external. A real detector can send `marker cx cy width height` over USB serial at ≥10 Hz, with a selected marker ID and the same camera axes. The detector needs its own camera feed because this board pauses browser video during missions. Data expire after 350 ms; invalid lines clear detection. These missions use center alignment only. The firmware does not include OpenCV, ArUco decoding or metric pose estimation. Do not feed synthetic coordinates during flight.

## Verification

The firmware builds with the pinned PlatformIO/Arduino toolchain. `test/host/test.cpp` exercises the actual C++ parser, transmitter and mission controller using simulated UART and time. `vectors.h` contains independent pymavlink 2.4.50 fixtures. It covers MAVLink 1/2, truncated ACKs, CRC errors, source filtering, rejected signed packets, outbound coordinate frames/masks, passive boot, arm rejection, mission sequencing, takeoff ACK timing, pilot override, target loss and external-marker settling. Run `test/host/run.ps1` on Windows with Visual Studio C++ Build Tools installed, or compile with a C++17 host compiler:

```text
g++ -std=c++17 -Itest/host -Iinclude test/host/test.cpp -o host-tests
./host-tests
```

These host checks do not prove physical UART, sensor orientation or flight behavior. Bench-test with propellers removed, then validate the mission state machine against ArduCopter SITL and controlled hardware before flight. USB upload, passive serial startup and the native USB camera stream have been verified. Physical Pixhawk exchange and flight have not yet been validated for this rewrite.

Protocol references: [MAVLink common messages](https://mavlink.io/en/messages/common.html) and [ArduCopter GUIDED commands](https://ardupilot.org/dev/docs/copter-commands-in-guided-mode.html).

Native USB reference: [Espressif USB Serial/JTAG controller](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/peripherals/usb_serial_jtag.html).

On 2026-11-19 the correct camera board was flashed and reported approximately 7.4 processed FPS while idle, JPEG encoding around 70–73 ms, QR processing around 43 ms, and roughly 7 KiB JPEG frames. These are serial observations from that scene and configuration, not a fixed specification or a USB/Wi-Fi benchmark. HTTP task stacks were increased to 12 KiB after the expanded status formatter exceeded the default stack in hardware testing.

On 2026-11-22, the native OTG USB camera passed a 60.09-second hardware test: 445 distinct frames, 7.41 received FPS, zero partial/invalid frames, and 135 ms mean request time, including deliberate 250 ms reader pauses every 25 frames. Two JPEGs were exact multiples of 64 bytes; the USB sender explicitly sends a zero-length termination packet for these frames to prevent Windows bulk-read stalls. Results are scene-dependent and recorded in `local/usb-video-soak.json`.
