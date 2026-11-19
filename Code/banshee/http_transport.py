"""Bounded Wi-Fi writes for the pinned MicroPython socket stream."""
import asyncio
import errno
import socket


WRITE_CHUNK = 192
WRITE_PAUSE_SECONDS = 0.02


class RadioWriter:
    """Send small packets cooperatively instead of filling the radio send queue."""
    def __init__(self, stream):
        self.stream = stream
        self.pending = b''
        self.stream.s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    def write(self, data):
        self.pending += data

    async def drain(self):
        while self.pending:
            try:
                sent = self.stream.s.send(self.pending[:WRITE_CHUNK])
            except OSError as exc:
                if exc.args[0] not in (errno.EAGAIN, getattr(errno, 'EWOULDBLOCK', errno.EAGAIN),
                                       getattr(errno, 'ENOBUFS', 105), 119):
                    raise
                sent = None
            if sent == 0:
                raise OSError(errno.ECONNRESET)
            if sent:
                self.pending = self.pending[sent:]
            await asyncio.sleep(WRITE_PAUSE_SECONDS)

    def close(self):
        self.stream.close()

    async def wait_closed(self):
        try:
            await self.stream.wait_closed()
        finally:
            self.pending = b''
