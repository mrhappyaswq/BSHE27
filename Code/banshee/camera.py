"""Onboard S3 camera; no WROOM, XIAO, or camera UART is used.

Capture uses cnadler86/micropython-camera-API (camera.Camera).
QR decoding is an optional local backend, separate from image capture.
"""

from banshee import status_led


import math
import config
from banshee.compat import sleep_ms, ticks_diff, ticks_ms


def _number(value):
    try:
        return (isinstance(value, (int, float)) and not isinstance(value, bool)
                and not math.isnan(value) and not math.isinf(value))
    except OverflowError:
        return False


@status_led.indicate("camera_init", "camera_ready")
def open_camera(grayscale=False):
    """Use explicit GOOUUU wiring rather than a firmware's board defaults."""
    config.validate_board()
    try:
        from camera import Camera, FrameSize, GrabMode, PixelFormat
    except ImportError:
        raise RuntimeError("Camera-enabled MicroPython with camera.Camera is required; see README.md")
    camera = Camera(
        data_pins=config.CAMERA_DATA_PINS,
        pclk_pin=config.CAMERA_PCLK_PIN,
        vsync_pin=config.CAMERA_VSYNC_PIN,
        href_pin=config.CAMERA_HREF_PIN,
        sda_pin=config.CAMERA_SDA_PIN,
        scl_pin=config.CAMERA_SCL_PIN,
        xclk_pin=config.CAMERA_XCLK_PIN,
        xclk_freq=config.CAMERA_XCLK_HZ,
        powerdown_pin=-1, reset_pin=-1,
        frame_size=FrameSize.QVGA,
        pixel_format=(PixelFormat.GRAYSCALE if grayscale else
                      PixelFormat.RGB565 if config.CAMERA_CAPTURE_MODE == "rgb565" else PixelFormat.JPEG),
        fb_count=1, grab_mode=GrabMode.WHEN_EMPTY,
        jpeg_quality=config.CAMERA_JPEG_QUALITY,
    )
    try:
        camera.hmirror = False
        camera.vflip = False
    except BaseException:
        camera.deinit()
        raise
    if not grayscale and config.CAMERA_CAPTURE_MODE == "rgb565":
        try:
            return EncodedCamera(camera)
        except BaseException:
            camera.deinit()
            raise
    return camera


class EncodedCamera:
    """Present captured RGB565 frames as JPEG using the native firmware codec."""

    def __init__(self, camera):
        self._camera = camera
        self._closed = False
        self.quality = config.CAMERA_JPEG_QUALITY
        self._encoder = self._make_encoder(self.quality)

    def _make_encoder(self, quality):
        import jpeg
        if type(quality) is not int or not 35 <= quality <= 90:
            raise ValueError("JPEG quality must be an integer from 35 to 90")
        return jpeg.Encoder(width=config.CAMERA_WIDTH, height=config.CAMERA_HEIGHT,
                            pixel_format=config.CAMERA_RGB565_FORMAT, quality=quality)

    def set_quality(self, quality):
        """Replace the codec only after its replacement was allocated successfully."""
        if self._closed:
            raise RuntimeError("Camera is closed")
        if type(quality) is not int or not 35 <= quality <= 90:
            raise ValueError("JPEG quality must be an integer from 35 to 90")
        if quality != self.quality:
            replacement = self._make_encoder(quality)
            previous, self._encoder = self._encoder, replacement
            self.quality = quality
            previous.__del__()

    async def capture_async(self, timeout_ms=1500):
        """Wait cooperatively for a frame before entering the native capture call.

        The native driver can block Python for seconds if a sensor stalls.
        Its frame_available() lets HTTP, UART and the button keep running while
        waiting. The native constructor and capture() both return their raw
        buffer before the next wait (there is only one native frame buffer).
        """
        import asyncio
        if self._closed:
            raise RuntimeError("Camera is closed")
        available = getattr(self._camera, "frame_available", None)
        if available is not None:
            started = ticks_ms()
            while not available():
                if ticks_diff(ticks_ms(), started) >= timeout_ms:
                    raise RuntimeError("Camera frame timed out")
                await asyncio.sleep(0.01)
        return self.capture()

    def capture(self):
        if self._closed:
            raise RuntimeError("Camera is closed")
        try:
            raw = self._camera.capture()
            if raw is None or len(raw) != config.CAMERA_WIDTH * config.CAMERA_HEIGHT * 2:
                raise ValueError("Expected a QVGA RGB565 camera frame")
            return self._encoder.encode(raw)
        finally:
            self._camera.free_buffer()

    def free_buffer(self):
        # capture() already returned the driver's raw buffer; JPEG owns its data.
        pass

    def deinit(self):
        if not self._closed:
            self._closed = True
            try:
                self._encoder.__del__()
            finally:
                self._camera.deinit()


