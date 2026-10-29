"""Small cooperative UART/MAVLink client for ArduCopter on MicroPython.

Transmit MAVLink 1; receive unsigned MAVLink 1 or 2. Only the common messages
needed by these missions are decoded. Call poll()/sleep() frequently; there is
no background thread. Signing is deliberately unsupported, never ignored.
"""

import math
import struct

import config
from banshee.compat import sleep_ms, ticks_diff, ticks_ms


# message ID: (CRC_EXTRA, base payload length)
_MESSAGES = {
    0: (50, 9),       # HEARTBEAT
    1: (124, 31),     # SYS_STATUS
    24: (24, 30),     # GPS_RAW_INT
    33: (104, 28),    # GLOBAL_POSITION_INT
    66: (148, 6),     # REQUEST_DATA_STREAM
    76: (152, 33),    # COMMAND_LONG
    77: (143, 3),     # COMMAND_ACK
    84: (143, 53),    # SET_POSITION_TARGET_LOCAL_NED
    86: (5, 53),      # SET_POSITION_TARGET_GLOBAL_INT
}
_MODES = {"GUIDED": 4, "LAND": 9}
_PREARM_CHECK = 1 << 28
_COPTER_TYPES = (2, 3, 4, 13, 14, 15, 29, 35)


def _crc(data, extra):
    value = 0xFFFF
    for byte in data:
        tmp = byte ^ (value & 0xFF)
        tmp ^= (tmp << 4) & 0xFF
        value = ((value >> 8) ^ (tmp << 8) ^ (tmp << 3) ^ (tmp >> 4)) & 0xFFFF
    tmp = extra ^ (value & 0xFF)
    tmp ^= (tmp << 4) & 0xFF
    return ((value >> 8) ^ (tmp << 8) ^ (tmp << 3) ^ (tmp >> 4)) & 0xFFFF


def _finite(value):
    return not math.isnan(value) and not math.isinf(value)


class Location:
    """Latitude/longitude in degrees; altitude in metres relative to home."""

    def __init__(self, lat, lon, alt):
        if not all(_finite(v) for v in (lat, lon, alt)):
            raise ValueError("Location coordinates must be finite")
        if not -90 <= lat <= 90 or not -180 <= lon <= 180:
            raise ValueError("Latitude or longitude out of range")
        self.lat = lat
        self.lon = lon
        self.alt = alt


def detect_pixhawk_uart():
    """Compatibility name: construct the configured UART, without probing pins.

    A Pixhawk is identified by MAVLinkVehicle's heartbeat handshake, not by the
    existence of a UART. No serial port discovery is available on this board.
    """
    try:
        from machine import Pin, UART
    except ImportError:
        raise RuntimeError("Run on an ESP32 with MicroPython, or inject a test UART")
    return UART(
        config.UART_ID, baudrate=config.UART_BAUDRATE,
        tx=Pin(config.UART_TX_PIN), rx=Pin(config.UART_RX_PIN),
        timeout=0, rxbuf=2048,
    )


