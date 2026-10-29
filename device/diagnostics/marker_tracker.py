"""Print marker poses supplied by a camera/vision coprocessor; no flight control."""

from banshee.compat import sleep_ms
from banshee.vision import pose_provider as marker_provider, require_pose_provider


def draw_marker(marker):
    x, y, z = marker
    print("Marker X=%.2f Y=%.2f Z=%.2f" % (x, y, z))


def main():
    require_pose_provider()
    while True:
        for marker in marker_provider():
            draw_marker(marker)
        sleep_ms(50)


if __name__ == "__main__":
    main()
