import importlib
import struct
import unittest
from unittest.mock import patch

import config
from banshee.mavlink import vehicle as mav


from tests.support.mavlink import Clock, UART, heartbeat, position, wire_frame


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.patches = [patch.object(mav, "ticks_ms", self.clock.ticks),
                        patch.object(mav, "sleep_ms", self.clock.sleep)]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    def connect(self, extra=b"", uart=None):
        uart = uart or UART(heartbeat() + extra)
        return mav.MAVLinkVehicle(uart, connect_timeout=0.2)

    def test_connect_sends_heartbeat_and_stream_request(self):
        vehicle = self.connect()
        self.assertEqual([p[5] for p in vehicle.uart.writes], [0, 66])
        self.assertEqual(vehicle.mode(), "GUIDED")
        self.assertFalse(vehicle.armed())

    def test_fragmented_frames_and_noise(self):
        uart = UART(b"noise" + heartbeat())
        uart.read_size = 2
        vehicle = self.connect(uart=uart)
        self.assertEqual(vehicle.mode(), "GUIDED")

    def test_checksum_corruption_is_ignored(self):
        corrupt = bytearray(heartbeat(mode=9))
        corrupt[-1] ^= 1
        vehicle = self.connect(uart=UART(bytes(corrupt) + heartbeat()))
        self.assertEqual(vehicle.mode(), "GUIDED")

    def test_v2_heartbeat(self):
        payload = struct.pack("<IBBBBB", 9, 2, 3, 128, 4, 3)
        vehicle = self.connect(uart=UART(wire_frame(0, payload, version=2)))
        self.assertEqual(vehicle.mode(), "LAND")
        self.assertTrue(vehicle.armed())

    def test_v2_trailing_zero_payload_is_restored(self):
        vehicle = self.connect()
        vehicle.uart.rx.extend(wire_frame(33, struct.pack("<Iii", 100, 475000000, -1220000000), version=2))
        self.assertEqual(vehicle.altitude(), 0)

    def test_v2_extended_sys_status(self):
        bit = 1 << 28
        payload = struct.pack("<III", bit, bit, bit) + b"\x00" * 31
        vehicle = self.connect(wire_frame(1, payload, version=2))
        self.assertTrue(vehicle.is_armable())

    def test_short_v1_payload_is_ignored(self):
        vehicle = self.connect(wire_frame(33, b"\x00"))
        with self.assertRaisesRegex(RuntimeError, "altitude"):
            vehicle.altitude()

    def test_other_system_and_component_do_not_replace_target(self):
        vehicle = self.connect()
        payload = struct.pack("<IBBBBB", 9, 2, 3, 128, 4, 3)
        vehicle.uart.rx.extend(wire_frame(0, payload, system=2) + wire_frame(0, payload, component=42))
        self.assertEqual(vehicle.mode(), "GUIDED")
        self.assertFalse(vehicle.armed())

    def test_px4_is_rejected_and_uart_closed(self):
        uart = UART(heartbeat(autopilot=12))
        with self.assertRaisesRegex(RuntimeError, "ArduCopter"):
            self.connect(uart=uart)
        self.assertTrue(uart.closed)

    def test_signed_frames_are_rejected(self):
        payload = struct.pack("<IBBBBB", 4, 2, 3, 0, 3, 3)
        with self.assertRaisesRegex(RuntimeError, "Signed"):
            self.connect(uart=UART(wire_frame(0, payload, version=2, flags=1)))

    def test_missing_heartbeat_times_out_and_closes(self):
        uart = UART()
        with self.assertRaisesRegex(RuntimeError, "heartbeat"):
            self.connect(uart=uart)
        self.assertTrue(uart.closed)

    def test_heartbeat_loss(self):
        vehicle = self.connect()
        self.clock.now = config.HEARTBEAT_TIMEOUT * 1000 + 1
        with self.assertRaisesRegex(RuntimeError, "heartbeat lost"):
            vehicle.poll()

    def test_altitude_units_and_staleness(self):
        vehicle = self.connect(position(1234))
        self.assertEqual(vehicle.altitude(), 1.234)
        self.clock.now = config.TELEMETRY_TIMEOUT * 1000 + 1
        with self.assertRaisesRegex(RuntimeError, "stale"):
            vehicle.altitude()

    def test_gps_fix_and_coordinates(self):
        gps = b"\x00" * 28 + bytes((3, 12))
        vehicle = self.connect(position() + wire_frame(24, gps))
        location = vehicle.global_location()
        self.assertEqual((location.lat, location.lon, location.alt), (47.5, -122, 1.5))
        vehicle.uart.rx.extend(wire_frame(24, b"\x00" * 28 + bytes((2, 12))))
        with self.assertRaisesRegex(RuntimeError, "3D GPS"):
            vehicle.global_location()

    def test_armability_requires_prearm_health(self):
        bit = 1 << 28
        healthy = struct.pack("<III", bit, bit, bit) + b"\x00" * 19
        vehicle = self.connect(wire_frame(1, healthy))
        self.assertTrue(vehicle.is_armable())
        unhealthy = struct.pack("<III", bit, bit, 0) + b"\x00" * 19
        vehicle.uart.rx.extend(wire_frame(1, unhealthy))
        self.assertFalse(vehicle.is_armable())

    def test_command_acceptance_and_mode_confirmation(self):
        def respond(uart, packet):
            if packet[5] == 76:
                command = struct.unpack("<H", packet[34:36])[0]
                uart.rx.extend(wire_frame(77, struct.pack("<HB", command, 0)))
                uart.rx.extend(heartbeat(mode=9))
        vehicle = self.connect(uart=UART(heartbeat(), respond))
        vehicle.set_mode("LAND")
        self.assertEqual(vehicle.mode(), "LAND")

    def test_rejected_command_raises(self):
        def reject(uart, packet):
            if packet[5] == 76:
                uart.rx.extend(wire_frame(77, struct.pack("<HB", 400, 2)))
        vehicle = self.connect(uart=UART(heartbeat(), reject))
        with self.assertRaisesRegex(RuntimeError, "rejected"):
            vehicle.arm()

    def test_ack_addressed_to_another_sender_is_ignored(self):
        def respond(uart, packet):
            if packet[5] == 76:
                ack = struct.pack("<HBBiBB", 400, 0, 0, 0, 99, 191)
                uart.rx.extend(wire_frame(77, ack, version=2))
        vehicle = self.connect(uart=UART(heartbeat(), respond))
        with self.assertRaisesRegex(RuntimeError, "command ACK"):
            vehicle.arm()

    def test_ack_does_not_substitute_for_armed_heartbeat(self):
        def respond(uart, packet):
            if packet[5] == 76:
                uart.rx.extend(wire_frame(77, struct.pack("<HB", 400, 0)))
        vehicle = self.connect(uart=UART(heartbeat(), respond))
        with self.assertRaisesRegex(RuntimeError, "armed heartbeat"):
            vehicle.arm()

    def test_velocity_body_frame_and_positive_down(self):
        vehicle = self.connect()
        vehicle.send_body_velocity(0.1, 0.2, 0.05, 0)
        packet = vehicle.uart.writes[-1]
        self.assertEqual((packet[5], len(packet[6:-2])), (84, 53))
        forward, right, down = struct.unpack("<fff", packet[22:34])
        self.assertAlmostEqual(forward, 0.1)
        self.assertAlmostEqual(right, 0.2)
        self.assertAlmostEqual(down, 0.05)
        self.assertEqual(packet[-3], 8)

    def test_global_target_relative_altitude_frame(self):
        vehicle = self.connect()
        vehicle.goto(mav.Location(47.5, -122, 1.5))
        packet = vehicle.uart.writes[-1]
        self.assertEqual((packet[5], len(packet[6:-2])), (86, 53))
        self.assertEqual(struct.unpack("<ii", packet[10:18]), (475000000, -1220000000))
        self.assertEqual(packet[-3], 3)

    def test_body_velocity_preserves_autopilot_yaw_by_default(self):
        vehicle = self.connect()
        for kwargs in ({}, {"yaw_rate": None}):
            with self.subTest(kwargs=kwargs):
                vehicle.send_body_velocity(0, 0, 0, 0, **kwargs)
                payload = vehicle.uart.writes[-1][6:-2]
                self.assertEqual(struct.unpack("<H", payload[48:50])[0], 0x0DC7)
                self.assertEqual(struct.unpack("<f", payload[44:48])[0], 0)

    def test_body_velocity_enables_signed_yaw_rate_and_explicit_zero(self):
        vehicle = self.connect()
        for rate in (0.25, -0.25, 0):
            with self.subTest(rate=rate):
                vehicle.send_body_velocity(0.1, -0.2, 0.05, 0, yaw_rate=rate)
                payload = vehicle.uart.writes[-1][6:-2]
                self.assertEqual(struct.unpack("<H", payload[48:50])[0], 0x05C7)
                self.assertEqual(payload[52], 8)  # MAV_FRAME_BODY_NED
                self.assertAlmostEqual(struct.unpack("<f", payload[44:48])[0], rate)
                self.assertEqual(struct.unpack("<f", payload[40:44])[0], 0)  # ignored yaw
                for actual, expected in zip(struct.unpack("<fff", payload[16:28]),
                                            (0.1, -0.2, 0.05)):
                    self.assertAlmostEqual(actual, expected)

    def test_invalid_yaw_rate_is_rejected_before_transmission(self):
        vehicle = self.connect()
        before = len(vehicle.uart.writes)
        for rate in (float("nan"), float("inf"), -float("inf")):
            with self.subTest(rate=rate):
                with self.assertRaisesRegex(ValueError, "Yaw rate"):
                    vehicle.send_body_velocity(0, 0, 0, 0, yaw_rate=rate)
        self.assertEqual(len(vehicle.uart.writes), before)

    def test_yaw_velocity_repeats_while_polling_telemetry(self):
        vehicle = self.connect()
        vehicle.send_body_velocity(0, 0, 0, 0.3, yaw_rate=0.25)
        packets = [packet for packet in vehicle.uart.writes if packet[5] == 84]
        self.assertGreaterEqual(len(packets), 4)
        for packet in packets:
            self.assertAlmostEqual(struct.unpack("<f", packet[50:54])[0], 0.25)

    def test_yaw_velocity_still_rejects_invalid_velocity_and_duration(self):
        vehicle = self.connect()
        before = len(vehicle.uart.writes)
        for values in ((float("nan"), 0, 0, 0), (0, float("inf"), 0, 0),
                       (0, 0, -float("inf"), 0), (0, 0, 0, -0.1),
                       (0, 0, 0, float("inf")), (0, 0, 0, float("nan"))):
            with self.subTest(values=values):
                with self.assertRaises(ValueError):
                    vehicle.send_body_velocity(*values, yaw_rate=0)
        self.assertEqual(len(vehicle.uart.writes), before)


    def test_long_sleep_keeps_sending_heartbeats(self):
        vehicle = self.connect()
        vehicle.sleep(2.1)
        self.assertEqual(sum(p[5] == 0 for p in vehicle.uart.writes), 3)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            mav.MAVLinkVehicle("UART1")
        for coordinates in ((91, 0, 1), (0, 181, 1), (0, 0, float("nan"))):
            with self.assertRaises(ValueError):
                mav.Location(*coordinates)
        vehicle = self.connect()
        for altitude in (0, -1, float("nan")):
            with self.assertRaises(ValueError):
                vehicle.takeoff(altitude)

    def test_short_write_raises_and_closes(self):
        uart = UART(heartbeat())
        uart.write = lambda data: 1
        with self.assertRaises(OSError):
            self.connect(uart=uart)
        self.assertTrue(uart.closed)

    def test_importing_missions_never_opens_uart(self):
        with patch.object(mav, "detect_pixhawk_uart", side_effect=AssertionError("UART opened")):
            for module in ("missions.hover", "missions.hover_gps", "missions.move_gps",
                           "missions.circle", "missions.aruco_landing",
                           "missions.aruco_move_gps", "diagnostics.marker_tracker"):
                importlib.reload(importlib.import_module(module))


if __name__ == "__main__":
    unittest.main()
