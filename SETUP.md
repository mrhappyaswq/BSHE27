# Quick setup — Windows / ESP32 WROOM

1. Install Python 3 and VS Code. Download this repository and open its folder in VS Code.
2. Open **Terminal → New Terminal** and run:

   ```powershell
   py -3 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install mpremote esptool
   ```

3. Install MicroPython on the ESP32 once: [firmware steps](docs/setup.md#install-micropython-firmware-once).
4. Connect the ESP32 by USB. Press **Ctrl+Shift+B** to upload.
5. Select **Terminal → Run Task → ESP32: Monitor**, then press the board's **EN/RESET**. Expect `Alive` every five seconds.
6. For Pixhawk UART: **TX → GPIO32, RX → GPIO33, GND → GND**, **57600 baud**. Verify [TELEM pinout/voltage](docs/hardware.md). Expect `HEARTBEAT` messages.

Keep propellers removed during bench setup.
