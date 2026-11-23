#include "Web Server/dashboard.h"
#include <Arduino.h>
#include <WiFi.h>
#include <esp_wifi.h>
#include <atomic>
#include <lwip/sockets.h>
#include "Camera/camera_frame.h"
#include "Camera/camera_service.h"
#include "Web Server/dashboard_page.h"
#include "Camera/camera_controls.h"
#include "Pixhawk Communication/wire.h"
namespace dashboard {
static portMUX_TYPE mux=portMUX_INITIALIZER_UNLOCKED;
static char snapshot[1536]="{}";static bool active=false,heartbeatSeen=false;
static uint32_t sampleAt=0,heartbeatAt=0;
static std::atomic<uint32_t> pageRequests{0},telemetryRequests{0},telemetryOk{0},telemetryErrors{0};
void statsJson(char* out,size_t size) {
  uint8_t protocol=0;esp_wifi_get_protocol(WIFI_IF_AP,&protocol);
  snprintf(out,size,"{\"wifi_clients\":%u,\"protocol_mask\":%u,\"page_requests\":%lu,\"telemetry_requests\":%lu,\"telemetry_ok\":%lu,\"telemetry_errors\":%lu}",
    unsigned(WiFi.softAPgetStationNum()),unsigned(protocol),(unsigned long)pageRequests.load(),(unsigned long)telemetryRequests.load(),
    (unsigned long)telemetryOk.load(),(unsigned long)telemetryErrors.load());
}
void publish(const char* json,bool mission,uint32_t heartbeat,bool seen) {
  portENTER_CRITICAL(&mux);strlcpy(snapshot,json,sizeof(snapshot));active=mission;
  sampleAt=millis();heartbeatAt=heartbeat;heartbeatSeen=seen;portEXIT_CRITICAL(&mux);
}
bool flying() { portENTER_CRITICAL(&mux);bool result=active;portEXIT_CRITICAL(&mux);return result; }
static esp_err_t telemetryResponse(httpd_req_t* r,bool withCamera) {
  char copy[1536];uint32_t sampled,hb;bool seen;
  portENTER_CRITICAL(&mux);strlcpy(copy,snapshot,sizeof(copy));sampled=sampleAt;hb=heartbeatAt;seen=heartbeatSeen;portEXIT_CRITICAL(&mux);
  if(!strcmp(copy,"{}")) {
    httpd_resp_set_status(r,"503 Service Unavailable");
    httpd_resp_set_hdr(r,"Access-Control-Allow-Origin","*");
    httpd_resp_set_hdr(r,"Cache-Control","no-store");
    return httpd_resp_send(r,"Telemetry initializing",HTTPD_RESP_USE_STRLEN);
  }
  uint32_t now=millis();char hbAge[16]="null";
  if(seen)snprintf(hbAge,sizeof(hbAge),"%lu",(unsigned long)(now-hb));
  char stats[384]="",camera[416]="",json[2304];
  if(withCamera){camera_service::statsJson(stats,sizeof(stats));snprintf(camera,sizeof(camera),",\"camera\":%s",stats);}
  snprintf(json,sizeof(json),"%.*s,\"uptime_ms\":%lu,\"sample_age_ms\":%lu,\"heartbeat_age_ms\":%s,\"heap_free\":%lu,\"psram_free\":%lu,\"wifi_clients\":%u%s}",
    int(strlen(copy))-1,copy,(unsigned long)now,(unsigned long)(now-sampled),hbAge,
    (unsigned long)ESP.getFreeHeap(),(unsigned long)ESP.getFreePsram(),unsigned(WiFi.softAPgetStationNum()),camera);
  httpd_resp_set_type(r,"application/json");httpd_resp_set_hdr(r,"Cache-Control","no-store");
  httpd_resp_set_hdr(r,"Access-Control-Allow-Origin","*");
  return httpd_resp_send(r,json,HTTPD_RESP_USE_STRLEN);
}
static esp_err_t status(httpd_req_t* r) {return telemetryResponse(r,true);}
static esp_err_t health(httpd_req_t* r) {
  httpd_resp_set_type(r,"application/json");
  httpd_resp_set_hdr(r,"Cache-Control","no-store");
  httpd_resp_set_hdr(r,"Access-Control-Allow-Origin","*");
  return httpd_resp_send(r,"{\"ok\":true}",HTTPD_RESP_USE_STRLEN);
}
static esp_err_t telemetry(httpd_req_t* r) {
  ++telemetryRequests;esp_err_t result=telemetryResponse(r,false);
  if(result==ESP_OK)++telemetryOk;else ++telemetryErrors;return result;
}
static esp_err_t home(httpd_req_t* r) {
  ++pageRequests;
  if(!strcmp(r->uri,"/viewer")) httpd_resp_set_hdr(r,"Content-Disposition","attachment; filename=BSHE27-USB-viewer.html");
  httpd_resp_set_type(r,"text/html; charset=utf-8");
  httpd_resp_set_hdr(r,"Cache-Control","no-store");
  return httpd_resp_send(r,CAMERA_PAGE,HTTPD_RESP_USE_STRLEN);
}
static esp_err_t controls(httpd_req_t* r) {
  char json[448];
  if(r->method==HTTP_GET) camera_controls::status(json,sizeof(json));
  else {
    uint8_t body[7];size_t used=0;
    if(r->content_len!=sizeof(body)) return httpd_resp_send_err(r,HTTPD_400_BAD_REQUEST,"Expected seven camera-control bytes");
    while(used<sizeof(body)) {int n=httpd_req_recv(r,reinterpret_cast<char*>(body)+used,sizeof(body)-used);if(n<=0) return ESP_FAIL;used+=n;}
    if(body[0]>1) return httpd_resp_send_err(r,HTTPD_400_BAD_REQUEST,"Invalid camera mode");
    camera_controls::apply(body[0]==1,wire::get<uint32_t>(body,1),wire::get<uint16_t>(body,5),json,sizeof(json));
  }
  httpd_resp_set_type(r,"application/json");httpd_resp_set_hdr(r,"Cache-Control","no-store");
  return httpd_resp_send(r,json,HTTPD_RESP_USE_STRLEN);
}
static esp_err_t configureSocket(httpd_handle_t,int socket) {
  int enabled=1;
  return setsockopt(socket,IPPROTO_TCP,TCP_NODELAY,&enabled,sizeof(enabled))==0 ? ESP_OK : ESP_FAIL;
}
static esp_err_t profile(httpd_req_t* r){
  uint8_t body[3];int used=0;if(r->content_len!=3)return httpd_resp_send_err(r,HTTPD_400_BAD_REQUEST,"Expected three profile bytes");
  while(used<3){int n=httpd_req_recv(r,reinterpret_cast<char*>(body)+used,3-used);if(n<=0)return ESP_FAIL;used+=n;}
  if(body[0]>1)return httpd_resp_send_err(r,HTTPD_400_BAD_REQUEST,"Invalid simulation mode");
  char json[320];camera_service::simulateAltitude(body[0]!=0,wire::get<uint16_t>(body,1),json,sizeof(json));
  httpd_resp_set_type(r,"application/json");httpd_resp_set_hdr(r,"Cache-Control","no-store");return httpd_resp_send(r,json,HTTPD_RESP_USE_STRLEN);
}
void begin(esp_err_t (*capture)(httpd_req_t*),esp_err_t (*stream)(httpd_req_t*),esp_err_t (*frame)(httpd_req_t*)) {
  for(int i=0;i<2;++i) {
    httpd_config_t c=HTTPD_DEFAULT_CONFIG(); c.server_port=80+i;c.ctrl_port=32768+i;
    c.stack_size=12288; // Status JSON includes camera timing and float formatting.
    c.max_uri_handlers=12;
    c.open_fn=configureSocket;
    c.send_wait_timeout=2;c.lru_purge_enable=true; httpd_handle_t server=nullptr;
    if(httpd_start(&server,&c)!=ESP_OK) { Serial.println("HTTP server failed"); continue; }
    if(!i) {
      httpd_uri_t p={};p.uri="/camera-profile";p.method=HTTP_POST;p.handler=profile;
      if(httpd_register_uri_handler(server,&p)!=ESP_OK)Serial.println("Camera profile route failed");
      for(auto method:{HTTP_GET,HTTP_POST}) {httpd_uri_t route={};route.uri="/camera-control";route.method=method;route.handler=controls;
        if(httpd_register_uri_handler(server,&route)!=ESP_OK) Serial.println("Camera control route failed");}
    }
    const char* paths[]={"/","/status","/capture","/viewer","/telemetry","/health","/stream","/frame","/capture"};
    esp_err_t (*handlers[])(httpd_req_t*)={home,status,capture,home,telemetry,health,stream,frame,capture};
    for(int j=i?6:0;j<(i?9:6);++j) {
      httpd_uri_t route={};route.uri=paths[j];route.method=HTTP_GET;route.handler=handlers[j];
      if(httpd_register_uri_handler(server,&route)!=ESP_OK) Serial.println("HTTP route failed");
    }
  }
}
}
