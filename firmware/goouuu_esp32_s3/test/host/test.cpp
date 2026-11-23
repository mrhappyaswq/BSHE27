#include <assert.h>
#include <stdio.h>
#include "mission.h"
#include "camera_frame.h"
#include "vectors.h"
#include "exposure_math.h"
#include "telemetry.h"
#include "marker_pose.h"
#include "aruco_tests.h"
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
int main(int argc,char** argv) {
  {
    auto base=altitude_profile::select(false,2000),low=altitude_profile::select(true,199),mid=altitude_profile::select(true,200),high=altitude_profile::select(true,800);
    assert(base.mode==0&&base.width==320&&base.quality==20&&base.targetFps==0);
    assert(low.width==320&&low.height==240&&low.quality==28&&low.targetFps==20);
    assert(mid.width==640&&mid.height==480&&mid.quality==20&&mid.targetFps==8);
    assert(high.width==1024&&high.height==768&&high.quality==10&&high.targetFps==2);
    assert(altitude_profile::select(true,799).mode==2&&altitude_profile::select(true,2000).mode==3);
    auto packed=altitude_profile::pack(high);assert((packed>>28)==10&&(packed&63)==10&&((packed>>6)&31)==2&&((packed>>13)&2047)==800);
    camera_service::Frame frame;frame.profile=high;uint8_t h[camera_service::HeaderSize];camera_service::frameHeader(h,&frame,1000);
    assert(wire::get<uint16_t>(h,36)==1024&&wire::get<uint16_t>(h,38)==768&&wire::get<uint32_t>(h,28)==packed);
  }
  arucoTests();
  if(argc==2)arucoPhotoTest(argv[1]);
  {
    using namespace marker_pose;
    Calibration c;c.fx=240;c.fy=245;c.cx=160;c.cy=120;
    const double side=.2,angle=.4;
    for(bool distorted:{false,true}) {
      c.k1=distorted?-.15:0;c.k2=distorted?.03:0;c.p1=distorted?.001:0;
      Point points[4];const Point model[4]={{-.1,-.1},{.1,-.1},{.1,.1},{-.1,.1}};
      for(int i=0;i<4;++i)points[i]=project(cos(angle)*model[i].x+.08,model[i].y-.04,-sin(angle)*model[i].x+.8,c);
      Pose p=estimate(points,side,c);
      assert(p.valid && fabs(p.translation[0]-.08)<1e-6 && fabs(p.translation[1]+.04)<1e-6);
      assert(fabs(p.translation[2]-.8)<1e-6 && fabs(p.pitch-angle)<1e-6);
      assert(fabs(p.distance-sqrt(.08*.08+.04*.04+.8*.8))<1e-6 && p.reprojectionPx<1e-5);
      Pose doubled=estimate(points,side*2,c);assert(doubled.valid && fabs(doubled.distance-2*p.distance)<1e-6);
      Point t=points[1];points[1]=points[3];points[3]=t;assert(!estimate(points,side,c).valid);
    }
    Point collapsed[4];assert(!estimate(collapsed,side,c).valid);
    assert(!estimate(collapsed,0,c).valid);c.fx=0;assert(!estimate(collapsed,side,c).valid);
  }
  {
    Vehicle v;char json[1536];
    telemetryJson(v,testNow,1,false,0,"Passive monitor",nullptr,27.8f,json,sizeof(json));
    assert(strstr(json,"\"heartbeat_seen\":false") && strstr(json,"\"armed\":null") && strstr(json,"\"battery_v\":null"));
    fresh(v);v.altitude=1.25f;v.batteryKnown=true;v.battery=12.3f;
    telemetryJson(v,testNow,2,false,0,"Passive monitor",nullptr,27.8f,json,sizeof(json));
    assert(strstr(json,"\"armed\":false") && strstr(json,"\"relative_altitude_m\":1.250") && strstr(json,"\"battery_v\":12.300"));
    telemetryJson(v,testNow+3001,3,false,0,"Passive monitor",nullptr,27.8f,json,sizeof(json));
    assert(strstr(json,"\"linked\":true") && strstr(json,"\"relative_altitude_m\":null") && strstr(json,"\"battery_v\":null"));
    telemetryJson(v,testNow+5001,4,false,0,"Passive monitor",nullptr,27.8f,json,sizeof(json));
    assert(strstr(json,"\"heartbeat_seen\":true") && strstr(json,"\"linked\":false") && strstr(json,"\"mode\":null"));
    v.heartbeatAt=v.positionAt=v.gpsAt=v.statusAt=0xfffffff0;
    telemetryJson(v,16,5,false,0,"Passive monitor",nullptr,0,json,sizeof(json));
    assert(strstr(json,"\"linked\":true") && strstr(json,"\"position_age_ms\":32"));
  }
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
    assert(wire::get<uint32_t>(header,28)==altitude_profile::pack(f.profile));
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
