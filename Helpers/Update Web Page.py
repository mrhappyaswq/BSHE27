"""Copy the camera web page into the board program. Run after editing viewer.html."""
from pathlib import Path

project = Path(__file__).resolve().parents[1]
web = project / "Code" / "Web Server"
# Preserve the page's exact line endings so Git needs no special file rules.
html = (web / "viewer.html").read_bytes().decode("utf-8-sig")
header = '#pragma once\n#include <Arduino.h>\nstatic const char CAMERA_PAGE[] PROGMEM=R"BSC_HTML(' + html + ')BSC_HTML";\n'
(web / "dashboard_page.h").write_bytes(header.encode("utf-8"))
print("Updated Code/Web Server/dashboard_page.h")
