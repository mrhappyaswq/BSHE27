#include "dashboard.h"
#include <Arduino.h>
#include "camera_frame.h"
#include "dashboard_page.h"
#include "camera_controls.h"
#include "wire.h"
namespace dashboard {
static portMUX_TYPE mux=portMUX_INITIALIZER_UNLOCKED;
static char snapshot[768]="{}"; static bool active=false;
void publish(const char* json,bool mission) { portENTER_CRITICAL(&mux); strlcpy(snapshot,json,sizeof(snapshot)); active=mission; portEXIT_CRITICAL(&mux); }
bool flying() { portENTER_CRITICAL(&mux); bool result=active; portEXIT_CRITICAL(&mux); return result; }
static esp_err_t status(httpd_req_t* r) {
  char copy[768]; portENTER_CRITICAL(&mux); strlcpy(copy,snapshot,sizeof(copy)); portEXIT_CRITICAL(&mux);
  httpd_resp_set_type(r,"application/json"); httpd_resp_set_hdr(r,"Cache-Control","no-store");
  char stats[384],json[1280]; camera_service::statsJson(stats,sizeof(stats));
  snprintf(json,sizeof(json),"%.*s,\"camera\":%s}",int(strlen(copy))-1,copy,stats);
  return httpd_resp_send(r,json,HTTPD_RESP_USE_STRLEN);
}
static esp_err_t home(httpd_req_t* r) {
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
void begin(esp_err_t (*capture)(httpd_req_t*),esp_err_t (*stream)(httpd_req_t*),esp_err_t (*frame)(httpd_req_t*)) {
  for(int i=0;i<2;++i) {
    httpd_config_t c=HTTPD_DEFAULT_CONFIG(); c.server_port=80+i;c.ctrl_port=32768+i;
    c.stack_size=12288; // Status JSON includes camera timing and float formatting.
    c.send_wait_timeout=2;c.lru_purge_enable=true; httpd_handle_t server=nullptr;
    if(httpd_start(&server,&c)!=ESP_OK) { Serial.println("HTTP server failed"); continue; }
    if(!i) {
      for(auto method:{HTTP_GET,HTTP_POST}) {httpd_uri_t route={};route.uri="/camera-control";route.method=method;route.handler=controls;
        if(httpd_register_uri_handler(server,&route)!=ESP_OK) Serial.println("Camera control route failed");}
    }
    const char* paths[]={"/","/status","/capture","/viewer","/stream","/frame"};
    esp_err_t (*handlers[])(httpd_req_t*)={home,status,capture,home,stream,frame};
    for(int j=i?4:0;j<(i?6:4);++j) {
      httpd_uri_t route={};route.uri=paths[j];route.method=HTTP_GET;route.handler=handlers[j];
      if(httpd_register_uri_handler(server,&route)!=ESP_OK) Serial.println("HTTP route failed");
    }
  }
}
}
