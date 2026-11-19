#!/usr/bin/env python3
import cv2 as cv
import numpy as np
import time, math
from pymavlink import mavutil

# --- User config ---
CAMERA_ID = 0
FRAME_W, FRAME_H = 1280, 720
ARUCO_DICT = cv.aruco.DICT_7X7_100
TAG_ID = 0
TAG_SIZE_M = 0.40  # marker side length in meters (used only if you want pose/xyz)
SERIAL_DEV = '/dev/ttyA0'  # Pixhawk TELEM port wired to Pi UART
BAUD = 57600                # or 57600 depending on your setup
USE_FULL_POSE = True        # True: send xyz + position_valid=1; False: angles-only

# --- Load calibration ---
fs = cv.FileStorage('camera.yaml', cv.FILE_STORAGE_READ)
K = fs.getNode('camera_matrix').mat()
D = fs.getNode('dist_coeffs').mat()
fs.release()

cam = cv.VideoCapture(CAMERA_ID)
cam.set(cv.CAP_PROP_FRAME_WIDTH, FRAME_W)
cam.set(cv.CAP_PROP_FRAME_HEIGHT, FRAME_H)
cam.set(cv.CAP_PROP_FPS, 60)

aruco = cv.aruco
dict_ = aruco.getPredefinedDictionary(ARUCO_DICT)
params = aruco.DetectorParameters()
detector = aruco.ArucoDetector(dict_, params)

# MAVLink connection
m = mavutil.mavlink_connection(SERIAL_DEV, baud=BAUD)
# Wait for heartbeat so target system/component IDs are known (optional but helpful)
try:
    m.wait_heartbeat(timeout=5)
except Exception:
    pass  # continue anyway

def center_from_corners(corners):
    # corners: (4,1,2) or similar; flatten:
    pts = corners.reshape(-1, 2)
    c = pts.mean(axis=0)
    return float(c[0]), float(c[1])

fx, fy = K[0,0], K[1,1]
cx, cy = K[0,2], K[1,2]

rate_hz = 20.0 #set loop frequency
period = 1.0 / rate_hz
next_t = time.time()

rvecs = None
tvecs = None

while True:
    ok, frame = cam.read()
    if not ok: 
        time.sleep(0.01)
        continue

    # Detect ArUco markers
    corners, ids, _ = detector.detectMarkers(frame)
    if ids is not None and TAG_ID in ids.flatten():
        idx = np.where(ids.flatten() == TAG_ID)[0][0]
        marker_corners = corners[idx]

        # --- Compute angles relative to optical axis ---
        u, v = center_from_corners(marker_corners)
        # Small-angle exact form:
        angle_x = math.atan2((u - cx) / fx, 1.0)
        angle_y = math.atan2((v - cy) / fy, 1.0)

        # Optional: full pose to get body-frame xyz from camera frame
        x_b = y_b = z_b = 0.0
        position_valid = 0
        distance_m = 0.0
        if USE_FULL_POSE:
            obj_pts = np.array([
                [-TAG_SIZE_M/2,  TAG_SIZE_M/2, 0],
                [ TAG_SIZE_M/2,  TAG_SIZE_M/2, 0],
                [ TAG_SIZE_M/2, -TAG_SIZE_M/2, 0],
                [-TAG_SIZE_M/2, -TAG_SIZE_M/2, 0],
            ], dtype=np.float32)
            img_pts = marker_corners.reshape(-1,2).astype(np.float32)
            okp, rvec, tvec = cv.solvePnP(obj_pts, img_pts, K, D, flags=cv.SOLVEPNP_IPPE_SQUARE)
            if okp:
                # Camera frame: x right, y down, z forward
                # Convert to BODY(NED): x forward, y right, z down
                # Approximate mapping: x_b =  tvec[2]; y_b =  tvec[0]; z_b =  tvec[1]
                x_b = float(tvec[2])
                y_b = float(tvec[0])
                z_b = float(tvec[1])
                position_valid = 1

                # Use vision-derived range (no rangefinder)
                distance_m = math.sqrt(x_b*x_b + y_b*y_b + z_b*z_b)

                # Re-derive angles from tvec for consistency
                angle_x = math.atan2(y_b, x_b)  # body: forward=x_b, right=y_b
                angle_y = math.atan2(z_b, x_b)  # body: down=z_b, forward=x_b

        # Throttle to target rate
        tnow = time.time()
        if tnow >= next_t:
            next_t += period

            # LANDING_TARGET send (MAVLink2 fields via keyword args are supported by pymavlink)
            m.mav.landing_target_send(
                int(tnow * 1e6),        # time_usec
                0,                      # target_num
                mavutil.mavlink.MAV_FRAME_BODY_NED,
                float(angle_x), float(angle_y),
                float(distance_m),      # distance (vision-derived; no rangefinder)
                TAG_SIZE_M, TAG_SIZE_M, # size_x, size_y
                x_b, y_b, z_b,          # position in body frame (if available)
                [1.0, 0.0, 0.0, 0.0],   # orientation (unused here)
                mavutil.mavlink.LANDING_TARGET_TYPE_VISION_FIDUCIAL,
                position_valid
            )

    #Optional visualization for bench testing:
    aruco.drawDetectedMarkers(frame, corners, ids)
    cv.imshow("landing", frame)
    if cv.waitKey(1) == 27:
        break
