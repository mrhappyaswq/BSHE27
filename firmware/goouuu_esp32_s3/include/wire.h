#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>
namespace wire {
inline uint16_t accumulate(uint16_t crc, uint8_t b) {
  uint8_t t = b ^ uint8_t(crc); t ^= t << 4;
  return (crc >> 8) ^ (uint16_t(t) << 8) ^ (uint16_t(t) << 3) ^ (t >> 4);
}
inline int extra(uint32_t id) {
  switch (id) {
    case 0: return 50; case 1: return 124; case 24: return 24;
    case 33: return 104; case 66: return 148; case 76: return 152;
    case 77: return 143; case 84: return 143; case 86: return 5;
    default: return -1;
  }
}
template<class T> T get(const uint8_t* p, size_t at) {
  T value; memcpy(&value, p + at, sizeof(T)); return value;
}
template<class T> void put(uint8_t* p, size_t at, T value) {
  memcpy(p + at, &value, sizeof(T));
}
struct Frame { uint32_t id; uint8_t system, component, payload[255]; };
class Parser {
  uint8_t buffer[280] = {}; size_t used = 0;
public:
  uint32_t bad = 0, signedFrames = 0;
  bool feed(uint8_t byte, Frame& frame) {
    if (!used && byte != 0xfe && byte != 0xfd) return false;
    buffer[used++] = byte;
    if (used < 2) return false;
    bool v2 = buffer[0] == 0xfd;
    size_t header = v2 ? 10 : 6;
    if (used < header) return false;
    uint8_t flags = v2 ? buffer[2] : 0;
    size_t end = header + buffer[1], total = end + 2 + ((flags & 1) ? 13 : 0);
    if (used < total) return false;
    used = 0;
    uint32_t id = v2 ? uint32_t(buffer[7]) | uint32_t(buffer[8]) << 8 |
                            uint32_t(buffer[9]) << 16 : buffer[5];
    if (flags) { if (flags & 1) ++signedFrames; return false; }
    int crcExtra = extra(id);
    if (crcExtra < 0) return false;
    uint16_t crc = 0xffff;
    for (size_t i = 1; i < end; ++i) crc = accumulate(crc, buffer[i]);
    crc = accumulate(crc, crcExtra);
    if (crc != get<uint16_t>(buffer, end)) { ++bad; return false; }
    // MAVLink2 truncates trailing zero bytes, including base fields.
    const int minimum = id == 0 ? 9 : id == 1 ? 31 : id == 24 ? 30 :
                        id == 33 ? 28 : id == 77 ? 3 : 0;
    if (!v2 && buffer[1] < minimum) { ++bad; return false; }
    frame.id = id; frame.system = buffer[v2 ? 5 : 3];
    frame.component = buffer[v2 ? 6 : 4];
    memset(frame.payload, 0, sizeof(frame.payload));
    memcpy(frame.payload, buffer + header, buffer[1]); return true;
  }
};
inline size_t encode(uint8_t* out, uint8_t id, const uint8_t* payload,
                     uint8_t length, uint8_t seq, uint8_t sys, uint8_t comp) {
  out[0]=0xfe; out[1]=length; out[2]=seq; out[3]=sys; out[4]=comp; out[5]=id;
  memcpy(out+6,payload,length); uint16_t crc=0xffff;
  for (size_t i=1;i<size_t(length)+6;++i) crc=accumulate(crc,out[i]);
  put(out,length+6,accumulate(crc,extra(id))); return length+8;
}
}