class MAVLinkVehicle:
    def __init__(self, uart, baudrate=None, connect_timeout=None):
        if not hasattr(uart, "read") or not hasattr(uart, "write"):
            raise ValueError("Pass a machine.UART object, not a 'UART1' string")
        if baudrate is not None and baudrate != config.UART_BAUDRATE:
            raise ValueError("Set UART baudrate in config.py before creating the UART")
        self.uart = uart
        self._buffer = bytearray()
        self._sequence = 0
        self._closed = False
        self._last_tx_heartbeat = None
        self._heartbeat = None
        self._heartbeat_at = None
        self._status = None
        self._status_at = None
        self._position = None
        self._position_at = None
        self._gps_fix = None
        self._gps_at = None
        self._pending_command = None
        self._ack = None
        timeout = config.CONNECT_TIMEOUT if connect_timeout is None else connect_timeout
        try:
            self._wait(lambda: self._heartbeat is not None, timeout, "Pixhawk heartbeat")
            # Ask for telemetry at 4 Hz. Firmware stream settings may override this.
            self._send(66, struct.pack(
                "<HBBBB", 4, config.TARGET_SYSTEM, config.TARGET_COMPONENT, 0, 1,
            ))
        except BaseException:
            self.close()
            raise

    def _send(self, message_id, payload):
        if self._closed:
            raise RuntimeError("Vehicle connection is closed")
        header = bytes((len(payload), self._sequence, config.SOURCE_SYSTEM,
                        config.SOURCE_COMPONENT, message_id))
        body = header + payload
        packet = b"\xfe" + body + struct.pack("<H", _crc(body, _MESSAGES[message_id][0]))
        written = self.uart.write(packet)
        if written != len(packet):
            raise OSError("Incomplete UART write")
        self._sequence = (self._sequence + 1) & 0xFF

    def _read_frames(self):
        # Bound work per poll so continuous telemetry cannot starve heartbeat TX.
        for _ in range(8):
            chunk = self.uart.read(256)
            if not chunk:
                break
            self._buffer.extend(chunk)
            while len(self._buffer) >= 2:
                magic = self._buffer[0]
                if magic not in (0xFE, 0xFD):
                    del self._buffer[0]
                    continue
                header_len = 6 if magic == 0xFE else 10
                if len(self._buffer) < header_len:
                    break
                length = self._buffer[1]
                flags = 0 if magic == 0xFE else self._buffer[2]
                frame_len = header_len + length + 2 + (13 if flags & 1 else 0)
                if len(self._buffer) < frame_len:
                    break
                if magic == 0xFE:
                    system, component, message_id = self._buffer[3:6]
                else:
                    system, component = self._buffer[5:7]
                    message_id = (self._buffer[7] | self._buffer[8] << 8
                                  | self._buffer[9] << 16)
                definition = _MESSAGES.get(message_id)
                if definition is None or flags & ~1:
                    del self._buffer[:frame_len]
                    continue
                payload_end = header_len + length
                expected = struct.unpack("<H", self._buffer[payload_end:payload_end + 2])[0]
                if _crc(self._buffer[1:payload_end], definition[0]) != expected:
                    # A damaged length/header may have swallowed the next STX.
                    del self._buffer[0]
                    continue
                payload = bytes(self._buffer[header_len:payload_end])
                del self._buffer[:frame_len]
                if (system, component) != (config.TARGET_SYSTEM, config.TARGET_COMPONENT):
                    continue
                if flags & 1:
                    raise RuntimeError("Signed MAVLink is unsupported by this helper")
                base_length = definition[1]
                if magic == 0xFE and length < base_length:
                    continue
                # MAVLink 2 strips trailing zeros, including within base fields.
                if length < base_length:
                    payload += b"\x00" * (base_length - length)
                self._handle(message_id, payload)

    def _handle(self, message_id, payload):
        now = ticks_ms()
        if message_id == 0:
            heartbeat = struct.unpack("<IBBBBB", payload[:9])
            if heartbeat[2] != 3 or heartbeat[1] not in _COPTER_TYPES:
                raise RuntimeError("These missions require an ArduCopter flight controller")
            self._heartbeat = heartbeat
            self._heartbeat_at = now
        elif message_id == 1:
            self._status = struct.unpack("<III", payload[:12])
            self._status_at = now
        elif message_id == 24:
            self._gps_fix = payload[28]
            self._gps_at = now
        elif message_id == 33:
            _, lat, lon, _, relative_alt = struct.unpack("<Iiiii", payload[:20])
            self._position = Location(lat / 1e7, lon / 1e7, relative_alt / 1000)
            self._position_at = now
        elif message_id == 77:
            command, result = struct.unpack("<HB", payload[:3])
            # MAVLink 2 ACKs may address a particular sender. Zero is broadcast.
            addressed = payload + b"\x00" * max(0, 10 - len(payload))
            if addressed[8] not in (0, config.SOURCE_SYSTEM):
                return
            if addressed[9] not in (0, config.SOURCE_COMPONENT):
                return
            if command == self._pending_command:
                self._ack = result

    def poll(self):
        if self._closed:
            raise RuntimeError("Vehicle connection is closed")
        now = ticks_ms()
        if (self._last_tx_heartbeat is None
                or ticks_diff(now, self._last_tx_heartbeat) >= 1000):
            self._send(0, struct.pack("<IBBBBB", 0, 18, 8, 0, 4, 3))
            self._last_tx_heartbeat = now
        self._read_frames()
        if (self._heartbeat_at is not None
                and ticks_diff(ticks_ms(), self._heartbeat_at) > config.HEARTBEAT_TIMEOUT * 1000):
            raise RuntimeError("Pixhawk heartbeat lost")

    def _wait(self, predicate, timeout, description):
        started = ticks_ms()
        while True:
            self.poll()
            if predicate():
                return
            if ticks_diff(ticks_ms(), started) >= timeout * 1000:
                raise RuntimeError("Timed out waiting for " + description)
            sleep_ms(20)

    def sleep(self, seconds):
        started = ticks_ms()
        while ticks_diff(ticks_ms(), started) < seconds * 1000:
            self.poll()
            sleep_ms(20)

    def _fresh(self, timestamp, description):
        if timestamp is None or ticks_diff(ticks_ms(), timestamp) > config.TELEMETRY_TIMEOUT * 1000:
            raise RuntimeError("Missing or stale " + description)

    def mode(self):
        self.poll()
        custom_mode = self._heartbeat[0]
        for name in _MODES:
            if _MODES[name] == custom_mode:
                return name
        return str(custom_mode)

    def armed(self):
        self.poll()
        return bool(self._heartbeat[3] & 128)

    def is_armable(self):
        self.poll()
        if self._status_at is None:
            return False
        self._fresh(self._status_at, "SYS_STATUS")
        present, enabled, healthy = self._status
        return (self._heartbeat[4] == 3
                and bool(present & enabled & healthy & _PREARM_CHECK))

    def gps_ready(self):
        self.poll()
        now = ticks_ms()
        return (self._gps_at is not None and self._position_at is not None
                and ticks_diff(now, self._gps_at) <= config.TELEMETRY_TIMEOUT * 1000
                and ticks_diff(now, self._position_at) <= config.TELEMETRY_TIMEOUT * 1000
                and self._gps_fix >= 3)

    def altitude(self):
        self.poll()
        self._fresh(self._position_at, "GLOBAL_POSITION_INT altitude")
        return self._position.alt

    def global_location(self):
        self.poll()
        if not self.gps_ready():
            raise RuntimeError("A fresh 3D GPS fix and global position are required")
        return Location(self._position.lat, self._position.lon, self._position.alt)

    def _command(self, command, params):
        self.poll()  # Drain old ACKs before starting a new transaction.
        self._pending_command = command
        self._ack = None
        try:
            self._send(76, struct.pack(
                "<7fHBBB", *params, command, config.TARGET_SYSTEM, config.TARGET_COMPONENT, 0,
            ))
            self._wait(lambda: self._ack is not None and self._ack != 5,
                       config.COMMAND_TIMEOUT, "command ACK %d" % command)
            if self._ack != 0:
                raise RuntimeError("MAVLink command %d rejected (result %d)" % (command, self._ack))
        finally:
            self._pending_command = None

    def set_mode(self, name):
        if name not in _MODES:
            raise ValueError("Unsupported mode: " + name)
        self._command(176, (1, _MODES[name], 0, 0, 0, 0, 0))
        self._wait(lambda: self._heartbeat[0] == _MODES[name],
                   config.COMMAND_TIMEOUT, name + " mode heartbeat")

    def arm(self):
        # No force-arm parameter or bypass of the autopilot's prearm checks.
        self._command(400, (1, 0, 0, 0, 0, 0, 0))
        self._wait(lambda: bool(self._heartbeat[3] & 128),
                   config.COMMAND_TIMEOUT, "armed heartbeat")

    def takeoff(self, altitude):
        if not _finite(altitude) or altitude <= 0:
            raise ValueError("Takeoff altitude must be positive and finite")
        self._command(22, (0, 0, 0, 0, 0, 0, altitude))

    def goto(self, location):
        self.poll()
        payload = struct.pack(
            "<IiifffffffffHBBB", ticks_ms() & 0xFFFFFFFF,
            int(round(location.lat * 1e7)), int(round(location.lon * 1e7)),
            location.alt, 0, 0, 0, 0, 0, 0, 0, 0,
            0x0DF8, config.TARGET_SYSTEM, config.TARGET_COMPONENT, 3,
        )
        self._send(86, payload)

    def send_body_velocity(self, forward, right, down, duration=0.1):
        """Metres/second in body NED: forward, right, DOWN positive."""
        if not all(_finite(v) for v in (forward, right, down, duration)) or duration < 0:
            raise ValueError("Velocity and duration must be finite; duration cannot be negative")
        started = ticks_ms()
        while True:
            self.poll()
            self._send(84, struct.pack(
                "<IfffffffffffHBBB", ticks_ms() & 0xFFFFFFFF,
                0, 0, 0, forward, right, down, 0, 0, 0, 0, 0,
                0x0DC7, config.TARGET_SYSTEM, config.TARGET_COMPONENT, 8,
            ))
            if ticks_diff(ticks_ms(), started) >= duration * 1000:
                return
            self.sleep(min(0.1, duration))

    def close(self):
        if not self._closed:
            self._closed = True
            if hasattr(self.uart, "deinit"):
                self.uart.deinit()
