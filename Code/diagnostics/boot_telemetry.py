"""ESP32-S3-CAM USB and Pixhawk telemetry check.

Runs after reset as /main.py. Receives only: it cannot arm or move the drone.
"""

from banshee import status_led


import sys
import time
from machine import UART

from config import (UART_ID, UART_BAUDRATE as UART_BAUD,
                    UART_RX_PIN as UART_RX_GPIO, UART_TX_PIN as UART_TX_GPIO)

from banshee.mavlink.heartbeat import HeartbeatParser


# UART1 uses the free S3 header pins configured in config.py.
# Boot listens only; it never arms, changes mode, or starts a mission.


@status_led.indicate("boot")
def main():
    """Print validated Pixhawk heartbeats and periodic UART status."""
    from config import validate_runtime
    validate_runtime()
    print("BSHE27 ESP32-S3 MicroPython check")
    print("Runtime:", sys.platform)
    print("Listening for Pixhawk MAVLink HEARTBEAT on GPIO", UART_RX_GPIO)
    uart = UART(
        UART_ID,
        baudrate=UART_BAUD,
        tx=UART_TX_GPIO,
        rx=UART_RX_GPIO,
        timeout=0,
    )
    parser = HeartbeatParser()
    last_report = time.ticks_ms()
    byte_count = 0
    heartbeat_count = 0
    last_heartbeat = None

    while True:
        if uart.any():
            data = uart.read(256)
            if data:
                byte_count += len(data)
                for heartbeat in parser.feed(data):
                    heartbeat_count += 1
                    print("HEARTBEAT", heartbeat)
                    from config import TARGET_SYSTEM, TARGET_COMPONENT
                    if (heartbeat["system_id"] == TARGET_SYSTEM and
                            heartbeat["component_id"] == TARGET_COMPONENT and
                            heartbeat["autopilot"] == 3 and
                            heartbeat["vehicle_type"] in (2, 3, 4, 13, 14, 15, 29, 35)):
                        last_heartbeat = time.ticks_ms()

        now = time.ticks_ms()
        status_led.telemetry(last_heartbeat, now)
        if time.ticks_diff(now, last_report) >= 5000:
            print(
                "Alive; UART bytes:",
                byte_count,
                "valid heartbeats:",
                heartbeat_count,
            )
            last_report = now
        time.sleep_ms(20)


if __name__ == "__main__":
    main()
