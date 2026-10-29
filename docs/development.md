# Development and tests

Run from the BM27 Banshee project root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v
```

Or use **Terminal → Run Task → BANSHEE: Run host tests**. Test discovery uses
`tests/` as a package so fixtures and imports work regardless of file order.

| Folder | Checks |
| --- | --- |
| `tests/unit/` | UART framing, heartbeat parser, telemetry freshness, command encoding, simulated missions, marker handling and upload layout |
| `tests/reference/` | Generated pymavlink interoperability |
| `tests/support/` | Independent wire frames, fake UART and simulated clock |

The six reference tests require the optional desktop dependency:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

They skip when pymavlink is unavailable. No host test opens flight hardware.
These tests do not validate physical wiring, camera behavior, ESP32 memory
use or flight performance; hardware and SITL verification remain necessary.

## Add or change code

1. Put board libraries in `device/banshee/`, flight entry points in
   `device/missions/`, or nonflight inspection tools in `device/diagnostics/`.
2. Use absolute imports such as `from banshee.flight import run_mission`.
3. Keep module imports free of flight side effects; use an explicit `main()`.
4. Place unit tests in `tests/unit/` and reusable fake hardware in `tests/support/`.
5. Run the host tests. Preview deployment with
   `.\.venv\Scripts\python.exe tools/esp32.py upload --dry-run`.

The uploader discovers package Python files automatically. Avoid putting
desktop dependencies in `device/`. Host tooling belongs in root `tools/`.

Original desktop examples and unrelated reports are preserved separately.
The preorganization snapshot and move manifest are under `local/archive/`.
Git metadata and the existing virtual environment remain at the project root.
