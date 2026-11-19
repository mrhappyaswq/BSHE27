import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import Mock, patch
import config


class BootTests(unittest.TestCase):
    def setUp(self):
        path=Path(__file__).resolve().parents[3]/'Code/main.py'
        spec=importlib.util.spec_from_file_location('bshe_boot_router',path)
        self.router=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.router)

    def run_mode(self,mode):
        camera,telemetry=Mock(),Mock()
        with patch.object(config,'validate_runtime') as validate, patch.object(config,'BOOT_APP',mode), patch.dict(sys.modules,{
            'apps.camera_web':SimpleNamespace(main=camera),
            'diagnostics.boot_telemetry':SimpleNamespace(main=telemetry)}):
            self.router.main()
            validate.assert_called_once()
        return camera,telemetry

    def test_default_boot_starts_camera_wifi_without_mission(self):
        self.assertEqual(config.BOOT_APP,'camera')
        camera,telemetry=self.run_mode('camera')
        camera.assert_called_once()
        telemetry.assert_not_called()

    def test_explicit_telemetry_option_preserves_old_monitor(self):
        camera,telemetry=self.run_mode('telemetry')
        telemetry.assert_called_once()
        camera.assert_not_called()

    def test_boot_cannot_be_used_to_launch_a_mission(self):
        with self.assertRaisesRegex(ValueError,'never starts a mission'):
            self.run_mode('missions.hover')
