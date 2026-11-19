"""Explicit onboard S3 QR alignment mission: center AND align heading before descent."""

from banshee import status_led


import math

import config
from banshee.camera import LocalCamera
from banshee.compat import ticks_diff, ticks_ms
from banshee.flight import arm_and_takeoff, ensure_guided, land_and_wait, run_mission


def _clamp(value, limit):
    return max(-limit, min(limit, value))


def yaw_error(marker):
    error = marker.yaw - math.radians(config.QR_DESIRED_ANGLE_DEG)
    return (error + math.pi) % (2 * math.pi) - math.pi


def land_on_qr(vehicle, camera):
    """Use body velocity+yaw-rate in GUIDED; hand off to LAND near home height.

    No PLND parameters/LANDING_TARGET backend are needed for this controller.
    Ordinary LAND after errors is inherited from run_mission; it may land away
    from the marker. Camera pixels do not provide a calibrated metric pose.
    """
    started = ticks_ms()
    last_seen = started
    aligned_at = None
    aligned_frames = 0
    last_frame_id = None
    while True:
        ensure_guided(vehicle)
        now = ticks_ms()
        if ticks_diff(now, started) >= config.MARKER_LANDING_TIMEOUT * 1000:
            raise RuntimeError("QR landing timed out")
        marker = camera.marker(service=vehicle.poll)
        # Capture/decoding can take time: respect any pilot override now.
        ensure_guided(vehicle)
        now = ticks_ms()
        if marker is None:
            aligned_at = None
            aligned_frames = 0
            vehicle.send_body_velocity(0, 0, 0, 0.1, yaw_rate=0)
            if ticks_diff(now, last_seen) >= config.MARKER_TIMEOUT * 1000:
                raise RuntimeError("Landing QR lost or stale")
            continue
        last_seen = now
        dx, dy = marker.cx - marker.width / 2, marker.cy - marker.height / 2
        error = yaw_error(marker)
        aligned = (abs(dx) <= config.QR_CENTER_TOLERANCE
                   and abs(dy) <= config.QR_CENTER_TOLERANCE
                   and abs(error) <= math.radians(config.QR_YAW_TOLERANCE_DEG))
        if not aligned:
            aligned_at = None
            aligned_frames = 0
        elif aligned_at is None:
            aligned_at = now
        if aligned and marker.frame_id != last_frame_id:
            aligned_frames += 1
        last_frame_id = marker.frame_id
        settled = (aligned_at is not None
                   and ticks_diff(now, aligned_at) >= config.QR_SETTLE_MS
                   and aligned_frames >= config.QR_SETTLE_FRAMES)
        if settled and vehicle.altitude() <= config.LANDING_ALTITUDE:
            # Cancel previous yaw/translation commands before mode transition.
            vehicle.send_body_velocity(0, 0, 0, 0, yaw_rate=0)
            land_and_wait(vehicle)
            return
        forward = _clamp(-dy * config.QR_KP, config.QR_MAX_SPEED)
        right = _clamp(dx * config.QR_KP, config.QR_MAX_SPEED)
        yaw_rate = _clamp(error * config.QR_YAW_KP, config.QR_MAX_YAW_RATE)
        down = config.MARKER_DESCENT_SPEED if settled else 0
        vehicle.send_body_velocity(forward, right, down, 0.1, yaw_rate=yaw_rate)


@status_led.indicate("qr_search")
def main():
    camera = LocalCamera()
    try:
        # Real QR must be visible and decoding BEFORE connecting or arming.
        camera.wait_for_marker()

        def mission(vehicle):
            arm_and_takeoff(vehicle, config.QR_TAKEOFF_ALTITUDE)
            land_on_qr(vehicle, camera)

        run_mission(mission)
    finally:
        camera.close()


if __name__ == "__main__":
    main()
