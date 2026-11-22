"""Keep the downloadable laptop viewer and firmware HTML byte-identical."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'firmware/goouuu_esp32_s3'
html=(root/'data/viewer.html').read_text(encoding='utf-8-sig')
(root/'include/dashboard_page.h').write_bytes(('#pragma once\n#include <Arduino.h>\nstatic const char CAMERA_PAGE[] PROGMEM=R"BSC_HTML('+html+')BSC_HTML";\n').encode('utf-8'))
