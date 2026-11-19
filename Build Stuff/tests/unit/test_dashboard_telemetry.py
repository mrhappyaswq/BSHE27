import asyncio
import importlib
import json
import struct
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import config
from banshee.telemetry import TelemetryMonitor
from tests.support.mavlink import UART, Clock, heartbeat, wire_frame
from tests.unit.test_camera_web import Reader, Writer


class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.uart = UART()
        self.monitor = TelemetryMonitor(lambda *a, **k: self.uart, self.clock.ticks)

    def test_target_heartbeat_timeout_recovery_and_no_transmission(self):
        self.assertEqual(self.monitor.snapshot()['state'], 'waiting')
        self.uart.rx.extend(heartbeat(mode=4, armed=True))
        self.monitor.poll()
        state = self.monitor.snapshot()
        self.assertEqual(state['state'], 'connected')
        self.assertTrue(state['armed'])
        self.assertEqual(state['custom_mode'], 4)
        self.clock.now = config.HEARTBEAT_TIMEOUT * 1000 + 1
        state = self.monitor.snapshot()
        self.assertEqual(state['state'], 'lost')
        self.assertIsNone(state['armed'])
        self.assertIsNone(state['custom_mode'])
        self.uart.rx.extend(heartbeat(mode=9))
        self.monitor.poll()
        self.assertEqual(self.monitor.snapshot()['state'], 'connected')
        self.assertFalse(self.monitor.snapshot()['armed'])
        self.assertEqual(self.uart.writes, [])
        self.monitor.close()
        self.assertTrue(self.uart.closed)

    def test_other_target_and_bad_crc_do_not_establish_link(self):
        payload = struct.pack('<IBBBBB', 4, 2, 3, 0, 3, 3)
        damaged = bytearray(heartbeat())
        damaged[-1] ^= 1
        self.uart.rx.extend(damaged + wire_frame(0, payload, system=2) +
                            wire_frame(0, payload, component=2) + heartbeat(autopilot=12))
        self.monitor.poll()
        self.assertEqual(self.monitor.snapshot()['state'], 'waiting')

    def test_uart_failure_is_reported_and_disabled_does_not_open_hardware(self):
        def broken(*args, **kwargs):
            raise OSError('UART unavailable')
        monitor = TelemetryMonitor(broken)
        monitor.poll()
        self.assertEqual(monitor.snapshot()['state'], 'error')
        with patch.object(config, 'TELEMETRY_ENABLED', False):
            disabled = TelemetryMonitor(broken)
        self.assertEqual(disabled.snapshot()['state'], 'disabled')
        self.assertIsNone(disabled.error)

    def test_uart_read_work_is_bounded(self):
        self.uart.rx.extend(b'x' * 5000)
        self.monitor.poll()
        self.assertEqual(self.monitor.byte_count, 1024)


class DashboardTests(unittest.IsolatedAsyncioTestCase):
    async def test_telemetry_changes_while_video_continues(self):
        with patch.dict(sys.modules, {'network': SimpleNamespace()}):
            app = importlib.import_module('apps.camera_web')
        clock = Clock()
        uart = UART(heartbeat())
        monitor = TelemetryMonitor(lambda *a, **k: uart, clock.ticks)
        camera = SimpleNamespace(capture=lambda: b'\xff\xd8JPEG\xff\xd9', free_buffer=lambda: None)
        handlers = []
        ready = asyncio.Event()
        async def server(handler, *args, **kwargs):
            handlers.append(handler)
            ready.set()
            return SimpleNamespace(close=lambda: None, wait_closed=lambda: asyncio.sleep(0))
        async def status():
            writer = Writer()
            await handlers[0](Reader(b'/status'), writer)
            return json.loads(bytes(writer.output).split(b'\r\n\r\n', 1)[1])
        with patch.object(app.asyncio, 'start_server', server):
            task = asyncio.create_task(app.serve(camera, telemetry=monitor))
            try:
                await ready.wait()
                await asyncio.sleep(.03)
                self.assertEqual((await status())['pixhawk']['state'], 'connected')
                clock.now = config.HEARTBEAT_TIMEOUT * 1000 + 1
                stale = await status()
                self.assertEqual(stale['pixhawk']['state'], 'lost')
                self.assertTrue(stale['ready'])
                writer = Writer()
                await handlers[0](Reader(b'/stream'), writer)
                self.assertGreaterEqual(writer.output.count(b'Content-Type: image/jpeg'), 2)
                uart.rx.extend(heartbeat(armed=True))
                await asyncio.sleep(.03)
                self.assertTrue((await status())['pixhawk']['armed'])
            finally:
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
                monitor.close()
        self.assertEqual(uart.writes, [])


class IndicatorTests(unittest.TestCase):
    def test_priority_and_streaming_pairs(self):
        with patch.dict(sys.modules, {'network': SimpleNamespace()}):
            app = importlib.import_module('apps.camera_web')
        ap = SimpleNamespace(active=lambda: True, isconnected=lambda: True)
        with patch.object(app.status_led, 'set') as show:
            for link, streaming, error, expected in [
                    ('waiting', True, None, 'streaming'),
                    ('connected', True, None, 'streaming_pixhawk'),
                    ('connected', False, None, 'wifi_connected_pixhawk'),
                    ('lost', True, None, 'link_lost'),
                    ('error', True, None, 'telemetry_error'),
                    ('lost', True, 'capture failed', 'wifi_connected_camera_error')]:
                app.update_wifi_led(ap, error, {'state': link}, streaming)
                show.assert_called_with(expected)
