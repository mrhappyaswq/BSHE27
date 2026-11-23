# Live camera webpage: start here for the Amazon board

This standalone firmware creates a local Wi-Fi network and a webpage with a
live VGA (640 x 480) MJPEG feed, Start/Stop button, status and JPEG snapshot.
The camera board itself hosts the page. No router, Raspberry Pi, cloud account
or internet connection is needed after installation.

## Which board?

The [supplied Amazon manual](https://m.media-amazon.com/images/I/D1Q5qrL0OoL.pdf),
PDF page **4**, shows a **GOOUUU ESP32-S3-CAM N16R8** with two USB-C ports and
an OV2640 camera. This is different from the XIAO Sense in the previous guide.
Match your actual board to that diagram before uploading. The default
`goouuu_s3_cam` environment uses its camera pin assignments and configures
16 MB flash and 8 MB OPI PSRAM. If the module marking is not N16R8 or the
layout differs, verify that hardware before using this profile. Sensor and
memory sizes are printed at startup; the manual does not establish the
sensor fitted to every seller's shipment. OV2640, OV3660 and OV5640 are accepted.

There is also an optional `xiao_sense` environment for the previously
recommended XIAO ESP32-S3 Sense. These profiles use different pin maps.

## Setup in VS Code

1. Clone or download this repository. The viewer is in **firmware/camera_web**.
2. Install **PlatformIO IDE** from VS Code's Extensions view, then open
   **firmware/camera_web** as the project folder. Wait for its first setup
   and dependency downloads to finish.
3. Disconnect the flight controller and other wiring. Fit the supplied
   camera ribbon with USB power disconnected; close its connector latch.
   Leave the microSD card out; this viewer does not need one.
4. Connect the board's **UART/TTL USB-C port** to your computer with a USB
   **data** cable. On the board drawn in the manual this is the port at the
   right when the camera faces you and the USB connectors point downward.
   Use the printed port label to confirm. This upload profile uses the
   USB-to-serial bridge, not the other OTG port.
5. If Windows shows no COM port, check Device Manager. The manual's text
   mentions CH343 while its diagram labels CH340; identify the actual USB
   bridge and use the matching official WCH driver if Windows needs one.
   Do not install an arbitrary driver merely because the manual names it.
6. In PlatformIO's sidebar, open **Project Tasks → goouuu_s3_cam → General**.
   Click **Build**, then **Upload**. Select the board's COM port if prompted.
   Close Thonny, Arduino serial monitors and other programs using that port.
7. If connection fails, hold **BOOT**, press and release **RST**, then release
   BOOT and retry Upload. After upload press RST to boot normally. If upload
   still stalls, use another data cable/USB port and confirm the selected COM
   port. PlatformIO uses the pinned Arduino framework automatically; no
   MicroPython installation is needed for this firmware.
8. Open **Monitor** at **115200 baud**, press RST and read the camera sensor,
   PSRAM, flash size, and webpage address. If using the XIAO instead, select
   **xiao_sense** for Build/Upload, use its single USB port and BOOT/reset
   procedure; do not use the default GOOUUU profile.

## Open the live camera

1. On your laptop or phone, join Wi-Fi **BSHE27-Camera**.
2. Enter password **bshe27cam** (all lowercase).
3. If the device says **No internet**, choose to stay connected. If mobile
   data, a VPN or another Wi-Fi connection takes over, temporarily turn that
   off so the browser can reach the camera.
4. Open **http://192.168.4.1/** in a normal browser. Type `http://`, not HTTPS.
5. Live view starts automatically. Use **Stop live view** before opening a
   snapshot if your browser struggles with both. **Open snapshot** shows a
   JPEG you can save using the browser. Start resumes the live view.

Only one Wi-Fi device/live viewer is supported at a time. The webpage and
status use port 80; the MJPEG stream uses port 81. Streaming is paced to at
most about 10 FPS; actual frame rate is unmeasured and depends on Wi-Fi,
sensor and power. No image or password is uploaded to an external service.
Change `AP_NAME` / `AP_PASSWORD` at the top of `src/main.cpp` before building
if desired; passwords require at least eight characters. The published
default password is public and intended for bench use. Anyone connected to this local network
can view the camera; the webpage has no separate login.

## Troubleshooting and limits

- **Camera initialization failed:** check the selected board environment,
  ribbon seating, supplied sensor and USB power. Disconnect power before
  touching the ribbon. Do not substitute the XIAO camera pin map for this board.
- **PSRAM not detected:** verify N16R8 marking and the selected environment.
  Do not disable the PSRAM check to hide a mismatched board profile.
- **No Wi-Fi:** open the 115200 serial monitor and press RST. Check USB power
  and startup messages. This is a 2.4 GHz network.
- **Page works but feed does not:** stop other viewers, reconnect Wi-Fi,
  press Start, and ensure your browser/network allows local port 81.
- **Resets/disconnections:** use a stable USB supply and a short cable.
- **Blurred/rotated picture:** verify lens focus and physical mounting with
  a printed QR. This pinned driver does not command OV5640 autofocus.
- This viewer sends **no MAVLink or flight commands** and does not decode QR
  codes. It is separate bench firmware, so flashing it replaces any existing
  program on the selected camera board. Back up files first if needed.
- To restore the earlier XIAO landing-camera firmware, build/upload
  `firmware/xiao_qr_camera`. That firmware is **XIAO-specific**; do not flash
  it to the Amazon GOOUUU board. Porting onboard QR landing to the GOOUUU
  board is separate from viewing its feed. Neither preview latency nor focus
  is validated for flight control.
- Camera, webpage and UART/SD functions never run together in this viewer;
  its only purpose is to inspect the supplied camera. Snapshots are saved by
  your browser, not onto an SD card.

## Verified pin map from the manual diagram

| Camera signal | GOOUUU GPIO | XIAO Sense GPIO |
| --- | --- | --- |
| SCCB SDA / SCL | 4 / 5 | 40 / 39 |
| XCLK | 15 | 10 |
| D0..D7 (Y2..Y9) | 11, 9, 8, 10, 12, 18, 17, 16 | 15, 17, 18, 16, 14, 12, 11, 48 |
| VSYNC / HREF / PCLK | 6 / 7 / 13 | 38 / 47 / 13 |

PlatformIO CLI equivalents (inside this directory):

```powershell
pio run -e goouuu_s3_cam
pio run -e goouuu_s3_cam -t upload --upload-port COM4
pio device monitor --port COM4 --baud 115200
```

Replace COM4 with the actual camera-board port. Compilation checks software
compatibility only; live hardware streaming has not been tested here.

## Source layout

- `src/main.cpp`: camera setup, local Wi-Fi and HTTP handlers.
- `include/viewer.h`: self-contained browser page, served from flash.
- `platformio.ini`: pinned build dependencies and board profiles.

Build both profiles before submitting changes:

```powershell
pio run -e goouuu_s3_cam -e xiao_sense
```

Browser checks can use simulated status and image responses to verify automatic
start, Stop/Restart, snapshots and errors. They do not verify a physical camera
feed, image quality, Wi-Fi range or actual frame rate.
