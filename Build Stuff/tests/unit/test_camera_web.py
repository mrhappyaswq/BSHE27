import asyncio
import importlib
import json
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch


class Reader:
    def __init__(self, path, method=b'GET', body=b'', headers=None):
        headers = [b'Host: camera'] if headers is None else headers
        if body:
            headers = headers + [b'Content-Length: ' + str(len(body)).encode()]
        self.data = method + b' ' + path + b' HTTP/1.1\r\n' + b'\r\n'.join(headers) + b'\r\n\r\n' + body

    async def read(self, size):
        chunk, self.data = self.data[:size], self.data[size:]
        return chunk

    async def readline(self):
        index = self.data.find(b'\n') + 1
        return await self.read(index or len(self.data))


class Writer:
    def __init__(self):
        self.output = bytearray()
        self.closed = False

    def write(self, data):
        self.output.extend(data)

    async def drain(self):
        # Simulate a viewer disconnect after receiving two full stream frames.
        if (b'multipart/x-mixed-replace' in self.output and
                self.output.count(b'Content-Type: image/jpeg') >= 2 and
                self.output.endswith(b'\r\n')):
            raise OSError('viewer disconnected')

    def close(self):
        self.closed = True

    async def wait_closed(self):
        pass


class CameraWebTests(unittest.IsolatedAsyncioTestCase):
    async def request(self, path, image=b'\xff\xd8JPEG\xff\xd9', unavailable=False, method=b'GET', body=b'', camera=None):
        with patch.dict(sys.modules, {'network': SimpleNamespace()}):
            app = importlib.import_module('apps.camera_web')
        freed = []
        camera = camera or SimpleNamespace(capture=lambda: image() if callable(image) else image, free_buffer=lambda: freed.append(True))
        ready = asyncio.Event()
        writer = Writer()
        async def server(handler, *args, **kwargs):
            await handler(Reader(path, method, body), writer)
            ready.set()
            return SimpleNamespace(close=lambda: None, wait_closed=lambda: asyncio.sleep(0))
        with patch.object(app.asyncio, 'start_server', server):
            task = asyncio.create_task(app.serve(None if unavailable else camera, 'Driver missing' if unavailable else None))
            await asyncio.wait_for(ready.wait(), 2)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertTrue(writer.closed)
        return bytes(writer.output), freed

    async def test_snapshot_is_real_jpeg_with_correct_length_and_releases_buffer(self):
        payload = b'\xff\xd8' + b'x'*10000 + b'\xff\xd9'
        response, freed = await self.request(b'/capture?t=123', payload)
        headers, body = response.split(b'\r\n\r\n', 1)
        self.assertIn(b'200 OK', headers)
        self.assertIn(b'Content-Type: image/jpeg', headers)
        self.assertIn(str(len(payload)).encode(), headers)
        self.assertEqual(body, payload)
        self.assertEqual(freed, [True])

    async def test_missing_capture_does_not_report_success(self):
        response, freed = await self.request(b'/capture', None)
        self.assertNotIn(b'200 OK', response)
        self.assertEqual(freed, [True])

    async def test_unknown_path_cannot_read_board_files(self):
        response, freed = await self.request(b'/../../config.py')
        self.assertIn(b'404 Not Found', response)
        self.assertEqual(freed, [])

    async def test_status_is_json_and_does_not_capture(self):
        import json
        response, freed = await self.request(b'/status')
        body = response.split(b'\r\n\r\n', 1)[1]
        self.assertTrue(json.loads(body)['ready'])
        self.assertEqual(freed, [])


    async def test_missing_camera_serves_diagnostics_without_losing_wifi(self):
        import json
        response, freed = await self.request(b'/status', unavailable=True)
        body=json.loads(response.split(b'\r\n\r\n',1)[1])
        self.assertFalse(body['ready'])
        self.assertEqual(body['error'],'Driver missing')
        response, freed = await self.request(b'/capture', unavailable=True)
        self.assertIn(b'503 Service Unavailable',response)
        self.assertIn(b'Driver missing',response)
        self.assertEqual(freed,[])


    async def test_mjpeg_stream_sends_consecutive_real_frames_and_releases_buffers(self):
        payload=b'\xff\xd8live frame\xff\xd9'
        response,freed=await self.request(b'/stream',payload)
        self.assertIn(b'multipart/x-mixed-replace; boundary=bshe27frame',response)
        self.assertGreaterEqual(response.count(payload),2)
        self.assertEqual(len(freed),response.count(payload))

    async def test_mjpeg_unavailable_has_useful_json_error(self):
        response,freed=await self.request(b'/stream',unavailable=True)
        self.assertIn(b'503 Service Unavailable',response)
        self.assertIn(b'Driver missing',response)
        self.assertEqual(freed,[])

    async def test_transient_capture_failure_recovers_in_same_stream(self):
        frames = iter([None, b'\xff\xd8recovered\xff\xd9', b'\xff\xd8recovered\xff\xd9'])
        response, freed = await self.request(b'/stream', lambda: next(frames))
        self.assertEqual(response.count(b'recovered'), 2)
        self.assertEqual(len(freed), 3)

    async def test_persistent_capture_failure_releases_stream_after_three_attempts(self):
        response, freed = await self.request(b'/stream', None)
        self.assertEqual(len(freed), 3)
        self.assertIn(b'multipart/x-mixed-replace', response)

    async def test_transport_timeout_is_not_a_camera_fault_and_allows_new_viewer(self):
        import json
        with patch.dict(sys.modules, {'network': SimpleNamespace()}):
            app = importlib.import_module('apps.camera_web')
        handlers = []
        ready = asyncio.Event()
        async def server(handler, *args, **kwargs):
            handlers.append(handler)
            ready.set()
            return SimpleNamespace(close=lambda: None, wait_closed=lambda: asyncio.sleep(0))
        class SlowViewer(Writer):
            async def drain(self):
                raise asyncio.TimeoutError('slow viewer')
        camera = SimpleNamespace(capture=lambda: b'\xff\xd8JPEG\xff\xd9', free_buffer=lambda: None)
        with patch.object(app.asyncio, 'start_server', server):
            task = asyncio.create_task(app.serve(camera))
            try:
                await ready.wait()
                await handlers[0](Reader(b'/stream'), SlowViewer())
                response = Writer()
                await handlers[0](Reader(b'/status'), response)
                state = json.loads(bytes(response.output).split(b'\r\n\r\n', 1)[1])
                self.assertFalse(state['streaming'])
                self.assertIsNone(state['error'])
                self.assertIn('Wi-Fi write timed out', state['stream_error'])
                next_viewer = Writer()
                await handlers[0](Reader(b'/stream'), next_viewer)
                self.assertEqual(next_viewer.output.count(b'Content-Type: image/jpeg'), 2)
            finally:
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task

    async def start_app(self, camera=None, camera_factory=None):
        with patch.dict(sys.modules, {'network': SimpleNamespace()}):
            app = importlib.import_module('apps.camera_web')
        handlers, ready = [], asyncio.Event()
        async def server(handler, *args, **kwargs):
            handlers.append(handler)
            ready.set()
            return SimpleNamespace(close=lambda: None, wait_closed=lambda: asyncio.sleep(0))
        patcher = patch.object(app.asyncio, 'start_server', server)
        patcher.start()
        task = asyncio.create_task(app.serve(camera if camera_factory else (camera or SimpleNamespace(
            capture=lambda: b'\xff\xd8JPEG\xff\xd9', free_buffer=lambda: None)), camera_factory=camera_factory))
        await ready.wait()
        async def cleanup():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            patcher.stop()
        self.addAsyncCleanup(cleanup)
        return app, handlers[0], task

    async def status(self, handle):
        response = Writer()
        await handle(Reader(b'/status'), response)
        return json.loads(bytes(response.output).split(b'\r\n\r\n', 1)[1])

    async def test_settings_validate_atomically_and_apply_quality_and_pacing(self):
        class Camera:
            quality = 75
            def capture(self):
                return b'\xff\xd8JPEG\xff\xd9'
            def free_buffer(self):
                pass
            def set_quality(self, value):
                self.quality = value
        camera = Camera()
        app, handle, task = await self.start_app(camera)
        initial_fps = (await self.status(handle))["fps_limit"]
        for bad in [{'quality': True}, {'quality': 100}, {'fps_limit': 0},
                    {'fps_limit': 16}, {'quality': 40, 'fps_limit': 2.5},
                    {'arbitrary': 1}, [], {}]:
            writer = Writer()
            await handle(Reader(b'/settings', b'POST', json.dumps(bad).encode()), writer)
            self.assertIn(b'400 Bad Request', writer.output)
            self.assertEqual(camera.quality, 75)
            self.assertEqual((await self.status(handle))['fps_limit'], initial_fps)
        writer = Writer()
        await handle(Reader(b'/settings', b'POST', b'{"quality":45,"fps_limit":15}'), writer)
        self.assertIn(b'200 OK', writer.output)
        state = await self.status(handle)
        self.assertEqual((state['quality'], state['fps_limit']), (45, 15))
        self.assertIn('fps_actual', state)
        self.assertIn('led_enabled', state)
        wrong_method = Writer()
        await handle(Reader(b'/settings'), wrong_method)
        self.assertIn(b'405 Method Not Allowed', wrong_method.output)

    async def test_whole_frame_deadline_releases_drip_fed_viewer(self):
        camera = SimpleNamespace(capture=lambda: b'x' * 12000, free_buffer=lambda: None)
        app, handle, task = await self.start_app(camera)
        class DripViewer(Writer):
            async def drain(self):
                if b'Content-Type: image/jpeg' in self.output:
                    await asyncio.sleep(.02)
        with patch.object(app, 'FRAME_WRITE_TIMEOUT', .035):
            await asyncio.wait_for(handle(Reader(b'/stream'), DripViewer()), .3)
        state = await self.status(handle)
        self.assertFalse(state['streaming'])
        self.assertEqual(state['frames_sent'], 0)
        self.assertIsNone(state['error'])
        self.assertIn('write timed out', state['stream_error'])
        next_viewer = Writer()
        await handle(Reader(b'/stream'), next_viewer)
        self.assertEqual(next_viewer.output.count(b'Content-Type: image/jpeg'), 2)

    async def test_new_viewer_cancels_blocked_old_stream_before_capture(self):
        # Test prompt replacement independently of the conservative boot FPS.
        with patch("config.CAMERA_FPS_LIMIT", 10):
            app, handle, task = await self.start_app()
        blocked = asyncio.Event()
        class BlockedViewer(Writer):
            async def drain(self):
                if b'Content-Type: image/jpeg' in self.output:
                    blocked.set()
                    await asyncio.Event().wait()
        old_writer = BlockedViewer()
        old = asyncio.create_task(handle(Reader(b'/stream'), old_writer))
        await blocked.wait()
        new_writer = Writer()
        await asyncio.wait_for(handle(Reader(b'/stream'), new_writer), 1)
        try:
            await old
        except asyncio.CancelledError:
            pass
        self.assertTrue(old_writer.closed)
        self.assertEqual(new_writer.output.count(b'Content-Type: image/jpeg'), 2)
        self.assertFalse((await self.status(handle))['streaming'])

    async def test_async_capture_keeps_status_responsive_and_releases_buffer(self):
        capturing, release, freed = asyncio.Event(), asyncio.Event(), []
        async def capture_async():
            capturing.set()
            await release.wait()
            return b'\xff\xd8async\xff\xd9'
        camera = SimpleNamespace(capture_async=capture_async,
                                 free_buffer=lambda: freed.append(True))
        app, handle, task = await self.start_app(camera)
        writer = Writer()
        snapshot = asyncio.create_task(handle(Reader(b'/capture'), writer))
        await capturing.wait()
        self.assertTrue((await asyncio.wait_for(self.status(handle), .2))['ready'])
        release.set()
        await snapshot
        self.assertIn(b'async', writer.output)
        self.assertEqual(freed, [True])

    async def test_request_byte_limits_and_total_timeout_release_clients(self):
        app, handle, task = await self.start_app()
        for reader in [Reader(b'/' + b'x' * 1100),
                       Reader(b'/', headers=[b'Long: ' + b'x' * 5000]),
                       Reader(b'/settings', b'POST', b'x' * 257),
                       Reader(b'/', headers=[b'Content-Length: 1', b'Content-Length: 1'])]:
            writer = Writer()
            await handle(reader, writer)
            self.assertIn(b'400 Bad Request', writer.output)
            self.assertTrue(writer.closed)
        class SilentReader:
            async def read(self, size):
                await asyncio.Event().wait()
        stalled = [Writer() for _ in range(app.MAX_CLIENTS)]
        with patch.object(app, 'REQUEST_TIMEOUT', .04):
            waits = [asyncio.create_task(handle(SilentReader(), writer)) for writer in stalled]
            await asyncio.sleep(.01)
            excess = Writer()
            await handle(Reader(b'/status'), excess)
            self.assertTrue(excess.closed)
            await asyncio.gather(*waits)
        self.assertTrue(all(writer.closed for writer in stalled))
        self.assertTrue((await self.status(handle))['ready'])

    async def test_shutdown_closes_active_viewer_and_request_tasks(self):
        app, handle, task = await self.start_app()
        blocked = asyncio.Event()
        class BlockedViewer(Writer):
            async def drain(self):
                blocked.set()
                await asyncio.Event().wait()
        writer = BlockedViewer()
        viewer = asyncio.create_task(handle(Reader(b'/stream'), writer))
        await blocked.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertTrue(writer.closed)
        self.assertTrue(viewer.done())

    async def test_listener_and_diagnostics_start_before_camera_initialization(self):
        from unittest.mock import Mock
        device = SimpleNamespace(capture=lambda: b'jpeg', free_buffer=lambda: None, deinit=Mock())
        opened = []
        def factory():
            opened.append(True)
            return device
        app, handle, task = await self.start_app(camera_factory=factory)
        initial = await self.status(handle)
        self.assertFalse(initial['ready'])
        self.assertEqual(initial['camera_state'], 'initializing')
        self.assertEqual(opened, [])
        await asyncio.sleep(.25)
        ready = await self.status(handle)
        self.assertTrue(ready['ready'])
        self.assertEqual(ready['camera_state'], 'ready')
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        device.deinit.assert_called_once()

    async def test_initialization_failure_preserves_http_diagnostics(self):
        def broken():
            raise OSError('camera ribbon fault')
        app, handle, task = await self.start_app(camera_factory=broken)
        await self.status(handle)
        await asyncio.sleep(.25)
        state = await self.status(handle)
        self.assertFalse(state['ready'])
        self.assertEqual(state['camera_state'], 'unavailable')
        self.assertIn('ribbon fault', state['error'])
        response = Writer()
        await handle(Reader(b'/capture'), response)
        self.assertIn(b'503 Service Unavailable', response.output)

    async def test_phone_portal_probe_redirects_to_dashboard(self):
        app, handle, task = await self.start_app()
        writer = Writer()
        await handle(Reader(b'/generate_204'), writer)
        self.assertIn(b'302 Found', writer.output)
        self.assertIn(b'Location: http://192.168.4.1/', writer.output)

    async def test_phone_probe_and_html_do_not_start_camera(self):
        from unittest.mock import Mock, mock_open
        factory = Mock(return_value=SimpleNamespace(deinit=lambda: None))
        app, handle, task = await self.start_app(camera_factory=factory)
        await handle(Reader(b'/hotspot-detect.html'), Writer())
        with patch('builtins.open', mock_open(read_data=b'<html>test</html>')):
            page = Writer()
            await handle(Reader(b'/'), page)
        await asyncio.sleep(.3)
        factory.assert_not_called()
        self.assertIn(b'<html>test</html>', page.output)
        await self.status(handle)
        await asyncio.sleep(.25)
        factory.assert_called_once()
