# Camera speed changes

The board still captures sensor JPEGs. USB and Wi-Fi still receive the original JPEG; only the onboard analysis path changes. Camera pins, exposure controls, calibration values and flight commands are unchanged.

## Implemented

- JPEGDEC 1.8.2, pinned and vendored in Code/Third Party/JPEGDEC, decodes directly to 8-bit brightness. The detector no longer constructs RGB pixels and then converts them back to gray. Both color and one-component grayscale JPEGs are accepted.
- Analysis geometry and pose calculations use single-precision float math. Distortion inversion exits early when converged and skips work only when all distortion coefficients are zero.
- Adaptive thresholding uses rolling column sums with the same clipped 15x15 neighborhoods. The 309,444-byte full integral image is replaced by a 1,280-byte column buffer.
- A padded tracking region reduces search work while a marker is visible. A region miss retries the full image in the same analysis. Full-image refresh occurs at least every 500 ms; stale tracks and image-size changes force a full search.
- Search rejects obviously undersized connected shapes before sorting boundaries. Marker-cell intensity comparisons use integer sums. Rotation matching and projective sampling avoid unnecessary arithmetic.
- The worker processes fresh frames rather than waiting for a fixed 200 ms schedule. It yields for 2 ms between jobs and while waiting for a new frame, keeps only the latest camera frame, and never queues a detection backlog.
- Small/hot buffers and persistent decoder state prefer internal RAM, while preserving a 64 KiB free-internal-memory reserve at allocation time and falling back to PSRAM. The large queue and gray image stay in PSRAM.
- Application and source libraries use -O2 rather than -Os. Precompiled Arduino/ESP-IDF libraries retain their bundled configuration. No fast-math, overclocking or unsupported RAM clock changes are enabled.
- The existing viewer JSON and binary image framing are preserved, with additive stage timings and measured analysis rate. Viewer-only coordinate arithmetic uses float too.

The fixed buffers plus decoder consume about 517 KiB on ESP32-S3, compared with about 800 KiB of fixed vision buffers previously. Allocation overhead, camera JPEGs, results, task stacks and networking buffers are additional. Internal/external allocation totals are reported separately.

## What remains separate

The camera's grayscale visual effect is not enabled: making a JPEG look black and white does not establish that it has only one encoded component. Direct Y8 capture is an alternative architecture, not an additional switch that can be combined with this JPEG cache/viewer. Sensor capture remains JPEG to preserve the existing controls, profiles and viewers.

The onboard ArUco feature remains a preview. These changes do not connect it to flight missions, change the external marker input, increase flight-command rates, or arm/upload/start anything.

No measured ESP32 speedup is claimed from desktop tests. Wider caches and a custom ESP-IDF configuration would require rebuilding the bundled SDK and comparing hardware measurements; setting header macros alone would not configure the precompiled SDK correctly.

## Read the new measurements

The USB viewer shows:

| Display / JSON field | Meaning |
| --- | --- |
| processing_ms | Decoder plus detector, pose and result bookkeeping; excludes outgoing JSON and USB transfer |
| decode_ms | JPEG-to-grayscale decoding, including writing the gray buffer |
| prepare_ms | Histogram, threshold selection and threshold image construction |
| search_ms | Connected-shape traversal, rejection and square fitting |
| identify_ms | Marker cell sampling and ID verification |
| pose_ms | Camera calibration scaling and pose estimation |
| analysis_fps | Completed analyses per second, updated over approximately one-second windows |
| search_pixels | Total searched pixels, including same-frame full-search recovery |
| tracked_search | A tracking-region search was attempted; full recovery can occur in that same result |
| internal_workspace_bytes / external_workspace_bytes | Fixed buffers and persistent decoder state by memory type |

Stage timing uses wall clocks, so scheduling and memory stalls are included. Stage totals need not exactly equal processing_ms because bookkeeping is additional. Worker busy fraction is wall-processing duty over an elapsed window, not scheduler-measured CPU utilization. JSON formatting is outside these timings.

## Measure on the board

Build and upload using the normal instructions, then close the browser USB viewer and run:

    python "Helpers/Check ArUco Speed.py" --port COM10 --seconds 30

Replace COM10 with the native OTG serial port. The helper sends only the existing V video/vision request; it cannot issue flight commands. It requires the optional pyserial package listed in Python Packages.txt and refuses older firmware lacking pipeline_version 2.

It saves Saved Results/ArUco Speed.json, including raw samples and mean/p50/p95/p99/max stage times, grouped by visible/missing marker and tracked/full-image search. Run separate tests with a visible marker, clutter, marker loss, sudden motion, high-resolution profiles and Wi-Fi/USB load. Compare equal scenes, camera settings and lighting. Retain frame age and detection reliability alongside FPS.

The helper does not measure optical exposure-to-Pixhawk response time. USB receipt rate and analysis_fps are different measurements.

## Verification

C++ checks cover the exact rolling threshold against an independent neighborhood sum, all original marker rotations/reflection rejection/lighting tests, tracked coordinates, sudden jumps with same-frame recovery, loss, periodic scans, resolution changes, nonzero-distortion pose accuracy, actual metadata JSON, and direct grayscale decoding.

JPEG fixtures include a saved OV3660 color frame, marker JPEGs derived from the existing real-camera regression image, normal/XGA/odd dimensions, and an independently constructed one-component gray JPEG. Host checks also reject incomplete or mismatched inputs and verify full output coverage and configured mirror/flip parity. Native ESP32-S3 compilation includes the decoder and its supported S3 assembly routines.

Browser simulations cover the new stage readouts as well as existing frame matching, marker loss, stale HOLD, camera controls, profiles and reconnect behavior. These are computer-side checks, not hardware throughput or flight validation.
