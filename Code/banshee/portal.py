"""Small local DNS responder for phone hotspot discovery; no internet needed."""
import socket


def dns_reply(packet):
    # Standard single-question, uncompressed DNS query only.
    if len(packet) < 17 or packet[2] & 128 or packet[4:6] != b'\x00\x01':
        return None
    end = 12
    while end < len(packet):
        size = packet[end]
        if size == 0:
            break
        if size > 63 or end + 1 + size >= len(packet):
            return None
        end += size + 1
    if end + 5 > len(packet):
        return None
    end += 1
    question = packet[12:end + 4]
    ipv4 = packet[end:end + 4] == b'\x00\x01\x00\x01'
    # AAAA/other requests get a valid empty answer, never a fake IPv6 record.
    header = packet[:2] + b'\x81\x80\x00\x01' + (b'\x00\x01' if ipv4 else b'\x00\x00') + b'\x00\x00\x00\x00'
    answer = b'\xc0\x0c\x00\x01\x00\x01\x00\x00\x00\x00\x00\x04\xc0\xa8\x04\x01' if ipv4 else b''
    return header + question + answer


class PortalDNS:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.socket.setblocking(False)
            self.socket.bind(('0.0.0.0', 53))
        except BaseException:
            self.socket.close()
            raise

    def poll(self):
        # Bound the work so probes cannot monopolize telemetry/video.
        for _ in range(2):
            try:
                data, address = self.socket.recvfrom(512)
            except OSError:
                return
            response = dns_reply(data)
            if response:
                try:
                    self.socket.sendto(response, address)
                except OSError:
                    pass

    def close(self):
        self.socket.close()
