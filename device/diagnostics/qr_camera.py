"""Print real XIAO QR detections, or save a bench photo. Never opens MAVLink."""

import math

from banshee.camera import XiaoCamera
from banshee.compat import sleep_ms, ticks_diff, ticks_ms


def main(seconds=10):
    camera = XiaoCamera()
    started = ticks_ms()
    try:
        while ticks_diff(ticks_ms(), started) < seconds * 1000:
            marker = camera.marker()
            if marker is None:
                print("QR absent/stale", camera.last_error or "")
            else:
                print("QR center=(%.1f, %.1f), clockwise yaw=%.1f deg" %
                      (marker.cx, marker.cy, math.degrees(marker.yaw)))
            sleep_ms(100)
    finally:
        camera.close()


def photo():
    camera = XiaoCamera()
    try:
        path = camera.capture_photo()
        print("Saved on XIAO microSD:", path)
        return path
    finally:
        camera.close()


if __name__ == "__main__":
    main()
