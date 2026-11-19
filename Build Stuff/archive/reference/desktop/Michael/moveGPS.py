from dronekit import connect, VehicleMode, LocationGlobalRelative
import time
import math

# -------------------- CONNECT TO VEHICLE --------------------
#connection_string = 'tcp:127.0.0.1:5762'
#print("Connecting to vehicle...")
#vehicle = connect(connection_string, wait_ready=True)


def find_pixhawk_port():
    """Auto-detect the Pixhawk COM port on Windows."""
    ports = list(serial.tools.list_ports.comports())

    for port in ports:
        print(f"🔍 Checking: {port.device} - {port.description}")
        if any(keyword in port.description.upper() for keyword in ["PX4", "AUTERION", "FTDI", "SILICON", "USB"]):
            print(f"✅ Found Pixhawk: {port.device}")
            return port.device

    print("❌ No valid Pixhawk port found!")
    return None


# -------------------- DroneKit Connection --------------------

def connect_to_pixhawk():
    port = find_pixhawk_port()
    if not port:
        return None

    try:
        print(f"🔌 Connecting to {port} at 115200 baud...")
        vehicle = connect(port, wait_ready=True, baud=115200)
        print("✅ Connected to Pixhawk!")
        return vehicle
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return None

# -------------------- ARM AND TAKEOFF FUNCTION --------------------
def arm_and_takeoff(target_altitude):
    print("\nArming motors...")
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

    # Wait until the vehicle reaches target altitude
    while True:
        alt = vehicle.location.global_relative_frame.alt
        print(f" Altitude: {alt:.2f} m")
        if alt >= target_altitude * 0.95:
            print("Reached target altitude")
            break
        time.sleep(1)

# -------------------- CALCULATE RELATIVE GPS COORDINATE --------------------
def get_location_metres(original_location, dNorth, dEast, alt):
    """
    Returns a LocationGlobalRelative object moved dNorth and dEast metres from original_location.
    """
    earth_radius = 6378137.0  # radius of Earth in meters
    new_lat = original_location.lat + (dNorth / earth_radius) * (180 / math.pi)
    new_lon = original_location.lon + (dEast / (earth_radius * math.cos(math.pi * original_location.lat / 180))) * (180 / math.pi)
    return LocationGlobalRelative(new_lat, new_lon, alt)

# -------------------- MAIN SEQUENCE --------------------
if __name__ == "__main__":
    vehicle = connect_to_pixhawk()

    if not vehicle:
        print("❌ Could not connect to Pixhawk. Exiting...")
        exit()


    target_altitude = 1.5

# Takeoff
    arm_and_takeoff(target_altitude)
    time.sleep(10)

# Record home GPS location
    home_location = vehicle.location.global_frame
    print("\nHome location recorded:")
    print(f" Latitude: {home_location.lat}")
    print(f" Longitude: {home_location.lon}")
    print(f" Altitude: {home_location.alt}")

# Move 3 m North from home, stay at 1.5 m altitude
    target_location = get_location_metres(home_location, dNorth=3, dEast=0, alt=target_altitude)
    print("\nFlying 3 meters north of takeoff point...")
    vehicle.simple_goto(target_location)

# Hover for 10 seconds at new location
    time.sleep(10)

# Return to home position
print("Returning to home location...")
return_location = get_location_metres(home_location, dNorth=0, dEast=0, alt=target_altitude)
vehicle.simple_goto(return_location)
time.sleep(10)

# Land
print("Landing...")
vehicle.mode = VehicleMode("LAND")

# Wait until landed
while vehicle.armed:
    print(" Waiting for landing...")
    time.sleep(1)

print("Landed and disarmed.")
vehicle.close()
