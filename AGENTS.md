# BSHE27 project rules for AI assistants

These rules record the owner's decisions from the project conversations. Apply
them throughout this repository. Follow newer explicit user instructions when
they change a decision, and update this file and the affected guides together.
Preserve unrelated work in this checkout; do not undo existing changes to make
your task easier. Check the actual checkout and configuration before editing.

## Project direction

- The active hardware is **one GOOUUU ESP32-S3-CAM N16R8**, replacing the old
  ESP32-WROOM. It uses its onboard camera and talks to a Pixhawk running
  ArduCopter. Do not restore a two-ESP32 or XIAO camera design by accident.
- The active application is **MicroPython only**. The owner wants to explore
  C++ combinations later. Keep Arduino, PlatformIO and old C++ experiments in
  the archive unless the owner explicitly changes this direction. Native C/C++
  inside the MicroPython interpreter and camera driver is firmware source,
  not a request to convert the application to C++.
- Keep the working camera integrated with Wi-Fi and passive Pixhawk monitoring.
  A missing Pixhawk must not prevent live video. A camera fault must not prevent
  the hotspot, status page or telemetry monitor from working.
- Pixhawk is the flight controller. Boot, upload and the dashboard never arm,
  take off, change flight mode or start a mission. Missions remain explicit
  programs. Stop the dashboard before a mission takes exclusive ownership of
  UART1 and/or the camera. Preserve pilot override, freshness and timeout checks.
- QR/ArUco detection is separate from image capture. Do not claim a decoder is
  installed or supply fake detections. Currently QR needs a local decoder and
  ArUco needs a registered provider.

## Keep the file structure simple

Use these three main folders, with their exact names:

```text
Code/          Actual MicroPython application, configuration and web assets
Build Stuff/   Tools, tests, firmware sources/images, archives and local backups
Guides/        Only the supporting instructions and diagrams the owner needs
```

- Put code the owner edits under `Code/`: `apps/`, `banshee/`, `web/`,
  `diagnostics/`, `missions/`, `config.py` and `main.py`.
- Put computer-side tools in `Build Stuff/tools/`, tests in `Build Stuff/tests/`,
  firmware material in `Build Stuff/Firmware/`, legacy work in
  `Build Stuff/archive/`, and ignored machine-local files/backups in
  `Build Stuff/local/`.
- Keep one short root `README.md` as the entry point. Keep this `AGENTS.md` at
  the root so assistants can find it. `.vscode/`, `.venv/`, Git metadata and the
  workspace file may remain at the root for tooling compatibility.
- Reuse `Guides/Setup.md`, `Guides/LED Guide.md`, `Guides/Code Map.md` and
  `Guides/Firmware Guide.md`. Do not create more READMEs, duplicate instructions,
  temporary reports or top-level documentation trees for ordinary changes.
- Preserve older work in the archive rather than silently deleting it. Do not
  treat a leftover legacy folder as active application code.
- Only deploy the Python and web runtime assets selected from `Code/` by the
  uploader. `Code/main.py` becomes `/main.py` on the board; `Build Stuff/`,
  `Guides/` and this file stay on the computer.
- Quote paths containing spaces and update imports, uploader paths, VS Code
  tasks and guide links when moving files. Avoid scanning the huge vendored
  firmware trees when a search can be limited to application code or guides.

## RGB LED conventions

- The onboard programmable **RGB LED is the debugging indicator**. It is GPIO48,
  separate from the power/USB lights. Current settings are brightness `0.08`,
  Timer0 and a 50 ms soft callback; keep settings in `Code/config.py` and
  behavior in `Code/banshee/status_led.py`.
- Use single-color groups of one, two or three 180 ms blinks, separated by
  180 ms gaps, followed by a 1200 ms dark pause. Each color/count is unique.
  The owner replaced the former two-color patterns because reversed pairs
  were indistinguishable. Preserve counted blinks, mute and state priority.
- A short BOOT press after startup toggles the RGB indicator without stopping
  monitoring or losing the logical state. GPIO0 is input-only, debounced through
  the existing soft timer and toggles once per press; require release after
  startup. Reset restores `RGB_ENABLED`. Holding BOOT during reset retains its
  download-mode function. Keep button settings in `Code/config.py`.
- Distinguish hotspot broadcasting, a Wi-Fi device joined, camera ready/fault,
  live streaming, Pixhawk connected and a previously connected Pixhawk lost.
  A phone joining Wi-Fi is not evidence that Pixhawk or the camera is healthy.
- Preserve these meanings and timings unless the owner requests a change.
  The tables below describe the current baseline; executable definitions remain
  in `status_led.py`. Keep code, the LED guide and the README legend consistent.

The executable baseline is `PATTERNS` in `Code/banshee/status_led.py`;
the complete color/count table is in `Guides/LED Guide.md`.

