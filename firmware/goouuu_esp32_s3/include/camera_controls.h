#pragma once
#include <stddef.h>
#include <stdint.h>
namespace camera_controls {
void begin();
// The same bounded, camera-only operations serve USB, HTTP and the TTL console.
// manual=false restores auto exposure/gain; manual uses microseconds and gain*16.
bool apply(bool manual,uint32_t exposureUs,uint16_t gain16,char* out,size_t size);
bool status(char* out,size_t size);
}
