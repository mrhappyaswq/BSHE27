#pragma once
#include <stdint.h>
#include <stddef.h>
#include <memory>
#include <stdlib.h>
#include "Pixhawk Communication/wire.h"
#include "Camera/altitude_profile.h"
namespace camera_service {
struct Frame {
  uint8_t* jpeg=nullptr;
  size_t size=0;
  uint32_t id=0, capturedMs=0, captureUs=0, jpegUs=0, prepareUs=0;
  float boardFps=0;
  altitude_profile::Profile profile;
  ~Frame() { free(jpeg); }
  Frame()=default;
  Frame(const Frame&)=delete;
  Frame& operator=(const Frame&)=delete;
};
using FramePtr=std::shared_ptr<const Frame>;
constexpr size_t HeaderSize=48;
// BSC1: little-endian header, then JPEG bytes. All timestamps are board time.
inline void frameHeader(uint8_t* out, const Frame* f, uint32_t now, uint32_t flags=0) {
  memset(out,0,HeaderSize); memcpy(out,"BSC1",4);
  wire::put<uint32_t>(out,4,f?uint32_t(f->size):0);
  wire::put<uint32_t>(out,8,f?f->id:0);
  wire::put<uint32_t>(out,12,f?f->capturedMs:0);
  wire::put<uint32_t>(out,16,now);
  wire::put<uint32_t>(out,20,f?f->captureUs:0);
  wire::put<uint32_t>(out,24,f?f->jpegUs:0);
  // Versioned profile metadata in the formerly reserved timing slot.
  wire::put<uint32_t>(out,28,f?altitude_profile::pack(f->profile):0);
  wire::put<float>(out,32,f?f->boardFps:0);
  wire::put<uint16_t>(out,36,f?f->profile.width:320); wire::put<uint16_t>(out,38,f?f->profile.height:240);
  wire::put<uint32_t>(out,40,f?now-f->capturedMs:0);
  wire::put<uint32_t>(out,44,flags);
}
FramePtr latestFrame();
void statsJson(char* out,size_t size);
}
