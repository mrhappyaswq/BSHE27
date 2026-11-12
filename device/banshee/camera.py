"""Nonblocking, checksummed UART client for the XIAO QR camera firmware.

Only one capture request is outstanding. Its LOCAL start time bounds image
age, so a delayed UART response cannot make an old image look fresh.
"""

import json
import math
import os

import config
from banshee.compat import sleep_ms, ticks_diff, ticks_ms

MAX_LINE = 1024


def crc16(data):
    """CRC-16/CCITT-FALSE (123456789 -> 0x29B1), shared with camera firmware."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ (0x1021 if crc & 0x8000 else 0)) & 0xFFFF
    return crc


def encode_packet(message):
    data = json.dumps(message).encode("utf-8")
    return data + ("*%04X\n" % crc16(data)).encode("ascii")


def decode_packet(line):
    data, checksum = line.rsplit(b"*", 1)
    if len(checksum) != 4 or crc16(data) != int(checksum, 16):
        raise ValueError("Camera packet checksum mismatch")
    message = json.loads(data)
    if not isinstance(message, dict) or message.get("v") != 1:
        raise ValueError("Unsupported camera packet")
    return message


def _number(value):
    try:
        return (isinstance(value, (int, float)) and not isinstance(value, bool)
                and not math.isnan(value) and not math.isinf(value))
    except OverflowError:
        return False


class QRMarker:
    """Validated canonical corners; image top=forward, image right=right.

    Corners MUST be QR top-left, top-right, bottom-right, bottom-left from
    quirc, not corners sorted by screen position. Mirrored images are rejected.
    Yaw is an image-plane approximation, intended for a near-level camera.
    """

    def __init__(self, message, target_payload):
        self.frame_id = message.get("id")
        self.width = message.get("width")
        self.height = message.get("height")
        if (self.width, self.height) != (320, 240):
            raise ValueError("Expected camera QVGA image dimensions")
        marker = message.get("marker")
        if not isinstance(marker, dict) or marker.get("payload") != target_payload:
            raise ValueError("Unexpected QR payload")
        corners = marker.get("corners")
        if not isinstance(corners, list) or len(corners) != 4:
            raise ValueError("QR requires four canonical corners")
        for point in corners:
            if (not isinstance(point, list) or len(point) != 2
                    or not all(_number(value) for value in point)
                    or not 0 <= point[0] < self.width
                    or not 0 <= point[1] < self.height):
                raise ValueError("QR corner outside image or nonfinite")
        for i in range(4):
            a, b, c = corners[i], corners[(i + 1) % 4], corners[(i + 2) % 4]
            cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
            if cross < 16:
                raise ValueError("QR corners mirrored, too small or not convex")
        self.corners = corners
        # Diagonal intersection is the projective image of the square's center.
        a, b, c, d = corners
        ux, uy = c[0] - a[0], c[1] - a[1]
        vx, vy = d[0] - b[0], d[1] - b[1]
        denominator = ux * vy - uy * vx
        t = ((b[0] - a[0]) * vy - (b[1] - a[1]) * vx) / denominator
        self.cx, self.cy = a[0] + t * ux, a[1] + t * uy
        self.yaw = math.atan2((b[1] - a[1]) + (c[1] - d[1]),
                              (b[0] - a[0]) + (c[0] - d[0]))


def open_camera_uart():
    from machine import Pin, UART
    return UART(config.CAMERA_UART_ID, baudrate=config.CAMERA_UART_BAUDRATE,
                tx=Pin(config.CAMERA_UART_TX_PIN), rx=Pin(config.CAMERA_UART_RX_PIN),
                timeout=0, rxbuf=2048)


class XiaoCamera:
    def __init__(self, uart=None):
        self.uart = open_camera_uart() if uart is None else uart
        self._buffer = bytearray()
        self._discarding = False
        self._next_id = int.from_bytes(os.urandom(4), "little") & 0x3FFFFFFF
        self._pending = None
        self._latest = None
        self._latest_at = None
        self._completed = None
        self.last_error = None
        self._closed = False

    def _request(self, operation):
        self._next_id = self._next_id % 0x7FFFFFFF + 1
        packet = encode_packet({"v": 1, "id": self._next_id, "op": operation})
        started = ticks_ms()
        if self.uart.write(packet) != len(packet):
            self._latest = None
            raise OSError("Incomplete camera UART write")
        self._pending = (self._next_id, started, operation)

    def _accept(self, line):
        try:
            message = decode_packet(line)
        except (ValueError, TypeError, UnicodeError):
            self._latest = None
            self.last_error = "Invalid camera packet"
            return
        if self._pending is None or message.get("id") != self._pending[0]:
            return
        _, started, operation = self._pending
        self._pending = None
        self._completed = message
        self._latest = None
        self.last_error = message.get("error")
        if operation != "scan" or self.last_error:
            return
        if ticks_diff(ticks_ms(), started) > config.CAMERA_MAX_AGE_MS:
            self.last_error = "Camera frame exceeded freshness limit"
            return
        if message.get("marker") is None:
            return
        try:
            self._latest = QRMarker(message, config.CAMERA_TARGET_PAYLOAD)
            self._latest_at = started
        except (ValueError, TypeError, ZeroDivisionError) as exc:
            self.last_error = str(exc)

    def _poll(self):
        if self._closed:
            raise RuntimeError("Camera is closed")
        # Bound time/memory even with noise or a continuously transmitting peer.
        for _ in range(8):
            chunk = self.uart.read(256)
            if not chunk:
                break
            for byte in chunk:
                if byte == 10:
                    if not self._discarding and self._buffer:
                        self._accept(bytes(self._buffer))
                    self._buffer = bytearray()
                    self._discarding = False
                elif not self._discarding:
                    if len(self._buffer) >= MAX_LINE:
                        self._buffer = bytearray()
                        self._discarding = True
                    else:
                        self._buffer.append(byte)
        if (self._pending is not None and self._pending[2] == "scan"
                and ticks_diff(ticks_ms(), self._pending[1]) > config.CAMERA_REQUEST_TIMEOUT_MS):
            self._pending = None
            self._latest = None
            self.last_error = "Camera request timed out"

    def marker(self):
        """Poll once, request next frame, return a fresh QRMarker or None."""
        self._poll()
        if self._pending is None:
            self._request("scan")
        if (self._latest_at is None
                or ticks_diff(ticks_ms(), self._latest_at) > config.CAMERA_MAX_AGE_MS):
            return None
        return self._latest

    def wait_for_marker(self, timeout=None):
        """Require three distinct fresh frames. BENCH/PREFLIGHT ONLY.

        This wait does not service a flight controller. It checks actual
        decoding within the configured deadline, not just UART connectivity.
        """
        timeout = config.CAMERA_PREFLIGHT_TIMEOUT if timeout is None else timeout
        started = ticks_ms()
        count = 0
        last_frame_id = None
        while True:
            marker = self.marker()
            if marker is None:
                count = 0
            elif marker.frame_id != last_frame_id:
                count += 1
                last_frame_id = marker.frame_id
                if count >= 3:
                    return marker
            if ticks_diff(ticks_ms(), started) >= timeout * 1000:
                raise RuntimeError("No fresh landing QR detected: " + (self.last_error or "target not visible"))
            sleep_ms(20)

    def capture_photo(self, timeout=5):
        """Save a grayscale JPEG to XIAO microSD; BENCH ONLY, never in flight.

        This blocking helper owns the UART until the photo response arrives.
        Firmware photo and camera errors are surfaced to the caller.
        """
        self._poll()
        if self._pending is not None:
            raise RuntimeError("Camera busy; use a separate bench camera session for photos")
        self._latest = None
        self._completed = None
        self._request("photo")
        started = ticks_ms()
        while self._completed is None:
            self._poll()
            if ticks_diff(ticks_ms(), started) >= timeout * 1000 or self._pending is None:
                if self._completed is None:
                    self._pending = None
                    raise RuntimeError("Camera photo request timed out")
            sleep_ms(20)
        if self._completed.get("error"):
            raise RuntimeError("Camera photo failed: " + str(self._completed["error"]))
        path = self._completed.get("path")
        if not isinstance(path, str) or not path.startswith("/photos/"):
            raise ValueError("Invalid camera photo path")
        return path

    def close(self):
        if not self._closed:
            self._closed = True
            self._latest = None
            if hasattr(self.uart, "deinit"):
                self.uart.deinit()
