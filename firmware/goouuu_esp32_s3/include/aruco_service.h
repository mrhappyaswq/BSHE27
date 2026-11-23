#pragma once
#include "camera_frame.h"
#include "aruco_detector.h"
#include "marker_pose.h"
#include "aruco_preview.h"
namespace aruco_service {
struct Result {
  camera_service::FramePtr frame;
  aruco_detector::Detection detection;
  marker_pose::Pose pose;
  uint32_t completedMs=0,processingUs=0,decodeUs=0,detectUs=0;
  float busyPercent=0;
  uint32_t stackFreeBytes=0,workspaceBytes=0;
  uint16_t analysisWidth=320,analysisHeight=240;
  const char* error=nullptr;
};
using ResultPtr=std::shared_ptr<const Result>;
void begin();
ResultPtr latest();
void json(char* out,size_t size,const Result* result,uint32_t now);
}
