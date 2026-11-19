# XIAO ESP32-S3 Sense QR camera firmware

This is firmware for a **second board**, the Seeed XIAO ESP32-S3 Sense and its
supplied camera/SD expansion board. The existing WROOM-32S runs the project's
MicroPython flight companion. Do not upload this firmware to that WROOM.

The camera returns measured QR corners over UART. It does not communicate
with the flight controller, arm anything, use Wi-Fi, or need a Raspberry Pi.
The intended sensor is OV3660 or OV5640; the older supplied OV2640 is also
accepted. Other sensors fail initialization. The main board must have 8 MB
PSRAM, which is checked at startup.

## Build and upload

1. Install the **PlatformIO IDE** extension in VS Code.
2. Open **this folder** (`firmware/xiao_qr_camera`) as a PlatformIO project.
3. Connect the XIAO by USB. Use **PlatformIO: Build** to compile, then
   **PlatformIO: Upload**. If upload does not connect, hold BOOT while
   connecting USB, release BOOT, and retry.
4. Open the PlatformIO serial monitor at 115200. It should print the detected
   sensor ID, PSRAM size, and `BSHE27 QR camera ready`. USB is for diagnostics;
   the CRC-framed detection protocol uses physical pins D6/D7.

Equivalent command-line operations, with PlatformIO Core 6.1.18 installed:

```powershell
pio run -e xiao_esp32s3_sense
pio run -e xiao_esp32s3_sense -t upload --upload-port COM7
pio device monitor --baud 115200 --port COM7
```

Select the XIAO's actual port instead of COM7. The project pins the Espressif32
platform to 6.10.0, Arduino-ESP32 to 2.0.17, and ArduinoJson to 6.21.5. quirc is
vendored at the exact commit in [UPSTREAM.md](lib/quirc/UPSTREAM.md), preserving
its license. The initial build downloads the platform/toolchain.

## Wiring and image orientation

| XIAO pin | WROOM-32S pin | Purpose |
| --- | --- | --- |
| D6 / GPIO43 TX | GPIO16 RX2 | Camera replies |
| D7 / GPIO44 RX | GPIO17 TX2 | Companion requests |
| GND | GND | Common signal reference |

The link uses **115200 baud, 8N1 and 3.3 V logic**. Power the XIAO through its
5 V input/USB using a regulated supply; do not power it from a GPIO or connect
flight-battery voltage directly. Use a regulator with sufficient measured
headroom for both boards, camera and SD write transients (5 V, 2 A is a
reasonable development supply). Disconnect USB power before connecting a
separate 5 V source unless the power arrangement is verified.

Do not confuse the WROOM's GPIO16/17 with the XIAO's GPIO16/17, which belong to
the camera. Existing WROOM TX33/RX32 to the FC remain separate. These default
WROOM UART pins require a WROOM board with exposed GPIO16/17; verify your exact
board before wiring, since WROVER variants may reserve those pins for PSRAM.

Camera pin allocation is explicit in [camera_settings.h](include/camera_settings.h):
XCLK10, SDA40, SCL39, D0..D7 = 15/17/18/16/14/12/11/48, VSYNC38, HREF47,
PCLK13. The SD card uses SCK7, MISO8, MOSI9, CS21. UART43/44 uses separate pins.

Mount downward, with **logical image top toward the nose and image right toward
vehicle right**. Confirm this using an actual saved photo. Adjust mounting and
`CAMERA_HMIRROR`/`CAMERA_VFLIP` if needed, then repeat all axis tests. The decoder
rejects mirrored QR codes rather than guessing their orientation. QR corners
remain in the printed QR's canonical TL, TR, BR, BL order even when the marker
rotates in the image; they are never sorted by screen coordinates.

## Marker and photos

Print a high-contrast QR code whose entire payload is exactly `BSHE27-LAND`.
Keep its white quiet zone. Mark the printed code's top edge as the desired
nose direction. `TARGET_PAYLOAD` in `camera_settings.h` must match the
MicroPython companion setting if changed. Nonmatching codes are ignored;
multiple matching codes return an error to avoid choosing an ambiguous pad.

Scanning uses **320 x 240 grayscale** to limit processing latency. Sensor
megapixel ratings do not describe this tracking resolution. This pinned camera
driver does not load OV5640 autofocus firmware or issue focus commands. Verify
the actual module is sharply focused at the acquisition height and through
descent; an OV5640 AF module must not be assumed focused automatically.

For `photo`, insert a FAT32 microSD card (up to 32 GB per Seeed). Storage is
initialized lazily, so a missing card does not prevent QR tracking. The camera
saves a grayscale QVGA JPEG under `/photos/IMG_00000001.jpg`, skipping existing
filenames, including after reboot. A full/unavailable card, capture error or
failed write returns `error`; no successful path is reported for a known
failed write. JPEG encoding and SD writes can exceed the tracking deadline:
only request photos while disarmed/outside the landing controller. Files have
no GPS/time metadata; filenames express sequence, not UTC. Retrieve photos by
powering down, removing the card, and using a card reader. The library flushes
and checks file length; sudden power loss can still damage the current file.

## UART protocol

Each UTF-8 JSON object is followed immediately by `*HHHH\n`, with four uppercase
hexadecimal digits containing CRC16-CCITT-FALSE over the JSON bytes (polynomial
0x1021, initial value 0xFFFF, no reflection, no final XOR). Requests fit within
255 bytes including checksum, excluding newline. Invalid CRC/JSON/version/ID,
oversized or unfinished lines are discarded. One request should be outstanding
at a time. IDs are integers in 1..2147483647.

JSON contents before checksum:

```json
{"v":1,"id":1,"op":"scan"}
{"v":1,"id":1,"width":320,"height":240,"marker":null}
{"v":1,"id":2,"width":320,"height":240,"marker":{"payload":"BSHE27-LAND","corners":[[110,80],[210,80],[210,180],[110,180]]}}
{"v":1,"id":3,"op":"photo"}
{"v":1,"id":3,"path":"/photos/IMG_00000001.jpg"}
{"v":1,"id":4,"error":"camera initialization failed"}
```

The corners above illustrate the format; firmware sends only actual camera
measurements. Each scan discards buffered exposures preceding request receipt.
The companion must independently enforce a request-to-response freshness
deadline, reject unmatched IDs, stop on loss/error, and measure actual update
rate. Receiving a response is not proof the landing update budget is met.

## Validation limits

The pinned `xiao_esp32s3_sense` environment compiled and linked successfully on
2026-11-12 with PlatformIO Core 6.1.18. Reported static RAM usage was 44,540
bytes (13.6% of internal RAM) and flash usage 417,301 bytes (12.5% of the app
partition). Runtime allocations such as the camera and QR image buffers are
additional and checked at startup; build size does not establish runtime timing.

Compilation and host tests cannot validate camera focus, rolling-shutter motion
distortion, lighting, detection range, UART wiring, power transients, SD writes
or flight accuracy. Verify those on the physical hardware before any flight.
The decoder and capture run on this separate board, leaving the WROOM available
to service MAVLink while it waits for a nonblocking camera response.

Official hardware references: [Seeed camera guide](https://wiki.seeedstudio.com/xiao_esp32s3_camera_usage/),
[Seeed SD guide](https://wiki.seeedstudio.com/xiao_esp32s3_sense_filesystem/),
[PlatformIO board configuration](https://github.com/platformio/platform-espressif32/blob/v6.10.0/boards/seeed_xiao_esp32s3.json).
