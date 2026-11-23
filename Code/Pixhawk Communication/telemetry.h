#pragma once
#include <stdio.h>
#include "Pixhawk Communication/vehicle.h"
// Called only by the main UART/mission task. HTTP serves a locked copy and
// never reads mutable Vehicle fields or transmits commands to the FC.
inline void telemetryJson(const Vehicle& v,uint32_t now,uint32_t sequence,bool mission,int phase,
                          const char* message,const char* cameraError,float cameraFps,char* out,size_t size) {
  bool link=v.haveHeartbeat && uint32_t(now-v.heartbeatAt)<settings::HeartbeatTimeout;
  bool position=link && v.havePosition && uint32_t(now-v.positionAt)<settings::TelemetryTimeout;
  bool gps=link && v.haveGps && uint32_t(now-v.gpsAt)<settings::TelemetryTimeout;
  bool status=link && v.haveStatus && uint32_t(now-v.statusAt)<settings::TelemetryTimeout;
  char mode[16]="null",alt[32]="null",battery[32]="null",fix[8]="null",sat[8]="null";
  char posAge[16]="null",gpsAge[16]="null",statusAge[16]="null";
  if(v.havePosition)snprintf(posAge,sizeof(posAge),"%lu",(unsigned long)(now-v.positionAt));
  if(v.haveGps)snprintf(gpsAge,sizeof(gpsAge),"%lu",(unsigned long)(now-v.gpsAt));
  if(v.haveStatus)snprintf(statusAge,sizeof(statusAge),"%lu",(unsigned long)(now-v.statusAt));
  if(link) snprintf(mode,sizeof(mode),"%lu",(unsigned long)v.mode);
  if(position) snprintf(alt,sizeof(alt),"%.3f",v.altitude);
  if(status && v.batteryKnown) snprintf(battery,sizeof(battery),"%.3f",v.battery);
  if(gps) {snprintf(fix,sizeof(fix),"%u",v.fix);snprintf(sat,sizeof(sat),"%u",v.satellites);}
  snprintf(out,size,"{\"board\":\"GOOUUU ESP32-S3\",\"seq\":%lu,\"sample_ms\":%lu,\"linked\":%s,\"heartbeat_seen\":%s,\"heartbeat_timeout_ms\":%lu,\"armed\":%s,\"mode\":%s,\"position_fresh\":%s,\"relative_altitude_m\":%s,\"gps_fix\":%s,\"satellites\":%s,\"battery_v\":%s,\"position_age_ms\":%s,\"gps_age_ms\":%s,\"status_age_ms\":%s,\"data_timeout_ms\":%lu,\"uart_bytes\":%lu,\"heartbeats\":%lu,\"bad_crc\":%lu,\"signed_rejected\":%lu,\"camera_error\":\"%s\",\"camera_fps\":%.2f,\"vision_backend\":\"esp32-aruco-7x7-id0\",\"mission_active\":%s,\"phase\":%d,\"message\":\"%s\"}",
    (unsigned long)sequence,(unsigned long)now,link?"true":"false",v.haveHeartbeat?"true":"false",(unsigned long)settings::HeartbeatTimeout,
    link?(v.armed()?"true":"false"):"null",mode,position?"true":"false",alt,fix,sat,battery,posAge,gpsAge,statusAge,(unsigned long)settings::TelemetryTimeout,
    (unsigned long)v.bytes,(unsigned long)v.heartbeats,(unsigned long)v.parser.bad,(unsigned long)v.parser.signedFrames,
    cameraError?cameraError:"",cameraFps,mission?"true":"false",phase,message);
}
