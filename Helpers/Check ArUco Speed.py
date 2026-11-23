"""Measure onboard ArUco stages over native USB. Sends video requests only.

Close the browser viewer first. Install Docs/Python Packages.txt.
Example: python "Helpers/Check ArUco Speed.py" --port COM10 --seconds 30
"""
import argparse
import json
import math
from pathlib import Path
import statistics
import struct
import time

import serial
from serial.tools import list_ports

STAGES = ("decode_ms", "prepare_ms", "search_ms", "identify_ms",
          "pose_ms", "processing_ms", "age_ms")


def read_exact(port, count, deadline):
    output = bytearray()
    while len(output) < count:
        if time.monotonic() >= deadline:
            raise TimeoutError("Incomplete USB reply; close other viewers and check the native OTG port")
        output.extend(port.read(count - len(output)))
    return bytes(output)


def sample(port, after):
    port.write(b"V" + struct.pack("<I", after))
    deadline = time.monotonic() + 4
    prefix = read_exact(port, 8, deadline)
    if prefix[:4] != b"BSV1":
        raise ValueError("Expected an ArUco reply from the native OTG port")
    size, = struct.unpack_from("<I", prefix, 4)
    if not 0 < size <= 4096:
        raise ValueError("Invalid metadata length")
    metadata = json.loads(read_exact(port, size, deadline))
    header = read_exact(port, 48, deadline)
    if header[:4] != b"BSC1":
        raise ValueError("Invalid image header")
    size, frame_id = struct.unpack_from("<II", header, 4)
    flags, = struct.unpack_from("<I", header, 44)
    if size > 2_000_000:
        raise ValueError("Invalid JPEG length")
    jpeg = read_exact(port, size, deadline)
    if metadata.get("pipeline_version") != 2:
        raise ValueError("Upload the optimized firmware first; this board lacks the new stage measurements")
    if flags:
        return None, after
    if metadata.get("frame_id") != frame_id or frame_id == after:
        raise ValueError("Repeated frame or metadata/image mismatch")
    if not jpeg.startswith(b"\xff\xd8") or not jpeg.endswith(b"\xff\xd9"):
        raise ValueError("Incomplete JPEG")
    return metadata, frame_id


def summarize(samples):
    result = {}
    for stage in STAGES:
        values = sorted(float(s[stage]) for s in samples
                        if isinstance(s.get(stage), (int, float)) and math.isfinite(s[stage]))
        if not values:
            continue
        result[stage] = {
            "mean": statistics.fmean(values),
            "p50": values[math.ceil(.50 * len(values)) - 1],
            "p95": values[math.ceil(.95 * len(values)) - 1],
            "p99": values[math.ceil(.99 * len(values)) - 1],
            "max": values[-1],
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port")
    parser.add_argument("--seconds", type=float, default=30)
    parser.add_argument("--report", type=Path, default=Path("Saved Results/ArUco Speed.json"))
    args = parser.parse_args()
    if not math.isfinite(args.seconds) or args.seconds <= 0:
        parser.error("--seconds must be positive and finite")
    if not args.port:
        ports = [p.device for p in list_ports.comports() if p.vid == 0x303A]
        if len(ports) != 1:
            parser.error("Use --port to select the Espressif native OTG serial port")
        args.port = ports[0]
    samples, failures, after = [], [], 0
    started = time.monotonic()
    with serial.Serial(args.port, 115200, timeout=.1, write_timeout=1) as port:
        port.reset_input_buffer()
        while time.monotonic() - started < args.seconds:
            try:
                data, after = sample(port, after)
                if data is not None:
                    samples.append(data)
                else:
                    time.sleep(.01)
            except (ValueError, TimeoutError, serial.SerialException) as error:
                failures.append(str(error))
                break  # Partial replies need a fresh session; never guess framing.
    elapsed = time.monotonic() - started
    report = {
        "port": args.port, "seconds": elapsed, "frames": len(samples),
        "received_fps": len(samples) / elapsed if elapsed else 0,
        "stale_frames": sum(not s.get("fresh", False) for s in samples),
        "note": "On-board wall times, not scheduler CPU usage. USB/JSON/browser time is outside processing_ms.",
        "all_frames": summarize(samples),
        "marker_visible": summarize([s for s in samples if s.get("detected")]),
        "marker_missing": summarize([s for s in samples if not s.get("detected")]),
        "tracked_search": summarize([s for s in samples if s.get("tracked_search")]),
        "full_image": summarize([s for s in samples if not s.get("tracked_search")]),
        "errors": failures, "samples": samples,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "samples"}, indent=2))
    if failures or not samples:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
