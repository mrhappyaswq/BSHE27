# BSHE27 project rules for AI assistants

## Current owner decision (2026-11-23)

The active project is the existing **GOOUUU ESP32-S3-CAM N16R8 C++ application**, built with Arduino/PlatformIO. The owner explicitly selected this project to replace GitHub main. This supersedes the former MicroPython-only rules. Do not restore the XIAO design or the old Python application.

## Preserve the actual checkout

- Check Git status and configuration before editing. Preserve unrelated changes.
- Active folders are `Code/`, `Docs/`, `Helpers/` and `Checks/`, as documented in `README.md` and `Docs/Project Map.md`. Do not reorganize them to match the former MicroPython layout.
- `Code/main.cpp` is the entry point; `platformio.ini` is the build recipe. Preserve the GOOUUU N16R8 flash/PSRAM settings and explicit board pins.
- `Build Tools/` and `Saved Results/` are computer-only and ignored by Git.
- The retained `Build Stuff/`, `Guides/` and old Python paths in `Code/` are ignored local legacy material. Do not stage, delete or recursively scan their firmware trees for routine work.
- Original MicroPython rules are preserved in `Build Stuff/local/AGENTS-micropython-before-cpp-2026-11-23.md` for historical reference, not as current C++ requirements.
- Keep instructions in the existing `Docs/` guides and one short root README. Quote paths containing spaces.

## GitHub backup

- `origin` is https://github.com/mrhappyaswq/BSHE27.git.
- `main` is the active GOOUUU C++ branch and tracks `origin/main`.
- `deprecated/main-before-goouuu-2026-11-23` preserves the former GitHub main. Leave that reference intact.
- `feature/xiao-s3-qr-landing` is older work; do not use it as the upstream of active C++ development.
- Saving, committing and pushing are distinct steps. Do not claim GitHub is backed up until a push succeeds and the remote commit is verified.
- Preserve history; routine updates should not require force pushing. Do not upload generated tools, firmware caches or local results.

## Hardware and safety

- Pixhawk remains the flight controller. Boot, builds, uploads and dashboards must not incidentally arm, take off, change modes or start missions. Missions require explicit commands.
- Preserve pilot override, freshness checks and timeouts. Distinguish stale telemetry from current state.
- Keep camera and telemetry behavior intact during repository maintenance. Preserve the owner's Wi-Fi settings; do not print passwords in logs.
- The supplied external antenna is attached to this physical GOOUUU board. Do not assume software can change the RF selector.
- Do not flash or erase hardware as part of Git maintenance. Firmware replacement requires its own requested scope and a verified backup.
- Distinguish real ArUco detections, simulated inputs and mission inputs accurately.

## Verification and handoff

- Read `Docs/Editing and Testing.md` for current checks. Build-only is `GOOUUU: Build` / `pio run`; Ctrl+Shift+B builds AND uploads.
- For web edits, regenerate `Code/Web Server/dashboard_page.h` using `Helpers/Update Web Page.py` and preserve both files.
- Use relevant checks for code changes. Repository-only changes need Git/configuration verification, not an incidental hardware upload or flight mission.
- Report what changed, what was pushed, what was tested and any remaining limitations. Keep explanations practical and brief.
