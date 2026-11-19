"""Print real onboard S3 QR detections. Never opens MAVLink."""

from banshee import status_led


import math

from banshee.camera import LocalCamera
from banshee.compat import sleep_ms, ticks_diff, ticks_ms


@status_led.indicate("qr_search")
def main(seconds=10):
    camera = LocalCamera()
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


if __name__ == "__main__":
    main()
