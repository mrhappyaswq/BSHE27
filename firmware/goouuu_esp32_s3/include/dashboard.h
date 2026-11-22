#pragma once
#include <esp_http_server.h>
namespace dashboard {
void begin(esp_err_t (*capture)(httpd_req_t*),esp_err_t (*stream)(httpd_req_t*),esp_err_t (*frame)(httpd_req_t*));
void publish(const char* json, bool mission);
bool flying();
}
