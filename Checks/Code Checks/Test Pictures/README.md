`aruco-real-usb-frame.pgm` is a grayscale camera-only crop sampled from the user's
USB-viewer failure screenshot. It contains no page chrome or simulated marker.
The delivered JPEG orientation decodes 7x7 ID 0 with zero bit errors. Vertically
reflecting it, as the original worker incorrectly did for sensor `Flip=true`,
prevents decoding. Keep the default detector image transforms independent of
sensor register flags. The Windows host runner includes this fixture check.

Speed-regression fixtures:
- ov3660-color.jpg: saved sensor-jpeg-first.jpg from the actual OV3660 capture report.
- marker.jpg, marker-xga.jpg, marker-odd.jpg: JPEG encodings of the existing PGM marker image at 320x240, 1024x768 and 319x239, generated with the browser canvas encoder at quality 0.92. These test the decoder, not measured sensor performance.
- gray-16x16.jpg: independently constructed baseline one-component JPEG containing constant luma 128. A JPEG comment pads the valid tiny image above the decoder library minimum input size.
