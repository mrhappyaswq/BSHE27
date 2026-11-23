`aruco-real-usb-frame.pgm` is a grayscale camera-only crop sampled from the user's
USB-viewer failure screenshot. It contains no page chrome or simulated marker.
The delivered JPEG orientation decodes 7x7 ID 0 with zero bit errors. Vertically
reflecting it, as the original worker incorrectly did for sensor `Flip=true`,
prevents decoding. Keep the default detector image transforms independent of
sensor register flags. The Windows host runner includes this fixture check.
