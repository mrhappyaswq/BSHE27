from dronekit import connect, VehicleMode, LocationGlobalRelative
import time
import cv2
import numpy as np
from pymavlink import mavutil
import os
import math
import serial.tools.list_ports


'''
# -------------------- CONNECT --------------------
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
'''

def find_pixhawk_port():
    """Find the Pixhawk's main MAVLink port via /dev/serial/by-id/ (Linux)."""
    serial_links = glob.glob('/dev/serial/by-id/*')

    for link in serial_links:
        if all(x in link for x in ["Pixhawk", "if00"]):  # Main MAVLink port
            real_path = os.path.realpath(link)
            print(f"✅ Found Pixhawk MAVLink port: {real_path}")
            return real_path

    print("❌ No valid Pixhawk MAVLink port found!")
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

# -------------------- SEND VELOCITY --------------------
def send_ned_velocity(vx, vy, vz, duration=0.1):
    msg = vehicle.message_factory.set_position_target_local_ned_encode(
        0, 0, 0,
        mavutil.mavlink.MAV_FRAME_BODY_NED,
        0b0000111111000111,
        0, 0, 0,
        vx, vy, vz,
        0, 0, 0,
        0, 0
    )
    vehicle.send_mavlink(msg)
    vehicle.flush()
    time.sleep(duration)

# -------------------- LANDING WITH ARUCO --------------------
def land_on_aruco():
    cap = cv2.VideoCapture(0)
    aruco_dict = cv2.aruco.Dictionary_get(cv2.aruco.DICT_4X4_50)
    parameters = cv2.aruco.DetectorParameters_create()

    kp = 0.002  # proportional gain for centering
    landing_altitude = 0.2

    print("Searching for ArUco marker...")

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = cv2.aruco.detectMarkers(gray, aruco_dict, parameters=parameters)

        if ids is not None:
            # Take first detected marker
            c = corners[0][0]
            cx = int(np.mean(c[:, 0]))
            cy = int(np.mean(c[:, 1]))

            height, width, _ = frame.shape
            dx = cx - width // 2
            dy = cy - height // 2

            # Convert pixel error to velocity
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

# -------------------- MAIN --------------------
if __name__ == "__main__":
    target_altitude = 1.5
    arm_and_takeoff(target_altitude)
    print("Hovering for 3 seconds...")
    time.sleep(3)

    print("Starting ArUco landing test...")
    land_on_aruco()

    while vehicle.armed:
        print(" Waiting for landing...")
        time.sleep(1)

    print("Landed and disarmed.")
    vehicle.close()
