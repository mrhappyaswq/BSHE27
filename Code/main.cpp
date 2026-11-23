#include <Arduino.h>
#include <esp32-hal-rgb-led.h>
#include "Board Settings/settings.h"
#include "Pixhawk Communication/vehicle.h"
#include "Flight Missions/mission.h"
#include "Web Server/dashboard.h"
#include "Camera/wired_camera.h"
#include "Camera/camera_frame.h"
#include "Camera/camera_controls.h"
#include "Pixhawk Communication/telemetry.h"
#include "ArUco/aruco_service.h"
Vehicle vehicle;
Mission mission(vehicle);
static char input[96]; static size_t inputSize=0; static bool overflow=false;
static void command(const String& cmd) {
  if(cmd.startsWith("marker ")) {
    float x,y,w,h; char tail;
    if(sscanf(cmd.c_str(),"marker %f %f %f %f %c",&x,&y,&w,&h,&tail)==4 &&
       isfinite(x) && isfinite(y) && isfinite(w) && isfinite(h) && w>0 && h>0 && x>=0 && x<w && y>=0 && y<h) {
      mission.external.x=x*320/w; mission.external.y=y*240/h;
      mission.external.yaw=0; mission.external.at=millis(); ++mission.external.id; mission.external.valid=true;
    } else mission.external.valid=false;
  } else if(cmd.startsWith("run ")) mission.start(cmd.substring(4));
  else if(cmd=="abort") mission.stop("Operator abort");
  else if(cmd=="photo") {
    if(mission.running() || vehicle.armed()) Serial.println("Photo requires idle disarmed vehicle");
    else Serial.println(camera_service::photo()?"Photo saved":"Photo failed (check SD configuration)");
  } else if(cmd=="telemetry") {
    if(!mission.running() && vehicle.linked()) { vehicle.streams(); Serial.println("Requested 4 Hz telemetry"); }
  } else if(cmd=="status") {
    Serial.printf("link=%d armed=%d mode=%lu altitude=%.2f phase=%d %s\n",vehicle.linked(),vehicle.armed(),(unsigned long)vehicle.mode,vehicle.altitude,int(mission.phase),mission.message.c_str());
    char cameraStats[384];camera_service::statsJson(cameraStats,sizeof(cameraStats));
    Serial.printf("Camera: %s\n%s\n",camera_service::error?camera_service::error:"running",cameraStats);
    char usbStats[192]; wired_camera::statsJson(usbStats,sizeof(usbStats)); Serial.printf("USB: %s\n",usbStats);
    char controls[448];camera_controls::status(controls,sizeof(controls));Serial.printf("Exposure: %s\n",controls);
    char wifiStats[256];dashboard::statsJson(wifiStats,sizeof(wifiStats));Serial.printf("Wi-Fi: %s\n",wifiStats);
  } else Serial.println("status | telemetry | photo | abort | run hover/hover_gps/move_gps/circle/aruco_landing/aruco_move_gps | marker cx cy width height");
}
void setup() {
  Serial.begin(115200); Serial.println(settings::Board); vehicle.begin(); camera_service::begin(); camera_controls::begin(); aruco_service::begin(); wired_camera::begin();
  Serial.println("Passive boot. Wi-Fi BSHE27-Camera / password; http://192.168.4.1/");
  command("help");
}
void loop() {
  vehicle.poll(); mission.tick();
  for(int budget=0;budget<128 && Serial.available();++budget) {
    char c=Serial.read();
    if(c=='\n') { if(!overflow) {input[inputSize]=0; command(String(input));} else Serial.println("Command too long"); inputSize=0;overflow=false; }
    else if(c!='\r') { if(inputSize<sizeof(input)-1 && !overflow) input[inputSize++]=c; else overflow=true; }
  }
  static uint32_t report=0; if(millis()-report>=250) {
    report=millis();static uint32_t sampleSequence=0;char json[1536];
    auto frame=camera_service::latestFrame();
    float fps=frame && uint32_t(millis()-frame->capturedMs)<2000 ? frame->boardFps:0;
    telemetryJson(vehicle,millis(),++sampleSequence,mission.running(),int(mission.phase),mission.message.c_str(),camera_service::error,fps,json,sizeof(json));
    dashboard::publish(json,mission.running(),vehicle.heartbeatAt,vehicle.haveHeartbeat);
    uint8_t r=0,g=0,b=0; bool on=millis()%2000<200;
    if(camera_service::error || (vehicle.haveHeartbeat && !vehicle.linked())) r=20;
    else if(mission.running()) b=20;
    else if(vehicle.linked()) g=20;
    else {r=20;g=8;}
    neopixelWrite(settings::Led,on?r:0,on?g:0,on?b:0);
  }
  delay(1);
}
