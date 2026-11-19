import copy
import math
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import config
from banshee import camera as cam


def detection(request_id=1, corners=None):
    return {"id": request_id, "width": 320, "height": 240,
            "marker": {"payload": "BSHE27-LAND", "corners": corners or
                       [[120, 80], [200, 80], [200, 160], [120, 160]]}}


class FakeCamera:
    def __init__(self):
        self.captures = 0
        self.freed = 0
        self.closed = False
        self.image = bytes(320 * 240)

    def capture(self):
        self.captures += 1
        return self.image

    def free_buffer(self):
        self.freed += 1

    def deinit(self):
        self.closed = True


class LocalCameraTests(unittest.TestCase):
    def setUp(self):
        self.device = FakeCamera()
        self.now = 0
        clock = patch.object(cam, "ticks_ms", lambda: self.now)
        clock.start()
        self.addCleanup(clock.stop)

    def camera(self, decoder=None):
        return cam.LocalCamera(self.device, decoder or (lambda *args: [detection()["marker"]]))

    def test_fresh_capture_is_local_and_frame_ids_are_distinct(self):
        camera = self.camera()
        first, second = camera.marker(), camera.marker()
        self.assertNotEqual(first.frame_id, second.frame_id)
        self.assertEqual((first.cx, first.cy), (160, 120))
        self.assertEqual(self.device.captures, 4)
        self.assertEqual(self.device.freed, 4)
        camera.close()
        self.assertTrue(self.device.closed)
        with self.assertRaisesRegex(RuntimeError, "closed"):
            camera.marker()

    def test_loss_does_not_return_a_cached_detection(self):
        results = [[detection()["marker"]], [], [{"payload": "other"}]]
        camera = self.camera(lambda *args: results.pop(0))
        self.assertIsNotNone(camera.marker())
        self.assertIsNone(camera.marker())
        self.assertIsNone(camera.marker())

    def test_multiple_targets_are_rejected(self):
        camera = self.camera(lambda *args: [detection()["marker"]]*2)
        self.assertIsNone(camera.marker())
        self.assertIn("Multiple", camera.last_error)

    def test_slow_decoder_raises_and_services_telemetry(self):
        def decode(*args):
            self.now = config.CAMERA_MAX_AGE_MS + 1
            return [detection()["marker"]]
        services = []
        with self.assertRaisesRegex(RuntimeError, "freshness"):
            self.camera(decode).marker(service=lambda: services.append(True))
        self.assertEqual(len(services), 2)
        self.assertEqual(self.device.freed, 2)

    def test_bad_capture_and_decoder_failure_release_buffer(self):
        self.device.image = None
        camera = self.camera()
        self.assertIsNone(camera.marker())
        self.assertIn("grayscale", camera.last_error)
        self.assertEqual(self.device.freed, 2)
        self.device.image = bytes(320*240)
        def fail(*args):
            raise OSError("decoder failed")
        with self.assertRaises(OSError):
            self.camera(fail).marker()
        self.assertEqual(self.device.freed, 4)

    def test_missing_decoder_fails_before_opening_camera(self):
        with patch.object(config, "QR_DECODER_MODULE", None), patch.object(cam, "open_camera") as opened:
            with self.assertRaisesRegex(RuntimeError, "local MicroPython QR decoder"):
                cam.LocalCamera()
            opened.assert_not_called()

    def test_preflight_requires_three_real_captures(self):
        camera = self.camera()
        marker = camera.wait_for_marker()
        self.assertEqual(marker.frame_id, 3)
        self.assertEqual(self.device.captures, 6)

    def test_driver_receives_s3_pins_not_its_default_board(self):
        from unittest.mock import Mock
        driver = Mock(return_value=SimpleNamespace(deinit=lambda: None))
        module = SimpleNamespace(Camera=driver, FrameSize=SimpleNamespace(QVGA=1),
                                 GrabMode=SimpleNamespace(WHEN_EMPTY=0),
                                 PixelFormat=SimpleNamespace(JPEG=2, GRAYSCALE=3))
        with patch.object(config, "CAMERA_CAPTURE_MODE", "jpeg"), patch.dict("sys.modules", {"camera": module}):
            cam.open_camera()
        self.assertEqual(driver.call_args.kwargs["data_pins"], [11, 9, 8, 10, 12, 18, 17, 16])
        self.assertEqual(driver.call_args.kwargs["sda_pin"], 4)
        self.assertEqual(driver.call_args.kwargs["scl_pin"], 5)


class BoardTests(unittest.TestCase):
    def test_uart_does_not_overlap_camera_memory_usb_or_console(self):
        config.validate_board()
        for pin in list(config.CAMERA_DATA_PINS) + [19, 20, 32, 33, 35, 36, 37, 43, 44, 48]:
            with patch.object(config, "UART_TX_PIN", pin):
                with self.assertRaises(ValueError):
                    config.validate_board()

    def test_wroom_runtime_is_rejected(self):
        with patch("os.uname", create=True, return_value=SimpleNamespace(machine="ESP32 module with ESP32")):
            with self.assertRaisesRegex(RuntimeError, "ESP32-S3"):
                config.validate_runtime()
        with patch("os.uname", create=True, return_value=SimpleNamespace(machine="Generic ESP32S3 module with ESP32S3")):
            config.validate_runtime()


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