def load_decoder():
    """Backend: decode(grayscale_bytes, width, height) -> iterable of markers.

    Each marker is {'payload': str, 'corners': [[x,y], ...]} in canonical
    QR TL/TR/BR/BL order. A backend must finish within CAMERA_MAX_AGE_MS.
    No desktop OpenCV, remote camera, or synthesized detections are used.
    """
    name = config.QR_DECODER_MODULE
    if not name:
        raise RuntimeError("QR landing unavailable: configure a local MicroPython QR decoder in config.py")
    module = __import__(name, None, None, ["decode"])
    decoder = getattr(module, "decode", None)
    if not callable(decoder):
        raise RuntimeError("Local QR decoder must provide decode(image, width, height)")
    return decoder


class LocalCamera:
    """Capture and decode on this S3. Injection is for host tests/backends."""

    def __init__(self, camera=None, decoder=None):
        # Missing decoding support must fail BEFORE allocating camera or arming.
        self._decode = load_decoder() if decoder is None else decoder
        self._camera = open_camera(grayscale=True) if camera is None else camera
        self._frame_id = 0
        self._closed = False
        self.last_error = None

    def marker(self, service=None):
        if self._closed:
            raise RuntimeError("Camera is closed")
        if service:
            service()
        started = ticks_ms()
        self.last_error = None
        try:
            # WHEN_EMPTY with one buffer may contain an old exposure. Release
            # it and wait for the next capture instead of relabeling it fresh.
            self._camera.capture()
            self._camera.free_buffer()
            image = self._camera.capture()
            try:
                if image is None or len(image) != config.CAMERA_WIDTH * config.CAMERA_HEIGHT:
                    raise ValueError("Expected a QVGA grayscale frame")
                matches = []
                for result in self._decode(image, config.CAMERA_WIDTH, config.CAMERA_HEIGHT):
                    if result.get("payload") == config.CAMERA_TARGET_PAYLOAD:
                        matches.append(result)
                        if len(matches) > 1:
                            raise ValueError("Multiple matching QR markers")
            finally:
                self._camera.free_buffer()
            if ticks_diff(ticks_ms(), started) > config.CAMERA_MAX_AGE_MS:
                raise RuntimeError("Local capture/decoder exceeded freshness limit")
            if not matches:
                status_led.set("qr_search")
                return None
            self._frame_id += 1
            marker = QRMarker({"id": self._frame_id, "width": config.CAMERA_WIDTH,
                             "height": config.CAMERA_HEIGHT, "marker": matches[0]},
                            config.CAMERA_TARGET_PAYLOAD)
            status_led.set("qr_found")
            return marker
        except (ValueError, TypeError, ZeroDivisionError) as exc:
            self.last_error = str(exc)
            status_led.set("qr_search")
            return None
        finally:
            if service:
                service()

    def wait_for_marker(self, timeout=None):
        timeout = config.CAMERA_PREFLIGHT_TIMEOUT if timeout is None else timeout
        status_led.set("qr_search")
        started = ticks_ms()
        count = 0
        while True:
            marker = self.marker()
            count = count + 1 if marker is not None else 0
            if count >= 3:
                return marker
            if ticks_diff(ticks_ms(), started) >= timeout * 1000:
                raise RuntimeError("No fresh landing QR detected: " + (self.last_error or "target not visible"))
            sleep_ms(20)

    def close(self):
        if not self._closed:
            self._closed = True
            self._camera.deinit()


class QRMarker:
    """Validated canonical corners; image top=forward, image right=right.

    Corners MUST be QR top-left, top-right, bottom-right, bottom-left from
    quirc, not corners sorted by screen position. Mirrored images are rejected.
    Yaw is an image-plane approximation, intended for a near-level camera.
    """

    def __init__(self, message, target_payload):
        self.frame_id = message.get("id")
        self.width = message.get("width")
        self.height = message.get("height")
        if (self.width, self.height) != (320, 240):
            raise ValueError("Expected camera QVGA image dimensions")
        marker = message.get("marker")
        if not isinstance(marker, dict) or marker.get("payload") != target_payload:
            raise ValueError("Unexpected QR payload")
        corners = marker.get("corners")
        if not isinstance(corners, list) or len(corners) != 4:
            raise ValueError("QR requires four canonical corners")
        for point in corners:
            if (not isinstance(point, list) or len(point) != 2
                    or not all(_number(value) for value in point)
                    or not 0 <= point[0] < self.width
                    or not 0 <= point[1] < self.height):
                raise ValueError("QR corner outside image or nonfinite")
        for i in range(4):
            a, b, c = corners[i], corners[(i + 1) % 4], corners[(i + 2) % 4]
            cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
            if cross < 16:
                raise ValueError("QR corners mirrored, too small or not convex")
        self.corners = corners
        # Diagonal intersection is the projective image of the square's center.
        a, b, c, d = corners
        ux, uy = c[0] - a[0], c[1] - a[1]
        vx, vy = d[0] - b[0], d[1] - b[1]
        denominator = ux * vy - uy * vx
        t = ((b[0] - a[0]) * vy - (b[1] - a[1]) * vx) / denominator
        self.cx, self.cy = a[0] + t * ux, a[1] + t * uy
        self.yaw = math.atan2((b[1] - a[1]) + (c[1] - d[1]),
                              (b[0] - a[0]) + (c[0] - d[0]))


