"""Board and mission settings. Verify these against your ESP32 and Pixhawk."""

# Match the existing WROOM Dev Board 32S telemetry monitor in main.py.
UART_ID = 1
UART_TX_PIN = 33
UART_RX_PIN = 32
UART_BAUDRATE = 57600

# This project implements ArduCopter GUIDED/LAND modes, not PX4 Offboard.
TARGET_SYSTEM = 1
TARGET_COMPONENT = 1
SOURCE_SYSTEM = 245
SOURCE_COMPONENT = 191

CONNECT_TIMEOUT = 10
COMMAND_TIMEOUT = 5
HEARTBEAT_TIMEOUT = 5
TELEMETRY_TIMEOUT = 3
READY_TIMEOUT = 60
TAKEOFF_TIMEOUT = 45
WAYPOINT_TIMEOUT = 60
LAND_TIMEOUT = 90
POSITION_TOLERANCE = 0.5
ALTITUDE_TOLERANCE = 0.3

LANDING_ALTITUDE = 0.2
MARKER_TIMEOUT = 5
MARKER_LANDING_TIMEOUT = 60
MARKER_KP = 0.002
MARKER_MAX_SPEED = 0.3
MARKER_DESCENT_SPEED = 0.05
MARKER_CENTER_TOLERANCE = 20  # Pixels; descent starts only inside this window.

# Downward camera contract: image top = vehicle forward, image right = right.
# Change these signs if your camera mounting/vision output uses different axes.
MARKER_FORWARD_SIGN = -1
MARKER_RIGHT_SIGN = 1

# XIAO ESP32-S3 Sense vision coprocessor, connected to the WROOM's second UART.
# Do not apply these pins to a WROVER (GPIO16/17 may be used by its PSRAM).
CAMERA_UART_ID = 2
CAMERA_UART_TX_PIN = 17  # -> XIAO D7 / GPIO44 (RX)
CAMERA_UART_RX_PIN = 16  # <- XIAO D6 / GPIO43 (TX)
CAMERA_UART_BAUDRATE = 115200
CAMERA_TARGET_PAYLOAD = "BSHE27-LAND"
CAMERA_MAX_AGE_MS = 350  # Age measured from request, including capture/decode.
CAMERA_REQUEST_TIMEOUT_MS = 1000
CAMERA_PREFLIGHT_TIMEOUT = 10

# QR mission works at QVGA; these pixel gains are independent of ArUco's.
QR_TAKEOFF_ALTITUDE = 1.5
QR_CENTER_TOLERANCE = 10
QR_KP = 0.002
QR_MAX_SPEED = 0.2
QR_YAW_KP = 0.8
QR_MAX_YAW_RATE = 0.35  # radians/s, positive clockwise about body down
QR_YAW_TOLERANCE_DEG = 5
QR_DESIRED_ANGLE_DEG = 0  # QR canonical top edge horizontal in camera image
QR_SETTLE_MS = 500
QR_SETTLE_FRAMES = 3  # Distinct captures; rereading one cached frame does not count.
