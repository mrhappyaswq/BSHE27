// Standalone bench camera viewer. No MAVLink, arming, or landing commands.
#include <Arduino.h>
#include <WiFi.h>
#include <esp_camera.h>
#include <esp_http_server.h>
#include <freertos/semphr.h>

#include "viewer.h"

// Local access point: no router, internet connection, or cloud service needed.
constexpr char AP_NAME[] = "BSHE27-Camera";
constexpr char AP_PASSWORD[] =
    "bshe27cam";  // Change before building if desired (8+ chars).
static_assert(sizeof(AP_PASSWORD) >= 9 && sizeof(AP_PASSWORD) <= 64,
              "Wi-Fi password must contain 8 to 63 characters");
SemaphoreHandle_t cameraLock = nullptr;
const char* cameraError = nullptr;
const char* boardName = nullptr;

bool initCamera() {
  camera_config_t c = {};
  c.pin_pwdn = -1;
  c.pin_reset = -1;
#if defined(BSHE_BOARD_GOOUUU)
  // Amazon manual, PDF page 4: GOOUUU ESP32-S3-CAM N16R8.
  boardName = "GOOUUU ESP32-S3-CAM N16R8";
  c.pin_sccb_sda = 4;
  c.pin_sccb_scl = 5;
  c.pin_xclk = 15;
  c.pin_d0 = 11;
  c.pin_d1 = 9;
  c.pin_d2 = 8;
  c.pin_d3 = 10;
  c.pin_d4 = 12;
  c.pin_d5 = 18;
  c.pin_d6 = 17;
  c.pin_d7 = 16;
  c.pin_vsync = 6;
  c.pin_href = 7;
  c.pin_pclk = 13;
#elif defined(BSHE_BOARD_XIAO)
  boardName = "XIAO ESP32-S3 Sense";
  c.pin_sccb_sda = 40;
  c.pin_sccb_scl = 39;
  c.pin_xclk = 10;
  c.pin_d0 = 15;
  c.pin_d1 = 17;
  c.pin_d2 = 18;
  c.pin_d3 = 16;
  c.pin_d4 = 14;
  c.pin_d5 = 12;
  c.pin_d6 = 11;
  c.pin_d7 = 48;
  c.pin_vsync = 38;
  c.pin_href = 47;
  c.pin_pclk = 13;
#else
#error Select a supported board environment
#endif
  if (!psramFound()) {
    cameraError = "PSRAM not detected; check board profile";
    return false;
  }
  c.ledc_timer = LEDC_TIMER_0;
  c.ledc_channel = LEDC_CHANNEL_0;
  c.xclk_freq_hz = 20000000;
  c.pixel_format = PIXFORMAT_JPEG;
  c.frame_size = FRAMESIZE_VGA;
  c.jpeg_quality = 12;
  c.fb_count = 2;
  c.fb_location = CAMERA_FB_IN_PSRAM;
  c.grab_mode = CAMERA_GRAB_LATEST;
  esp_err_t err = esp_camera_init(&c);
  if (err != ESP_OK) {
    Serial.printf("Camera init error: 0x%x\n", err);
    cameraError =
        "Camera initialization failed; check cable, sensor and selected board";
    return false;
  }
  sensor_t* sensor = esp_camera_sensor_get();
  if (!sensor ||
      (sensor->id.PID != OV2640_PID && sensor->id.PID != OV3660_PID &&
       sensor->id.PID != OV5640_PID)) {
    esp_camera_deinit();
    cameraError = "Expected supplied OV2640, OV3660 or OV5640 JPEG camera";
    return false;
  }
  sensor->set_hmirror(sensor, 0);
  sensor->set_vflip(sensor, 0);
  Serial.printf("%s, sensor=0x%04x, PSRAM=%u bytes, flash=%u bytes\n",
                boardName, sensor->id.PID, ESP.getPsramSize(),
                ESP.getFlashChipSize());
  return true;
}

