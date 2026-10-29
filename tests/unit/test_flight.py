import unittest
from unittest.mock import patch

from missions import aruco_landing
import config
from missions import hover
from banshee import flight as mission
from missions import move_gps
from banshee import vision
from banshee.mavlink.vehicle import Location


class FakeVehicle:
    def __init__(self):
        self.now = 0
        self.current_mode = "GUIDED"
        self.is_armed = False
        self.location = Location(47.5, -122, 0)
        self.calls = []
        self.closed = False

    def mode(self):
        return self.current_mode

    def armed(self):
        return self.is_armed

    def is_armable(self):
        return True

    def gps_ready(self):
        return True

    def set_mode(self, name):
        self.calls.append(("mode", name))
        self.current_mode = name
        if name == "LAND":
            self.is_armed = False

    def arm(self):
        self.calls.append(("arm",))
        self.is_armed = True

    def takeoff(self, altitude):
        self.calls.append(("takeoff", altitude))
        self.location.alt = altitude

    def altitude(self):
        return self.location.alt

    def global_location(self):
        return Location(self.location.lat, self.location.lon, self.location.alt)

    def goto(self, target):
        self.calls.append(("goto", target))
        self.location = target

    def sleep(self, seconds):
        self.now += int(seconds * 1000)

    def send_body_velocity(self, forward, right, down, duration):
        self.calls.append(("velocity", forward, right, down))
        self.location.alt -= down * duration
        self.sleep(duration)

    def close(self):
        self.closed = True


