"""Single GOOUUU ESP32-S3-CAM N16R8 configuration. No WROOM required."""

# Auto-start camera + receive-only Pixhawk dashboard. "telemetry" is serial-only.
BOOT_APP = "camera"

BOARD_NAME = "GOOUUU ESP32-S3-CAM N16R8"
# UART1 leaves the TTL/USB console (GPIO43/44) available.
# Pixhawk TX -> S3 GPIO42 (RX); Pixhawk RX <- S3 GPIO41 (TX).
# These header pins are free with no external OLED/JTAG attached.
UART_ID = 1
UART_TX_PIN = 41
UART_RX_PIN = 42
UART_BAUDRATE = 57600
# Dashboard listens alongside video; never sends flight commands.
TELEMETRY_ENABLED = True

# Supplied camera: explicit wiring, not XIAO Sense defaults.
CAMERA_DATA_PINS = [11, 9, 8, 10, 12, 18, 17, 16]
CAMERA_SDA_PIN = 4
CAMERA_SCL_PIN = 5
CAMERA_XCLK_PIN = 15
CAMERA_VSYNC_PIN = 6
CAMERA_HREF_PIN = 7
CAMERA_PCLK_PIN = 13
CAMERA_XCLK_HZ = 20000000
CAMERA_WIDTH = 320
CAMERA_HEIGHT = 240
CAMERA_JPEG_QUALITY = 35
# Dashboard defaults; the webpage can change these until the next reset.
# Lower quality makes smaller JPEGs. This is an FPS ceiling, not a guarantee.
CAMERA_FPS_LIMIT = 1
# OV3660 direct-JPEG capture fails in Camera API 0.6.2. Capture color frames
# and use the firmware's native JPEG encoder instead (hardware-tested).
CAMERA_CAPTURE_MODE = "rgb565"
CAMERA_RGB565_FORMAT = "RGB565_BE"
CAMERA_TARGET_PAYLOAD = "BSHE27-LAND"
CAMERA_MAX_AGE_MS = 350
CAMERA_PREFLIGHT_TIMEOUT = 10
# Optional importable module implementing decode(image, width, height).
# Image capture firmware alone does not include a QR decoder.
QR_DECODER_MODULE = None

# Onboard WS2812 debug indicator. Timer0 is reserved for soft RGB updates.
RGB_ENABLED = True
RGB_PIN = 48
RGB_BRIGHTNESS = 0.08
RGB_TIMER_ID = 0
# Press/release BOOT after startup to mute/unmute the RGB indicator.
# GPIO0 is read as an input only; holding BOOT at reset still selects download mode.
RGB_BUTTON_ENABLED = True
RGB_BUTTON_PIN = 0
RGB_BUTTON_DEBOUNCE_MS = 50

# Phone compatibility: 3 = 802.11b/g; 7 also enables 802.11n.
# Keep WPA2 authentication; disabling radio power-save avoids sleep delays.
WIFI_PROTOCOL = 3
WIFI_POWER_MANAGEMENT = 0

WIFI_SSID = "BSHE27-Camera"
WIFI_PASSWORD = "password"


def validate_board():
    if RGB_BUTTON_ENABLED and (RGB_BUTTON_PIN != 0 or
            not isinstance(RGB_BUTTON_DEBOUNCE_MS, int) or
            not 20 <= RGB_BUTTON_DEBOUNCE_MS <= 1000):
        raise ValueError("RGB BOOT button requires input GPIO0 and 20..1000 ms debounce")
    camera_pins = CAMERA_DATA_PINS + [CAMERA_SDA_PIN, CAMERA_SCL_PIN,
        CAMERA_XCLK_PIN, CAMERA_VSYNC_PIN, CAMERA_HREF_PIN, CAMERA_PCLK_PIN]
    if RGB_ENABLED and RGB_PIN in (camera_pins + list(range(22, 38)) +
            [0, 2, 3, 19, 20, 43, 44, 45, 46, UART_TX_PIN, UART_RX_PIN]):
        raise ValueError("RGB pin conflicts with S3 camera, memory, USB or UART")
    # N16R8 memory, USB, boot strapping, console, user LED and RGB LED.
    reserved = [RGB_PIN] + camera_pins + list(range(22, 38)) + [0, 2, 3, 19, 20, 43, 44, 45, 46, 48]
    if (UART_TX_PIN == UART_RX_PIN or UART_TX_PIN in reserved or UART_RX_PIN in reserved
            or not 0 <= UART_TX_PIN <= 48 or not 0 <= UART_RX_PIN <= 48):
        raise ValueError("Pixhawk UART pins conflict with S3 camera, memory, USB or board functions")


def validate_runtime():
    from os import uname
    machine = uname().machine.upper().replace("-", "")
    if "ESP32S3" not in machine:
        raise RuntimeError("This configuration requires an ESP32-S3; do not upload to the old WROOM")
    validate_board()


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
