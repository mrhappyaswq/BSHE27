"""Take off to 1.5 m, fly 3 m north, return, and land."""

from banshee.flight import arm_and_takeoff, get_location_metres, goto_and_wait, hold, land_and_wait, run_mission

TARGET_ALTITUDE = 1.5


def mission(vehicle):
    arm_and_takeoff(vehicle, TARGET_ALTITUDE)
    home = vehicle.global_location()
    goto_and_wait(vehicle, get_location_metres(home, 3, 0, TARGET_ALTITUDE))
    hold(vehicle, 10)
    goto_and_wait(vehicle, get_location_metres(home, 0, 0, TARGET_ALTITUDE))
    hold(vehicle, 10)
    land_and_wait(vehicle)


def main():
    run_mission(mission)


if __name__ == "__main__":
    main()
