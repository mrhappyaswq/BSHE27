import binascii
import copy
import math
import unittest
from unittest.mock import patch

import config
from banshee import camera as cam
from tests.support.mavlink import Clock, UART


def detection(request_id, corners=None):
    return {"v": 1, "id": request_id, "width": 320, "height": 240,
            "marker": {"payload": "BSHE27-LAND", "corners": corners or
                       [[120, 80], [200, 80], [200, 160], [120, 160]]}}


def packet(message):
    # Independent CRC implementation for wire fixtures.
    data = cam.json.dumps(message).encode()
    return data + ("*%04X\n" % binascii.crc_hqx(data, 0xFFFF)).encode()


class CameraTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        for name, value in (("ticks_ms", self.clock.ticks), ("sleep_ms", self.clock.sleep)):
            item = patch.object(cam, name, value)
            item.start()
            self.addCleanup(item.stop)
        self.uart = UART()
        self.camera = cam.XiaoCamera(self.uart)

    def request_id(self):
        return cam.decode_packet(self.uart.writes[-1].rstrip(b"\n"))["id"]

    def reply(self, message):
        self.uart.rx.extend(packet(message))
        return self.camera.marker()

    def test_crc_and_wire_format(self):
        self.assertEqual(cam.crc16(b"123456789"), 0x29B1)
        self.assertEqual(cam.encode_packet({"v": 1}), packet({"v": 1}))

    def test_fragmented_reply_selects_real_target_and_requests_next_frame(self):
        self.assertIsNone(self.camera.marker())
        first = self.request_id()
        self.uart.read_size = 7
        self.uart.rx.extend(packet(detection(first)))
        marker = None
        for _ in range(10):
            marker = self.camera.marker()
            if marker is not None:
                break
        self.assertEqual((marker.cx, marker.cy, marker.yaw), (160, 120, 0))
        self.assertEqual(marker.frame_id, first)
        self.assertNotEqual(self.request_id(), first)

    def test_late_capture_cannot_be_freshened_by_response_arrival(self):
        self.camera.marker()
        first = self.request_id()
        self.clock.now = config.CAMERA_MAX_AGE_MS + 1
        self.assertIsNone(self.reply(detection(first)))
        self.assertIn("freshness", self.camera.last_error)

    def test_cached_detection_expires_from_request_time(self):
        self.camera.marker()
        self.clock.now = 100
        marker = self.reply(detection(self.request_id()))
        self.assertIsNotNone(marker)
        self.clock.now = config.CAMERA_MAX_AGE_MS + 1
        self.assertIsNone(self.camera.marker())

    def test_wrong_request_and_wrong_target_do_not_create_detection(self):
        self.camera.marker()
        request_id = self.request_id()
        self.assertIsNone(self.reply(detection(request_id + 1)))
        message = detection(request_id)
        message["marker"]["payload"] = "different-pad"
        self.assertIsNone(self.reply(message))

    def test_target_loss_and_error_immediately_invalidate_previous_detection(self):
        for reply in ({"marker": None}, {"error": "camera_capture_failed"}):
            self.camera.marker()
            self.assertIsNotNone(self.reply(detection(self.request_id())))
            self.assertIsNone(self.reply(dict(v=1, id=self.request_id(), **reply)))

    def test_corrupted_packet_cannot_keep_old_marker(self):
        self.camera.marker()
        self.assertIsNotNone(self.reply(detection(self.request_id())))
        damaged = bytearray(packet(detection(self.request_id())))
        damaged[-3] ^= 1
        self.uart.rx.extend(damaged)
        self.assertIsNone(self.camera.marker())

    def test_uart_noise_is_bounded_and_recovers_after_newline(self):
        self.camera.marker()
        self.uart.rx.extend(b"x" * 4000 + b"\n" + packet(detection(self.request_id())))
        marker = None
        for _ in range(5):
            marker = self.camera.marker()
            self.assertLessEqual(len(self.camera._buffer), cam.MAX_LINE)
        self.assertIsNotNone(marker)

    def test_timed_out_request_is_replaced_and_old_reply_ignored(self):
        self.camera.marker()
        old = self.request_id()
        self.clock.now += config.CAMERA_REQUEST_TIMEOUT_MS + 1
        self.camera.marker()
        self.assertNotEqual(self.request_id(), old)
        self.assertIsNone(self.reply(detection(old)))

    def test_short_uart_write_is_error(self):
        self.uart.write = lambda data: 1
        with self.assertRaises(OSError):
            self.camera.marker()

    def test_camera_wait_timeout_and_close(self):
        with self.assertRaisesRegex(RuntimeError, "No fresh"):
            self.camera.wait_for_marker(timeout=0.05)
        self.camera.close()
        self.assertTrue(self.uart.closed)
        with self.assertRaisesRegex(RuntimeError, "closed"):
            self.camera.marker()

    def test_preflight_requires_three_distinct_decoded_captures(self):
        def respond(uart, data):
            request = cam.decode_packet(data.rstrip(b"\n"))
            uart.rx.extend(packet(detection(request["id"])))
        self.uart.on_write = respond
        marker = self.camera.wait_for_marker(timeout=1)
        self.assertIsNotNone(marker)
        # A next scan is sent as each previous one completes.
        self.assertEqual(len(self.uart.writes), 4)

    def test_photo_error_success_and_timeout(self):
        def respond(uart, data):
            request = cam.decode_packet(data.rstrip(b"\n"))
            self.assertEqual(request["op"], "photo")
            uart.rx.extend(packet(dict(v=1, id=request["id"], path="/photos/000001.jpg")))
        self.uart.on_write = respond
        self.assertEqual(self.camera.capture_photo(), "/photos/000001.jpg")
        def fail(uart, data):
            request = cam.decode_packet(data.rstrip(b"\n"))
            uart.rx.extend(packet(dict(v=1, id=request["id"], error="sd_full")))
        self.uart.on_write = fail
        with self.assertRaisesRegex(RuntimeError, "sd_full"):
            self.camera.capture_photo()
        self.uart.on_write = None
        with self.assertRaisesRegex(RuntimeError, "timed out"):
            self.camera.capture_photo(timeout=0.05)


