"""Receive-only Pixhawk monitor shared by the camera dashboard.

Owns UART1 while the dashboard runs. Never transmits or starts missions.
"""

import config
from banshee.compat import ticks_ms, ticks_diff
from banshee.mavlink.heartbeat import HeartbeatParser


class TelemetryMonitor:
    def __init__(self, uart_factory=None, clock=ticks_ms):
        self.clock = clock
        self.uart = None
        self.parser = HeartbeatParser()
        self.last_heartbeat = None
        self.heartbeat = None
        self.byte_count = 0
        self.heartbeat_count = 0
        self.error = None
        self.enabled = config.TELEMETRY_ENABLED
        if self.enabled:
            try:
                if uart_factory is None:
                    from machine import UART
                    uart_factory = UART
                self.uart = uart_factory(
                    config.UART_ID, baudrate=config.UART_BAUDRATE,
                    tx=config.UART_TX_PIN, rx=config.UART_RX_PIN,
                    timeout=0, rxbuf=8192)
                print("Pixhawk receive-only monitor: GPIO%d RX, %d baud" %
                      (config.UART_RX_PIN, config.UART_BAUDRATE))
            except Exception as exc:
                self.error = str(exc)
                print("Pixhawk monitor unavailable:", self.error)

    def poll(self):
        if self.uart is None or self.error:
            return
        try:
            # Bounded work; video and HTTP must continue under heavy UART traffic.
            for _ in range(4):
                data = self.uart.read(256)
                if not data:
                    break
                self.byte_count += len(data)
                for heartbeat in self.parser.feed(data):
                    if (heartbeat["system_id"] == config.TARGET_SYSTEM and
                            heartbeat["component_id"] == config.TARGET_COMPONENT and
                            heartbeat["autopilot"] == 3 and
                            heartbeat["vehicle_type"] in (2, 3, 4, 13, 14, 15, 29, 35)):
                        self.heartbeat = heartbeat
                        self.last_heartbeat = self.clock()
                        self.heartbeat_count += 1
        except Exception as exc:
            self.error = str(exc)
            print("Pixhawk UART:", self.error)

    def snapshot(self):
        age = None if self.last_heartbeat is None else max(
            0, ticks_diff(self.clock(), self.last_heartbeat))
        if not self.enabled:
            state = "disabled"
        elif self.error:
            state = "error"
        elif age is None:
            state = "waiting"
        elif age > config.HEARTBEAT_TIMEOUT * 1000:
            state = "lost"
        else:
            state = "connected"
        fresh = state == "connected"
        return {"state": state, "error": self.error, "heartbeat_age_ms": age,
                "uart_bytes": self.byte_count, "heartbeats": self.heartbeat_count,
                "system_id": config.TARGET_SYSTEM, "component_id": config.TARGET_COMPONENT,
                "armed": bool(self.heartbeat["base_mode"] & 128) if fresh else None,
                "custom_mode": self.heartbeat["custom_mode"] if fresh else None,
                "system_status": self.heartbeat["system_status"] if fresh else None}

    def close(self):
        if self.uart is not None:
            try:
                self.uart.deinit()
            except Exception as exc:
                print("Pixhawk UART cleanup:", exc)
            finally:
                self.uart = None
