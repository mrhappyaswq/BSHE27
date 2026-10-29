import cv2
import cv2.aruco as aruco
import numpy as np

# Works on Pyton 3.9.0, OpenCV 4.7.0, and NumPy 1.25.2
# Generate Aruco Marker: https://chev.me/arucogen/

# --- TO INSTALL OPENCV AND NUMPY --- 
#   pip install opencv-contrib-python

# --- Camera calibration ---
camera_matrix = np.array([[600, 0, 320],
                          [0, 600, 240],
                          [0,   0,   1]], dtype=float)
dist_coeffs = np.zeros((5, 1))

# --- Webcam ---
cap = cv2.VideoCapture(0)

# --- ArUco dictionary ---
aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
params = aruco.DetectorParameters_create() if hasattr(aruco, 'DetectorParameters_create') else aruco.DetectorParameters()

marker_length = 0.04  # meters

while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    corners, ids, _ = aruco.detectMarkers(gray, aruco_dict, parameters=params)

    if ids is not None:
        aruco.drawDetectedMarkers(frame, corners, ids)

        rvecs, tvecs, _ = aruco.estimatePoseSingleMarkers(
            corners, marker_length, camera_matrix, dist_coeffs
        )

        for rvec, tvec, corner in zip(rvecs, tvecs, corners):
            rvec = np.array(rvec).reshape((3,1))
            tvec = np.array(tvec).reshape((3,1))

            # Draw 3D axes using correct Python function
            cv2.drawFrameAxes(frame, camera_matrix, dist_coeffs, rvec, tvec, 0.03)

            # Display coordinates
            x, y, z = tvec.flatten()
            text_pos = corner[0][0]
            cv2.putText(frame,
                        f"X:{x:.2f} Y:{y:.2f} Z:{z:.2f}",
                        (int(text_pos[0]), int(text_pos[1]-10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)

    cv2.imshow("Aruco Tracker", frame)
    if cv2.waitKey(1) & 0xFF == 27:  # ESC to quit
        break

cap.release()
cv2.destroyAllWindows()
