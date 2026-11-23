#pragma once
#include "Camera/camera_frame.h"
#include "ArUco/aruco_detector.h"
#include "ArUco/marker_pose.h"
#include "ArUco/aruco_preview.h"
namespace aruco_service {
struct Result {
  camera_service::FramePtr frame;
  aruco_detector::Detection detection;
  marker_pose::Pose pose;
  uint32_t completedMs=0,processingUs=0,decodeUs=0,detectUs=0;
  aruco_detector::Profile profile;
  uint32_t poseUs=0,internalBytes=0,externalBytes=0;
  float analysisFps=0,busyPercent=0;
  uint32_t stackFreeBytes=0,workspaceBytes=0;
  uint16_t analysisWidth=320,analysisHeight=240;
  const char* error=nullptr;
};
using ResultPtr=std::shared_ptr<const Result>;
void begin();
ResultPtr latest();
void json(char* out,size_t size,const Result* result,uint32_t now);
}
