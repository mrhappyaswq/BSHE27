#pragma once

// Print exactly this payload in the QR marker, preserving case. Keep this in
// sync with CAMERA_TARGET_PAYLOAD on the MicroPython companion.
constexpr char TARGET_PAYLOAD[] = "BSHE27-LAND";

// Logical image top must point toward the nose; logical image right toward
// vehicle right. Inspect a saved photo before flight. A mirrored image is
// deliberately rejected by the QR decoder rather than reporting a wrong yaw.
constexpr bool CAMERA_HMIRROR = false;
constexpr bool CAMERA_VFLIP = false;
constexpr int IMAGE_WIDTH = 320;
constexpr int IMAGE_HEIGHT = 240;

constexpr int VISION_TX_PIN = 43;  // XIAO D6 -> WROOM GPIO16 (RX2)
constexpr int VISION_RX_PIN = 44;  // XIAO D7 <- WROOM GPIO17 (TX2)
constexpr unsigned long VISION_BAUD = 115200;

// XIAO Sense expansion board camera and microSD connections. The UART uses
// different pins, and the expansion-board microphone is not initialized.
constexpr int CAMERA_XCLK = 10;
constexpr int CAMERA_SDA = 40;
constexpr int CAMERA_SCL = 39;
constexpr int CAMERA_D0 = 15;
constexpr int CAMERA_D1 = 17;
constexpr int CAMERA_D2 = 18;
constexpr int CAMERA_D3 = 16;
constexpr int CAMERA_D4 = 14;
constexpr int CAMERA_D5 = 12;
constexpr int CAMERA_D6 = 11;
constexpr int CAMERA_D7 = 48;
constexpr int CAMERA_VSYNC = 38;
constexpr int CAMERA_HREF = 47;
constexpr int CAMERA_PCLK = 13;
constexpr int SD_SCK = 7;
constexpr int SD_MISO = 8;
constexpr int SD_MOSI = 9;
constexpr int SD_CS = 21;
