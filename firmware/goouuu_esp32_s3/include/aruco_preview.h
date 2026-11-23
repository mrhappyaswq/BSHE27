#pragma once
#include "aruco_config.h"
namespace aruco_preview {
struct Command { bool valid=false;double forward=0,right=0,down=0,yaw=0;const char* action="HOLD - no usable marker"; };
inline double limit(double v,double max){return fmax(-max,fmin(max,v));}
inline Command propose(const marker_pose::Pose& p,bool fresh) {
  Command c;if(!fresh||!p.valid)return c;
  constexpr double Pi=3.14159265358979323846;
  if(p.tilt>Pi/3){c.action="HOLD - marker too oblique";return c;}
  double a=aruco_config::CameraTopClockwiseDeg*Pi/180;
  double x=-p.translation[1],y=p.translation[0];
  double forward=cos(a)*x-sin(a)*y,right=sin(a)*x+cos(a)*y;
  double yaw=remainder(p.yaw+a,2*Pi);bool centered=hypot(x,y)<aruco_config::PositionDeadbandM;
  bool aligned=fabs(yaw)<aruco_config::YawDeadbandDeg*Pi/180;
  if(!centered){c.forward=limit(forward*aruco_config::PositionGain,aruco_config::MaxHorizontalMps);c.right=limit(right*aruco_config::PositionGain,aruco_config::MaxHorizontalMps);}
  if(!aligned)c.yaw=limit(yaw*aruco_config::YawGain,aruco_config::MaxYawRadps);
  if(centered&&aligned)c.down=limit((p.translation[2]-aruco_config::TargetHeightM)*aruco_config::PositionGain,aruco_config::MaxVerticalMps);
  if(fabs(p.translation[2]-aruco_config::TargetHeightM)<.05)c.down=0;
  c.valid=true;c.action=!centered?"ALIGN over marker":!aligned?"ALIGN heading":c.down>.001?"DESCEND toward test height":c.down<-.001?"CLIMB toward test height":"HOLD at test height";return c;
}
}
