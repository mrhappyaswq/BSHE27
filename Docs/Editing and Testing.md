# Editing and testing

Run commands from the project root. Put board changes in the matching **Code** feature folder. Put computer helper programs in **Helpers**.

## Build the board program

Use **GOOUUU: Build** in VS Code, or `pio run`. This compiles without uploading. **Ctrl+Shift+B** instead builds and uploads.

## Change the camera page

Edit `Code/Web Server/viewer.html`, then update its copy inside the board program:

```powershell
python "Helpers/Update Web Page.py"
```

Save both `viewer.html` and `dashboard_page.h` in version control. The updater preserves the page's exact text, including line endings.

## Check the C++ code

On Windows with Visual Studio C++ Build Tools installed:

```powershell
& "./Checks/Code Checks/Run Checks.ps1"
```

These checks exercise the actual MAVLink parser, vehicle client, mission state machine, frame metadata, camera math and ArUco detector/pose/preview using simulated UART and time. They also check the real-camera picture in **Checks/Code Checks/Test Pictures**. Results go to **Saved Results/Code Checks**. No flight hardware is opened.

To regenerate `Checks/Code Checks/vectors.h` when necessary:

```powershell
python "Helpers/Make Test Messages.py"
```

This requires pymavlink. Install the versions in [Python Packages.txt](Python%20Packages.txt) using the command in [Setup](Setup%20Guide.md).

## Check the web page

With Node.js, Playwright and Microsoft Edge installed:

```powershell
node "Checks/Web Page Checks/viewer.cjs"
```

Install Playwright into your computer-only tool folder if needed:

```powershell
npm install --prefix "Build Tools/Browser Checks" playwright
$env:PLAYWRIGHT_MODULE = (Resolve-Path "Build Tools/Browser Checks/node_modules/playwright").Path
node "Checks/Web Page Checks/viewer.cjs"
```

The browser checks simulate telemetry, video, USB framing, camera controls, altitude profiles, ArUco overlays and stale data. Screenshots go to **Saved Results**. They do not connect to the board.

## Check the real camera

Use `--help` to see the options:

```powershell
python "Helpers/Check USB Camera.py" --help
python "Helpers/Check Camera Settings.py" --help
python "Helpers/Check WiFi.py" --help
python "Helpers/Check ArUco Speed.py" --help
```

These require the relevant live connection. Close competing serial viewers first. Camera-setting checks deliberately change settings while testing. See the [Camera Guide](Camera%20Guide.md) for examples and interpretation.

Builds and simulations do not validate physical Pixhawk wiring, camera calibration, ESP32 timing or flight performance.

See [Camera Speed](Camera%20Speed.md) for per-stage USB timing and the exact optimization scope. The C++ runner now also compiles the vendored JPEG decoder and verifies real JPEG fixtures.
