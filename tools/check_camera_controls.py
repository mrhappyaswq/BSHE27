"""Check real OV3660 USB exposure controls and video; close the viewer first.

Only camera commands are sent. Restores automatic exposure/gain on exit.
Example: python tools/check_camera_controls.py --port COM10
"""
import argparse
import json
from pathlib import Path
import struct
import time

import serial


def exact(port, count):
    data = port.read(count)
    if len(data) != count:
        raise RuntimeError(f"Expected {count} bytes, got {len(data)}")
    return data


def settings(port, mode=None, us=0, gain16=64):
    port.write(b"S" if mode is None else b"C" + struct.pack("<BIH", mode, us, gain16))
    header = exact(port, 8)
    if header[:4] != b"BSS1":
        raise RuntimeError("Expected BSS1 settings response; upload current firmware")
    length = struct.unpack_from("<I", header, 4)[0]
    if not 0 < length <= 4096:
        raise RuntimeError("Invalid settings response length")
    return json.loads(exact(port, length))


def frames(port, count=20):
    last = 0
    started = time.monotonic()
    for _ in range(count):
        port.write(b"F" + struct.pack("<I", last))
        h = exact(port, 48)
        if h[:4] != b"BSC1" or struct.unpack_from("<I", h, 44)[0]:
            raise RuntimeError("Camera frame unavailable")
        length, frame_id = struct.unpack_from("<II", h, 4)
        if not 0 < length <= 524288 or frame_id == last:
            raise RuntimeError("Invalid/duplicate camera frame")
        image = exact(port, length)
        if not image.startswith(b"\xff\xd8") or not image.endswith(b"\xff\xd9"):
            raise RuntimeError("Invalid JPEG")
        last = frame_id
    return round(count / (time.monotonic() - started), 2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True)
    parser.add_argument("--report", default="local/camera-controls-hardware.json")
    args = parser.parse_args()
    port = serial.Serial(port=None, baudrate=115200, timeout=5, write_timeout=5)
    port.dtr, port.rts, port.port = True, False, args.port
    port.open()
    if hasattr(port, "set_buffer_size"):
        port.set_buffer_size(rx_size=1048576, tx_size=65536)
    results = []
    try:
        initial = settings(port)
        assert initial["ok"], initial
        for us, gain16 in [(500, 64), (1000, 64), (2000, 128)]:
            value = settings(port, 1, us, gain16)
            assert value["ok"] and value["manual"] and not value["night_mode"], value
            assert abs(value["exposure_ms"] - us / 1000) <= value["row_us"] / 2000 + 0.0002, value
            assert abs(value["gain"] - gain16 / 16) < 0.001, value
            value["requested_ms"] = us / 1000
            value["received_fps"] = frames(port)
            results.append(value)
        for mode, us, gain16 in [(1, 1, 64), (1, 1000, 65535), (2, 1000, 64)]:
            assert not settings(port, mode, us, gain16)["ok"]
        unchanged = settings(port)
        assert unchanged["manual"] and unchanged["gain"] == 8, unchanged
        assert abs(unchanged["exposure_ms"] - results[-1]["exposure_ms"]) < 0.001
        auto = settings(port, 0)
        assert auto["ok"] and not auto["manual"] and not auto["night_mode"], auto
        auto_fps = frames(port, 50)
        report = dict(result="pass", initial=initial, manual_cases=results,
                      invalid_requests_rejected=3, restored_auto=auto,
                      auto_received_fps=auto_fps)
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
    finally:
        try:
            settings(port, 0)
        finally:
            port.close()


if __name__ == "__main__":
    main()
