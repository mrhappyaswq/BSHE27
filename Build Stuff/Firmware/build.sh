#!/usr/bin/env bash
# Build only. This script contains no erase, write-flash, deploy, or serial calls.
set -euo pipefail

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: bash build.sh [--prepare-only]"
  echo "Run in Linux/WSL2. Copies editable Sources to a fresh space-free build folder."
  echo "Then installs the S3 compiler environment if needed and builds camera-enabled MicroPython."
  echo "Never flashes. See Guides/Firmware Guide.md."
  exit 0
fi
if [[ "${1:-}" != "" && "${1:-}" != "--prepare-only" ]]; then
  echo "Unknown option: $1" >&2
  exit 2
fi
if [[ "$(uname -s)" != "Linux" ]]; then
  echo "Use Linux or WSL2 Ubuntu for ESP-IDF. Ordinary Windows Git Bash is not supported." >&2
  exit 2
fi
for command in python3 git make cmake ninja; do
  command -v "$command" >/dev/null || { echo "Missing tool: $command; see Firmware Guide." >&2; exit 2; }
done

WORK_ROOT="${BSHE_BUILD_ROOT:-$HOME/bshe27-firmware-builds}"
if [[ "$WORK_ROOT" == *" "* ]]; then
  echo "BSHE_BUILD_ROOT must not contain spaces (ESP-IDF limitation)." >&2
  exit 2
fi
mkdir -p -- "$WORK_ROOT"
WORK="$(mktemp -d "$WORK_ROOT/build-XXXXXXXX")"
python3 "$HERE/prepare_build.py" "$WORK"
echo "Prepared editable source snapshot at: $WORK"
if [[ "${1:-}" == "--prepare-only" ]]; then
  exit 0
fi

export IDF_PATH="$WORK/ESP-IDF"
# install.sh installs Espressif tools/Python dependencies in the user's tool
# cache. It does not connect to the board. First use requires internet access.
bash "$IDF_PATH/install.sh" esp32s3
source "$IDF_PATH/export.sh"
make -C "$WORK/MicroPython/mpy-cross" -j"$(nproc)"
cd "$WORK/MicroPython/ports/esp32"
idf.py -B build-BSHE27-S3 \
  -D MICROPY_BOARD=ESP32_GENERIC_S3 \
  -D MICROPY_BOARD_VARIANT=SPIRAM_OCT \
  -D "USER_C_MODULES=$WORK/Camera-API/micropython.cmake" \
  -D "ESP_JPEG_DIR=$WORK/Managed/esp_new_jpeg" \
  -D "EXTRA_COMPONENT_DIRS=$WORK/Camera-API" build
python3 makeimg.py \
  build-BSHE27-S3/sdkconfig \
  build-BSHE27-S3/bootloader/bootloader.bin \
  build-BSHE27-S3/partition_table/partition-table.bin \
  build-BSHE27-S3/micropython.bin \
  build-BSHE27-S3/firmware.bin \
  build-BSHE27-S3/micropython.uf2
echo "Built firmware: $PWD/build-BSHE27-S3/firmware.bin"
echo "No firmware was flashed. Your running board has not been changed."
