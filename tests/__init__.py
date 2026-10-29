"""Host tests for Banshee; the device tree is the MicroPython import root."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "device"))
