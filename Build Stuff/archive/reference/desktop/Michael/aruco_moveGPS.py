from dronekit import connect, VehicleMode, LocationGlobalRelative
import time
import math
import cv2
import numpy as np
from pymavlink import mavutil

# -------------------- CONNECT TO VEHICLE --------------------
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

# -------------------- ARM AND TAKEOFF --------------------
def arm_and_takeoff(target_altitude):
    print("Arming motors...")
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

    while True:
        alt = vehicle.location.global_relative_frame.alt
        print(f" Altitude: {alt:.2f} m")
        if alt >= target_altitude * 0.95:
            print("Reached target altitude")
            break
        time.sleep(1)

# -------------------- CALCULATE RELATIVE GPS COORDINATE --------------------
def get_location_metres(original_location, dNorth, dEast, alt):
    earth_radius = 6378137.0
    new_lat = original_location.lat + (dNorth / earth_radius) * (180 / math.pi)
    new_lon = original_location.lon + (dEast / (earth_radius * math.cos(math.pi * original_location.lat / 180))) * (180 / math.pi)
    return LocationGlobalRelative(new_lat, new_lon, alt)

# -------------------- SEND VELOCITY --------------------
def send_ned_velocity(vx, vy, vz, duration=1):
    msg = vehicle.message_factory.set_position_target_local_ned_encode(
        0, 0, 0,
        mavutil.mavlink.MAV_FRAME_BODY_NED,
        0b0000111111000111,  # bitmask: ignore pos, use velocity
        0, 0, 0,
        vx, vy, vz,
        0, 0, 0,
        0, 0
    )
    vehicle.send_mavlink(msg)
    vehicle.flush()
    time.sleep(duration)

# -------------------- LANDING WITH ARUCO CENTERING --------------------
def land_on_aruco():
    cap = cv2.VideoCapture(0)
    aruco_dict = cv2.aruco.Dictionary_get(cv2.aruco.DICT_7X7_50)
    parameters = cv2.aruco.DetectorParameters_create()

    kp = 0.002  # proportional gain for centering
    landing_altitude = 0.2

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = cv2.aruco.detectMarkers(gray, aruco_dict, parameters=parameters)

        if ids is not None:
            c = corners[0][0]
            cx = int(np.mean(c[:, 0]))
            cy = int(np.mean(c[:, 1]))

            height, width, _ = frame.shape
            dx = cx - width // 2
            dy = cy - height // 2

            vx = -dy * kp
            vy = -dx * kp
            vz = -0.05  # slow descent

            send_ned_velocity(vx, vy, vz, duration=0.1)

            alt = vehicle.location.global_relative_frame.alt
            print(f"Centering: dx={dx}, dy={dy}, alt={alt:.2f}")

            if alt <= landing_altitude:
                print("Reached landing altitude, switching to LAND mode")
                vehicle.mode = VehicleMode("LAND")
                break

        cv2.aruco.drawDetectedMarkers(frame, corners, ids)
        cv2.imshow("ArUco Landing", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

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

    # Return to home
    print("Returning to home location...")
    return_location = get_location_metres(home_location, dNorth=0, dEast=0, alt=target_altitude)
    vehicle.simple_goto(return_location)
    time.sleep(10)

    # -------------------- LAND WITH ARUCO CENTERING --------------------
    print("Landing while centering on ArUco marker...")
    land_on_aruco()

    while vehicle.armed:
        print(" Waiting for full landing...")
        time.sleep(1)

    print("Landed and disarmed.")
    vehicle.close()