esp_err_t home(httpd_req_t* r) {
  httpd_resp_set_type(r, "text/html; charset=utf-8");
  return httpd_resp_send(r, PAGE, HTTPD_RESP_USE_STRLEN);
}
esp_err_t status(httpd_req_t* r) {
  httpd_resp_set_type(r, "application/json");
  httpd_resp_set_hdr(r, "Cache-Control", "no-store");
  char json[256];
  snprintf(json, sizeof(json), "{\"ready\":%s,\"error\":\"%s\"}",
           cameraError ? "false" : "true", cameraError ? cameraError : "");
  return httpd_resp_send(r, json, HTTPD_RESP_USE_STRLEN);
}
esp_err_t unavailable(httpd_req_t* r, const char* message) {
  httpd_resp_set_status(r, "503 Service Unavailable");
  httpd_resp_set_type(r, "text/plain; charset=utf-8");
  httpd_resp_set_hdr(r, "Cache-Control", "no-store");
  return httpd_resp_send(r, message, HTTPD_RESP_USE_STRLEN);
}
esp_err_t capture(httpd_req_t* r) {
  if (cameraError || xSemaphoreTake(cameraLock, pdMS_TO_TICKS(500)) != pdTRUE)
    return unavailable(r, "Camera unavailable or busy");
  camera_fb_t* fb = esp_camera_fb_get();
  esp_err_t result = ESP_FAIL;
  if (fb) {
    httpd_resp_set_type(r, "image/jpeg");
    httpd_resp_set_hdr(r, "Cache-Control", "no-store");
    result =
        httpd_resp_send(r, reinterpret_cast<const char*>(fb->buf), fb->len);
    esp_camera_fb_return(fb);
  } else
    result = unavailable(r, "Capture failed");
  xSemaphoreGive(cameraLock);
  return result;
}
esp_err_t stream(httpd_req_t* r) {
  if (cameraError) return unavailable(r, cameraError);
  httpd_resp_set_type(r, "multipart/x-mixed-replace;boundary=bshe27frame");
  httpd_resp_set_hdr(r, "Cache-Control", "no-store");
  while (true) {
    if (xSemaphoreTake(cameraLock, pdMS_TO_TICKS(500)) != pdTRUE)
      return ESP_FAIL;
    camera_fb_t* fb = esp_camera_fb_get();
    esp_err_t result = ESP_FAIL;
    if (fb) {
      char header[128];
      int n = snprintf(header, sizeof(header),
                       "\r\n--bshe27frame\r\nContent-Type: "
                       "image/jpeg\r\nContent-Length: %u\r\n\r\n",
                       static_cast<unsigned>(fb->len));
      result = httpd_resp_send_chunk(r, header, n);
      if (result == ESP_OK)
        result = httpd_resp_send_chunk(
            r, reinterpret_cast<const char*>(fb->buf), fb->len);
      esp_camera_fb_return(fb);
    }
    xSemaphoreGive(cameraLock);
    if (result != ESP_OK)
      return result;  // Disconnect/timeout releases all capture resources.
    vTaskDelay(
        pdMS_TO_TICKS(100));  // At most ~10 FPS; actual speed depends on Wi-Fi.
  }
}
bool startServer(uint16_t port, uint16_t controlPort, bool streaming) {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = port;
  config.ctrl_port = controlPort;
  config.send_wait_timeout = 2;
  config.lru_purge_enable = true;
  httpd_handle_t server = nullptr;
  esp_err_t result = httpd_start(&server, &config);
  if (result != ESP_OK) {
    Serial.printf("HTTP server on port %u failed: %s\n", port,
                  esp_err_to_name(result));
    return false;
  }

  httpd_uri_t route = {};
  route.method = HTTP_GET;
  if (streaming) {
    route.uri = "/stream";
    route.handler = stream;
    result = httpd_register_uri_handler(server, &route);
  } else {
    const char* paths[] = {"/", "/status", "/capture"};
    esp_err_t (*handlers[])(httpd_req_t*) = {home, status, capture};
    for (size_t i = 0; i < 3 && result == ESP_OK; ++i) {
      route.uri = paths[i];
      route.handler = handlers[i];
      result = httpd_register_uri_handler(server, &route);
    }
  }

  if (result != ESP_OK) {
    Serial.printf("HTTP route registration failed: %s\n",
                  esp_err_to_name(result));
    httpd_stop(server);
    return false;
  }
  return true;
}
void setup() {
  Serial.begin(115200);
  cameraLock = xSemaphoreCreateMutex();
  if (!cameraLock)
    cameraError = "Camera lock allocation failed";
  else
    initCamera();
  WiFi.mode(WIFI_AP);
  if (!WiFi.softAP(AP_NAME, AP_PASSWORD, 1, false, 1)) {
    Serial.println("Wi-Fi startup failed");
    return;
  }
  if (!startServer(80, 32768, false) || !startServer(81, 32769, true)) {
    Serial.println("Webserver startup failed");
    return;
  }
  Serial.printf("Connect to Wi-Fi %s, then open http://%s/\n", AP_NAME,
                WiFi.softAPIP().toString().c_str());
  if (cameraError) Serial.println(cameraError);
}
void loop() { delay(1000); }
