#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string>
#include <vector>
#include <deque>
#include <algorithm>
#include <math.h>
using String=std::string;
constexpr double PI=3.14159265358979323846;
extern uint32_t testNow;
inline uint32_t millis() {return testNow;}
template<class T> T constrain(T v,T lo,T hi) {return std::max(lo,std::min(hi,v));}
struct HardwareSerial {
  std::deque<uint8_t> rx; std::vector<std::vector<uint8_t>> tx;
  explicit HardwareSerial(int) {}
  void setRxBufferSize(int) {} void begin(uint32_t,int,int,int) {}
  int available() const {return int(rx.size());}
  int read() {int b=rx.front();rx.pop_front();return b;}
  size_t write(const uint8_t* p,size_t n) {tx.emplace_back(p,p+n);return n;}
  void println(const String&) {}
};
extern HardwareSerial Serial;
constexpr int SERIAL_8N1=0;
