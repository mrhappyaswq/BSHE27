# RGB indicator guide

Each state uses one color: count 1, 2 or 3 blinks, then a clear dark pause.
Blinks last 180 ms, gaps between blinks 180 ms, and the final pause 1200 ms.
The same color/count is never assigned to two states.

| State | Color | Blinks, then pause |
| --- | --- | --- |
| `boot` | ![White](assets/led/white.svg) | 1 |
| `idle` | ![White](assets/led/white.svg) | 2 |
| `stopped` | ![White](assets/led/white.svg) | 3 |
| `wifi_up` | ![Cyan](assets/led/cyan.svg) | 1 |
| `wifi_connected` | ![Cyan](assets/led/cyan.svg) | 2 |
| `wifi_up_pixhawk` | ![Cyan](assets/led/cyan.svg) | 3 |
| `connected` | ![Green](assets/led/green.svg) | 1 |
| `wifi_connected_pixhawk` | ![Green](assets/led/green.svg) | 2 |
| `qr_found` | ![Green](assets/led/green.svg) | 3 |
| `streaming` | ![Blue](assets/led/blue.svg) | 1 |
| `streaming_pixhawk` | ![Blue](assets/led/blue.svg) | 2 |
| `mission` | ![Blue](assets/led/blue.svg) | 3 |
| `camera_init` | ![Purple](assets/led/purple.svg) | 1 |
| `camera_ready` | ![Purple](assets/led/purple.svg) | 2 |
| `capture` | ![Purple](assets/led/purple.svg) | 3 |
| `error` | ![Red](assets/led/red.svg) | 1 |
| `link_lost` | ![Red](assets/led/red.svg) | 2 |
| `telemetry_error` | ![Red](assets/led/red.svg) | 3 |
| `wifi_up_camera_error` | ![Amber](assets/led/amber.svg) | 1 |
| `wifi_connected_camera_error` | ![Amber](assets/led/amber.svg) | 2 |
| `landing` | ![Amber](assets/led/amber.svg) | 3 |
| `waiting` | ![Magenta](assets/led/magenta.svg) | 1 |
| `qr_search` | ![Magenta](assets/led/magenta.svg) | 2 |

Briefly press BOOT to mute/resume. Reset restores the configured indicator.
Holding BOOT during reset still enters download mode. Power/USB lights are separate.

Fault priority: Wi-Fi down, camera fault, UART error, lost heartbeat, streaming, idle Wi-Fi.
A lost heartbeat means a previously connected Pixhawk expired; an unplugged Pixhawk
that has never connected remains waiting. The webpage shows every subsystem.

Edit `Code/banshee/status_led.py` for patterns and `Code/config.py` for brightness
and button settings. Updates use a soft timer and do not sleep in application code.
