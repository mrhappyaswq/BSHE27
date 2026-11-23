#pragma once
#include <Arduino.h>
#include "settings.h"
#include "wire.h"
struct Vehicle {
  HardwareSerial uart{1}; wire::Parser parser;
  uint32_t heartbeatAt=0, positionAt=0, gpsAt=0, statusAt=0;
  bool haveHeartbeat=false, havePosition=false, haveGps=false, haveStatus=false, batteryKnown=false;
  uint32_t mode=0, present=0, enabled=0, healthy=0, bytes=0, heartbeats=0;
  uint8_t baseMode=0, state=0, fix=0, satellites=0, sequence=0;
  int32_t lat=0, lon=0; float altitude=0, battery=0;
  uint16_t pending=0; int ack=-1; uint32_t commandAt=0;
  bool active=false, txFault=false;
  bool linked() const { return haveHeartbeat && millis()-heartbeatAt<settings::HeartbeatTimeout; }
  bool positioned() const { return havePosition && millis()-positionAt<settings::TelemetryTimeout; }
  bool ready() const {
    return linked() && positioned() && haveGps && haveStatus &&
      millis()-gpsAt<3000 && millis()-statusAt<3000 && fix>=3 && state==3 &&
      (present & enabled & healthy & (1UL<<28));
  }
  bool armed() const { return baseMode & 128; }
  void begin() { uart.setRxBufferSize(8192); uart.begin(settings::Baud,SERIAL_8N1,settings::Rx,settings::Tx); }
  void send(uint8_t id,const uint8_t* p,uint8_t n) {
    uint8_t out[280]; size_t count=wire::encode(out,id,p,n,sequence++,settings::Source,settings::SourceComponent);
    if (uart.write(out,count)!=count) txFault=true;
  }
  void poll() {
    wire::Frame f;
    for (int budget=0;budget<2048 && uart.available();++budget) {
      ++bytes; if (!parser.feed(uart.read(),f)) continue;
      if (f.system!=settings::System || f.component!=settings::Component) continue;
      const uint8_t* p=f.payload; uint32_t now=millis();
      switch(f.id) {
        case 0: {
          uint8_t type=p[4];
          if(p[5]!=3 || !(type==2 || type==3 || type==4 || type==13 || type==14 || type==15 || type==29 || type==35)) break;
          mode=wire::get<uint32_t>(p,0); baseMode=p[6]; state=p[7];
          heartbeatAt=now; haveHeartbeat=true; ++heartbeats; break;
        }
        case 1: present=wire::get<uint32_t>(p,0); enabled=wire::get<uint32_t>(p,4);
          healthy=wire::get<uint32_t>(p,8); batteryKnown=wire::get<uint16_t>(p,14)!=65535;
          battery=batteryKnown?wire::get<uint16_t>(p,14)*0.001f:0;
          statusAt=now; haveStatus=true; break;
        case 24: fix=p[28]; satellites=p[29]; gpsAt=now; haveGps=true; break;
        case 33: lat=wire::get<int32_t>(p,4); lon=wire::get<int32_t>(p,8);
          altitude=wire::get<int32_t>(p,16)*0.001f; positionAt=now;
          havePosition=lat>=-900000000 && lat<=900000000 && lon>=-1800000000 && lon<=1800000000; break;
        case 77: if(pending && wire::get<uint16_t>(p,0)==pending &&
          (!p[8] || p[8]==settings::Source) && (!p[9] || p[9]==settings::SourceComponent)) ack=p[2]; break;
      }
    }
    static uint32_t sent=0;
    if(active && millis()-sent>=1000) {
      uint8_t p[9]={}; p[4]=18; p[5]=8; p[7]=4; p[8]=3;
      send(0,p,9); sent=millis();
    }
  }
  void streams() { uint8_t p[6]={}; wire::put<uint16_t>(p,0,4); p[2]=settings::System;
    p[3]=settings::Component; p[5]=1; send(66,p,6); }
  void command(uint16_t cmd,float p1=0,float p2=0,float p7=0) {
    uint8_t p[33]={}; wire::put(p,0,p1); wire::put(p,4,p2); wire::put(p,24,p7);
    wire::put(p,28,cmd); p[30]=settings::System; p[31]=settings::Component;
    pending=cmd; ack=-1; commandAt=millis(); send(76,p,33);
  }
  bool accepted() const { return ack==0; }
  bool failed() const { return txFault || (ack>=0 && ack!=0 && ack!=5) || millis()-commandAt>5000; }
  void velocity(float forward=0,float right=0,float down=0,float yaw=0) {
    uint8_t p[53]={}; wire::put(p,0,millis()); wire::put(p,16,forward);
    wire::put(p,20,right); wire::put(p,24,down); wire::put(p,44,yaw);
    wire::put<uint16_t>(p,48,0x05c7); p[50]=settings::System; p[51]=settings::Component; p[52]=8; send(84,p,53);
  }
  void go(int32_t latitude,int32_t longitude,float alt) {
    uint8_t p[53]={}; wire::put(p,0,millis()); wire::put(p,4,latitude);
    wire::put(p,8,longitude); wire::put(p,12,alt); wire::put<uint16_t>(p,48,0x0df8);
    p[50]=settings::System; p[51]=settings::Component; p[52]=3; send(86,p,53);
  }
};
