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
