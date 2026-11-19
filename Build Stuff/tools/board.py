"""Desktop commands for the ESP32. Run from the project or use VS Code tasks."""

import argparse
import hashlib
from pathlib import Path
import shlex
import subprocess
import sys

PROJECT = Path(__file__).resolve().parents[2]


def runtime_files(project=PROJECT):
    """Return deployable Python and web assets, preserving the board's package layout."""
    device = project / "Code"
    files = [path for path in device.rglob("*")
             if path.is_file() and path.suffix in (".py", ".html", ".css", ".js")
             and not any(part.startswith(".") or part == "__pycache__"
                        for part in path.relative_to(device).parts)]
    if not (device / "main.py").is_file() or not (device / "config.py").is_file():
        raise RuntimeError("Code/main.py and Code/config.py are required")
    # Catch an incomplete edit before touching the working files on the board.
    for path in files:
        if path.suffix == ".py":
            compile(path.read_bytes(), str(path), "exec")
    # Install boot code last, after its imports are present.
    return sorted(files, key=lambda path: (path.name == "main.py", path.as_posix()))


def upload_arguments(project=PROJECT, port="auto"):
    device = project / "Code"
    files = runtime_files(project)
    directories = sorted({parent.as_posix()
                          for path in files
                          for parent in path.relative_to(device).parents
                          if parent != Path(".")}, key=lambda path: (path.count("/"), path))
    args = ["connect", port, "sleep", "2", "exec",
            "import os; assert 'ESP32S3' in os.uname().machine.upper().replace('-', ''), 'Expected ESP32-S3, not WROOM'", "+"]
    if directories:
        mkdir = ("import os\nfor path in " + repr(tuple(directories)) + ":\n"
                 " try:\n  os.mkdir(path)\n except OSError:\n"
                 "  if not os.stat(path)[0] & 0x4000:\n   raise\n")
        args += ["exec", mkdir, "+"]
    expected = []
    for source in files:
        relative = source.relative_to(device).as_posix()
        content = source.read_bytes()
        expected.append((relative, len(content), hashlib.sha256(content).hexdigest()))
        args += ["fs", "cp", str(source), ":" + relative + ".bshe-upload", "+"]
    # A failed transfer must not truncate the installed app. Check ALL staged
    # files before replacing any; rename each file atomically, main.py last.
    install = ("import os, hashlib, binascii\n"
               "_uploads = " + repr(tuple(expected)) + "\n"
               "for _path, _size, _digest in _uploads:\n"
               " _hash = hashlib.sha256()\n"
               " _count = 0\n"
               " with open(_path + '.bshe-upload', 'rb') as _file:\n"
               "  while True:\n"
               "   _chunk = _file.read(1024)\n"
               "   if not _chunk:\n    break\n"
               "   _count += len(_chunk)\n"
               "   _hash.update(_chunk)\n"
               " if _count != _size or binascii.hexlify(_hash.digest()).decode() != _digest:\n"
               "  raise RuntimeError('Upload verification failed: ' + _path)\n"
               "for _path, _size, _digest in _uploads:\n"
               " os.rename(_path + '.bshe-upload', _path)\n"
               "os.sync()\n"
               "print('Verified and installed %d runtime files; restarting dashboard' % len(_uploads))\n")
    return args + ["exec", install, "+", "reset"]


def command(action, port="auto", project=PROJECT):
    prefix = [sys.executable, "-m", "mpremote"]
    if action == "upload":
        return prefix + upload_arguments(project, port)
    if action == "list":
        return prefix + ["connect", "list"]
    if action == "monitor":
        return prefix + ["connect", port, "repl"]
    applications = {"camera": "apps.camera_web", "qr-check": "diagnostics.qr_camera", "led-test": "diagnostics.led"}
    if action in applications:
        return prefix + ["connect", port, "exec", "from " + applications[action] + " import main; main()"]
    if action == "check":
        return prefix + ["connect", port, "sleep", "2", "run",
                         str(project / "Code/diagnostics/telemetry.py")]
    raise ValueError("Unknown ESP32 command: " + action)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("upload", "check", "monitor", "list", "camera", "qr-check", "led-test"))
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
        if args.action != "list":
            print("Check the S3 COM port and close other monitors. The board must run MicroPython, not the archived Arduino firmware.", file=sys.stderr)
        return exc.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
