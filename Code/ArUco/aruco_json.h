#pragma once
#include <stdio.h>
#include "ArUco/aruco_service.h"
namespace aruco_service {
inline void formatJson(char* out,size_t size,const Result* r,uint32_t now,uint32_t heap,uint32_t psram,const char* startupError){
  uint32_t age=r&&r->frame?now-r->frame->capturedMs:UINT32_MAX;
  bool fresh=r&&r->frame&&age<=aruco_config::MaxAgeMs;
  bool detected=fresh&&r->detection.valid,posed=detected&&r->pose.valid;
  auto command=aruco_preview::propose(r?r->pose:marker_pose::Pose{},posed);
  char corners[160]="null",position[120]="null",angles[120]="null",distance[48]="null",depth[48]="null",cameraPosition[120]="null";
  if(detected){
    float x[4],y[4];for(int i=0;i<4;++i){x[i]=r->detection.corners[i].x;y[i]=r->detection.corners[i].y;aruco_image::map(x[i],y[i],r->analysisWidth,r->analysisHeight,aruco_config::DetectorMirrorX,aruco_config::DetectorFlipY);
      x[i]=(x[i]+.5f)*r->frame->profile.width/r->analysisWidth-.5f;y[i]=(y[i]+.5f)*r->frame->profile.height/r->analysisHeight-.5f;}
    snprintf(corners,sizeof(corners),"[[%.2f,%.2f],[%.2f,%.2f],[%.2f,%.2f],[%.2f,%.2f]]",x[0],y[0],x[1],y[1],x[2],y[2],x[3],y[3]);
  }
  if(posed){auto& p=r->pose;snprintf(position,sizeof(position),"[%.4f,%.4f,%.4f]",p.translation[0],p.translation[1],p.translation[2]);
    float camera[3];for(int i=0;i<3;++i)camera[i]=-(p.rotation[i]*p.translation[0]+p.rotation[3+i]*p.translation[1]+p.rotation[6+i]*p.translation[2]);
    snprintf(cameraPosition,sizeof(cameraPosition),"[%.4f,%.4f,%.4f]",camera[0],camera[1],camera[2]);
    constexpr float Degrees=180/3.14159265358979323846f;
    snprintf(angles,sizeof(angles),"[%.2f,%.2f,%.2f]",p.roll*Degrees,p.pitch*Degrees,p.yaw*Degrees);
    snprintf(distance,sizeof(distance),"%.4f",p.distance);snprintf(depth,sizeof(depth),"%.4f",p.translation[2]);}
  const char* error=r?r->error:startupError;
  snprintf(out,size,"{\"pipeline_version\":2,\"decoder\":\"JPEGDEC-1.8.2-luma\",\"backend\":\"esp32-aruco-7x7-id0\",\"frame_id\":%lu,\"age_ms\":%lu,\"max_age_ms\":%lu,\"fresh\":%s,\"detected\":%s,\"pose_valid\":%s,\"marker_id\":%d,\"placeholder\":%s,\"mount_verified\":%s,\"marker_side_m\":%.4f,\"target_height_m\":%.3f,\"corners\":%s,\"marker_in_camera_m\":%s,\"camera_in_marker_m\":%s,\"rpy_deg\":%s,\"distance_m\":%s,\"depth_m\":%s,\"reprojection_px\":%.3f,\"bit_errors\":%d,\"processing_ms\":%.3f,\"decode_ms\":%.3f,\"detect_pose_ms\":%.3f,\"prepare_ms\":%.3f,\"search_ms\":%.3f,\"identify_ms\":%.3f,\"pose_ms\":%.3f,\"analysis_fps\":%.2f,\"search_pixels\":%lu,\"tracked_search\":%s,\"internal_workspace_bytes\":%lu,\"external_workspace_bytes\":%lu,\"worker_busy_percent\":%.1f,\"workspace_bytes\":%lu,\"heap_free\":%lu,\"psram_free\":%lu,\"stack_free_bytes\":%lu,\"preview_only\":true,\"command_valid\":%s,\"command\":\"%s\",\"body_velocity_mps\":[%.3f,%.3f,%.3f],\"yaw_rate_deg_s\":%.2f,\"error\":\"%s\"}",
    (unsigned long)(r&&r->frame?r->frame->id:0),(unsigned long)age,(unsigned long)aruco_config::MaxAgeMs,fresh?"true":"false",detected?"true":"false",posed?"true":"false",detected?0:-1,
    aruco_config::CalibrationVerified?"false":"true",aruco_config::MountVerified?"true":"false",aruco_config::MarkerSideM,aruco_config::TargetHeightM,
    corners,position,cameraPosition,angles,distance,depth,posed?r->pose.reprojectionPx:0,detected?r->detection.bitErrors:0,
    r?r->processingUs/1000.:0,r?r->decodeUs/1000.:0,r?r->detectUs/1000.:0,
    r?r->profile.prepareUs/1000.:0,r?r->profile.searchUs/1000.:0,r?r->profile.identifyUs/1000.:0,r?r->poseUs/1000.:0,r?r->analysisFps:0,
    (unsigned long)(r?r->profile.pixels:0),r&&r->profile.tracked?"true":"false",
    (unsigned long)(r?r->internalBytes:0),(unsigned long)(r?r->externalBytes:0),r?r->busyPercent:0,(unsigned long)(r?r->workspaceBytes:0),
    (unsigned long)heap,(unsigned long)psram,(unsigned long)(r?r->stackFreeBytes:0),command.valid?"true":"false",command.action,
    command.forward,command.right,command.down,command.yaw*180/3.14159265358979323846f,error?error:"");
}
}
