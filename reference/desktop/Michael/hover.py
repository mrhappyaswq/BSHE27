from dronekit import connect, VehicleMode, LocationGlobalRelative
import time

# Connect to SITL
connection_string = 'tcp:127.0.0.1:5762'
vehicle = connect(connection_string, wait_ready=True)

print("Connected to vehicle")

# Change to GUIDED mode
print("Setting mode to GUIDED...")
vehicle.mode = VehicleMode("GUIDED")
while not vehicle.mode.name == 'GUIDED':
    print(" Waiting for mode change...")
    time.sleep(1)

# Arm the drone
print("Arming motors...")
vehicle.armed = True
while not vehicle.armed:
    print(" Waiting for arming...")
    time.sleep(1)

print("Taking off!")
target_altitude = 2
vehicle.simple_takeoff(target_altitude)

# Wait until the vehicle reaches the target altitude
while True:
    alt = vehicle.location.global_relative_frame.alt
    print(f"Altitude: {alt:.2f} m")
    if alt >= target_altitude * 0.95:
        print("Target altitude reached")
        break
    time.sleep(1)

# Hover for 5 seconds
time.sleep(5)

# Land
print("Landing...")
vehicle.mode = VehicleMode("LAND")

# Wait until it lands
while vehicle.armed:
    print(" Waiting for landing...")
    time.sleep(1)

print("Landed and disarmed.")
vehicle.close()
