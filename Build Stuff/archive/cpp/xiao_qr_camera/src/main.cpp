// XIAO camera coprocessor only. This firmware never sends flight commands.
#include <Arduino.h>
#include <ArduinoJson.h>
#include <FS.h>
#include <SD.h>
#include <SPI.h>
#include <ctype.h>
#include <stdlib.h>
#include <string.h>
#include <esp_camera.h>
#include <img_converters.h>
#include <esp_timer.h>
#include <quirc.h>

#include "camera_settings.h"

namespace {
HardwareSerial vision(1);
struct quirc *recognizer = nullptr;
// Keep large quirc structures off the Arduino task's stack.
struct quirc_code decodedCode;
struct quirc_data decodedData;
const char *startupError = nullptr;
char requestLine[256];
size_t requestLength = 0;
bool discardLine = false;
uint32_t lineStarted = 0;
bool sdReady = false;
uint32_t nextPhoto = 1;

uint16_t crc16(const uint8_t *data, size_t size) {
  uint16_t crc = 0xffff;
  while (size--) {
    crc ^= static_cast<uint16_t>(*data++) << 8;
    for (int bit = 0; bit < 8; ++bit)
      crc = (crc & 0x8000) ? (crc << 1) ^ 0x1021 : crc << 1;
  }
  return crc;
}

void sendResponse(JsonDocument &response) {
  char output[768];
  const size_t needed = measureJson(response);
  if (needed >= sizeof(output)) return;
  const size_t length = serializeJson(response, output, sizeof(output));
  const uint16_t checksum = crc16(reinterpret_cast<uint8_t *>(output), length);
  vision.write(reinterpret_cast<uint8_t *>(output), length);
  char suffix[8];
  snprintf(suffix, sizeof(suffix), "*%04X\n", checksum);
  vision.print(suffix);
}

void sendError(uint32_t id, const char *message) {
  StaticJsonDocument<256> response;
  response["v"] = 1;
  response["id"] = id;
  response["error"] = message;
  sendResponse(response);
}

bool initializeCamera() {
  if (!psramFound() || ESP.getPsramSize() < 8 * 1024 * 1024) {
    startupError = "8 MB PSRAM required";
    return false;
  }
  camera_config_t camera = {};
  camera.pin_pwdn = -1;
  camera.pin_reset = -1;
  camera.pin_xclk = CAMERA_XCLK;
  camera.pin_sccb_sda = CAMERA_SDA;
  camera.pin_sccb_scl = CAMERA_SCL;
  camera.pin_d0 = CAMERA_D0;
  camera.pin_d1 = CAMERA_D1;
  camera.pin_d2 = CAMERA_D2;
  camera.pin_d3 = CAMERA_D3;
  camera.pin_d4 = CAMERA_D4;
  camera.pin_d5 = CAMERA_D5;
  camera.pin_d6 = CAMERA_D6;
  camera.pin_d7 = CAMERA_D7;
  camera.pin_vsync = CAMERA_VSYNC;
  camera.pin_href = CAMERA_HREF;
  camera.pin_pclk = CAMERA_PCLK;
  camera.xclk_freq_hz = 20000000;
  camera.ledc_timer = LEDC_TIMER_0;
  camera.ledc_channel = LEDC_CHANNEL_0;
  camera.pixel_format = PIXFORMAT_GRAYSCALE;
  camera.frame_size = FRAMESIZE_QVGA;
  camera.jpeg_quality = 12;
  camera.fb_count = 1;
  camera.fb_location = CAMERA_FB_IN_PSRAM;
  camera.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  if (esp_camera_init(&camera) != ESP_OK) {
    startupError = "camera initialization failed";
    return false;
  }
  sensor_t *sensor = esp_camera_sensor_get();
  if (!sensor || (sensor->id.PID != OV2640_PID &&
                  sensor->id.PID != OV3660_PID &&
                  sensor->id.PID != OV5640_PID)) {
    startupError = "unsupported camera sensor";
    return false;
  }
  if (sensor->set_hmirror(sensor, CAMERA_HMIRROR) != 0 ||
      sensor->set_vflip(sensor, CAMERA_VFLIP) != 0) {
    startupError = "camera orientation configuration failed";
    return false;
  }
  Serial.printf("Camera sensor 0x%04x, PSRAM %u bytes\n",
                sensor->id.PID, ESP.getPsramSize());
  recognizer = quirc_new();
  if (!recognizer || quirc_resize(recognizer, IMAGE_WIDTH, IMAGE_HEIGHT) < 0) {
    startupError = "QR recognizer allocation failed";
    return false;
  }
  return true;
}

camera_fb_t *freshFrame(int64_t requestStarted) {
  // A one-buffer camera can retain an old exposure while idle. Return it and
  // wait for a frame whose first DMA timestamp is after this request.
  for (int attempt = 0; attempt < 3; ++attempt) {
    camera_fb_t *frame = esp_camera_fb_get();
    if (!frame) return nullptr;
    const int64_t exposed = static_cast<int64_t>(frame->timestamp.tv_sec) *
                            1000000 + frame->timestamp.tv_usec;
    if (exposed >= requestStarted && frame->format == PIXFORMAT_GRAYSCALE &&
        frame->width == IMAGE_WIDTH && frame->height == IMAGE_HEIGHT &&
        frame->len == IMAGE_WIDTH * IMAGE_HEIGHT) return frame;
    esp_camera_fb_return(frame);
  }
  return nullptr;
}

bool validCorners(const struct quirc_code &code) {
  for (const auto &corner : code.corners)
    if (corner.x < 0 || corner.x >= IMAGE_WIDTH ||
        corner.y < 0 || corner.y >= IMAGE_HEIGHT) return false;
  return true;
}

void scan(uint32_t id, int64_t requestStarted) {
  camera_fb_t *frame = freshFrame(requestStarted);
  if (!frame) {
    sendError(id, "fresh grayscale capture failed");
    return;
  }
  uint8_t *image = quirc_begin(recognizer, nullptr, nullptr);
  memcpy(image, frame->buf, IMAGE_WIDTH * IMAGE_HEIGHT);
  esp_camera_fb_return(frame);
  quirc_end(recognizer);

  StaticJsonDocument<768> response;
  response["v"] = 1;
  response["id"] = id;
  response["width"] = IMAGE_WIDTH;
  response["height"] = IMAGE_HEIGHT;
  response["marker"] = nullptr;
  bool found = false;
  for (int index = 0; index < quirc_count(recognizer); ++index) {
    quirc_extract(recognizer, index, &decodedCode);
    // Never use quirc_flip here: it transposes cells without changing corners.
    // Accepting mirrored codes would produce an invalid heading estimate.
    if (quirc_decode(&decodedCode, &decodedData) != QUIRC_SUCCESS ||
        decodedData.payload_len != sizeof(TARGET_PAYLOAD) - 1 ||
        memcmp(decodedData.payload, TARGET_PAYLOAD, sizeof(TARGET_PAYLOAD) - 1) ||
        !validCorners(decodedCode)) continue;
    if (found) {
      sendError(id, "multiple matching QR markers");
      return;
    }
    found = true;
    JsonObject marker = response.createNestedObject("marker");
    marker["payload"] = TARGET_PAYLOAD;
    JsonArray corners = marker.createNestedArray("corners");
    // quirc preserves QR-grid TL, TR, BR, BL even when rotated in the image.
    for (const auto &corner : decodedCode.corners) {
      JsonArray point = corners.createNestedArray();
      point.add(corner.x);
      point.add(corner.y);
    }
  }
  if (response.overflowed()) {
    sendError(id, "QR response allocation failed");
    return;
  }
  sendResponse(response);
}

bool initializeStorage() {
  if (sdReady) return true;
  SPI.begin(SD_SCK, SD_MISO, SD_MOSI, SD_CS);
  if (!SD.begin(SD_CS, SPI, 10000000) || SD.cardType() == CARD_NONE)
    return false;
  if (!SD.exists("/photos") && !SD.mkdir("/photos")) return false;
  sdReady = true;
  return true;
}

void photo(uint32_t id, int64_t requestStarted) {
  // On demand only, outside the landing controller. SD writes and JPEG
  // conversion can take longer than the marker freshness deadline.
  if (!initializeStorage()) {
    sendError(id, "microSD unavailable (FAT32 required)");
    return;
  }
  camera_fb_t *frame = freshFrame(requestStarted);
  if (!frame) {
    sendError(id, "fresh grayscale capture failed");
    return;
  }
  uint8_t *jpeg = nullptr;
  size_t jpegSize = 0;
  const bool encoded = frame2jpg(frame, 85, &jpeg, &jpegSize);
  esp_camera_fb_return(frame);
  if (!encoded || !jpeg || !jpegSize) {
    free(jpeg);
    sendError(id, "JPEG encoding failed");
    return;
  }
  char path[48];
  // An existing filename is skipped, including after a restart. Bound the
  // search per request to keep a nearly-full card from blocking indefinitely.
  bool available = false;
  for (int attempt = 0; attempt < 1000 && nextPhoto < 100000000; ++attempt) {
    snprintf(path, sizeof(path), "/photos/IMG_%08lu.jpg",
             static_cast<unsigned long>(nextPhoto++));
    if (!SD.exists(path)) {
      available = true;
      break;
    }
  }
  if (!available) {
    free(jpeg);
    sendError(id, "photo filename search exhausted; retry or retrieve photos");
    return;
  }
  File output = SD.open(path, FILE_WRITE);
  const bool written = output && output.write(jpeg, jpegSize) == jpegSize;
  if (output) {
    output.flush();
    output.close();
  }
  free(jpeg);
  // Reopen and check length, so a failed/full-card write is not reported saved.
  File check = SD.open(path, FILE_READ);
  const bool verified = written && check && check.size() == jpegSize;
  if (check) check.close();
  if (!verified) {
    SD.remove(path);
    sdReady = false;
    sendError(id, "photo write failed or microSD full");
    return;
  }
  StaticJsonDocument<256> response;
  response["v"] = 1;
  response["id"] = id;
  response["path"] = path;
  sendResponse(response);
}

void handleRequest(char *line, size_t length) {
  // The CRC is the final four hex digits after '*'; payloads may contain '*'.
  if (length < 6 || line[length - 5] != '*') return;
  char *end = nullptr;
  for (size_t i = length - 4; i < length; ++i)
    if (!isxdigit(static_cast<unsigned char>(line[i]))) return;
  const unsigned long received = strtoul(line + length - 4, &end, 16);
  if (end != line + length ||
      received != crc16(reinterpret_cast<uint8_t *>(line), length - 5)) return;
  line[length - 5] = '\0';
  StaticJsonDocument<256> request;
  if (deserializeJson(request, line)) return;
  if (!request["v"].is<int>() || request["v"].as<int>() != 1 ||
      !request["id"].is<uint32_t>()) return;
  const uint32_t id = request["id"].as<uint32_t>();
  if (!id || id > 0x7fffffff) return;
  const char *operation = request["op"] | "";
  if (startupError) {
    sendError(id, startupError);
    return;
  }
  const int64_t requestStarted = esp_timer_get_time();
  if (!strcmp(operation, "scan")) scan(id, requestStarted);
  else if (!strcmp(operation, "photo")) photo(id, requestStarted);
  else sendError(id, "unsupported operation");
}
}  // namespace

void setup() {
  Serial.begin(115200);  // USB diagnostics; never wait for a connected laptop.
  vision.setRxBufferSize(512);
  vision.begin(VISION_BAUD, SERIAL_8N1, VISION_RX_PIN, VISION_TX_PIN);
  if (!initializeCamera()) Serial.println(startupError);
  else Serial.println("BSHE27 QR camera ready (no Wi-Fi, no flight control)");
}

void loop() {
  // Drop unfinished lines after one second and overflowed lines until newline.
  if ((requestLength || discardLine) && millis() - lineStarted > 1000) {
    requestLength = 0;
    discardLine = false;
  }
  for (int budget = 0; budget < 256 && vision.available(); ++budget) {
    const char byte = static_cast<char>(vision.read());
    if (byte == '\n') {
      if (!discardLine && requestLength) {
        requestLine[requestLength] = '\0';
        handleRequest(requestLine, requestLength);
      }
      requestLength = 0;
      discardLine = false;
    } else if (byte != '\r') {
      if (!requestLength && !discardLine) lineStarted = millis();
      if (requestLength < sizeof(requestLine) - 1 && !discardLine)
        requestLine[requestLength++] = byte;
      else discardLine = true;
    }
  }
  delay(1);
}
