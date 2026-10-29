"""Vision integration hooks. No OpenCV or fabricated detections on the ESP32.

A downward camera/vision coprocessor must supply fresh coordinates. Register
providers from your own board-side startup script before calling a mission.
"""

import math

_marker_provider = None
_pose_provider = None


def set_marker_provider(provider):
    """provider() -> (cx, cy, image_width, image_height), or None when lost/stale.

    Pixel origin is top-left. Image top points forward and image right points
    right on the vehicle. Calls must be nonblocking and select one target ID.
    A provider receiving remote detections must expire old packets itself.
    """
    global _marker_provider
    if not callable(provider):
        raise ValueError("Marker provider must be callable")
    _marker_provider = provider


def require_marker_provider():
    if _marker_provider is None:
        raise RuntimeError("Register a camera provider with banshee.vision.set_marker_provider() first")


def marker_provider():
    require_marker_provider()
    marker = _marker_provider()
    if marker is None:
        return None
    if len(marker) != 4:
        raise ValueError("Marker must be (cx, cy, width, height)")
    cx, cy, width, height = marker
    if not all(not math.isnan(v) and not math.isinf(v) for v in marker):
        raise ValueError("Marker coordinates must be finite")
    if width <= 0 or height <= 0 or not 0 <= cx < width or not 0 <= cy < height:
        raise ValueError("Marker coordinates lie outside the image")
    return marker


def set_pose_provider(provider):
    """provider() -> iterable of (x, y, z) poses in metres; empty if none visible."""
    global _pose_provider
    if not callable(provider):
        raise ValueError("Pose provider must be callable")
    _pose_provider = provider


def require_pose_provider():
    if _pose_provider is None:
        raise RuntimeError("Register a camera provider with banshee.vision.set_pose_provider() first")


def pose_provider():
    require_pose_provider()
    return _pose_provider()
