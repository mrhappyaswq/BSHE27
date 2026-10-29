from dronekit import connect, VehicleMode, LocationGlobalRelative
import time, math

# --- CONNECT TO SITL ---
print("Connecting to vehicle...")
vehicle = connect('tcp:127.0.0.1:5762', wait_ready=True)

# --- ARM AND TAKEOFF FUNCTION ---
def arm_and_takeoff(target_altitude):
    """
    Arms vehicle and flies to target_altitude.
    """
    print("\nBasic pre-arm checks...")
    while not vehicle.is_armable:
        print(" Waiting for vehicle to initialize...")
        time.sleep(1)

    print("Arming motors...")
    vehicle.mode = VehicleMode("GUIDED")
    vehicle.armed = True

    # Wait until armed
    while not vehicle.armed:
        print(" Waiting for arming...")
        vehicle.armed = True  # force arm in SITL if needed
        time.sleep(1)

    print(f"Taking off to {target_altitude} meters...")
    vehicle.simple_takeoff(target_altitude)

    # Wait until the vehicle reaches target altitude
    while True:
        alt = vehicle.location.global_relative_frame.alt
        print(f" Altitude: {alt:.2f} m")
        if alt >= target_altitude * 0.95:
            print("Reached target altitude.")
            break
        time.sleep(1)

# --- FLY IN A CIRCLE FUNCTION ---
def fly_circle(center, radius, altitude):
    print(f"\nFlying one circle around home (radius={radius} m, altitude={altitude} m)...")
    steps = 36  # 10° increments
    for i in range(steps):
        angle = (i / steps) * 2 * math.pi
        dlat = (radius / 6378137) * (180 / math.pi)
        dlon = dlat / math.cos(math.radians(center.lat))
        target_lat = center.lat + dlat * math.cos(angle)
        target_lon = center.lon + dlon * math.sin(angle)
        point = LocationGlobalRelative(target_lat, target_lon, altitude)
        vehicle.simple_goto(point)
        time.sleep(1.5)
    print("Finished one full circle.")

# --- MAIN MISSION ---
try:
    arm_and_takeoff(10)

    # Record takeoff (home) location
    home = vehicle.location.global_relative_frame
    print(f"Home location: {home.lat:.6f}, {home.lon:.6f}")

    # Fly one circle around home
    fly_circle(home, radius=20, altitude=10)

    # Return to home point
    print("\nReturning to exact takeoff location...")
    vehicle.simple_goto(LocationGlobalRelative(home.lat, home.lon, 10))

    # Wait until close to home
    while True:
        current = vehicle.location.global_relative_frame
        dist = math.sqrt(
            (current.lat - home.lat)**2 + (current.lon - home.lon)**2
        ) * 1.113195e5
        print(f" Distance to home: {dist:.2f} m")
        if dist < 2:
            print("Reached takeoff location.")
            break
        time.sleep(1)

    # Land
    print("Landing...")
    vehicle.mode = VehicleMode("LAND")

    # Wait until disarmed
    while vehicle.armed:
        print(f" Altitude: {vehicle.location.global_relative_frame.alt:.2f} m")
        time.sleep(2)

    print("Landed successfully.")

finally:
    print("Closing vehicle connection...")
    vehicle.close()
