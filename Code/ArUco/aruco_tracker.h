#pragma once
#include "ArUco/aruco_detector.h"
#include "ArUco/aruco_config.h"
namespace aruco_detector {
class Tracker {
  Detection previous;
  int width=0,height=0;
  uint32_t seenAt=0,fullAt=0;
public:
  void reset(){previous=Detection{};width=height=0;seenAt=fullAt=0;}
  Detection find(const uint8_t* gray,int w,int h,Workspace& workspace,uint32_t now,
                 Profile* profile=nullptr,Clock clock=nullptr){
    bool useRegion=previous.valid&&w==width&&h==height&&
      uint32_t(now-seenAt)<=aruco_config::TrackingMaxAgeMs&&
      uint32_t(now-fullAt)<aruco_config::FullScanIntervalMs;
    Detection result;
    if(useRegion){
      float x0=w,y0=h,x1=0,y1=0;
      for(auto p:previous.corners){x0=std::min(x0,p.x);x1=std::max(x1,p.x);y0=std::min(y0,p.y);y1=std::max(y1,p.y);}
      int pad=std::max(24,int(std::max(x1-x0,y1-y0)*.4f));
      int left=std::max(0,int(floorf(x0))-pad),top=std::max(0,int(floorf(y0))-pad);
      int right=std::min(w,int(ceilf(x1))+pad+1),bottom=std::min(h,int(ceilf(y1))+pad+1);
      if((right-left)*(bottom-top)<w*h*4/5){
        if(profile)profile->tracked=true;
        result=aruco_detector::find(gray,w,h,workspace,{left,top,right-left,bottom-top},profile,clock);
      }
    }
    // A miss, stale track, format change or periodic refresh scans the SAME image.
    if(!result.valid){result=aruco_detector::find(gray,w,h,workspace,{},profile,clock);fullAt=now;}
    width=w;height=h;previous=result;if(result.valid)seenAt=now;
    return result;
  }
};
}