class MarkerGeometryTests(unittest.TestCase):
    def test_canonical_corner_order_preserves_rotation(self):
        corners = [[200, 80], [200, 160], [120, 160], [120, 80]]
        marker = cam.QRMarker(detection(1, corners), "BSHE27-LAND")
        self.assertAlmostEqual(marker.yaw, math.pi / 2)
        self.assertEqual((marker.cx, marker.cy), (160, 120))

    def test_projective_center_is_diagonal_intersection(self):
        corners = [[100, 80], [220, 80], [190, 160], [130, 160]]
        marker = cam.QRMarker(detection(1, corners), "BSHE27-LAND")
        self.assertAlmostEqual(marker.cx, 160)
        self.assertAlmostEqual(marker.cy, 80 + 160 / 3)

    def test_invalid_geometry_is_rejected(self):
        valid = detection(1)
        changes = [
            [[120, 80], [120, 160], [200, 160], [200, 80]],  # mirror
            [[120, 80], [200, 160], [200, 80], [120, 160]],  # bow tie
            [[1, 1], [2, 1], [2, 2], [1, 2]],  # too small
            [[-1, 80], [200, 80], [200, 160], [120, 160]],
            [[float("nan"), 80], [200, 80], [200, 160], [120, 160]],
            [[1e300, 80], [200, 80], [200, 160], [120, 160]],
        ]
        for corners in changes:
            message = copy.deepcopy(valid)
            message["marker"]["corners"] = corners
            with self.subTest(corners=corners), self.assertRaises(ValueError):
                cam.QRMarker(message, "BSHE27-LAND")


if __name__ == "__main__":
    unittest.main()
