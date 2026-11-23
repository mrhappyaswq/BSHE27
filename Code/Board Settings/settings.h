#pragma once
#include <stdint.h>
namespace settings {
constexpr char Board[] = "GOOUUU ESP32-S3-CAM N16R8";
constexpr char Ssid[] = "BSHE27-Camera";
constexpr char Password[] = "password";
// Optional legacy b/g profile. Default retains the driver's b/g/n protocol set.
constexpr bool WifiCompatibility = false;
constexpr int Rx = 42, Tx = 41, Led = 48;
constexpr uint32_t Baud = 57600;
constexpr uint8_t System = 1, Component = 1, Source = 245, SourceComponent = 191;
constexpr uint32_t HeartbeatTimeout = 5000, TelemetryTimeout = 3000;
constexpr int Width = 320, Height = 240;
// Sensor JPEG scale: 0..63, lower means higher quality and larger transfers.
constexpr uint8_t JpegQuality = 20;
// Optional external SPI microSD. Disabled until wired/configured; these are
// free header pins, NOT an assumption about an onboard card socket.
constexpr bool SdEnabled = false;
constexpr int SdSck = 38, SdMiso = 39, SdMosi = 40, SdCs = 21;
constexpr bool Mirror = false, Flip = true;
constexpr bool freeHeader(int pin) {
  return pin==1 || pin==14 || pin==21 || pin==38 || pin==39 || pin==40 || pin==41 || pin==42 || pin==47;
}
static_assert(Rx!=Tx && freeHeader(Rx) && freeHeader(Tx),"UART conflicts with camera, memory, USB or reserved pins");
static_assert(!SdEnabled || (freeHeader(SdSck) && freeHeader(SdMiso) && freeHeader(SdMosi) && freeHeader(SdCs) &&
  SdSck!=Rx && SdSck!=Tx && SdMiso!=Rx && SdMiso!=Tx && SdMosi!=Rx && SdMosi!=Tx && SdCs!=Rx && SdCs!=Tx &&
  SdSck!=SdMiso && SdSck!=SdMosi && SdSck!=SdCs && SdMiso!=SdMosi && SdMiso!=SdCs && SdMosi!=SdCs),
  "SD pins conflict with UART, camera or reserved pins");
}
