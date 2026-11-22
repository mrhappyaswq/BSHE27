#include <Arduino.h>
#include <esp_camera.h>
#include <math.h>
#include "camera_controls.h"
#include "camera_service.h"
#include "dashboard.h"
#include "exposure_math.h"
namespace camera_controls {
static SemaphoreHandle_t sensorLock;
static int reg(sensor_t* s,int address,int mask=255) { return s->get_reg(s,address,mask); }
static int word(sensor_t* s,int address) {
  int a=reg(s,address),b=reg(s,address+1); return a<0||b<0 ? -1 : (a<<8)|b;
}
static bool fail(char* out,size_t size,const char* text) {
  snprintf(out,size,"{\"ok\":false,\"error\":\"%s\"}",text);return false;
}
static bool snapshot(sensor_t* s,char* out,size_t size) {
  int hts=word(s,0x380c),vts=word(s,0x380e);
  double row=exposure_math::rowUs(s->xclk_freq_hz,reg(s,0x303a),reg(s,0x303b),reg(s,0x303c),reg(s,0x303d),hts);
  int a=reg(s,0x3500,15),b=reg(s,0x3501),c=reg(s,0x3502),gain=word(s,0x350a),mode=reg(s,0x3503),night=reg(s,0x3a00);
  if(row<=0 || vts<5 || a<0 || b<0 || c<0 || gain<0 || mode<0 || night<0) return fail(out,size,"Cannot read sensor timing");
  double exposure=(((a<<16)|(b<<8)|c)/16.0)*row/1000;
  snprintf(out,size,"{\"ok\":true,\"manual\":%s,\"exposure_ms\":%.4f,\"gain\":%.4f,\"row_us\":%.4f,\"frame_period_ms\":%.4f,\"max_exposure_ms\":%.4f,\"night_mode\":%s}",
    (mode&3)==3?"true":"false",exposure,(gain&1023)/16.0,row,row*vts/1000,fmin(20.0,row*(vts-4)/1000),(night&4)?"true":"false");
  return true;
}
static sensor_t* acquire() {
  if(!sensorLock || camera_service::error || xSemaphoreTake(sensorLock,pdMS_TO_TICKS(200))!=pdTRUE) return nullptr;
  sensor_t* s=esp_camera_sensor_get();
  if(!s || s->id.PID!=OV3660_PID) { xSemaphoreGive(sensorLock); return nullptr; }
  return s;
}
bool status(char* out,size_t size) {
  auto s=acquire();if(!s) return fail(out,size,"OV3660 controls unavailable");
  bool ok=snapshot(s,out,size);xSemaphoreGive(sensorLock);return ok;
}
bool apply(bool manual,uint32_t us,uint16_t gain16,char* out,size_t size) {
  if(dashboard::flying()) return fail(out,size,"Camera controls locked during missions");
  auto s=acquire();if(!s) return fail(out,size,"OV3660 controls unavailable");
  int hts=word(s,0x380c),vts=word(s,0x380e);
  double row=exposure_math::rowUs(s->xclk_freq_hz,reg(s,0x303a),reg(s,0x303b),reg(s,0x303c),reg(s,0x303d),hts);
  int rows=exposure_math::rowsForUs(us,row,vts);
  if(manual && (rows<0 || gain16<16 || gain16>248)) {
    xSemaphoreGive(sensorLock);return fail(out,size,"Use 0.1-20 ms within frame period and 1-15.5x gain");
  }
  // Disable night-mode frame extension in both modes. Manual exposure and gain
  // are paired so auto gain cannot fight manual exposure between frames.
  int rc=s->set_aec2(s,0);
  if(!rc && manual) rc=s->set_exposure_ctrl(s,0) || s->set_gain_ctrl(s,0) || s->set_aec_value(s,rows) ||
    s->set_reg(s,0x350a,3,gain16>>8) || s->set_reg(s,0x350b,255,gain16&255);
  if(!rc && !manual) rc=s->set_gain_ctrl(s,1) || s->set_exposure_ctrl(s,1);
  // On a partial I2C write failure restore auto rather than leave mixed modes.
  if(rc) { s->set_gain_ctrl(s,1);s->set_exposure_ctrl(s,1); }
  bool ok=rc ? fail(out,size,"Sensor write failed; auto restore attempted") : snapshot(s,out,size);
  xSemaphoreGive(sensorLock);return ok;
}
void begin() {
  sensorLock=xSemaphoreCreateMutex();
  auto s=esp_camera_sensor_get();
  if(s && s->id.PID==OV3660_PID) s->set_aec2(s,0);
}
}
