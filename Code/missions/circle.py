"""Fly the pasted 20 m radius circle at 10 m. GPS waypoints close the circle."""

import math

from banshee.flight import arm_and_takeoff, get_location_metres, goto_and_wait, hold, land_and_wait, run_mission

TARGET_ALTITUDE = 10
CIRCLE_RADIUS = 20
CIRCLE_STEPS = 36


def fly_circle(vehicle, center, radius, altitude):
    # Include the first point again at the end to close the circle.
    for index in range(CIRCLE_STEPS + 1):
        angle = index * 2 * math.pi / CIRCLE_STEPS
        point = get_location_metres(center, radius * math.cos(angle),
                                    radius * math.sin(angle), altitude)
        goto_and_wait(vehicle, point)


def mission(vehicle):
    arm_and_takeoff(vehicle, TARGET_ALTITUDE)
    home = vehicle.global_location()
    fly_circle(vehicle, home, CIRCLE_RADIUS, TARGET_ALTITUDE)
    goto_and_wait(vehicle, get_location_metres(home, 0, 0, TARGET_ALTITUDE))
    hold(vehicle, 5)
    land_and_wait(vehicle)


def main():
    run_mission(mission)


if __name__ == "__main__":
    main()