class MissionTests(unittest.TestCase):
    def setUp(self):
        self.vehicle = FakeVehicle()
        for module in (mission, aruco_landing):
            item = patch.object(module, "ticks_ms", lambda: self.vehicle.now)
            item.start()
            self.addCleanup(item.stop)
        marker_patch = patch.object(vision, "_marker_provider", None)
        marker_patch.start()
        self.addCleanup(marker_patch.stop)

    def run_mission(self, callback):
        with patch.object(mission, "connect_to_pixhawk", return_value=self.vehicle):
            mission.run_mission(callback)

    def test_hover_takes_off_holds_lands_and_closes(self):
        self.run_mission(hover.mission)
        self.assertEqual(self.vehicle.calls, [("mode", "GUIDED"), ("arm",),
                                             ("takeoff", 2), ("mode", "LAND")])
        self.assertEqual(self.vehicle.now, 5000)
        self.assertTrue(self.vehicle.closed)

    def test_move_flies_north_and_returns(self):
        self.run_mission(move_gps.mission)
        targets = [call[1] for call in self.vehicle.calls if call[0] == "goto"]
        self.assertEqual(len(targets), 2)
        self.assertAlmostEqual(mission.distance_metres(targets[0], targets[1]), 3, places=5)
        self.assertGreater(targets[0].lat, targets[1].lat)
        self.assertEqual(self.vehicle.mode(), "LAND")

    def test_waypoint_waits_for_arrival(self):
        self.vehicle.is_armed = True
        target = mission.get_location_metres(self.vehicle.location, 3, 0, 0)
        original_goto = self.vehicle.goto
        self.vehicle.goto = lambda point: None
        original_sleep = self.vehicle.sleep
        def arrive(seconds):
            original_sleep(seconds)
            if self.vehicle.now >= 1500:
                original_goto(target)
        self.vehicle.sleep = arrive
        mission.goto_and_wait(self.vehicle, target)
        self.assertGreaterEqual(self.vehicle.now, 1500)

    def test_error_during_guided_flight_requests_land(self):
        def fail(vehicle):
            vehicle.is_armed = True
            raise RuntimeError("camera failed")
        with self.assertRaisesRegex(RuntimeError, "camera failed"):
            self.run_mission(fail)
        self.assertEqual(self.vehicle.mode(), "LAND")
        self.assertTrue(self.vehicle.closed)

    def test_pilot_override_is_respected(self):
        def override(vehicle):
            vehicle.is_armed = True
            vehicle.current_mode = "LOITER"
            mission.hold(vehicle, 1)
        with self.assertRaises(mission.MissionInterrupted):
            self.run_mission(override)
        self.assertEqual(self.vehicle.mode(), "LOITER")
        self.assertTrue(self.vehicle.closed)

    def test_starting_armed_is_refused(self):
        self.vehicle.is_armed = True
        with self.assertRaisesRegex(RuntimeError, "armed vehicle"):
            self.run_mission(lambda vehicle: self.fail("mission started"))
        self.assertEqual(self.vehicle.calls, [])
        self.assertTrue(self.vehicle.closed)

    def test_readiness_timeout(self):
        self.vehicle.is_armable = lambda: False
        with patch.object(config, "READY_TIMEOUT", 0.2):
            with self.assertRaisesRegex(RuntimeError, "prearm"):
                self.run_mission(lambda vehicle: mission.arm_and_takeoff(vehicle, 1.5))
        self.assertNotIn(("arm",), self.vehicle.calls)

    def test_missing_vision_fails_before_connect(self):
        with patch.object(mission, "connect_to_pixhawk") as connect:
            with self.assertRaisesRegex(RuntimeError, "camera provider"):
                aruco_landing.main()
            connect.assert_not_called()

    def test_marker_validation(self):
        for marker in ((0, 0, 0, 480), (999, 1, 640, 480), (1, float("nan"), 640, 480)):
            vision.set_marker_provider(lambda: marker)
            with self.assertRaises(ValueError):
                vision.marker_provider()

    def test_centered_marker_descends_in_positive_down_direction(self):
        self.vehicle.is_armed = True
        self.vehicle.location.alt = 0.205
        vision.set_marker_provider(lambda: (320, 240, 640, 480))
        aruco_landing.land_on_aruco(self.vehicle)
        velocities = [call for call in self.vehicle.calls if call[0] == "velocity"]
        self.assertTrue(velocities)
        self.assertTrue(all(call[3] > 0 for call in velocities))
        self.assertEqual(self.vehicle.mode(), "LAND")

    def test_off_center_marker_does_not_descend(self):
        self.vehicle.is_armed = True
        self.vehicle.location.alt = 1.5
        vision.set_marker_provider(lambda: (600, 400, 640, 480))
        with patch.object(config, "MARKER_LANDING_TIMEOUT", 0.2):
            with self.assertRaisesRegex(RuntimeError, "timed out"):
                aruco_landing.land_on_aruco(self.vehicle)
        calls = [call for call in self.vehicle.calls if call[0] == "velocity"]
        self.assertTrue(all(call[1] < 0 and call[2] > 0 and call[3] == 0 for call in calls))
        self.assertTrue(all(abs(call[2]) <= config.MARKER_MAX_SPEED for call in calls))

    def test_marker_loss_cancels_velocity_and_times_out(self):
        self.vehicle.is_armed = True
        vision.set_marker_provider(lambda: None)
        with patch.object(config, "MARKER_TIMEOUT", 0.2):
            with self.assertRaisesRegex(RuntimeError, "marker lost"):
                aruco_landing.land_on_aruco(self.vehicle)
        calls = [call for call in self.vehicle.calls if call[0] == "velocity"]
        self.assertTrue(calls)
        self.assertTrue(all(call[1:] == (0, 0, 0) for call in calls))

    def test_gps_offsets_and_dateline(self):
        origin = Location(0, 179.99999, 0)
        target = mission.get_location_metres(origin, 0, 3, 1.5)
        self.assertLess(target.lon, 0)
        self.assertAlmostEqual(mission.distance_metres(origin, target), 3, places=5)
        with self.assertRaises(ValueError):
            mission.get_location_metres(Location(90, 0, 0), 0, 3, 1)


if __name__ == "__main__":
    unittest.main()
