# GOOUUU ESP32-S3 setup

1. Clone this branch into any folder and open its `BSHE27.code-workspace` in desktop Visual Studio Code, or open the repository folder itself.
2. Install the recommended **PlatformIO IDE** extension (`platformio.platformio-ide`) and let its initial setup finish. It installs/manages PlatformIO Core and downloads the pinned toolchain on the first build; internet is needed for that setup. No separate MicroPython runtime or Python virtual environment is needed to build.
3. Connect the GOOUUU ESP32-S3-CAM N16R8 USB-to-UART port. Disconnect the USB video viewer and close serial monitors before uploading. Press **Ctrl+Shift+B** to build and upload. Use **GOOUUU: Build** for compilation only.
4. Open **GOOUUU: Monitor** at 115200 baud.
5. Join **BSHE27-Camera**, password **password**, and open **http://192.168.4.1/**.

Pixhawk UART: TX → GPIO42, RX ← GPIO41, common GND, 57600 baud, MAVLink, ArduCopter. Boot is passive; no mission starts automatically.

See the [complete C++ firmware guide](firmware/goouuu_esp32_s3/README.md) for wiring, mission commands, limitations and bench validation.

The VS Code tasks use PlatformIO's native task provider. They contain no developer-specific executable paths, COM port numbers or sibling-folder references. Firmware source, settings, viewer HTML and helper scripts are in this repository. `.pio/` and PlatformIO-generated editor/debug files are machine-local and ignored by Git.

Outside VS Code, install PlatformIO Core and run `pio run` or `pio run -t upload` from this checkout. Optional Python diagnostics use `python -m pip install -r requirements-dev.txt`; these packages are not firmware build prerequisites.

For wired video, use the native USB-C socket and **GOOUUU: Open USB camera**, then **Connect USB** in Edge/Chrome. Choose the Espressif USB JTAG/serial device. The TTL/CH340 port remains for uploads and the console.
