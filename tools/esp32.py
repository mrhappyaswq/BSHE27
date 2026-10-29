"""Desktop commands for the ESP32. Run from the project or use VS Code tasks."""

import argparse
from pathlib import Path
import shlex
import subprocess
import sys

PROJECT = Path(__file__).resolve().parents[1]


def runtime_files(project=PROJECT):
    """Return deployable Python files, preserving the board's package layout."""
    device = project / "device"
    files = [path for path in device.rglob("*.py")
             if not any(part.startswith(".") or part == "__pycache__"
                        for part in path.relative_to(device).parts)]
    if not (device / "main.py").is_file() or not (device / "config.py").is_file():
        raise RuntimeError("device/main.py and device/config.py are required")
    # Install boot code last, after its imports are present.
    return sorted(files, key=lambda path: (path.name == "main.py", path.as_posix()))


def upload_arguments(project=PROJECT, port="auto"):
    device = project / "device"
    files = runtime_files(project)
    directories = sorted({parent.as_posix()
                          for path in files
                          for parent in path.relative_to(device).parents
                          if parent != Path(".")}, key=lambda path: (path.count("/"), path))
    args = ["connect", port, "sleep", "2"]
    if directories:
        mkdir = ("import os\nfor path in " + repr(tuple(directories)) + ":\n"
                 " try:\n  os.mkdir(path)\n except OSError:\n"
                 "  if not os.stat(path)[0] & 0x4000:\n   raise\n")
        args += ["exec", mkdir, "+"]
    for source in files:
        relative = source.relative_to(device).as_posix()
        args += ["fs", "cp", str(source), ":" + relative, "+"]
    return args + ["reset"]


def command(action, port="auto", project=PROJECT):
    prefix = [sys.executable, "-m", "mpremote"]
    if action == "upload":
        return prefix + upload_arguments(project, port)
    if action == "list":
        return prefix + ["connect", "list"]
    if action == "monitor":
        return prefix + ["connect", port, "repl"]
    if action == "check":
        return prefix + ["connect", port, "sleep", "2", "run",
                         str(project / "device/diagnostics/telemetry.py")]
    raise ValueError("Unknown ESP32 command: " + action)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("upload", "check", "monitor", "list"))
    parser.add_argument("--port", default="auto", help="ESP32 USB port, such as COM4 (default: auto)")
    parser.add_argument("--dry-run", action="store_true", help="Show the command without connecting")
    args = parser.parse_args(argv)
    invocation = command(args.action, args.port)
    if args.dry_run:
        print(shlex.join(invocation))
        return 0
    try:
        subprocess.run(invocation, check=True, cwd=PROJECT)
    except subprocess.CalledProcessError as exc:
        return exc.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
