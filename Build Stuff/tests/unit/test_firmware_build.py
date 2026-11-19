"""Check source-build preparation without a toolchain or copied vendor trees."""

import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch


FIRMWARE = Path(__file__).resolve().parents[2] / "Firmware"


class FirmwareBuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bshe-build-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        # The real helper rejects spaces because ESP-IDF cannot build there.
        # A compact fake kit exercises its actual copy and manifest behavior.
        self.kit = self.root / "kit"
        self.kit.mkdir()
        shutil.copyfile(FIRMWARE / "prepare_build.py", self.kit / "prepare_build.py")
        for name in ("MicroPython", "Camera-API", "ESP-IDF", "mp_jpeg", "Managed"):
            (self.kit / "Sources" / name).mkdir(parents=True)
        self.board_relative = Path("MicroPython/ports/esp32/boards/ESP32_GENERIC_S3")
        self.board = self.kit / "Sources" / self.board_relative
        self.board.mkdir(parents=True)
        self.variant = "set(SDKCONFIG_DEFAULTS boards/sdkconfig.base boards/sdkconfig.spiram_oct)\n"
        (self.board / "mpconfigvariant_SPIRAM_OCT.cmake").write_text(self.variant)
        for path in ("MicroPython/ports/esp32/main", "Managed/esp_new_jpeg",
                     "Managed/mdns", "Managed/tinyusb"):
            (self.kit / "Sources" / path).mkdir(parents=True, exist_ok=True)
        (self.kit / "Sources/Managed/esp_new_jpeg/include").mkdir()
        (self.kit / "Sources/Managed/esp_new_jpeg/include/esp_jpeg_common.h").write_text("// local codec\n")
        (self.kit / "Sources/Camera-API/edited.c").write_text("// owner's edit\n")
        (self.kit / "source-lock.json").write_text(json.dumps({"source_links": []}))
        spec = importlib.util.spec_from_file_location("test_firmware_prepare", self.kit / "prepare_build.py")
        self.helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.helper)

    def prepare(self):
        with patch.object(self.helper.subprocess, "run") as command:
            result = self.helper.prepare(self.root / "build")
        # Preparation only creates local Git metadata, never installs or flashes.
        self.assertTrue(command.call_args_list)
        self.assertTrue(all(call.args[0][0] == "git" for call in command.call_args_list))
        return result

    def test_preparation_preserves_edits_and_adds_16mb_after_octal_settings(self):
        build = self.prepare()
        self.assertEqual((build / "Camera-API/edited.c").read_text(), "// owner's edit\n")
        prepared = (build / self.board_relative / "mpconfigvariant_SPIRAM_OCT.cmake").read_text()
        self.assertTrue(prepared.startswith(self.variant))
        config_path = prepared.split("list(APPEND SDKCONFIG_DEFAULTS", 1)[1].split(")", 1)[0].strip()
        settings = (build / "MicroPython/ports/esp32" / config_path).read_text()
        self.assertIn("CONFIG_ESPTOOLPY_FLASHSIZE_16MB=y", settings)
        self.assertIn("# CONFIG_ESPTOOLPY_FLASHSIZE_4MB is not set", settings)
        # Retain the existing flash partition layout and PSRAM profile.
        self.assertNotIn("CONFIG_PARTITION_TABLE", settings)
        self.assertNotIn("CONFIG_SPIRAM", settings)
        self.assertEqual((self.board / "mpconfigvariant_SPIRAM_OCT.cmake").read_text(), self.variant)
        self.assertFalse((self.board / "sdkconfig.bshe27_n16r8").exists())

    def test_jpeg_include_directory_matches_the_local_component_override(self):
        build = self.prepare()
        manifest = json.loads((build / "Camera-API/idf_component.yml").read_text())
        codec = Path(manifest["dependencies"]["espressif/esp_new_jpeg"]["override_path"])
        script = (FIRMWARE / "build.sh").read_text()
        definition = next(line.strip().rstrip("\\").strip()
                          for line in script.splitlines() if '"ESP_JPEG_DIR=' in line)
        passed_path = definition.split("ESP_JPEG_DIR=", 1)[1].rstrip('"')
        self.assertEqual(Path(passed_path.replace("$WORK", str(build))), codec)
        self.assertTrue((codec / "include/esp_jpeg_common.h").is_file())

    def test_existing_build_output_is_never_overwritten(self):
        output = self.root / "build"
        output.mkdir()
        (output / "keep.txt").write_text("keep")
        with self.assertRaisesRegex(RuntimeError, "must be empty"):
            self.helper.prepare(output)
        self.assertEqual((output / "keep.txt").read_text(), "keep")
