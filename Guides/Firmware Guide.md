# Firmware: what it is and where to change it

Your project has two layers:

```text
Code/*.py                  Your MicroPython app: Wi-Fi, LEDs, camera page, missions
           ↓ runs on
MicroPython firmware       Interpreter + hardware drivers + ESP32 operating system
           ↓ runs on
ESP32-S3 hardware          CPU, memory, Wi-Fi radio, GPIO and attached camera
```

Editing **Code/** and pressing **Ctrl+Shift+B** uploads Python/web files.
Editing the firmware's C code requires compiling a new `.bin`, then separately
flashing that image. Those are different operations. Your app stays Python;
you only need C knowledge when you choose to modify the interpreter/drivers.

## Source files included in the project

Open **Build Stuff/Firmware/**:

| Folder/file | What it contains |
| --- | --- |
| `Sources/MicroPython/` | MicroPython v1.27.0 interpreter and ESP32 port for the camera-enabled build recipe. |
| `Sources/Installed-MicroPython/` | MicroPython v1.29.0 source, matching the previous standard firmware, retained as a reference. Included for inspection; not selected by the camera build helper. |
| `Sources/Camera-API/` | Camera API v0.6.2: the native module that provides Python's `camera.Camera`. |
| `Sources/Camera-API/esp32-camera/` | Pinned low-level camera capture and sensor drivers. |
| `Sources/mp_jpeg/` | MicroPython JPEG bindings, pinned to a source snapshot at the camera release date. |
| `Sources/ESP-IDF/` | Espressif SDK v5.5.1, including available source and its required submodules: RTOS, Wi-Fi interfaces, peripherals, bootloader and build system. |
| `Sources/Managed/` | Pinned S3 USB, mDNS and JPEG component packages used by the local recipe. |
| `Images/Camera-enabled/firmware.bin` | The verified, prebuilt optional camera firmware. **Now installed on the board with 16 MB flash configuration.** |
| `source-lock.json` | Repository URLs, commits, source archive hashes and the firmware image hash. |
| `managed-source-lock.json` | Source/version records for the additional component packages. |
| `build.sh`, `prepare_build.py` | Helpers that copy your edited sources to a fresh Linux build folder and compile. They do not flash. |

These are real source snapshots, not just links or empty submodule folders.
Upstream licenses are retained alongside their code. The full interpreter and
ESP32 SDK trees are present; unrelated MicroPython third-party SDK submodules
for other microcontroller families are not required by this S3 build.

Some Espressif components ship precompiled libraries rather than all their
internal source. Those vendor binaries are included where supplied; their
unpublished internals and the chip's factory ROM cannot be edited here.
Compilers and Python build tools are separate tools installed on first build,
not source files that run on the board.

## Which files should I edit?

| Change you want | Start here |
| --- | --- |
| Wi-Fi name, pins, brightness, mission settings | `Code/config.py` — ordinary Python upload |
| Camera webpage, quality/FPS defaults or preview behavior | `Code/config.py`, `Code/web/index.html`, `Code/apps/camera_web.py` — ordinary upload |
| RGB colors, blink patterns or BOOT mute behavior | `Code/banshee/status_led.py`, `Code/config.py` — ordinary upload |
| Python camera adapter | `Code/banshee/camera.py` — ordinary upload |
| Camera functions exposed to Python | `Sources/Camera-API/src/modcamera.c`, `src/modcamera_api.c` — firmware rebuild |
| Default camera models/pins inside the native driver | `Sources/Camera-API/src/camera_pins.h` — firmware rebuild. BSHE27 currently passes pins explicitly from Python. |
| Sensor register handling | `Sources/Camera-API/esp32-camera/sensors/` — firmware rebuild |
| Interpreter, parser, bytecode execution | `Sources/MicroPython/py/` — firmware rebuild |
| ESP32 startup and hardware modules | `Sources/MicroPython/ports/esp32/` — firmware rebuild |
| ESP32-S3 board/PSRAM defaults | `Sources/MicroPython/ports/esp32/boards/ESP32_GENERIC_S3/` — firmware rebuild |
| SDK drivers, radio interfaces, operating system | `Sources/ESP-IDF/components/` — firmware rebuild |

Paths beginning with `Sources/` above are relative to **Build Stuff/Firmware/**.
The code map for your app remains [Code Map](Code%20Map.md).

## Building your edited firmware later

Use **WSL2 Ubuntu or Linux**, as recommended by the
[MicroPython ESP32 build instructions](https://github.com/micropython/micropython/blob/v1.27.0/ports/esp32/README.md).
The helper targets **ESP32_GENERIC_S3 + SPIRAM_OCT** and explicitly selects
**16 MB flash** for the N16R8. The generic board otherwise defaults to a 4 MB
flash header. This override is added only to the disposable build copy; the
source snapshots stay intact. The upstream flexible partition layout gives the
remaining flash to the filesystem. It builds the v1.27.0 camera-target tree.

1. In Ubuntu, install build prerequisites:

   ```bash
   sudo apt update
   sudo apt install git wget flex bison gperf python3 python3-pip python3-venv \
     cmake ninja-build ccache libffi-dev libssl-dev dfu-util libusb-1.0-0 build-essential
   ```

2. Edit source files in this project. Open a WSL terminal in
   **Build Stuff/Firmware**. You can first prepare a build copy without compiling:

   ```bash
   bash build.sh --prepare-only
   ```

   The script prints a new folder under `~/bshe27-firmware-builds/`.
   This copy includes your edits. It restores Unix source links and creates
   local version metadata needed by upstream tools. It never overwrites an
   existing build folder or changes the original source snapshots.

3. To prepare a fresh copy and compile:

   ```bash
   bash build.sh
   ```

   First use installs the S3 toolchain/Python dependencies through Espressif's
   `install.sh`, so internet access is needed. The build uses the vendored
   component copies rather than silently selecting newer source revisions.
   `ESP_JPEG_DIR` points the JPEG module's headers at the same local
   `Managed/esp_new_jpeg` component used by the dependency manifest.
   SDK output and compiler objects stay in the Linux build folder. That avoids
   ESP-IDF path restrictions caused by the spaces in this Windows project path.

4. The helper prints the resulting `firmware.bin` path. Inspect/test that build
   before choosing to flash it. **The helper never erases or flashes the board.**
   Normal Ctrl+Shift+B still uploads only **Code/**; it does not build firmware.

The build recipe is supplied for future use. It has not been fully compiled
or hardware-validated in this Windows session. Installing WSL/toolchains and
flashing remain separate actions.

## Versions and reproducibility

The optional prebuilt image came from
[Camera API release v0.6.2](https://github.com/cnadler86/micropython-camera-API/releases/tag/v0.6.2).
Its downloaded ZIP was checked against the published SHA-256; the image hash
is also recorded in `source-lock.json`.

The release workflow selected some dependencies dynamically, including the
JPEG module, so it does not disclose enough information to prove a byte-for-byte
rebuild of that existing binary. This project records the exact snapshots
selected for **future local builds** instead of claiming that equivalence.
The earlier standard firmware's v1.29.0 source is retained as a reference;
the current camera firmware reports v1.27.0. Neither version string identifies
every original compiler option or SDK artifact.

You can change those sources later. Keep the source lock and note your edits
so you know which code produced each new image. Source changes have no effect
on the current board until you deliberately rebuild and flash.


## Current installed camera firmware

The verified camera image is now installed, and the previous complete 16 MB
flash is backed up under **Build Stuff/local/board-backups/**. Runtime reports
MicroPython 1.27.0 with octal PSRAM and approximately 8 MB available heap.
The sensor is an **OV3660**. Direct JPEG capture fails in this driver; Python
adapter `EncodedCamera` in **Code/banshee/camera.py** instead captures RGB565
and uses the included native `jpeg.Encoder`. The webserver streams the resulting
JPEGs as MJPEG. Firmware source remains unchanged; the workaround is editable
application code. The full custom firmware source build has not been run.
