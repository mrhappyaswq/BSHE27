#include "ArUco/aruco_service.h"
#include "ArUco/aruco_image.h"
#include "ArUco/grayscale_jpeg.h"
#include "ArUco/aruco_tracker.h"
#include "ArUco/aruco_json.h"
#include <new>
#include "esp_timer.h"
#include "esp_heap_caps.h"
#include <Arduino.h>
namespace aruco_service {
static_assert(aruco_config::TargetId==0,"This detector currently implements only 7x7 marker ID 0");
static SemaphoreHandle_t lock=nullptr;
static ResultPtr current;
static const char* startupError="ArUco starting";
static uint8_t* gray=nullptr;
static aruco_detector::Workspace workspace{};
static uint32_t workspaceBytes=0;
constexpr int Width=320,Height=240,Pixels=Width*Height;
static aruco_image::GrayDecoder* decoder=nullptr;
static uint32_t internalBytes=0,externalBytes=0;
static uint32_t clockUs(){return micros();}
ResultPtr latest(){if(!lock)return {};xSemaphoreTake(lock,portMAX_DELAY);auto r=current;xSemaphoreGive(lock);return r;}
static void worker(void*) {
  uint32_t previous=0,windowAt=micros(),windowBusy=0,windowFrames=0;
  float fps=0,busy=0;aruco_detector::Tracker tracker;
  while(true){
    auto frame=camera_service::latestFrame();
    if(!frame||frame->id==previous||millis()-frame->capturedMs>=aruco_config::MaxAgeMs){
      vTaskDelay(pdMS_TO_TICKS(aruco_config::IdleYieldMs));continue;
    }
    uint32_t started=micros();previous=frame->id;
    auto r=std::make_shared<Result>();r->frame=frame;r->workspaceBytes=workspaceBytes;
    r->internalBytes=internalBytes;r->externalBytes=externalBytes;
    uint32_t at=micros();
    bool decoded=decoder->decode(frame->jpeg,frame->size,gray,frame->profile.width,frame->profile.height,
      Width,Height,aruco_config::DetectorMirrorX,aruco_config::DetectorFlipY);
    r->decodeUs=micros()-at;at=micros();
    if(decoded){
      r->analysisWidth=decoder->decodedWidth();r->analysisHeight=decoder->decodedHeight();
      r->detection=tracker.find(gray,r->analysisWidth,r->analysisHeight,workspace,millis(),&r->profile,clockUs);
      uint32_t poseAt=micros();
      auto calibration=aruco_config::calibration();
      float sx=r->analysisWidth/float(Width),sy=r->analysisHeight/float(Height);
      calibration.fx*=sx;calibration.fy*=sy;calibration.cx=(calibration.cx+.5f)*sx-.5f;calibration.cy=(calibration.cy+.5f)*sy-.5f;
      if(r->detection.valid)r->pose=marker_pose::estimate(r->detection.corners,aruco_config::MarkerSideM,calibration,aruco_config::MaxReprojectionPx);
      r->poseUs=micros()-poseAt;
      if(r->detection.valid&&!r->pose.valid)tracker.reset();
    }else {r->error="JPEG decode failed";tracker.reset();}
    r->detectUs=micros()-at;r->processingUs=micros()-started;r->completedMs=millis();
    windowBusy+=r->processingUs;++windowFrames;
    uint32_t elapsed=micros()-windowAt;
    if(elapsed>=1000000){
      fps=windowFrames*1000000.f/elapsed;busy=std::min(100.f,100.f*windowBusy/elapsed);
      windowAt=micros();windowBusy=windowFrames=0;
    }
    // Wall processing duty over an elapsed window, not scheduler CPU utilization.
    r->analysisFps=fps;r->busyPercent=busy;r->stackFreeBytes=uxTaskGetStackHighWaterMark(nullptr);
    xSemaphoreTake(lock,portMAX_DELAY);current=r;xSemaphoreGive(lock);
    // Process fresh frames without a 200ms schedule, but always leave idle time.
    vTaskDelay(pdMS_TO_TICKS(aruco_config::IdleYieldMs));
  }
}

template<class T> static bool allocate(T*& pointer,size_t count,bool preferInternal=false){
  size_t bytes=count*sizeof(T);constexpr size_t Reserve=64*1024;
  if(preferInternal&&heap_caps_get_free_size(MALLOC_CAP_INTERNAL|MALLOC_CAP_8BIT)>bytes+Reserve)
    pointer=static_cast<T*>(heap_caps_malloc(bytes,MALLOC_CAP_INTERNAL|MALLOC_CAP_8BIT));
  if(pointer)internalBytes+=bytes;
  else {
    pointer=static_cast<T*>(heap_caps_malloc(bytes,MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT));
    if(pointer)externalBytes+=bytes;
  }
  if(pointer)workspaceBytes+=bytes;
  return pointer!=nullptr;
}
void begin(){
  lock=xSemaphoreCreateMutex();if(!lock){startupError="ArUco mutex allocation failed";return;}
  bool ok=allocate(decoder,1,true);
  if(decoder)new(decoder) aruco_image::GrayDecoder;
  ok=ok&&allocate(workspace.columns,Width,true)&&allocate(workspace.binary,Pixels,true)&&
    allocate(workspace.boundary,aruco_detector::MaxBoundary,true)&&allocate(workspace.hull,aruco_detector::MaxBoundary*2,true)&&
    allocate(gray,Pixels)&&allocate(workspace.queue,Pixels);
  if(!ok){
    if(decoder)decoder->~GrayDecoder();
    free(decoder);free(gray);free(workspace.columns);free(workspace.queue);free(workspace.binary);free(workspace.boundary);free(workspace.hull);
    startupError="ArUco workspace allocation failed";return;
  }
  if(xTaskCreatePinnedToCore(worker,"ArUco preview",8192,nullptr,1,nullptr,1)!=pdPASS){startupError="ArUco task allocation failed";return;}
  startupError=nullptr;
}
void json(char* out,size_t size,const Result* r,uint32_t now){
  formatJson(out,size,r,now,ESP.getFreeHeap(),ESP.getFreePsram(),startupError);
}
}
