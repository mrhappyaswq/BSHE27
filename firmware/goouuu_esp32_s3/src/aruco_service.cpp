#include "aruco_service.h"
#include "aruco_image.h"
#include "esp_jpg_decode.h"
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
struct Decode {const camera_service::Frame* frame;bool dimensionsOk=false;uint16_t width=0,height=0;explicit Decode(const camera_service::Frame* f):frame(f){} };
static size_t readJpeg(void* arg,size_t index,uint8_t* buffer,size_t len) {
  auto& d=*static_cast<Decode*>(arg);if(index>=d.frame->size)return 0;
  len=std::min(len,d.frame->size-index);if(buffer)memcpy(buffer,d.frame->jpeg+index,len);return len;
}
static bool writeGray(void* arg,uint16_t x,uint16_t y,uint16_t w,uint16_t h,uint8_t* data) {
  auto& d=*static_cast<Decode*>(arg);
  if(!data){if(x==0&&y==0&&w&&h){d.width=w;d.height=h;d.dimensionsOk=w<=Width&&h<=Height;return d.dimensionsOk;}return true;}
  if(!d.dimensionsOk||x+w>d.width||y+h>d.height)return false;
  for(int row=0;row<h;++row)for(int col=0;col<w;++col){
    const uint8_t* rgb=data+3*(row*w+col);
    // Sensor flags do not describe parity of the delivered OV3660 JPEG.
    int gx=x+col,gy=y+row;
    aruco_image::map(gx,gy,d.width,d.height,aruco_config::DetectorMirrorX,aruco_config::DetectorFlipY);
    gray[gy*d.width+gx]=(77*rgb[0]+150*rgb[1]+29*rgb[2])>>8;
  }
  return true;
}
ResultPtr latest(){if(!lock)return {};xSemaphoreTake(lock,portMAX_DELAY);auto r=current;xSemaphoreGive(lock);return r;}
static void worker(void*) {
  uint32_t previous=0;TickType_t wake=xTaskGetTickCount();
  while(true){
    uint32_t started=micros();auto frame=camera_service::latestFrame();
    if(frame&&frame->id!=previous&&millis()-frame->capturedMs<aruco_config::MaxAgeMs){
      previous=frame->id;auto r=std::make_shared<Result>();r->frame=frame;r->workspaceBytes=workspaceBytes;
      Decode decode{frame.get()};uint32_t at=micros();
      int scale=0;while(((frame->profile.width>>scale)>Width||(frame->profile.height>>scale)>Height)&&scale<3)++scale;
      esp_err_t result=esp_jpg_decode(frame->size,jpg_scale_t(scale),readJpeg,writeGray,&decode);
      r->decodeUs=micros()-at;at=micros();
      if(result==ESP_OK&&decode.dimensionsOk){
        r->analysisWidth=decode.width;r->analysisHeight=decode.height;
        r->detection=aruco_detector::find(gray,decode.width,decode.height,workspace);
        auto calibration=aruco_config::calibration();double sx=decode.width/double(Width),sy=decode.height/double(Height);
        calibration.fx*=sx;calibration.fy*=sy;calibration.cx=(calibration.cx+.5)*sx-.5;calibration.cy=(calibration.cy+.5)*sy-.5;
        if(r->detection.valid)r->pose=marker_pose::estimate(r->detection.corners,aruco_config::MarkerSideM,calibration,aruco_config::MaxReprojectionPx);
      }else r->error="JPEG decode failed";
      r->detectUs=micros()-at;r->processingUs=micros()-started;r->completedMs=millis();
      // Wall busy fraction of one worker; NOT scheduler-measured CPU utilization.
      r->busyPercent=100.f*r->processingUs/std::max(float(aruco_config::IntervalMs*1000),float(r->processingUs));
      r->stackFreeBytes=uxTaskGetStackHighWaterMark(nullptr);
      xSemaphoreTake(lock,portMAX_DELAY);current=r;xSemaphoreGive(lock);
    }
    // Always leave idle time even if processing exceeds the target period.
    vTaskDelayUntil(&wake,pdMS_TO_TICKS(aruco_config::IntervalMs));vTaskDelay(1);
  }
}
template<class T> static bool allocate(T*& pointer,size_t n){pointer=static_cast<T*>(heap_caps_malloc(n*sizeof(T),MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT));if(pointer)workspaceBytes+=n*sizeof(T);return pointer!=nullptr;}
void begin(){
  lock=xSemaphoreCreateMutex();if(!lock){startupError="ArUco mutex allocation failed";return;}
  bool ok=allocate(gray,Pixels)&&allocate(workspace.integral,(Width+1)*(Height+1))&&allocate(workspace.queue,Pixels)&&
    allocate(workspace.binary,Pixels)&&allocate(workspace.boundary,aruco_detector::MaxBoundary)&&allocate(workspace.hull,aruco_detector::MaxBoundary*2);
  if(!ok){free(gray);free(workspace.integral);free(workspace.queue);free(workspace.binary);free(workspace.boundary);free(workspace.hull);startupError="ArUco PSRAM allocation failed";return;}
  if(xTaskCreatePinnedToCore(worker,"ArUco preview",8192,nullptr,1,nullptr,1)!=pdPASS){startupError="ArUco task allocation failed";return;}
  startupError=nullptr;
}
void json(char* out,size_t size,const Result* r,uint32_t now){
  uint32_t age=r&&r->frame?now-r->frame->capturedMs:UINT32_MAX;
  bool fresh=r&&r->frame&&age<=aruco_config::MaxAgeMs;
  bool detected=fresh&&r->detection.valid,posed=detected&&r->pose.valid;
  auto command=aruco_preview::propose(r?r->pose:marker_pose::Pose{},posed);
  char corners[160]="null",position[120]="null",angles[120]="null",distance[48]="null",depth[48]="null",cameraPosition[120]="null";
  if(detected){
    double x[4],y[4];for(int i=0;i<4;++i){x[i]=r->detection.corners[i].x;y[i]=r->detection.corners[i].y;aruco_image::map(x[i],y[i],r->analysisWidth,r->analysisHeight,aruco_config::DetectorMirrorX,aruco_config::DetectorFlipY);
      x[i]=(x[i]+.5)*r->frame->profile.width/r->analysisWidth-.5;y[i]=(y[i]+.5)*r->frame->profile.height/r->analysisHeight-.5;}
    snprintf(corners,sizeof(corners),"[[%.2f,%.2f],[%.2f,%.2f],[%.2f,%.2f],[%.2f,%.2f]]",x[0],y[0],x[1],y[1],x[2],y[2],x[3],y[3]);
  }
  if(posed){auto& p=r->pose;snprintf(position,sizeof(position),"[%.4f,%.4f,%.4f]",p.translation[0],p.translation[1],p.translation[2]);
    double camera[3];for(int i=0;i<3;++i)camera[i]=-(p.rotation[i]*p.translation[0]+p.rotation[3+i]*p.translation[1]+p.rotation[6+i]*p.translation[2]);
    snprintf(cameraPosition,sizeof(cameraPosition),"[%.4f,%.4f,%.4f]",camera[0],camera[1],camera[2]);
    constexpr double Degrees=180/3.14159265358979323846;
    snprintf(angles,sizeof(angles),"[%.2f,%.2f,%.2f]",p.roll*Degrees,p.pitch*Degrees,p.yaw*Degrees);
    snprintf(distance,sizeof(distance),"%.4f",p.distance);snprintf(depth,sizeof(depth),"%.4f",p.translation[2]);}
  const char* error=r?r->error:startupError;
  snprintf(out,size,"{\"backend\":\"esp32-aruco-7x7-id0\",\"frame_id\":%lu,\"age_ms\":%lu,\"max_age_ms\":%lu,\"fresh\":%s,\"detected\":%s,\"pose_valid\":%s,\"marker_id\":%d,\"placeholder\":%s,\"mount_verified\":%s,\"marker_side_m\":%.4f,\"target_height_m\":%.3f,\"corners\":%s,\"marker_in_camera_m\":%s,\"camera_in_marker_m\":%s,\"rpy_deg\":%s,\"distance_m\":%s,\"depth_m\":%s,\"reprojection_px\":%.3f,\"bit_errors\":%d,\"processing_ms\":%.3f,\"decode_ms\":%.3f,\"detect_pose_ms\":%.3f,\"worker_busy_percent\":%.1f,\"workspace_bytes\":%lu,\"heap_free\":%lu,\"psram_free\":%lu,\"stack_free_bytes\":%lu,\"preview_only\":true,\"command_valid\":%s,\"command\":\"%s\",\"body_velocity_mps\":[%.3f,%.3f,%.3f],\"yaw_rate_deg_s\":%.2f,\"error\":\"%s\"}",
    (unsigned long)(r&&r->frame?r->frame->id:0),(unsigned long)age,(unsigned long)aruco_config::MaxAgeMs,fresh?"true":"false",detected?"true":"false",posed?"true":"false",detected?0:-1,
    aruco_config::CalibrationVerified?"false":"true",aruco_config::MountVerified?"true":"false",aruco_config::MarkerSideM,aruco_config::TargetHeightM,
    corners,position,cameraPosition,angles,distance,depth,posed?r->pose.reprojectionPx:0,detected?r->detection.bitErrors:0,
    r?r->processingUs/1000.:0,r?r->decodeUs/1000.:0,r?r->detectUs/1000.:0,r?r->busyPercent:0,(unsigned long)workspaceBytes,
    (unsigned long)ESP.getFreeHeap(),(unsigned long)ESP.getFreePsram(),(unsigned long)(r?r->stackFreeBytes:0),command.valid?"true":"false",command.action,
    command.forward,command.right,command.down,command.yaw*180/3.14159265358979323846,error?error:"");
}
}
