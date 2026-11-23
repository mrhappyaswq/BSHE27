#include <Arduino.h>
#include <driver/usb_serial_jtag.h>
#include <hal/usb_serial_jtag_ll.h>
#include <algorithm>
#include <atomic>
#include "wired_camera.h"
#include "camera_frame.h"
#include "camera_service.h"
#include "camera_controls.h"
#include "dashboard.h"
#include "aruco_service.h"
namespace wired_camera {
static std::atomic<uint32_t> received{0},requests{0},sentBytes{0},failures{0};
static bool ready=false;
void statsJson(char* out,size_t size) {
  snprintf(out,size,"{\"ready\":%s,\"received_bytes\":%lu,\"requests\":%lu,\"sent_bytes\":%lu,\"send_failures\":%lu}",
    ready?"true":"false",(unsigned long)received.load(),(unsigned long)requests.load(),
    (unsigned long)sentBytes.load(),(unsigned long)failures.load());
}
// Use the ESP-IDF driver for RX and the hardware FIFO directly for TX.
// This explicitly terminates full-size USB transfers; Arduino HWCDC's
// disconnected-write fallback can discard queued bytes.
// The native USB Serial/JTAG peripheral remains on GPIO19/20.
// Serial remains the separate CH340/UART0 console, and UART1 owns Pixhawk.
static bool send(const uint8_t* data,size_t size) {
  uint32_t lastProgress=millis();
  uint32_t lastPacket=0;
  while(size && millis()-lastProgress<1000) {
    // One worker owns TX. Flush each USB packet and honor host backpressure;
    // never drop queued bytes or let the USB task block the mission loop.
    size_t count=std::min(size,size_t(USB_SERIAL_JTAG_PACKET_SZ_BYTES));
    uint32_t sent=usb_serial_jtag_ll_write_txfifo(data,count);
    if(sent>0) {
      data+=sent; size-=sent; sentBytes+=sent; lastProgress=millis();
      lastPacket=sent;
      usb_serial_jtag_ll_txfifo_flush();
    }
    else {
      // USB may become writable again within microseconds. Sleeping a full
      // RTOS tick for every 64-byte packet needlessly caps throughput.
      // Briefly poll, then yield if the laptop is actually applying pressure.
      uint32_t waitStarted=micros();
      while(!usb_serial_jtag_ll_txfifo_writable() && uint32_t(micros()-waitStarted)<100) {}
      if(!usb_serial_jtag_ll_txfifo_writable()) vTaskDelay(1);
    }
  }
  // Windows can retain the tail of a bulk transfer until a short packet.
  // A JPEG whose size is divisible by 64 therefore needs a zero-length packet;
  // otherwise the laptop waits for its tail while we wait for another request.
  if(!size && lastPacket==USB_SERIAL_JTAG_PACKET_SZ_BYTES) {
    while(!usb_serial_jtag_ll_txfifo_writable() && millis()-lastProgress<1000) vTaskDelay(1);
    if(usb_serial_jtag_ll_txfifo_writable()) usb_serial_jtag_ll_txfifo_flush();
    else { ++failures; return false; }
  }
  if(size) ++failures;
  return size==0;
}
static void worker(void*) {
  uint8_t request[7]; size_t used=0,expected=0; char operation=0; bool reading=false; uint32_t requestAt=0;
  auto settingsReply=[&](bool change) {
    char json[448];
    if(!change) camera_controls::status(json,sizeof(json));
    else if(request[0]>1) snprintf(json,sizeof(json),"{\"ok\":false,\"error\":\"Invalid camera mode\"}");
    else camera_controls::apply(request[0]==1,wire::get<uint32_t>(request,1),wire::get<uint16_t>(request,5),json,sizeof(json));
    uint8_t h[8];memcpy(h,"BSS1",4);wire::put<uint32_t>(h,4,strlen(json));
    if(send(h,sizeof(h))) send(reinterpret_cast<const uint8_t*>(json),strlen(json));
  };
  while(true) {
    if(reading && millis()-requestAt>500) { reading=false; used=0; }
    uint8_t byte=0;
    if(usb_serial_jtag_read_bytes(&byte,1,pdMS_TO_TICKS(2))==1) {
      ++received;
      if(!reading) {
        if(byte=='S') settingsReply(false);
        else if(byte=='F' || byte=='V' || byte=='C'||byte=='A') {operation=byte;expected=byte=='C'?7:byte=='A'?3:4;reading=true;used=0;requestAt=millis();}
      }
      else {
        request[used++]=byte;
        if(used==expected) {
          ++requests;
          reading=false;
          if(operation=='C') {settingsReply(true);continue;}
          if(operation=='A'){
            char json[320];if(request[0]>1)snprintf(json,sizeof(json),"{\"ok\":false,\"error\":\"Invalid simulation mode\"}");
            else camera_service::simulateAltitude(request[0]!=0,wire::get<uint16_t>(request,1),json,sizeof(json));
            uint8_t prefix[8];memcpy(prefix,"BSP1",4);wire::put<uint32_t>(prefix,4,strlen(json));
            if(send(prefix,sizeof(prefix)))send(reinterpret_cast<const uint8_t*>(json),strlen(json));continue;
          }
          uint32_t after=wire::get<uint32_t>(request,0),started=millis();
          camera_service::FramePtr frame;
          aruco_service::ResultPtr vision;
          while(!dashboard::flying() && !camera_service::error && millis()-started<1000) {
            if(operation=='V'){vision=aruco_service::latest();frame=vision?vision->frame:camera_service::FramePtr{};}
            else frame=camera_service::latestFrame();
            if(frame && frame->id!=after && millis()-frame->capturedMs<2000) break;
            frame.reset(); vTaskDelay(pdMS_TO_TICKS(5));
          }
          uint32_t flags=dashboard::flying()?1:!frame?2:0;
          if(flags) frame.reset();
          if(operation=='V') {
            // Results precede their exact analyzed frame. F/BSC1 stays compatible.
            char json[2304];aruco_service::json(json,sizeof(json),flags?nullptr:vision.get(),millis());
            uint8_t prefix[8];memcpy(prefix,"BSV1",4);wire::put<uint32_t>(prefix,4,strlen(json));
            if(!send(prefix,sizeof(prefix))||!send(reinterpret_cast<const uint8_t*>(json),strlen(json)))continue;
          }
          uint8_t header[camera_service::HeaderSize];
          camera_service::frameHeader(header,frame.get(),millis(),flags);
          if(send(header,sizeof(header)) && frame) send(frame->jpeg,frame->size);
        }
      }
    } else vTaskDelay(pdMS_TO_TICKS(2));
  }
}
void begin() {
  usb_serial_jtag_driver_config_t config={};
  config.tx_buffer_size=8192; config.rx_buffer_size=128;
  if(usb_serial_jtag_driver_install(&config)!=ESP_OK) {
    Serial.println("Native USB camera driver failed"); return;
  }
  // RX keeps its interrupt-driven queue; TX belongs exclusively to worker().
  usb_serial_jtag_ll_disable_intr_mask(USB_SERIAL_JTAG_INTR_SERIAL_IN_EMPTY);
  usb_serial_jtag_ll_txfifo_flush();
  if(xTaskCreatePinnedToCore(worker,"USB camera",8192,nullptr,1,nullptr,1)!=pdPASS) {
    Serial.println("Native USB viewer task failed");
    usb_serial_jtag_driver_uninstall();
  } else { ready=true; Serial.println("Native USB camera ready (OTG socket)"); }
}
}
