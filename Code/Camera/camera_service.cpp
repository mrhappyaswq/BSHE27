#include "Camera/camera_service.h"
#include "Camera/camera_frame.h"
#include "Board Settings/settings.h"
#include <WiFi.h>
#include <esp_wifi.h>
#include <esp_camera.h>
#include <esp_http_server.h>
#include <esp_timer.h>
#include <SD.h>
#include <SPI.h>
#include "Web Server/dashboard.h"
#include "Camera/camera_controls.h"
namespace camera_service {
const char* error=nullptr;
static SemaphoreHandle_t lock;
static uint32_t nextId=0;
static FramePtr latestJpeg;
static uint32_t rateAt=0, rateFrames=0;
static float boardFps=0;
static altitude_profile::Profile wanted;
static uint32_t revision=0,doneRevision=0;
static const char* profileError=nullptr;
bool simulateAltitude(bool enabled,uint16_t cm,char* out,size_t size){
  auto fail=[&](const char* text){snprintf(out,size,"{\"ok\":false,\"error\":\"%s\"}",text);return false;};
  if(cm>2000)return fail("Use simulated altitude 0-20 m");
  if(dashboard::flying())return fail("Altitude simulation locked during missions");
  if(!lock||error)return fail("Camera unavailable");
  auto selected=altitude_profile::select(enabled,cm);xSemaphoreTake(lock,portMAX_DELAY);wanted=selected;uint32_t token=++revision;xSemaphoreGive(lock);
  uint32_t started=millis();
  while(millis()-started<2500){xSemaphoreTake(lock,portMAX_DELAY);bool done=doneRevision==token;const char* e=profileError;xSemaphoreGive(lock);
    if(done){if(e)return fail(e);snprintf(out,size,"{\"ok\":true,\"enabled\":%s,\"altitude_m\":%.2f,\"width\":%u,\"height\":%u,\"quality\":%u,\"target_fps\":%u,\"mode\":%u}",enabled?"true":"false",selected.altitudeCm/100.,selected.width,selected.height,selected.quality,selected.targetFps,selected.mode);return true;}
    vTaskDelay(pdMS_TO_TICKS(5));
  }
  return fail("Camera profile timed out; check live frame settings");
}
FramePtr latestFrame() {
  FramePtr f;
  if(lock && xSemaphoreTake(lock,pdMS_TO_TICKS(5))==pdTRUE) { f=latestJpeg; xSemaphoreGive(lock); }
  return f;
}
void statsJson(char* out,size_t size) {
  auto f=latestFrame(); bool fresh=f && millis()-f->capturedMs<2000;
  snprintf(out,size,"{\"board_fps\":%.2f,\"frames\":%lu,\"capture_wait_ms\":%.2f,\"jpeg_ms\":0,\"prepare_ms\":%.3f,\"jpeg_source\":\"sensor\",\"jpeg_quality\":%u,\"jpeg_bytes\":%u,\"frame_age_ms\":%lu,\"fresh\":%s}",
    fresh?f->boardFps:0,(unsigned long)(f?f->id:0),f?f->captureUs/1000.0:0,
    f?f->prepareUs/1000.0:0,unsigned(f?f->profile.quality:settings::JpegQuality),unsigned(f?f->size:0),
    (unsigned long)(f?millis()-f->capturedMs:0),fresh?"true":"false");
}
static void worker(void*) {
  rateAt=millis();
  altitude_profile::Profile active;uint32_t seen=0,lastPublished=0;int discard=0;bool pendingCommit=false;
  while(true) {
    xSemaphoreTake(lock,portMAX_DELAY);auto requested=wanted;uint32_t version=revision;xSemaphoreGive(lock);
    if(version!=seen){seen=version;
      if(!altitude_profile::sameFormat(active,requested)){
        if(!camera_controls::format(requested.width,requested.height,requested.quality)){
          if(!camera_controls::format(active.width,active.height,active.quality))error="Camera format rollback failed; reboot";
          xSemaphoreTake(lock,portMAX_DELAY);doneRevision=seen;profileError="Camera rejected profile";xSemaphoreGive(lock);continue;
        }
        discard=3;pendingCommit=true;rateAt=millis();rateFrames=0;boardFps=0;
      }else {xSemaphoreTake(lock,portMAX_DELAY);doneRevision=seen;profileError=nullptr;xSemaphoreGive(lock);}
      active=requested;lastPublished=0;
    }
    if(!discard&&lastPublished&&active.targetFps&&millis()-lastPublished<1000u/active.targetFps){vTaskDelay(pdMS_TO_TICKS(5));continue;}
    int64_t captureStart=esp_timer_get_time();
    camera_fb_t* fb=esp_camera_fb_get();
    uint32_t captureUs=esp_timer_get_time()-captureStart;
    if(!fb) { vTaskDelay(1); continue; }
    if(discard){--discard;esp_camera_fb_return(fb);continue;}
    // The OV3660 supplies an already compressed JPEG. Return its driver buffer
    // promptly so a slow USB/HTTP client cannot hold up camera acquisition.
    auto encoded=std::make_shared<Frame>();
    encoded->id=++nextId; encoded->captureUs=captureUs;
    encoded->profile=active;
    encoded->capturedMs=uint32_t(int64_t(fb->timestamp.tv_sec)*1000+fb->timestamp.tv_usec/1000);
    int64_t prepareStart=esp_timer_get_time();
    if(fb->format==PIXFORMAT_JPEG && fb->width==active.width && fb->height==active.height && fb->len>=4 &&
       fb->buf[0]==0xff && fb->buf[1]==0xd8) {
      encoded->jpeg=static_cast<uint8_t*>(ps_malloc(fb->len));
      if(encoded->jpeg) { memcpy(encoded->jpeg,fb->buf,fb->len); encoded->size=fb->len; }
    }
    esp_camera_fb_return(fb);
    encoded->prepareUs=esp_timer_get_time()-prepareStart;
    if(encoded->size) {
      ++rateFrames;
      uint32_t elapsed=millis()-rateAt;
      if(elapsed>=1000) { boardFps=rateFrames*1000.0f/elapsed; rateFrames=0; rateAt=millis(); }
      encoded->boardFps=boardFps;
      xSemaphoreTake(lock,portMAX_DELAY); latestJpeg=encoded;if(pendingCommit){doneRevision=seen;profileError=nullptr;pendingCommit=false;} xSemaphoreGive(lock);
      lastPublished=millis();
    } else vTaskDelay(1);
    // Simulation limits published frames above; the sensor may capture faster.
  }
}
// HTTP and native USB read the same immutable, already encoded frame.
static esp_err_t unavailable(httpd_req_t* r) {
  httpd_resp_set_status(r,"503 Service Unavailable");
  httpd_resp_set_hdr(r,"Access-Control-Allow-Origin","*");
  return httpd_resp_send(r,error?error:"Camera paused or frame unavailable",HTTPD_RESP_USE_STRLEN);
}
static FramePtr nextFrame(uint32_t after) {
  uint32_t start=millis();
  do {
    auto f=latestFrame();
    if(f && f->id!=after && millis()-f->capturedMs<2000) return f;
    if(error || dashboard::flying()) break;
    vTaskDelay(pdMS_TO_TICKS(5));
  } while(millis()-start<1000);
  return {};
}
static esp_err_t capture(httpd_req_t* r) {
  if(dashboard::flying() || error) return unavailable(r);
  auto f=nextFrame(0); if(!f) return unavailable(r);
  httpd_resp_set_type(r,"image/jpeg"); httpd_resp_set_hdr(r,"Cache-Control","no-store");
  httpd_resp_set_hdr(r,"Access-Control-Allow-Origin","*");
  httpd_resp_set_hdr(r,"Access-Control-Expose-Headers","X-Frame-Id, X-Frame-Age-Ms");
  char id[16],age[16];snprintf(id,sizeof(id),"%lu",(unsigned long)f->id);snprintf(age,sizeof(age),"%lu",(unsigned long)(millis()-f->capturedMs));
  httpd_resp_set_hdr(r,"X-Frame-Id",id);httpd_resp_set_hdr(r,"X-Frame-Age-Ms",age);
  return httpd_resp_send(r,reinterpret_cast<const char*>(f->jpeg),f->size);
}
static esp_err_t frame(httpd_req_t* r) {
  if(dashboard::flying() || error) return unavailable(r);
  char query[64]={}, value[24]={}; uint32_t after=0;
  if(httpd_req_get_url_query_str(r,query,sizeof(query))==ESP_OK &&
     httpd_query_key_value(query,"after",value,sizeof(value))==ESP_OK) after=strtoul(value,nullptr,10);
  auto f=nextFrame(after); if(!f) return unavailable(r);
  uint8_t header[HeaderSize]; frameHeader(header,f.get(),millis());
  httpd_resp_set_type(r,"application/octet-stream");
  httpd_resp_set_hdr(r,"Access-Control-Allow-Origin","*"); httpd_resp_set_hdr(r,"Cache-Control","no-store");
  esp_err_t result=httpd_resp_send_chunk(r,reinterpret_cast<const char*>(header),sizeof(header));
  if(result==ESP_OK) result=httpd_resp_send_chunk(r,reinterpret_cast<const char*>(f->jpeg),f->size);
  if(result==ESP_OK) result=httpd_resp_send_chunk(r,nullptr,0);
  return result;
}
static esp_err_t stream(httpd_req_t* r) {
  if(error || dashboard::flying()) return unavailable(r);
  httpd_resp_set_type(r,"multipart/x-mixed-replace;boundary=frame"); uint32_t after=0;
  while(!dashboard::flying()) {
    auto f=nextFrame(after); if(!f) return ESP_FAIL; after=f->id;
    char header[120]; int n=snprintf(header,sizeof(header),"\r\n--frame\r\nContent-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n",unsigned(f->size));
    esp_err_t result=httpd_resp_send_chunk(r,header,n);
    if(result==ESP_OK) result=httpd_resp_send_chunk(r,reinterpret_cast<const char*>(f->jpeg),f->size);
    if(result!=ESP_OK) return result;
  }
  return ESP_FAIL;
}
bool photo() {
  if(!settings::SdEnabled || error) return false;
  SPI.begin(settings::SdSck,settings::SdMiso,settings::SdMosi,settings::SdCs);
  if(!SD.begin(settings::SdCs) || (!SD.exists("/photos") && !SD.mkdir("/photos"))) return false;
  auto frame=latestFrame(); if(!frame || millis()-frame->capturedMs>2000) return false;
  const uint8_t* jpg=frame->jpeg; size_t n=frame->size; bool ok=true;
  char path[64]; snprintf(path,sizeof(path),"/photos/%08lx-%08lx.jpg",(unsigned long)esp_random(),(unsigned long)millis());
  if(SD.exists(path)) ok=false;
  if(ok && jpg) { File f=SD.open(path,FILE_WRITE); ok=f && f.write(jpg,n)==n; if(f) {f.flush();f.close();}
    File check=SD.open(path); ok=ok && check && check.size()==n; check.close(); if(!ok) SD.remove(path); }
  else ok=false;
  if(ok) Serial.println(path); return ok;
}
void begin() {
  lock=xSemaphoreCreateMutex(); if(!lock) error="Camera mutex allocation failed";
  if(!psramFound()) error="PSRAM unavailable";
  camera_config_t c={}; c.pin_pwdn=-1; c.pin_reset=-1;
  c.pin_sccb_sda=4;c.pin_sccb_scl=5;c.pin_xclk=15;
  c.pin_d0=11;c.pin_d1=9;c.pin_d2=8;c.pin_d3=10;c.pin_d4=12;c.pin_d5=18;c.pin_d6=17;c.pin_d7=16;
  c.pin_vsync=6;c.pin_href=7;c.pin_pclk=13;
  c.xclk_freq_hz=20000000;c.ledc_timer=LEDC_TIMER_0;c.ledc_channel=LEDC_CHANNEL_0;
  // Allocate JPEG buffers for large frames, then start the sensor at QVGA.
  // Espressif's CameraWebServer uses this same maximum-allocation approach.
  c.pixel_format=PIXFORMAT_JPEG;c.frame_size=FRAMESIZE_UXGA;c.jpeg_quality=settings::JpegQuality;
  c.fb_count=2;c.fb_location=CAMERA_FB_IN_PSRAM;c.grab_mode=CAMERA_GRAB_LATEST;
  if(!error && esp_camera_init(&c)!=ESP_OK) error="Camera initialization failed";
  if(!error) {
    sensor_t* s=esp_camera_sensor_get();
    if(s&&s->set_framesize(s,FRAMESIZE_QVGA))error="Camera initial frame size failed";
    if(!s || s->set_hmirror(s,settings::Mirror) || s->set_vflip(s,settings::Flip)) error="Camera orientation failed";
    if(!error && xTaskCreatePinnedToCore(worker,"Camera",4096,nullptr,1,nullptr,0)!=pdPASS) error="Camera task allocation failed";
  }
  WiFi.mode(WIFI_AP); WiFi.setSleep(false);
  uint8_t protocol=WIFI_PROTOCOL_11B|WIFI_PROTOCOL_11G;
  if(!settings::WifiCompatibility) protocol|=WIFI_PROTOCOL_11N;
  if(esp_wifi_set_protocol(WIFI_IF_AP,protocol)!=ESP_OK)
    Serial.println("Wi-Fi protocol profile could not be applied");
  if(!WiFi.softAP(settings::Ssid,settings::Password,1,false,2)) { Serial.println("Wi-Fi AP failed"); return; }
  dashboard::begin(capture,stream,frame);
}
}
