# Setup and upload

Open the project root in VS Code, or open `BSHE27.code-workspace`.

## Install the Windows tools

Install [VS Code](https://code.visualstudio.com/download),
[Python 3](https://www.python.org/downloads/) and
[Git](https://git-scm.com/download/win). In VS Code, open the **entire project
folder**, then open **Terminal > New Terminal** (PowerShell) and run:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install mpremote esptool
.\.venv\Scripts\python.exe -m mpremote connect list
```

The `py -3` command comes from the Windows Python installation. Select
**Install Recommended Extensions** when VS Code offers it. These add Python
editing, a status-bar upload button, and optional GitHub pull-request tools.
The built-in Git support handles commits and pushes without an extension.

## Install MicroPython firmware once

Connect the ESP32 to the laptop with a **USB data cable**. Download the stable
`.bin` from the official [ESP32 / WROOM firmware page](https://micropython.org/download/ESP32_GENERIC/).
Confirm that your module has **at least 4 MiB flash**, as required by that
generic image. Use the board's COM port from Device Manager or the `mpremote
connect list` output. Replace `COM4` and the `.bin` path below:

```powershell
.\.venv\Scripts\python.exe -m esptool --port COM4 erase-flash
.\.venv\Scripts\python.exe -m esptool --port COM4 --baud 460800 write-flash 0x1000 "C:\path\to\ESP32_GENERIC-firmware.bin"
.\.venv\Scripts\python.exe -m mpremote connect COM4 repl
```

The erase step clears the board's existing firmware and files. Follow the
firmware page's board instructions if your exact module needs a different
image. The REPL should display a `>>>` prompt. Leave it with **Ctrl+]** before
using the upload button. If the firmware tool cannot connect, use the board's
BOOT and RESET buttons as described in the official ESP32 tutorial.

## Upload and monitor

Use **Upload ESP32** or **Ctrl+Shift+B**. The uploader discovers Python files
under `device/`, creates package folders on the board, copies the files and
resets into the passive boot monitor. It excludes cache and hidden folders.

Use **ESP32 Monitor** for the USB REPL and **Check Pixhawk** for the five-second
telemetry check. Close the monitor with **Ctrl+]** before another operation
opens the same serial port.

The same commands work from the project root:

```powershell
.\.venv\Scripts\python.exe tools/esp32.py list
.\.venv\Scripts\python.exe tools/esp32.py upload --port COM4
.\.venv\Scripts\python.exe tools/esp32.py monitor --port COM4
.\.venv\Scripts\python.exe tools/esp32.py check --port COM4
```

Substitute your ESP32's USB port for `COM4`. VS Code tasks use `auto`; change
their `--port` argument if multiple USB serial devices are connected.
`--dry-run` previews an operation without connecting to a board.

Check the [wiring guide](hardware.md) before connecting the Pixhawk, and the
[mission guide](missions.md) before starting flight code. VS Code's ordinary
Python Run button executes host Python; device modules require MicroPython.
