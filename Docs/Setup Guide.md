# Setup

## Install and open

1. Open `BSHE27.code-workspace` in desktop VS Code.
2. Install the recommended **PlatformIO IDE** extension. It installs the tools needed to build and upload the board program. The first setup needs internet access.
3. Connect the GOOUUU ESP32-S3-CAM N16R8 through its TTL/USB-to-UART socket.
4. Disconnect any camera viewer and close serial monitors before uploading.
5. Press **Ctrl+Shift+B** to build and upload. For a build without upload, choose **Terminal > Run Task > GOOUUU: Build**.
6. Choose **GOOUUU: Monitor** for the 115200-baud serial console.

The board program is C++; you do not install MicroPython on the board. No mission starts automatically.

## Open the camera

For USB video, connect the board's **OTG USB-C** socket, run **GOOUUU: Open USB camera**, click **Connect USB** in Chrome or Edge, and select the Espressif USB JTAG/serial device. The TTL socket remains the console/upload connection.

For Wi-Fi, join **BSHE27-Camera**, password **password**, and open **http://192.168.4.1/**. The page initially loads telemetry; video is optional.

## Connect the Pixhawk

Use the [wiring guide](Wiring.md). The GOOUUU receives on GPIO42 and transmits on GPIO41, at 57600 baud. Both boards share ground. The Pixhawk runs ArduCopter.

## Optional Python helpers

These run on your computer, not on the GOOUUU. Install Python and the packages listed in [Python Packages.txt](Python%20Packages.txt):

```powershell
python -m pip install -r "Docs/Python Packages.txt"
```

- **pyserial 3.5** lets the USB/camera-setting and optional serial Wi-Fi checks talk to the board.
- **pymavlink 2.4.50** is used only when regenerating independent MAVLink test messages.

The web-page updater uses Python's built-in tools and needs neither package. PlatformIO manages its own Python environment for builds.

For browser checks, install Node.js, Microsoft Edge and Playwright. For Windows C++ checks, install Visual Studio C++ Build Tools. See [Editing and Testing](Editing%20and%20Testing.md) for commands. These extras are optional for normal build/upload and camera viewing.

## Where files go

Downloaded build tools and temporary builds go in **Build Tools**. Diagnostics, screenshots and test outputs go in **Saved Results**. Both stay on this computer and are excluded from Git.

From a terminal with PlatformIO on PATH, run `pio run` to build or `pio run -t upload` to upload from the project root.
