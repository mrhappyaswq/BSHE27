#pragma once
#include "ArUco/aruco_config.h"
namespace aruco_preview {
struct Command { bool valid=false;float forward=0,right=0,down=0,yaw=0;const char* action="HOLD - no usable marker"; };
inline float limit(float v,float max){return fmaxf(-max,fminf(max,v));}
inline Command propose(const marker_pose::Pose& p,bool fresh) {
  Command c;if(!fresh||!p.valid)return c;
  constexpr float Pi=3.14159265358979323846f;
  if(p.tilt>Pi/3){c.action="HOLD - marker too oblique";return c;}
  float a=aruco_config::CameraTopClockwiseDeg*Pi/180;
  float x=-p.translation[1],y=p.translation[0];
  float forward=cosf(a)*x-sinf(a)*y,right=sinf(a)*x+cosf(a)*y;
  float yaw=remainderf(p.yaw+a,2*Pi);bool centered=hypotf(x,y)<aruco_config::PositionDeadbandM;
  bool aligned=fabsf(yaw)<aruco_config::YawDeadbandDeg*Pi/180;
  if(!centered){c.forward=limit(forward*aruco_config::PositionGain,aruco_config::MaxHorizontalMps);c.right=limit(right*aruco_config::PositionGain,aruco_config::MaxHorizontalMps);}
  if(!aligned)c.yaw=limit(yaw*aruco_config::YawGain,aruco_config::MaxYawRadps);
  if(centered&&aligned)c.down=limit((p.translation[2]-aruco_config::TargetHeightM)*aruco_config::PositionGain,aruco_config::MaxVerticalMps);
  if(fabsf(p.translation[2]-aruco_config::TargetHeightM)<.05f)c.down=0;
  c.valid=true;c.action=!centered?"ALIGN over marker":!aligned?"ALIGN heading":c.down>.001f?"DESCEND toward test height":c.down<-.001f?"CLIMB toward test height":"HOLD at test height";return c;
}
}
