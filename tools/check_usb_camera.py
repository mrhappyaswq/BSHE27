"""Read-only native USB camera soak test. Close the browser viewer first.

Example: python tools/check_usb_camera.py --port COM10 --seconds 45
Requires pyserial; never sends flight commands or resets the board.
"""
import argparse
import json
import os
from pathlib import Path
import struct
import time

import serial
from serial.tools import list_ports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="auto", help="Native USB port, or auto (default)")
    parser.add_argument("--seconds", type=float, default=45)
    parser.add_argument("--pause-every", type=int, default=25)
    parser.add_argument("--pause-ms", type=float, default=250)
    parser.add_argument("--report")
    parser.add_argument("--snapshot", help="Save the first complete JPEG to this path")
    args = parser.parse_args()
    if args.seconds <= 0 or args.pause_every < 0 or args.pause_ms < 0:
        parser.error("seconds must be positive; pause settings must be nonnegative")
    if args.port == "auto":
        matches = [p.device for p in list_ports.comports() if (p.vid, p.pid) == (0x303A, 0x1001)]
        if len(matches) != 1:
            parser.error("Connect one ESP32-S3 OTG USB-C socket, or specify --port COMxx")
        args.port = matches[0]
    port = serial.Serial(port=None, baudrate=115200, timeout=5, write_timeout=5)
    port.dtr, port.rts, port.port = True, False, args.port
    count, last, total_bytes, aligned_jpegs = 0, 0, 0, 0
    times, board_fps, frame_ages = [], [], []
    started = time.monotonic()
    try:
        port.open()
        # Windows defaults to a small receive queue (often 4096 bytes), which
        # can overflow within one JPEG while the laptop is briefly busy.
        # Match/exceed the browser viewer's explicit receive buffer.
        if os.name == "nt":
            port.set_buffer_size(rx_size=1048576, tx_size=65536)
        port.reset_input_buffer()
        started = time.monotonic()
        while time.monotonic() - started < args.seconds:
            request_at = time.monotonic()
            port.write(b"F" + struct.pack("<I", last))
            header = port.read(48)
            if len(header) != 48 or header[:4] != b"BSC1":
                raise RuntimeError(f"Frame {count}: invalid/short header ({len(header)} bytes). "
                                   "Check the OTG socket, close other viewers, and upload the latest firmware.")
            length, frame_id = struct.unpack_from("<II", header, 4)
            flags = struct.unpack_from("<I", header, 44)[0]
            if flags or not 0 < length <= 524288:
                raise RuntimeError(f"Camera unavailable: flags={flags}, size={length}")
            if args.pause_every and count and count % args.pause_every == 0:
                time.sleep(args.pause_ms / 1000)
            image = port.read(length)
            if len(image) != length:
                raise RuntimeError(f"Frame {count}: expected {length} JPEG bytes, received {len(image)}")
            if image[:2] != b"\xff\xd8" or image[-2:] != b"\xff\xd9":
                raise RuntimeError(f"Frame {count}: invalid JPEG boundaries")
            if frame_id == last:
                raise RuntimeError(f"Frame {count}: duplicate capture ID {frame_id}")
            if struct.unpack_from("<HH", header, 36) != (320, 240):
                raise RuntimeError("Unexpected camera dimensions")
            if args.snapshot and not count:
                snapshot_path = Path(args.snapshot)
                snapshot_path.parent.mkdir(parents=True, exist_ok=True)
                snapshot_path.write_bytes(image)
            last = frame_id
            count += 1
            total_bytes += length
            aligned_jpegs += int(length % 64 == 0)
            times.append((time.monotonic() - request_at) * 1000)
            board_fps.append(struct.unpack_from("<f", header, 32)[0])
            frame_ages.append(struct.unpack_from("<I", header, 40)[0])
            if count % 50 == 0:
                print(json.dumps({"frames": count, "seconds": round(time.monotonic() - started, 2)}), flush=True)
        elapsed = time.monotonic() - started
        report = {
            "result": "pass", "port": args.port, "frames": count,
            "seconds": round(elapsed, 2), "display_requests_fps": round(count / elapsed, 2),
            "jpeg_bytes": total_bytes, "mean_request_ms": round(sum(times) / len(times), 2),
            "mean_board_fps": round(sum(board_fps) / len(board_fps), 2),
            "mean_frame_age_ms": round(sum(frame_ages) / len(frame_ages), 2),
            "max_request_ms": round(max(times), 2),
            "packet_aligned_jpegs": aligned_jpegs,
            "pause_every_frames": args.pause_every, "pause_ms": args.pause_ms,
            "partial_or_invalid_frames": 0,
        }
        if args.report:
            report_path = Path(args.report)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report), flush=True)
    finally:
        port.close()


if __name__ == "__main__":
    main()