class EncodedCameraTests(unittest.TestCase):
    def test_quality_change_releases_old_encoder_and_keeps_camera_open(self):
        from unittest.mock import Mock
        driver = SimpleNamespace(deinit=Mock())
        first = SimpleNamespace(__del__=Mock())
        second = SimpleNamespace(__del__=Mock())
        factory = Mock(side_effect=[first, second])
        with patch.dict('sys.modules', {'jpeg': SimpleNamespace(Encoder=factory)}):
            camera = cam.EncodedCamera(driver)
            camera.set_quality(90)
        self.assertEqual(camera.quality, 90)
        self.assertEqual(factory.call_args.kwargs['quality'], 90)
        first.__del__.assert_called_once()
        driver.deinit.assert_not_called()
        camera.deinit()
        second.__del__.assert_called_once()

    def test_failed_quality_change_preserves_working_encoder(self):
        from unittest.mock import Mock
        encoder = SimpleNamespace(encode=Mock(return_value=b'jpeg'), __del__=Mock())
        factory = Mock(side_effect=[encoder, MemoryError('codec memory')])
        driver = SimpleNamespace(capture=lambda: bytes(320*240*2), free_buffer=Mock())
        with patch.dict('sys.modules', {'jpeg': SimpleNamespace(Encoder=factory)}):
            camera = cam.EncodedCamera(driver)
            with self.assertRaises(MemoryError):
                camera.set_quality(90)
        self.assertEqual(camera.quality, config.CAMERA_JPEG_QUALITY)
        self.assertEqual(camera.capture(), b'jpeg')
        encoder.__del__.assert_not_called()
        for value in [True, 0, 100, 75.5, '75']:
            with self.assertRaises(ValueError):
                camera.set_quality(value)

    def test_color_frames_are_encoded_and_native_buffers_released_once(self):
        from unittest.mock import Mock
        raw=bytes(320*240*2)
        driver=SimpleNamespace(capture=Mock(return_value=raw),free_buffer=Mock(),deinit=Mock())
        encoder=SimpleNamespace(encode=Mock(), __del__=Mock())
        encoder.encode.return_value=b'\xff\xd8jpeg\xff\xd9'
        with patch.dict('sys.modules',{'jpeg':SimpleNamespace(Encoder=Mock(return_value=encoder))}):
            camera=cam.EncodedCamera(driver)
        self.assertEqual(camera.capture(),encoder.encode.return_value)
        encoder.encode.assert_called_once_with(raw)
        camera.free_buffer()
        driver.free_buffer.assert_called_once()
        camera.deinit()
        driver.deinit.assert_called_once()


class CooperativeCaptureTests(unittest.IsolatedAsyncioTestCase):
    async def test_waiting_for_sensor_yields_and_releases_capture_buffer(self):
        import asyncio
        from unittest.mock import Mock
        freed, services = [], []
        available = iter([False, False, True])
        driver = SimpleNamespace(
            frame_available=lambda: next(available),
            capture=lambda: bytes(320*240*2), free_buffer=lambda: freed.append(True))
        encoder = SimpleNamespace(encode=Mock(return_value=b'jpeg'))
        with patch.dict('sys.modules', {'jpeg': SimpleNamespace(Encoder=lambda **kw: encoder)}):
            camera = cam.EncodedCamera(driver)
        async def service():
            await asyncio.sleep(0)
            services.append(True)
        await asyncio.gather(camera.capture_async(), service())
        self.assertEqual(services, [True])
        self.assertEqual(freed, [True])

    async def test_stalled_sensor_times_out_without_blocking_native_capture(self):
        from unittest.mock import Mock
        driver = SimpleNamespace(frame_available=lambda: False, capture=Mock(), free_buffer=Mock())
        with patch.dict('sys.modules', {'jpeg': SimpleNamespace(Encoder=lambda **kw: None)}):
            camera = cam.EncodedCamera(driver)
        with self.assertRaisesRegex(RuntimeError, 'timed out'):
            await camera.capture_async(timeout_ms=0)
        driver.capture.assert_not_called()

    def test_encoder_failure_releases_frame_and_reaches_caller(self):
        from unittest.mock import Mock
        driver=SimpleNamespace(capture=Mock(return_value=bytes(320*240*2)),free_buffer=Mock(),deinit=Mock())
        encoder=SimpleNamespace(encode=Mock(), __del__=Mock())
        encoder.encode.side_effect=RuntimeError('codec failed')
        with patch.dict('sys.modules',{'jpeg':SimpleNamespace(Encoder=Mock(return_value=encoder))}):
            camera=cam.EncodedCamera(driver)
        with self.assertRaisesRegex(RuntimeError,'codec failed'):
            camera.capture()
        driver.free_buffer.assert_called_once()
