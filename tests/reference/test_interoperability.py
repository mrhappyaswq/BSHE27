"""Optional interoperability tests against generated pymavlink common dialects."""

import struct
import unittest
from unittest.mock import patch

import config
from banshee.mavlink import vehicle as mav
from tests.support.mavlink import Clock, UART, heartbeat

try:
    from pymavlink.dialects.v10 import common as v10
    from pymavlink.dialects.v20 import common as v20
except ImportError:
    v10 = v20 = None


@unittest.skipIf(v20 is None, "Optional: install requirements-dev.txt for pymavlink interoperability checks")
class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        for item in (patch.object(mav, "ticks_ms", self.clock.ticks),
                     patch.object(mav, "sleep_ms", self.clock.sleep)):
            item.start()
            self.addCleanup(item.stop)

    def decode(self, packet):
        return v20.MAVLink(None).parse_char(packet)

    def connect(self):
        return mav.MAVLinkVehicle(UART(heartbeat()), connect_timeout=0.2)

    def test_reference_decodes_heartbeat_and_stream_request(self):
        vehicle = self.connect()
        pulse, request = [self.decode(packet) for packet in vehicle.uart.writes]
        self.assertEqual(pulse.get_type(), "HEARTBEAT")
        self.assertEqual(pulse.type, v20.MAV_TYPE_ONBOARD_CONTROLLER)
        self.assertEqual(request.get_type(), "REQUEST_DATA_STREAM")
        self.assertEqual((request.req_message_rate, request.start_stop), (4, 1))

    def test_reference_decodes_global_position_target(self):
        vehicle = self.connect()
        vehicle.goto(mav.Location(47.5, -122, 1.5))
        message = self.decode(vehicle.uart.writes[-1])
        self.assertEqual(message.get_type(), "SET_POSITION_TARGET_GLOBAL_INT")
        self.assertEqual(message.coordinate_frame, v20.MAV_FRAME_GLOBAL_RELATIVE_ALT)
        self.assertEqual((message.lat_int, message.lon_int, message.alt), (475000000, -1220000000, 1.5))
        self.assertEqual(message.type_mask, 3576)

    def test_reference_decodes_body_velocity(self):
        vehicle = self.connect()
        vehicle.send_body_velocity(0.2, -0.3, 0.05, 0)
        message = self.decode(vehicle.uart.writes[-1])
        self.assertEqual(message.get_type(), "SET_POSITION_TARGET_LOCAL_NED")
        self.assertEqual(message.coordinate_frame, v20.MAV_FRAME_BODY_NED)
        self.assertEqual(message.type_mask, 3527)
        for actual, expected in zip((message.vx, message.vy, message.vz), (0.2, -0.3, 0.05)):
            self.assertAlmostEqual(actual, expected)

    def test_reference_decodes_takeoff_command(self):
        vehicle = self.connect()
        sender = v20.MAVLink(None, srcSystem=1, srcComponent=1)
        def respond(uart, packet):
            message = self.decode(packet)
            if message.get_type() == "COMMAND_LONG":
                uart.rx.extend(v20.MAVLink_command_ack_message(
                    message.command, v20.MAV_RESULT_ACCEPTED,
                ).pack(sender))
        vehicle.uart.on_write = respond
        vehicle.takeoff(1.5)
        message = self.decode(vehicle.uart.writes[-1])
        self.assertEqual(message.command, v20.MAV_CMD_NAV_TAKEOFF)
        self.assertEqual(message.param7, 1.5)

    def test_reference_heartbeat_and_telemetry_both_versions(self):
        for dialect in (v10, v20):
            with self.subTest(version=dialect.WIRE_PROTOCOL_VERSION):
                sender = dialect.MAVLink(None, srcSystem=1, srcComponent=1)
                prearm = 1 << 28
                messages = [
                    dialect.MAVLink_heartbeat_message(2, 3, 0, 4, 3, 3),
                    dialect.MAVLink_sys_status_message(prearm, prearm, prearm,
                                                      0, 12000, 0, 100, 0, 0, 0, 0, 0, 0),
                    dialect.MAVLink_gps_raw_int_message(100, 3, 475000000, -1220000000,
                                                       10000, 100, 100, 0, 0, 12),
                    dialect.MAVLink_global_position_int_message(100, 475000000, -1220000000,
                                                               10000, 1234, 0, 0, 0, 0),
                ]
                uart = UART(b"".join(message.pack(sender) for message in messages))
                vehicle = mav.MAVLinkVehicle(uart, connect_timeout=0.2)
                self.assertTrue(vehicle.is_armable())
                self.assertTrue(vehicle.gps_ready())
                self.assertEqual(vehicle.altitude(), 1.234)
                self.assertEqual(vehicle.global_location().lon, -122)

    def test_reference_truncated_zero_altitude_is_decoded(self):
        vehicle = self.connect()
        sender = v20.MAVLink(None, srcSystem=1, srcComponent=1)
        message = v20.MAVLink_global_position_int_message(0, 0, 0, 0, 0, 0, 0, 0, 0)
        packet = message.pack(sender)
        self.assertEqual(packet[1], 1)  # Generated library strips trailing zeros.
        vehicle.uart.rx.extend(packet)
        self.assertEqual(vehicle.altitude(), 0)


if __name__ == "__main__":
    unittest.main()
