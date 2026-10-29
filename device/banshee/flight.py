"""Shared mission operations with bounded waits and cooperative telemetry."""

import math

import config
from banshee.compat import ticks_diff, ticks_ms
from banshee.mavlink.vehicle import Location, MAVLinkVehicle, detect_pixhawk_uart


class MissionInterrupted(RuntimeError):
    """The pilot/autopilot changed mode or disarmed during guided flight."""


def connect_to_pixhawk():
    vehicle = MAVLinkVehicle(detect_pixhawk_uart())
    print("Connected to ArduCopter")
    return vehicle


def ensure_guided(vehicle):
    if vehicle.mode() != "GUIDED" or not vehicle.armed():
        raise MissionInterrupted("Guided mission stopped: mode changed or vehicle disarmed")


def wait_until(vehicle, predicate, timeout, description, guided=False):
    started = ticks_ms()
    while True:
        if guided:
            ensure_guided(vehicle)
        if predicate():
            return
        if ticks_diff(ticks_ms(), started) >= timeout * 1000:
            raise RuntimeError("Timed out waiting for " + description)
        vehicle.sleep(0.1)


def arm_and_takeoff(vehicle, target_altitude):
    print("Waiting for prearm checks, GPS and position telemetry")
    wait_until(vehicle, lambda: vehicle.is_armable() and vehicle.gps_ready(),
               config.READY_TIMEOUT, "prearm readiness and GPS")
    vehicle.set_mode("GUIDED")
    vehicle.arm()
    vehicle.takeoff(target_altitude)
    wait_until(vehicle, lambda: vehicle.altitude() >= target_altitude * 0.95,
               config.TAKEOFF_TIMEOUT, "takeoff altitude", guided=True)
    print("Reached %.2f m" % vehicle.altitude())


def hold(vehicle, seconds):
    started = ticks_ms()
    while ticks_diff(ticks_ms(), started) < seconds * 1000:
        ensure_guided(vehicle)
        vehicle.sleep(0.1)


def get_location_metres(origin, north, east, altitude):
    radius = 6378137.0
    scale = math.cos(math.radians(origin.lat))
    if abs(scale) < 1e-6:
        raise ValueError("Local GPS offsets are unsupported near the poles")
    lat = origin.lat + north / radius * 180 / math.pi
    lon = origin.lon + east / (radius * scale) * 180 / math.pi
    lon = (lon + 180) % 360 - 180
    return Location(lat, lon, altitude)


def distance_metres(first, second):
    north = math.radians(second.lat - first.lat) * 6378137.0
    delta_lon = (second.lon - first.lon + 180) % 360 - 180
    east = (math.radians(delta_lon) * 6378137.0
            * math.cos(math.radians((first.lat + second.lat) / 2)))
    return math.sqrt(north * north + east * east)


def goto_and_wait(vehicle, target):
    started = ticks_ms()
    last_sent = None
    while True:
        ensure_guided(vehicle)
        now = ticks_ms()
        if last_sent is None or ticks_diff(now, last_sent) >= 1000:
            vehicle.goto(target)
            last_sent = now
        current = vehicle.global_location()
        if (distance_metres(current, target) <= config.POSITION_TOLERANCE
                and abs(current.alt - target.alt) <= config.ALTITUDE_TOLERANCE):
            return
        if ticks_diff(now, started) >= config.WAYPOINT_TIMEOUT * 1000:
            raise RuntimeError("Timed out reaching GPS waypoint")
        vehicle.sleep(0.1)


def land_and_wait(vehicle):
    vehicle.set_mode("LAND")
    started = ticks_ms()
    while vehicle.armed():
        if vehicle.mode() != "LAND":
            raise MissionInterrupted("Landing stopped: pilot/autopilot changed mode")
        if ticks_diff(ticks_ms(), started) >= config.LAND_TIMEOUT * 1000:
            raise RuntimeError("Timed out waiting for landing and disarm")
        vehicle.sleep(0.1)


def run_mission(mission):
    vehicle = connect_to_pixhawk()
    started = False
    try:
        if vehicle.armed():
            raise RuntimeError("Refusing to start a new mission on an armed vehicle")
        started = True
        mission(vehicle)
    except BaseException as exc:
        print("Mission stopped:", exc)
        # Respect pilot mode changes. Link loss still needs autopilot failsafes.
        if started and not isinstance(exc, MissionInterrupted):
            try:
                if vehicle.armed() and vehicle.mode() == "GUIDED":
                    print("Requesting LAND after mission error")
                    land_and_wait(vehicle)
            except BaseException as landing_error:
                print("Could not confirm landing:", landing_error)
        raise
    finally:
        vehicle.close()
