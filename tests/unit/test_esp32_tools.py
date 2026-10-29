import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import esp32


class DeviceToolTests(unittest.TestCase):
    def test_upload_preserves_packages_and_filters_caches(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            for name in ("main.py", "config.py", "banshee/__init__.py",
                         "banshee/mavlink/__init__.py", "banshee/mavlink/vehicle.py",
                         "__pycache__/junk.py", ".scratch/junk.py", "notes.txt"):
                path = project / "device" / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("", encoding="utf-8")
            args = esp32.upload_arguments(project, "COM7")
            self.assertEqual(args[:4], ["connect", "COM7", "sleep", "2"])
            destinations = [item for item in args if item.startswith(":")]
            self.assertEqual(len(destinations), 5)
            self.assertIn(":banshee/mavlink/vehicle.py", destinations)
            self.assertEqual(destinations[-1], ":main.py")
            self.assertEqual(args[-1], "reset")
            self.assertNotIn("junk", " ".join(args))
            # Directory creation must work on first and subsequent uploads.
            prepare_dirs = args[args.index("exec") + 1]
            with tempfile.TemporaryDirectory() as remote:
                real_os = __import__("os")
                class RemoteOS:
                    def mkdir(self, path):
                        return real_os.mkdir(Path(remote) / path)
                    def stat(self, path):
                        return real_os.stat(Path(remote) / path)
                original_import = __import__
                def remote_import(name, *other):
                    return RemoteOS() if name == "os" else original_import(name, *other)
                scope = {"__builtins__": {"__import__": remote_import,
                                           "OSError": OSError}}
                exec(prepare_dirs, scope)
                exec(prepare_dirs, scope)
                self.assertTrue((Path(remote) / "banshee/mavlink").is_dir())

    def test_upload_requires_boot_and_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "required"):
                esp32.runtime_files(Path(directory))

    def test_check_runs_only_telemetry_diagnostic(self):
        args = esp32.command("check", "COM7")
        self.assertEqual(args[-2], "run")
        self.assertTrue(args[-1].endswith("telemetry.py"))
        self.assertNotIn("missions", " ".join(args))

    def test_dry_run_does_not_start_mpremote(self):
        with patch.object(esp32.subprocess, "run") as run:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(esp32.main(["upload", "--dry-run"]), 0)
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
