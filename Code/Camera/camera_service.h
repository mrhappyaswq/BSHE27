#pragma once
#include <Arduino.h>
struct Marker { bool valid=false; float x=0,y=0,yaw=0; uint32_t at=0,id=0; };
namespace camera_service {
extern const char* error;
void begin();
bool photo();
bool simulateAltitude(bool enabled,uint16_t centimeters,char* out,size_t size);
}
