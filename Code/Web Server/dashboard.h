#pragma once
#include <esp_http_server.h>
namespace dashboard {
void begin(esp_err_t (*capture)(httpd_req_t*),esp_err_t (*stream)(httpd_req_t*),esp_err_t (*frame)(httpd_req_t*));
void publish(const char* json, bool mission,uint32_t heartbeatAt=0,bool heartbeatSeen=false);
bool flying();
void statsJson(char* out,size_t size);
}
