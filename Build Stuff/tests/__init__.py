"""Host tests; desktop helpers and board imports live in separate folders."""
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "Build Stuff"))
sys.path.insert(0, str(PROJECT / "Code"))
