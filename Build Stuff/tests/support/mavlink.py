"""Independent frame fixtures, simulated clock and fake UART."""

import struct

def wire_frame(message_id, payload, version=1, system=1, component=1, flags=0):
    """Independent bitwise X.25 implementation used to build test input."""
    if version == 1:
        header = bytes((len(payload), 0, system, component, message_id))
        magic = b"\xfe"
    else:
        header = bytes((len(payload), flags, 0, 0, system, component,
                        message_id & 255, (message_id >> 8) & 255, message_id >> 16))
        magic = b"\xfd"
    extra = {0: 50, 1: 124, 24: 24, 33: 104, 77: 143}[message_id]
    crc = 0xFFFF
    for byte in header + payload + bytes((extra,)):
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (0x8408 if crc & 1 else 0)
    return magic + header + payload + struct.pack("<H", crc) + (b"\x00" * 13 if flags & 1 else b"")


def heartbeat(mode=4, armed=False, autopilot=3):
    return wire_frame(0, struct.pack("<IBBBBB", mode, 2, autopilot, 128 if armed else 0, 3, 3))


def position(altitude=1500):
    return wire_frame(33, struct.pack("<IiiiihhhH", 100, 475000000, -1220000000,
                                      10000, altitude, 0, 0, 0, 0))


class Clock:
    def __init__(self):
        self.now = 0

    def ticks(self):
        return self.now

    def sleep(self, milliseconds):
        self.now += milliseconds


class UART:
    def __init__(self, rx=b"", on_write=None):
        self.rx = bytearray(rx)
        self.writes = []
        self.on_write = on_write
        self.closed = False
        self.read_size = 256

    def read(self, count):
        result = bytes(self.rx[:min(count, self.read_size)])
        del self.rx[:len(result)]
        return result or None

    def write(self, data):
        self.writes.append(data)
        if self.on_write:
            self.on_write(self, data)
        return len(data)

    def deinit(self):
        self.closed = True
