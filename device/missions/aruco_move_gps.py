"""Fly 3 m north, return to the takeoff position, then land on an ArUco marker."""

from missions.aruco_landing import land_on_aruco
from banshee.flight import arm_and_takeoff, get_location_metres, goto_and_wait, hold, run_mission
from banshee.vision import require_marker_provider

TARGET_ALTITUDE = 1.5


def mission(vehicle):
    arm_and_takeoff(vehicle, TARGET_ALTITUDE)
    home = vehicle.global_location()
    goto_and_wait(vehicle, get_location_metres(home, 3, 0, TARGET_ALTITUDE))
    hold(vehicle, 10)
    goto_and_wait(vehicle, get_location_metres(home, 0, 0, TARGET_ALTITUDE))
    hold(vehicle, 10)
    land_on_aruco(vehicle)


def main():
    require_marker_provider()
    run_mission(mission)


if __name__ == "__main__":
    main()
