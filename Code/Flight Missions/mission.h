#pragma once
#include "Pixhawk Communication/vehicle.h"
#include "Camera/camera_service.h"
#include <math.h>
class Mission {
public:
  enum Phase { Idle, VisionCheck, Ready, Mode, Arm, Takeoff, Hold, Waypoint, Align, Landing, Stopped };
  Vehicle& v; Phase phase=Idle; String name, message="Passive monitor";
  uint32_t since=0,lastSetpoint=0,lastSeen=0,settledAt=0,frame=0; int frames=0,leg=0;
  float height=0; int32_t homeLat=0,homeLon=0,targetLat=0,targetLon=0;
  Marker external;
  bool aruco() const { return name=="aruco_landing" || name=="aruco_move_gps"; }
  bool gpsTrip() const { return name=="move_gps" || name=="aruco_move_gps"; }
  Marker observed() { Marker m=external; if(millis()-m.at>350) m.valid=false; return m; }
  void align() { frames=0; settledAt=0; frame=0; lastSeen=millis(); enter(Align); }
  explicit Mission(Vehicle& vehicle):v(vehicle) {}
  bool running() const { return phase!=Idle && phase!=Stopped; }
  void enter(Phase p) { phase=p; since=millis(); }
  void finish(const char* text) { message=text; enter(Stopped); v.active=false; v.pending=0; Serial.println(message); }
  void land(const char* text) { message=text; v.velocity(); v.command(176,1,9); enter(Landing); }
  void stop(const char* text) {
    if(running() && phase!=VisionCheck && phase!=Ready && v.linked() && v.armed() && v.mode==4) land(text);
    else finish(text);
  }
  void start(const String& requested) {
    if(running()) { Serial.println("Mission already running"); return; }
    if(requested!="hover" && requested!="hover_gps" && requested!="move_gps" && requested!="circle" && requested!="aruco_landing" && requested!="aruco_move_gps") {
      Serial.println("Unknown mission"); return;
    }
    if(!v.linked() || v.armed()) { Serial.println("Need fresh disarmed ArduCopter heartbeat"); return; }
    name=requested; height=name=="hover" || name=="circle" ? 10 : name=="hover_gps" ? 2 : 1.5;
    frames=0; frame=0; settledAt=0; leg=0; message="Preflight";
    v.txFault=false; v.active=true; v.streams(); enter(aruco() ? VisionCheck : Ready);
  }
  void waypoint() {
    double north=0,east=0;
    if(gpsTrip()) north=leg==0 ? 3 : 0;
    if(name=="circle" && leg<=36) { double angle=leg*2*PI/36; north=20*cos(angle); east=20*sin(angle); }
    double scale=cos(homeLat*1e-7*PI/180);
    if(fabs(scale)<1e-6) { stop("GPS offset too close to pole"); return; }
    targetLat=homeLat+int32_t(north/6378137*180/PI*1e7);
    double longitude=homeLon*1e-7+east/(6378137*scale)*180/PI;
    longitude=fmod(longitude+540,360)-180; targetLon=int32_t(longitude*1e7);
    enter(Waypoint); lastSetpoint=millis()-1000;
  }
  void tick() {
    if(!running()) return;
    uint32_t now=millis(),age=now-since;
    if(!v.linked()) { finish("Heartbeat lost; autopilot failsafes own recovery"); return; }
    if(v.txFault) { finish("UART write failed; autopilot failsafes own recovery"); return; }
    if(phase>=Takeoff && phase<Landing && (!v.armed() || v.mode!=4)) { finish("Pilot/autopilot interrupted mission"); return; }
    if(phase>=Takeoff && phase<Landing && !v.positioned()) { stop("Position telemetry stale"); return; }
    if(phase==VisionCheck) {
      Marker m=observed();
      if(!m.valid) frames=0;
      else if(m.id!=frame) { frame=m.id; ++frames; }
      if(frames>=3) enter(Ready);
      else if(age>10000) finish("Marker preflight failed");
    } else if(phase==Ready) {
      if(v.armed()) { finish("Vehicle armed outside mission"); return; }
      if(v.ready()) { v.command(176,1,4); enter(Mode); }
      else if(age>60000) finish("Prearm/GPS timeout");
    } else if(phase==Mode) {
      if(v.failed()) stop("GUIDED command failed");
      else if(v.accepted() && v.mode==4) { v.command(400,1); enter(Arm); }
    } else if(phase==Arm) {
      if(v.mode!=4) { finish("Mode changed during arming"); return; }
      if(v.failed()) stop("Arm command failed");
      else if(v.accepted() && v.armed()) {
        if(!v.positioned()) { stop("No position at takeoff"); return; }
        homeLat=v.lat; homeLon=v.lon; v.command(22,0,0,height); enter(Takeoff);
      }
    } else if(phase==Takeoff) {
      if(!v.accepted() && v.failed()) stop("Takeoff command failed");
      else if(v.accepted() && v.altitude>=height*0.95f) {
        if(name=="aruco_landing") align();
        else if(gpsTrip() || name=="circle") waypoint();
        else enter(Hold);
      } else if(age>45000) stop("Takeoff timeout");
      // ACK timeout applies only until the command has been accepted.
    } else if(phase==Hold) {
      uint32_t duration=name=="hover_gps" || name=="circle" ? 5000 : 10000;
      if(age>=duration) {
        if(gpsTrip() && leg==0) { ++leg; waypoint(); }
        else if(aruco()) align();
        else land("Mission landing");
      }
    } else if(phase==Waypoint) {
      if(!v.haveGps || now-v.gpsAt>3000 || v.fix<3) { stop("GPS fix stale or lost"); return; }
      if(now-lastSetpoint>=1000) { v.go(targetLat,targetLon,height); lastSetpoint=now; }
      double north=(int64_t(v.lat)-targetLat)*1e-7*PI/180*6378137;
      double delta=(int64_t(v.lon)-targetLon)*1e-7; delta=fmod(delta+540,360)-180;
      double east=delta*PI/180*6378137*cos(v.lat*1e-7*PI/180);
      if(hypot(north,east)<=0.5 && fabs(v.altitude-height)<=0.3) {
        if(name=="circle" && leg<37) { ++leg; waypoint(); } else enter(Hold);
      } else if(age>60000) stop("Waypoint timeout");
    } else if(phase==Align) {
      if(age>60000) { stop("Marker landing timeout"); return; }
      if(now-lastSetpoint<100) return; lastSetpoint=now;
      Marker m=observed();
      if(!m.valid) { frames=0; settledAt=0; v.velocity(); if(now-lastSeen>5000) stop("Marker lost"); return; }
      lastSeen=now;
      float dx=m.x-160,dy=m.y-120;
      bool aligned=fabsf(dx)<=10 && fabsf(dy)<=10 && fabsf(m.yaw)<=5*PI/180;
      if(!aligned) { frames=0; settledAt=0; }
      else { if(!settledAt) settledAt=now; if(m.id!=frame) ++frames; }
      frame=m.id;
      bool settled=aligned && now-settledAt>=500 && frames>=3;
      if(settled && v.altitude<=0.2f) { land("Marker aligned; LAND handoff"); return; }
      v.velocity(constrain(-dy*0.002f,-0.2f,0.2f),constrain(dx*0.002f,-0.2f,0.2f),
        settled ? 0.05f : 0,constrain(m.yaw*0.8f,-0.35f,0.35f));
    } else if(phase==Landing) {
      if(v.mode!=4 && v.mode!=9) { finish("Pilot changed landing mode"); return; }
      if(!v.armed() && v.mode==9) finish("Landed and disarmed");
      else if(v.failed() && v.mode!=9) finish("LAND unconfirmed; pilot action required");
      else if(age>90000) finish("Landing timeout; pilot action required");
    }
  }
};
