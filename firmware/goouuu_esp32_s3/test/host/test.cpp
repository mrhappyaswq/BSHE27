#include <assert.h>
#include <stdio.h>
#include "mission.h"
#include "camera_frame.h"
#include "vectors.h"
#include "exposure_math.h"
uint32_t testNow=1000;
HardwareSerial Serial(0);
namespace camera_service { const char* error=nullptr; }
template<size_t N> void inject(Vehicle& v,const uint8_t (&p)[N]) {
  v.uart.rx.insert(v.uart.rx.end(),p,p+N);v.poll();
}
void fresh(Vehicle& v,bool armed=false,uint32_t mode=0) {
  v.haveHeartbeat=v.havePosition=v.haveStatus=v.haveGps=true;
  v.heartbeatAt=v.positionAt=v.statusAt=v.gpsAt=testNow;
  v.baseMode=armed?128:0;v.mode=mode;v.state=3;v.fix=3;
  v.present=v.enabled=v.healthy=1UL<<28;
}
int main() {
  {
    double row=exposure_math::rowUs(20000000,0,30,0x11,0x30,1600);
    assert(fabs(row-32)<0.0001); // 50 MHz SYSCLK, 1600 clocks per row.
    assert(exposure_math::rowsForUs(1000,row,1125)==31);
    assert(exposure_math::rowsForUs(500,row,1125)==16);
    assert(exposure_math::rowsForUs(1000,0,1125)==-1);
    assert(exposure_math::rowsForUs(20000,row,100)==-1);
    assert(exposure_math::rowsForUs(NAN,row,1125)==-1);
    assert(exposure_math::rowUs(20000000,-1,30,0x11,0x30,1600)==0);
  }
  {
    camera_service::Frame f;f.size=1234;f.id=5;f.capturedMs=900;
    f.captureUs=1200;f.jpegUs=2300;f.boardFps=8.5f;
    uint8_t header[camera_service::HeaderSize];
    camera_service::frameHeader(header,&f,1000);
    assert(!memcmp(header,"BSC1",4) && sizeof(header)==48);
    assert(wire::get<uint32_t>(header,4)==1234 && wire::get<uint32_t>(header,8)==5);
    assert(wire::get<uint32_t>(header,20)==1200 && wire::get<float>(header,32)==8.5f);
    assert(wire::get<uint32_t>(header,28)==0); // Reserved slot; no vision processing.
    assert(wire::get<uint32_t>(header,40)==100 && wire::get<uint32_t>(header,44)==0);
    camera_service::frameHeader(header,nullptr,1000,1);
    assert(wire::get<uint32_t>(header,4)==0 && wire::get<uint32_t>(header,44)==1);
    f.capturedMs=0xfffffff0;camera_service::frameHeader(header,&f,16);
    assert(wire::get<uint32_t>(header,40)==32); // Timestamp rollover.
  }
  {
    Vehicle v;inject(v,otherSystem);inject(v,wrongAutopilot);assert(!v.linked());
    inject(v,heartbeat1);assert(v.linked() && !v.armed());
    inject(v,heartbeat2);assert(v.armed() && v.mode==4);
    uint8_t corrupt[sizeof(heartbeat1)];memcpy(corrupt,heartbeat1,sizeof(corrupt));corrupt[6]^=1;
    inject(v,corrupt);assert(v.parser.bad==1 && v.heartbeats==2);
    testNow+=5001;assert(!v.linked());testNow=1000;
  }
  {
    Vehicle v;v.pending=22;inject(v,acceptedTakeoff);assert(v.accepted());
    v.pending=400;inject(v,deniedArm);assert(v.failed());
    v.pending=22;v.ack=-1;inject(v,deniedArm);assert(v.ack==-1);
    uint8_t signedPacket[sizeof(heartbeat2)+13]={};memcpy(signedPacket,heartbeat2,sizeof(heartbeat2));signedPacket[2]=1;
    inject(v,signedPacket);assert(v.parser.signedFrames==1 && !v.haveHeartbeat);
  }
  {
    Vehicle v;v.velocity(0.1f,-0.2f,0.05f,0.3f);
    assert(v.uart.tx.back()==std::vector<uint8_t>(expectedVelocity,expectedVelocity+sizeof(expectedVelocity)));
    v.sequence=0;v.go(370000000,-1220000000,1.5f);
    assert(v.uart.tx.back()==std::vector<uint8_t>(expectedGoto,expectedGoto+sizeof(expectedGoto)));
  }
  {
    Vehicle v;fresh(v);Mission m(v);m.start("qr_landing");
    assert(!m.running() && v.uart.tx.empty()); // Removed mission cannot initiate flight.
    m.start("aruco_landing");m.tick();
    assert(m.phase==Mission::VisionCheck && !v.armed());
    testNow+=10001;fresh(v);m.tick();
    assert(!m.running() && !v.armed()); // No detector means no takeoff.
  }
  {
    Vehicle v;fresh(v);Mission m(v);v.poll();assert(v.uart.tx.empty());
    fresh(v,true);m.start("hover");assert(!m.running() && v.uart.tx.empty());
    fresh(v);m.start("hover");m.tick();assert(m.phase==Mission::Mode && v.pending==176);
    v.ack=0;v.mode=4;m.tick();assert(m.phase==Mission::Arm && v.pending==400);
    v.ack=0;v.baseMode=128;m.tick();assert(m.phase==Mission::Takeoff && v.pending==22);
    v.ack=0;testNow+=6000;fresh(v,true,4);m.tick();assert(m.phase==Mission::Takeoff);
    v.altitude=10;m.tick();assert(m.phase==Mission::Hold);
    v.mode=5;size_t count=v.uart.tx.size();m.tick();assert(!m.running() && v.uart.tx.size()==count);
  }
  {
    Vehicle v;fresh(v,true,4);Mission m(v);m.name="aruco_landing";m.height=1.5;m.align();
    m.external=Marker{};testNow+=100;m.tick();assert(v.uart.tx.back()[5]==84);
    testNow+=5100;fresh(v,true,4);m.tick();assert(m.phase==Mission::Landing && v.pending==176);
    v.mode=9;v.baseMode=0;m.tick();assert(!m.running());
  }
  {
    Vehicle v;fresh(v,true,4);Mission m(v);m.name="aruco_landing";m.align();
    v.altitude=1;m.external.valid=true;m.external.x=160;m.external.y=120;m.external.yaw=0;
    for(int i=0;i<8;++i) {testNow+=100;fresh(v,true,4);m.external.at=testNow;m.external.id=1;m.tick();}
    assert(m.frames==1); // Cached captures never satisfy settling.
    for(int i=2;i<5;++i) {testNow+=100;fresh(v,true,4);m.external.id=i;m.external.at=testNow;m.tick();}
    assert(m.frames>=3 && m.phase==Mission::Align);
    v.altitude=0.1f;testNow+=100;fresh(v,true,4);m.external.at=testNow;++m.external.id;m.tick();
    assert(m.phase==Mission::Landing);
  }
  {
    Vehicle v;fresh(v);Mission m(v);m.start("hover");m.tick();
    v.ack=2;m.tick();assert(!m.running() && !v.armed());
    fresh(v,true,4);m.enter(Mission::Hold);v.positionAt=testNow-3001;m.tick();
    assert(m.phase==Mission::Landing); // Stale navigation never continues.
  }
  {
    Vehicle v;fresh(v,true,4);Mission m(v);m.name="move_gps";m.enter(Mission::Waypoint);
    v.gpsAt=testNow-3001;m.tick();assert(m.phase==Mission::Landing);
  }
  {
    Vehicle v;fresh(v,true,4);Mission m(v);m.name="aruco_landing";m.align();v.altitude=1;
    m.external.valid=true;m.external.x=160;m.external.y=120;m.external.yaw=0.5f;
    for(int i=0;i<10;++i) { testNow+=100;fresh(v,true,4);m.external.at=testNow;++m.external.id;m.tick(); }
    assert(wire::get<float>(v.uart.tx.back().data(),6+24)==0); // No descent while yaw misaligned.
    v.mode=5;size_t count=v.uart.tx.size();m.stop("Operator abort");
    assert(!m.running() && v.uart.tx.size()==count); // Never override pilot mode.
  }
  puts("C++ protocol interoperability and mission checks passed");
}
