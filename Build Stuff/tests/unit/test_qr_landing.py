import importlib
import math
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import config
from banshee import flight
from missions import qr_landing as qr
from tests.unit.test_flight import FakeVehicle


class QRVehicle(FakeVehicle):
    def poll(self):
        pass

    def send_body_velocity(self, forward, right, down, duration, yaw_rate=None):
        self.calls.append(("velocity", forward, right, down, yaw_rate))
        self.location.alt -= down * duration
        self.sleep(duration)


class QRLandingTests(unittest.TestCase):
    def setUp(self):
        self.vehicle = QRVehicle()
        self.vehicle.is_armed = True
        self.vehicle.location.alt = 0.205
        self.frame = 0
        for module in (qr, flight):
            item = patch.object(module, "ticks_ms", lambda: self.vehicle.now)
            item.start()
            self.addCleanup(item.stop)

    def marker(self, x=160, y=120, yaw=0):
        self.frame += 1
        return SimpleNamespace(cx=x, cy=y, width=320, height=240, yaw=yaw, frame_id=self.frame)

    def run_camera(self, getter):
        qr.land_on_qr(self.vehicle, SimpleNamespace(marker=lambda service=None: getter()))

    def velocities(self):
        return [call for call in self.vehicle.calls if call[0] == "velocity"]

    def test_center_and_yaw_must_settle_before_descent(self):
        self.run_camera(lambda: self.marker())
        self.assertTrue(all(v[3] == 0 for v in self.velocities()[:5]))
        self.assertTrue(any(v[3] > 0 for v in self.velocities()))
        self.assertEqual(self.vehicle.current_mode, "LAND")
        self.assertEqual(self.velocities()[-1], ("velocity", 0, 0, 0, 0))

    def test_centered_but_rotated_turns_without_descent_or_land(self):
        with patch.object(config, "MARKER_LANDING_TIMEOUT", 0.3):
            with self.assertRaisesRegex(RuntimeError, "timed out"):
                self.run_camera(lambda: self.marker(yaw=math.pi / 2))
        self.assertTrue(all(v[3] == 0 and v[4] == config.QR_MAX_YAW_RATE for v in self.velocities()))
        self.assertEqual(self.vehicle.current_mode, "GUIDED")

    def test_translation_axes_and_speed_limits(self):
        with patch.object(config, "MARKER_LANDING_TIMEOUT", 0.2):
            with self.assertRaises(RuntimeError):
                self.run_camera(lambda: self.marker(x=300, y=220, yaw=-0.5))
        self.assertTrue(all(v[1] < 0 and v[2] > 0 and v[3] == 0 and v[4] < 0
                            for v in self.velocities()))
        self.assertTrue(all(abs(v[1]) <= config.QR_MAX_SPEED and abs(v[2]) <= config.QR_MAX_SPEED
                            for v in self.velocities()))

    def test_cached_single_frame_cannot_establish_alignment(self):
        marker = self.marker()
        with patch.object(config, "MARKER_LANDING_TIMEOUT", 0.8):
            with self.assertRaises(RuntimeError):
                self.run_camera(lambda: marker)
        self.assertTrue(all(v[3] == 0 for v in self.velocities()))

    def test_loss_cancels_yaw_and_descent_and_resets_settling(self):
        self.vehicle.location.alt = 0.3
        def get():
            if 600 <= self.vehicle.now < 800:
                return None
            return self.marker()
        with patch.object(config, "MARKER_LANDING_TIMEOUT", 1.1):
            with self.assertRaises(RuntimeError):
                self.run_camera(get)
        calls = self.velocities()
        self.assertGreater(calls[5][3], 0)
        self.assertTrue(all(v == ("velocity", 0, 0, 0, 0) for v in calls[6:8]))
        self.assertTrue(all(v[3] == 0 for v in calls[8:]))

    def test_no_marker_times_out_without_moving(self):
        with patch.object(config, "MARKER_TIMEOUT", 0.2):
            with self.assertRaisesRegex(RuntimeError, "lost or stale"):
                self.run_camera(lambda: None)
        self.assertTrue(all(v == ("velocity", 0, 0, 0, 0) for v in self.velocities()))

    def test_pilot_override_stops_commands(self):
        self.vehicle.current_mode = "LOITER"
        with self.assertRaises(flight.MissionInterrupted):
            self.run_camera(lambda: self.marker())
        self.assertFalse(self.vehicle.calls)

    def test_pilot_override_during_capture_stops_all_motion(self):
        def capture(service=None):
            self.vehicle.current_mode = "LOITER"
            return self.marker()
        with self.assertRaises(flight.MissionInterrupted):
            qr.land_on_qr(self.vehicle, SimpleNamespace(marker=capture))
        self.assertFalse(self.vehicle.calls)

    def test_yaw_wrap_and_desired_heading(self):
        with patch.object(config, "QR_DESIRED_ANGLE_DEG", 170):
            self.assertAlmostEqual(qr.yaw_error(self.marker(yaw=math.radians(-170))), math.radians(20))

    def test_camera_preflight_failure_never_connects_or_arms(self):
        with patch.object(qr, "LocalCamera") as camera_type, patch.object(qr, "run_mission") as run:
            camera_type.return_value.wait_for_marker.side_effect = RuntimeError("no QR")
            with self.assertRaisesRegex(RuntimeError, "no QR"):
                qr.main()
            run.assert_not_called()
            camera_type.return_value.close.assert_called_once()

    def test_imports_have_no_camera_or_flight_side_effects(self):
        with patch("banshee.camera.open_camera", side_effect=AssertionError("Camera opened")):
            importlib.reload(qr)
            importlib.reload(importlib.import_module("diagnostics.qr_camera"))


if __name__ == "__main__":
    unittest.main()
