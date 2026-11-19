"""Take off to 1.5 m, align with a supplied ArUco marker, and land."""

import config
from banshee.compat import ticks_diff, ticks_ms
from banshee.flight import arm_and_takeoff, ensure_guided, hold, land_and_wait, run_mission
from banshee.vision import marker_provider, require_marker_provider

TARGET_ALTITUDE = 1.5
LANDING_ALTITUDE = config.LANDING_ALTITUDE
KP = config.MARKER_KP


def _clamp(value, limit):
    return max(-limit, min(limit, value))


def land_on_aruco(vehicle):
    require_marker_provider()
    print("Searching for ArUco marker")
    started = ticks_ms()
    last_seen = started
    while True:
        ensure_guided(vehicle)
        now = ticks_ms()
        if ticks_diff(now, started) >= config.MARKER_LANDING_TIMEOUT * 1000:
            raise RuntimeError("ArUco landing timed out")
        marker = marker_provider()
        if marker is None:
            # Cancel both horizontal and descent velocity immediately on loss.
            vehicle.send_body_velocity(0, 0, 0, 0.1)
            if ticks_diff(now, last_seen) >= config.MARKER_TIMEOUT * 1000:
                raise RuntimeError("ArUco marker lost")
            continue
        last_seen = now
        cx, cy, width, height = marker
        dx = cx - width / 2
        dy = cy - height / 2
        centered = (abs(dx) <= config.MARKER_CENTER_TOLERANCE
                    and abs(dy) <= config.MARKER_CENTER_TOLERANCE)
        if centered and vehicle.altitude() <= LANDING_ALTITUDE:
            land_and_wait(vehicle)
            return
        forward = _clamp(config.MARKER_FORWARD_SIGN * dy * KP, config.MARKER_MAX_SPEED)
        right = _clamp(config.MARKER_RIGHT_SIGN * dx * KP, config.MARKER_MAX_SPEED)
        # MAVLink body NED uses positive Z downward, unlike the pasted -0.05.
        down = config.MARKER_DESCENT_SPEED if centered else 0
        vehicle.send_body_velocity(forward, right, down, 0.1)


def mission(vehicle):
    arm_and_takeoff(vehicle, TARGET_ALTITUDE)
    hold(vehicle, 3)
    land_on_aruco(vehicle)


def main():
    require_marker_provider()  # Fail before connecting/arming if vision is absent.
    run_mission(mission)


if __name__ == "__main__":
    main()
