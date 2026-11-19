from dronekit import connect, VehicleMode, LocationGlobalRelative
import time

# --- Connect to the Vehicle ---
print("Connecting to vehicle...")
vehicle = connect('tcp:127.0.0.1:5762', wait_ready=True)

# --- Connect to Pixhawk via USB cable ---
# connection_string = 'COM14'
# vehicle = connect(connection_string, baud=57600, wait_ready=True)

# --- Connect to Pi ---
# connection_string = '/dev/ttyAMA0'
# vehicle = connect(connection_string, baud=57600, wait_ready=True)

# --- Arm and Takeoff Function ---
def arm_and_takeoff(target_altitude):
    print("Arming motors")
    while not vehicle.is_armable:
        print(" Waiting for vehicle to initialize...")
        time.sleep(1)

    vehicle.mode = VehicleMode("GUIDED")
    vehicle.armed = True

    while not vehicle.armed:
        print(" Waiting for arming...")
        time.sleep(1)

    print("Taking off!")
    vehicle.simple_takeoff(target_altitude)

    # Wait until the vehicle reaches a safe height
    while True:
        alt = vehicle.location.global_relative_frame.alt
        print(f" Altitude: {alt:.2f} m")
        if alt >= target_altitude * 0.95:
            print("Reached target altitude")
            break
        time.sleep(1)

# --- Main Execution ---
target_altitude = 10  # meters
arm_and_takeoff(target_altitude)

print("Hovering for 10 seconds...")
time.sleep(10)

print("Landing...")
vehicle.mode = VehicleMode("LAND")

# Wait until disarmed
while vehicle.armed:
    print(" Waiting for landing...")
    time.sleep(1)

print("Landed and disarmed. Closing connection.")
vehicle.close()
