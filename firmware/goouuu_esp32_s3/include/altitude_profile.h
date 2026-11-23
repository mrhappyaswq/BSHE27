#pragma once
#include <stdint.h>
#include "settings.h"
namespace altitude_profile {
// Bench simulation only. No FC altitude, barometer, or flight commands involved.
struct Profile {
  uint16_t width=320,height=240,altitudeCm=0;
  uint8_t quality=settings::JpegQuality,targetFps=0,mode=0; // mode 0 = original camera settings
};
inline Profile select(bool enabled,uint16_t cm){
  Profile p;if(!enabled)return p;
  p.altitudeCm=cm;
  if(cm<200){p.mode=1;p.quality=28;p.targetFps=20;}
  else if(cm<800){p.mode=2;p.width=640;p.height=480;p.quality=20;p.targetFps=8;}
  else {p.mode=3;p.width=1024;p.height=768;p.quality=10;p.targetFps=2;}
  return p;
}
inline bool sameFormat(const Profile& a,const Profile& b){return a.width==b.width&&a.height==b.height&&a.quality==b.quality;}
inline uint32_t pack(const Profile& p){return 0xa0000000u|uint32_t(p.quality)|(uint32_t(p.targetFps)<<6)|(uint32_t(p.mode)<<11)|(uint32_t(p.altitudeCm)<<13);}
}
