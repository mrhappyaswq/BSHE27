import unittest
from banshee.portal import dns_reply

class PortalTests(unittest.TestCase):
    def test_dns_ipv4_and_ipv6(self):
        question = b'\x06camera\x04test\x00'
        header = b'\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00'
        answer = dns_reply(header + question + b'\x00\x01\x00\x01')
        self.assertEqual(answer[:2], header[:2])
        self.assertEqual(answer[-4:], bytes([192,168,4,1]))
        answer6 = dns_reply(header + question + b'\x00\x1c\x00\x01')
        self.assertEqual(answer6[6:8], b'\x00\x00')
    def test_truncated_and_compressed_queries_are_ignored(self):
        for packet in [b'', bytes(12), b'\x00\x00\x00\x00\x00\x01' + bytes(6) + b'\xc0\x0c' + bytes(4)]:
            self.assertIsNone(dns_reply(packet))