- Dashboard priority: **Wi-Fi down → camera fault → UART error → lost Pixhawk
  heartbeat → streaming → connected/idle Wi-Fi**. Show all subsystem states on
  the webpage even when the LED displays a higher priority condition.
- Waiting means no valid target heartbeat yet. Lost means a previously seen
  target heartbeat expired, currently after five seconds. Do not show link loss
  simply because an unplugged Pixhawk has never connected.
- Stable streaming blink groups must retain their phase. Repeatedly setting the same
  state must preserve its phase; do not restart a capture pulse on every frame.
  Activity overlays must not hide persistent faults.
- LED updates must not block video, telemetry or flight operations. Contain
  indicator driver failures and release timers/hardware cleanly on shutdown.
- When behavior introduces a meaningful new debug state, update the indicator
  and its guide together. Do not arbitrarily reassign existing colors.

## Readable documentation and visual code map

- Write for an owner who is learning microcontrollers. Explain what a file or
  function does and what to edit using clear, practical language.
- The owner wants **visible colors in the README and LED guide**, not just
  color names. Use the existing colored SVG labels with standard Markdown image
  syntax, for example `![Cyan](Guides/assets/led/cyan.svg)` in the root README.
  In `Guides/LED Guide.md`, use `assets/led/cyan.svg`. Include text alternatives.
  Raw HTML `<img>`/`<span>` previously displayed as literal text in their
  preview, so do not reintroduce it as the color-rendering solution.
- Maintain the **visual block diagram** in `Guides/assets/code-map.svg` and
  the function reference in `Guides/Code Map.md`. Show which services run
  together, the main functions, data flow and manually started mission path.
  Keep the README diagram link working as the architecture changes.
- Keep status messages accurate: distinguish camera initialization, capture
  errors, stream transport failures, Wi-Fi association and Pixhawk heartbeat.
  Do not label a frozen last frame as healthy live video.

## Protect the working camera and dashboard

The following is the tested baseline, not a reason to resist a later requested
hardware or firmware change. Verify it before changing drivers or pin mappings.

- S3 has 16 MB flash and 8 MB octal PSRAM. Camera-enabled MicroPython v1.27.0 /
  Camera API v0.6.2, generic S3 **SPIRAM_OCT**, is installed. The stock
  interpreter previously lacked `camera.Camera` and used an unsuitable PSRAM
  configuration. Do not accidentally replace the working image with stock or
  quad-PSRAM firmware.
- Sensor is **OV3660**. Direct JPEG failed with this driver. The working path
  captures **320×240 RGB565** and uses native `jpeg.Encoder` with `RGB565_BE`,
  default quality 35. The webpage can set JPEG quality 35–90 and an FPS ceiling
  of 1–15 until reset; boot defaults are `CAMERA_JPEG_QUALITY` and
  `CAMERA_FPS_LIMIT`. Keep QVGA resolution fixed and describe actual FPS honestly.
  Keep raw frame ownership/release and encoder cleanup correct.
  The grayscale QR path is separate. Do not switch the live camera back to
  direct JPEG without validating it on this hardware.
- Camera pins: data `[11, 9, 8, 10, 12, 18, 17, 16]`, SDA4, SCL5, XCLK15,
  VSYNC6, HREF7 and PCLK13; XCLK is 20 MHz. Use explicit board wiring.
  Respect config validation and reserved flash/PSRAM, USB and boot pins.
- `BOOT_APP = "camera"` starts the integrated dashboard automatically.
  `BOOT_APP = "telemetry"` is the optional serial-only diagnostic.
- Preserve the owner's current Wi-Fi name and password in `Code/config.py`.
  The hotspot is `BSHE27-Camera`, visible on 2.4 GHz channel 1, with the page
  at `http://192.168.4.1/`. Start the hotspot and HTTP listener before camera
  initialization; expose an initializing state before camera readiness/fault.
  On 2026-11-19 the owner connected the supplied external antenna and confirmed
  that the dashboard and camera image worked. Keep that antenna attached for
  this physical board; do not revert to the earlier onboard-antenna assumption.
  The actual RF-selector position was not inspected. Software cannot move it.
- Preserve `/`, `/status`, `/stream` (MJPEG) and `/capture` (JPEG snapshot).
  Live view starts automatically; Start/Stop and snapshots remain available.
  Preserve validated runtime quality/FPS changes through `POST /settings`.
  The current server supports one MJPEG viewer at a time; a new stream releases
  the previous one. Other auto-reconnecting tabs should be closed.
- Preserve automatic recovery from a closed or stalled stream and Wi-Fi loss.
  A deliberate Stop must remain paused. Status requests are bounded and must
  not accumulate. Current baseline: 5 s status timeout, 8 s watchdog based on
  frames decoded by the browser, 1–5 s reconnect backoff, 5 s total-frame write
  timeout and at most three consecutive capture attempts before ending a failed
  stream. Server frame counters alone cannot prove that a browser is progressing.
