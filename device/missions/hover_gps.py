"""Take off to 10 m, hover for 10 seconds, then land."""

from banshee.flight import arm_and_takeoff, hold, land_and_wait, run_mission

TARGET_ALTITUDE = 10
HOVER_SECONDS = 10


def mission(vehicle):
    arm_and_takeoff(vehicle, TARGET_ALTITUDE)
    hold(vehicle, HOVER_SECONDS)
    land_and_wait(vehicle)


def main():
    run_mission(mission)


if __name__ == "__main__":
    main()
