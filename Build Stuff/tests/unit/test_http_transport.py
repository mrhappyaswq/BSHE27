import asyncio
import errno
import unittest
from types import SimpleNamespace
from banshee.http_transport import RadioWriter, WRITE_CHUNK


class Socket:
    def __init__(self, actions):
        self.actions = iter(actions)
        self.output = bytearray()
        self.options = []
    def setsockopt(self, *options):
        self.options.append(options)
    def send(self, data):
        action = next(self.actions, len(data))
        if isinstance(action, Exception):
            raise action
        count = min(action, len(data))
        self.output.extend(data[:count])
        return count


class RadioWriterTests(unittest.IsolatedAsyncioTestCase):
    async def test_partial_writes_and_backpressure_preserve_exact_http_bytes(self):
        sock = Socket([OSError(errno.EAGAIN), 7, 3, WRITE_CHUNK])
        stream = SimpleNamespace(s=sock)
        writer = RadioWriter(stream)
        expected = b'HTTP/1.1 200 OK\r\n\r\n' + bytes(range(256))*2
        writer.write(expected[:19])
        writer.write(memoryview(expected)[19:])
        await writer.drain()
        self.assertEqual(bytes(sock.output), expected)
        self.assertEqual(writer.pending, b'')
        self.assertTrue(sock.options)

    async def test_closed_peer_is_not_retried_forever(self):
        writer = RadioWriter(SimpleNamespace(s=Socket([0])))
        writer.write(b'response')
        with self.assertRaises(OSError):
            await asyncio.wait_for(writer.drain(), .2)

    async def test_cancel_and_close_release_pending_response(self):
        closed = []
        async def close():
            closed.append(True)
        sock = Socket([OSError(errno.EAGAIN)]*100)
        writer = RadioWriter(SimpleNamespace(s=sock, close=lambda: None, wait_closed=close))
        writer.write(b'pending')
        task = asyncio.create_task(writer.drain())
        await asyncio.sleep(.001)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        writer.close()
        await writer.wait_closed()
        self.assertEqual(closed, [True])
        self.assertEqual(writer.pending, b'')
