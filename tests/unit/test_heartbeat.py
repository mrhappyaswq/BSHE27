"""Host-side checks for the MicroPython heartbeat parser."""

import unittest


from banshee.mavlink.heartbeat import HeartbeatParser  # noqa: E402


def crc_step(crc, value):
    value ^= crc & 0xFF
    value ^= (value << 4) & 0xFF
    return ((crc >> 8) ^ (value << 8) ^ (value << 3) ^ (value >> 4)) & 0xFFFF


def heartbeat_frame(version=2, signed=False):
    payload = bytes((0x78, 0x56, 0x34, 0x12, 2, 3, 0x51, 4, 3))
    if version == 2:
        header = bytes((0xFD, len(payload), int(signed), 0, 7, 1, 2, 0, 0, 0))
    else:
        header = bytes((0xFE, len(payload), 7, 1, 2, 0))
    crc = 0xFFFF
    for value in header[1:] + payload + bytes((50,)):
        crc = crc_step(crc, value)
    frame = header + payload + bytes((crc & 0xFF, crc >> 8))
    return frame + (bytes(13) if signed else b"")


class HeartbeatParserTests(unittest.TestCase):
    def test_v1_and_v2_heartbeats(self):
        parser = HeartbeatParser()
        results = parser.feed(heartbeat_frame(1) + heartbeat_frame(2))
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0]["custom_mode"], 0x12345678)
        self.assertEqual(results[0]["system_id"], 1)
        self.assertEqual(results[0]["component_id"], 2)

    def test_fragmented_signed_v2_frame(self):
        parser = HeartbeatParser()
        frame = heartbeat_frame(2, signed=True)
        self.assertEqual(parser.feed(frame[:4]), [])
        self.assertEqual(parser.feed(frame[4:-1]), [])
        self.assertEqual(len(parser.feed(frame[-1:])), 1)
        self.assertEqual(parser.buffer, bytearray())

    def test_bad_crc_is_ignored_and_next_frame_is_found(self):
        parser = HeartbeatParser()
        damaged = bytearray(heartbeat_frame())
        damaged[10] ^= 0x01
        self.assertEqual(len(parser.feed(b"noise" + damaged + heartbeat_frame())), 1)

    def test_unknown_incompatibility_flag_is_ignored(self):
        parser = HeartbeatParser()
        invalid = bytearray(heartbeat_frame())
        invalid[2] = 0x02
        self.assertEqual(len(parser.feed(invalid + heartbeat_frame())), 1)


if __name__ == "__main__":
    unittest.main()
