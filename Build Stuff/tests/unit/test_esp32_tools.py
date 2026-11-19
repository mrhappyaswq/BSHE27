import contextlib
import builtins
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import board as esp32


class DeviceToolTests(unittest.TestCase):
    def test_upload_preserves_packages_and_filters_caches(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            for name in ("main.py", "config.py", "banshee/__init__.py",
                         "banshee/mavlink/__init__.py", "banshee/mavlink/vehicle.py",
                         "web/index.html", "__pycache__/junk.py", ".scratch/junk.py", "notes.txt"):
                path = project / "Code" / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("", encoding="utf-8")
            args = esp32.upload_arguments(project, "COM7")
            self.assertEqual(args[:4], ["connect", "COM7", "sleep", "2"])
            self.assertIn("ESP32S3", args[args.index("exec") + 1])
            destinations = [item for item in args if item.startswith(":")]
            self.assertEqual(len(destinations), 6)
            self.assertIn(":web/index.html.bshe-upload", destinations)
            self.assertIn(":banshee/mavlink/vehicle.py.bshe-upload", destinations)
            self.assertEqual(destinations[-1], ":main.py.bshe-upload")
            self.assertEqual(args[-1], "reset")
            self.assertNotIn("junk", " ".join(args))
            # Directory creation must work on first and subsequent uploads.
            prepare_dirs = next(args[i+1] for i, value in enumerate(args) if value == "exec" and "os.mkdir" in args[i+1])
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

    def test_syntax_error_is_caught_before_connecting(self):
        with tempfile.TemporaryDirectory() as directory:
            project=Path(directory)
            (project/'Code').mkdir()
            (project/'Code/main.py').write_text('def broken(',encoding='utf-8')
            (project/'Code/config.py').write_text('',encoding='utf-8')
            with self.assertRaises(SyntaxError):
                esp32.upload_arguments(project,'COM7')

    def test_staged_upload_is_verified_before_any_installed_file_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            project=Path(directory)
            (project/'Code').mkdir()
            contents={'config.py':'SETTING = 42\n','main.py':'print("ready")\n'}
            for name,content in contents.items():
                (project/'Code'/name).write_text(content,encoding='utf-8')
            args=esp32.upload_arguments(project,'COM7')
            install=next(args[i+1] for i,value in enumerate(args)
                         if value=='exec' and '_uploads =' in args[i+1])
            with tempfile.TemporaryDirectory() as remote:
                destination=Path(remote)
                renamed=[]
                class RemoteOS:
                    def rename(self,source,target):
                        renamed.append(target)
                        (destination/source).replace(destination/target)
                    def sync(self):
                        pass
                original_import=builtins.__import__
                def remote_import(name,*other):
                    return RemoteOS() if name=='os' else original_import(name,*other)
                def remote_open(name,*other,**kwargs):
                    return builtins.open(destination/name,*other,**kwargs)
                scope={'__builtins__':dict(vars(builtins),__import__=remote_import,open=remote_open)}
                for name,content in contents.items():
                    (destination/name).write_text('old installed file',encoding='utf-8')
                    (destination/(name+'.bshe-upload')).write_bytes((project/'Code'/name).read_bytes())
                (destination/'main.py.bshe-upload').write_text('truncated',encoding='utf-8')
                with self.assertRaisesRegex(RuntimeError,'verification failed'):
                    exec(install,scope)
                self.assertEqual(renamed,[])
                for name in contents:
                    self.assertEqual((destination/name).read_text(),'old installed file')
                (destination/'main.py.bshe-upload').write_bytes((project/'Code/main.py').read_bytes())
                with contextlib.redirect_stdout(io.StringIO()):
                    exec(install,scope)
                self.assertEqual(renamed,['config.py','main.py'])
                for name,content in contents.items():
                    self.assertEqual((destination/name).read_text(),content)

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
