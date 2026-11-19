"""Run explicitly on the S3 via mpremote; receive-only, never starts a mission.

Exercises the real sensor/codec and HTTP over on-board TCP loopback. This is
not a browser-over-radio test. Reset after running to restore the dashboard.
"""
import asyncio
import gc
import json
import time
from apps.camera_web import start_access_point, serve
from banshee.camera import open_camera
from banshee.telemetry import TelemetryMonitor
from banshee import status_led


async def connection(path, changes=None):
    reader, writer = await asyncio.open_connection('127.0.0.1', 80)
    body = b'' if changes is None else json.dumps(changes).encode()
    method = 'GET' if changes is None else 'POST'
    writer.write(('%s %s HTTP/1.1\r\nHost: camera\r\nContent-Length: %d\r\n\r\n' %
                  (method, path, len(body))).encode() + body)
    await writer.drain()
    return reader, writer


async def close(writer):
    writer.close()
    try:
        await writer.wait_closed()
    except OSError:
        pass


async def request(path, changes=None):
    reader, writer = await connection(path, changes)
    try:
        response = await asyncio.wait_for(reader.read(), 6)
        headers, body = response.split(b'\r\n\r\n', 1)
        assert b'200 OK' in headers, response[:256]
        return body
    finally:
        await close(writer)


async def snapshot():
    image = await request('/capture')
    assert image[:2] == b'\xff\xd8' and image[-2:] == b'\xff\xd9'
    return len(image)


async def frame(reader):
    length = None
    for _ in range(16):
        line = await asyncio.wait_for(reader.readline(), 7)
        if not line:
            raise RuntimeError('MJPEG ended unexpectedly')
        if line.lower().startswith(b'content-length:'):
            length = int(line.split(b':', 1)[1])
        if length is not None and line == b'\r\n':
            break
    assert length is not None
    image = await asyncio.wait_for(reader.readexactly(length), 7)
    assert image[:2] == b'\xff\xd8' and image[-2:] == b'\xff\xd9'
    return length


async def check(camera, ap, telemetry):
    task = asyncio.create_task(serve(camera, ap=ap, telemetry=telemetry))
    viewers = []
    try:
        await asyncio.sleep(0.2)
        state = json.loads(await request('/status'))
        assert state['ready'] and state['app_version'] == 7, state
        assert b'receiveFrames' in await request('/')
        print('READY:', state['camera_state'], state['pixhawk']['state'])
        status_led.set_enabled(False)
        assert not json.loads(await request('/status'))['led_enabled']
        status_led.set_enabled(True)
        assert json.loads(await request('/status'))['led_enabled']
        print('LED software mute/resume: PASS (physical BOOT still needs a press)')
        low = json.loads(await request('/settings', {'quality': 35, 'fps_limit': 15}))
        assert low['quality'] == 35 and low['fps_limit'] == 15
        print('LOW QUALITY JPEG:', await snapshot())
        high = json.loads(await request('/settings', {'quality': 90, 'fps_limit': 3}))
        assert high['quality'] == 90 and high['fps_limit'] == 3
        print('HIGH QUALITY JPEG:', await snapshot())
        await request('/settings', {'quality': 75, 'fps_limit': 5})
        # Rapid stream replacement must release the old loop and its socket.
        old_reader, old_writer = await connection('/stream')
        viewers.append(old_writer)
        await frame(old_reader)
        reader, writer = await connection('/stream')
        viewers.append(writer)
        await frame(reader)
        await close(old_writer)
        assert json.loads(await request('/status'))['streaming']
        print('REPLACED VIEWER: PASS')
        gc.collect()
        initial_heap = gc.mem_free()
        started = time.ticks_ms()
        for index in range(650):
            size = await frame(reader)
            if index % 25 == 0:
                state = json.loads(await request('/status'))
                assert state['ready'] and state['streaming'] and state['error'] is None, state
                assert state['pixhawk']['state'] in ('waiting', 'connected', 'lost', 'disabled'), state
            if index % 100 == 0:
                print('FRAME:', index, size, 'bytes; snapshot:', await snapshot())
        elapsed = time.ticks_diff(time.ticks_ms(), started)
        assert elapsed >= 120000, elapsed
        gc.collect()
        print('ENDURANCE: 650 frames in', elapsed, 'ms; free heap:', initial_heap, '->', gc.mem_free())
        await close(writer)
        # Leave TCP open and stop reading: frame deadline must release it.
        slow_reader, slow_writer = await connection('/stream')
        viewers.append(slow_writer)
        released = False
        for second in range(20):
            await asyncio.sleep(1)
            state = json.loads(await request('/status'))
            if not state['streaming']:
                assert state['error'] is None and state['stream_error'], state
                released = True
                print('STALLED VIEWER RELEASED:', second + 1, 'seconds')
                break
        assert released, state
        await close(slow_writer)
        assert await snapshot() > 4
        reader, writer = await connection('/stream')
        viewers.append(writer)
        await frame(reader)
        print('RECOVERY CAPTURE/STREAM: PASS')
        print('CAMERA HARDWARE LOOPBACK CHECK PASSED')
    finally:
        for writer in viewers:
            await close(writer)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


ap = start_access_point()
camera = None
telemetry = None
try:
    camera = open_camera()
    telemetry = TelemetryMonitor()
    asyncio.run(check(camera, ap, telemetry))
finally:
    status_led.set_enabled(True)
    if telemetry is not None:
        telemetry.close()
    if camera is not None:
        camera.deinit()
    ap.active(False)