- Release a blocked/disconnected viewer so another stream can start. Record
  network write/disconnect errors separately from camera capture errors.
  Brief capture failures should be retried, not permanently stop live view.
- UART1: S3 RX GPIO42 receives Pixhawk TX; S3 TX GPIO41; 57600 baud;
  configured target IDs are system1/component1. The dashboard monitor is
  **receive only** and uses bounded cooperative polling with an 8192-byte RX
  buffer. Keep video, status requests, snapshots and telemetry cooperative.
- Validate target heartbeats and CRC. Report heartbeat age, armed/disarmed
  state and numeric mode. When heartbeat data expires, armed/mode must become
  unknown rather than continuing to present stale values as current.

## Firmware source ownership and deployment

- The owner wants access to the firmware source so they can change it later.
  Keep the source kit, licenses, pinned versions/manifests, images and future
  build helpers under `Build Stuff/Firmware/`. Document any unavailable source
  or binary-only vendor portions honestly.
- Distinguish editing/uploading `Code/*.py` from rebuilding and reflashing the
  native interpreter/driver image. Explain that distinction when relevant.
- Routine application and LED/web changes should use normal uploads. Keeping
  firmware source in the repository does not by itself authorize erasing the
  board or reflashing. Treat firmware replacement as a separate action within
  the user's requested scope; explain erasure and preserve a verified backup
  before a replacement. Do not add confirmation gates to ordinary authorized
  code, documentation or reversible fixes.
- Preserve full-flash backups under `Build Stuff/local/board-backups/`, outside
  the deployable files. Build helpers must not silently flash a board.
- Do not claim vendored sources were built successfully or reproduce an
  upstream binary exactly unless that was actually verified.
- The Linux build helper retains `ESP32_GENERIC_S3 + SPIRAM_OCT`, adds the N16R8
  16 MB flash override only to the disposable build copy, and passes
  `ESP_JPEG_DIR` to the same local JPEG component selected by its manifest.
  Preserve these settings and the original source snapshots.
- Ordinary uploads check Python syntax, stage all runtime files and verify
  size/SHA-256 before installing with `main.py` last and resetting. Failed
  transfer/verification must leave installed files intact. This is not a fully
  transactional deployment: power loss during the final commit can leave mixed
  versions and requires another upload.

## Verification and handoff

- Use the existing computer environment and tools. Typical commands from the
  project root, in PowerShell:

  ```powershell
  & '.venv/Scripts/python.exe' -B -m unittest discover -s 'Build Stuff/tests' -t 'Build Stuff'
  node 'Build Stuff/tests/ui/test_camera_page.js'
  & '.venv/Scripts/python.exe' 'Build Stuff/tools/board.py' list
  & '.venv/Scripts/python.exe' 'Build Stuff/tools/board.py' upload --port COM4
  ```

- Discover the board port rather than assuming COM4 is permanent. Avoid
  competing serial monitors. A physical test must use the S3, not old WROOM.
- For video/telemetry/recovery changes, use meaningful regression checks for
  the affected behavior. When hardware is available and testing is authorized,
  verify sustained streaming, concurrent status/snapshot/telemetry, and recovery
  from a stalled viewer. The prior working endurance check was **650 frames
  over more than two minutes**; a few frames alone cannot establish stability.
- After a board test, restore the normal integrated startup and release the
  serial connection. Never run a flight mission as an incidental smoke test.
- Report what was changed, whether it was uploaded, what was actually tested,
  and any important unverified behavior. Distinguish host simulations and
  on-board loopback tests from an actual browser-over-Wi-Fi test; do not claim
  the owner's exact freeze was reproduced if it was not.
- Prefer doing the requested work to giving the owner a long plan. Keep final
  explanations short and practical, including a page refresh when web assets
  changed. Update these rules when the owner changes project preferences.

- Hotspot discovery uses bounded local DNS and redirects common phone portal
  probes. Keep HTTP available before camera initialization, which is triggered
  by the first camera/status request. Do not claim radio tests from loopback alone.

- The browser preview uses complete JPEG requests, serializing frame transfers
  with status polling. Preserve the raw MJPEG API, explicit Stop and recovery.
  Report rendering errors separately from network/status failures. Successful
  snapshot responses keep the live-preview LED active for three seconds.

- The owner confirmed images after connecting the antenna, but the original
  high-throughput profile still reconnected. The driver logged CCMP replay
  rejections. Keep the compatibility baseline: Wi-Fi b/g (protocol 3), no radio
  power-save, paced 192-byte TCP writes with TCP_NODELAY, JPEG quality 35 and
  1 FPS ceiling. Keep WPA2 and the owner's credentials. Quality/FPS remain
  adjustable; test real phone-over-Wi-Fi stability before increasing defaults.
