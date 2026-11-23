#pragma once
#include <string>
#include <chrono>
#include "ArUco/aruco_tracker.h"
#include "ArUco/grayscale_jpeg.h"
#include "ArUco/aruco_json.h"

inline void visionSpeedTests(){
  constexpr int W=320,H=240,N=W*H;
  std::vector<uint8_t> gray(N),binary(N);
  std::vector<uint32_t> columns(W),queue(N);
  std::vector<aruco_detector::Pixel> boundary(aruco_detector::MaxBoundary),hull(aruco_detector::MaxBoundary*2);
  aruco_detector::Workspace work{columns.data(),queue.data(),binary.data(),boundary.data(),hull.data()};
  for(int i=0;i<N;++i)gray[i]=uint8_t((i*73+(i/W)*17)%256);
  // Exact comparison to an independent, deliberately slow neighborhood sum,
  // including clipped image and ROI edges.
  for(auto region:{aruco_detector::Region(0,0,1,1),aruco_detector::Region(3,5,7,8),
                  aruco_detector::Region(7,9,31,25),aruco_detector::Region(0,0,W,H)}){
    aruco_detector::threshold(gray.data(),W,region,work);
    for(int y=0;y<region.height;++y)for(int x=0;x<region.width;++x){
      uint32_t sum=0;int count=0;
      for(int yy=std::max(0,y-7);yy<std::min(region.height,y+8);++yy)
        for(int xx=std::max(0,x-7);xx<std::min(region.width,x+8);++xx){
          sum+=gray[(yy+region.y)*W+xx+region.x];++count;
        }
      assert(binary[y*region.width+x]==(gray[(y+region.y)*W+x+region.x]<int(sum/count)-7));
    }
  }
  auto marker=[&](int left,int top){
    std::fill(gray.begin(),gray.end(),235);
    for(int y=0;y<54;++y)for(int x=0;x<54;++x){
      int gx=x/6,gy=y/6;
      bool white=gx>0&&gy>0&&gx<8&&gy<8&&aruco_detector::referenceBit(gx-1,gy-1);
      gray[(top+y)*W+left+x]=white?235:20;
    }
  };
  aruco_detector::Tracker tracker;marker(35,50);
  aruco_detector::Profile first;auto d=tracker.find(gray.data(),W,H,work,100,&first);
  assert(d.valid&&!first.tracked&&first.pixels==N);
  aruco_detector::Profile tracked;auto fast=tracker.find(gray.data(),W,H,work,120,&tracked);
  assert(fast.valid&&tracked.tracked&&tracked.pixels<N/2);
  for(int i=0;i<4;++i)assert(fabsf(fast.corners[i].x-d.corners[i].x)<.01f&&fabsf(fast.corners[i].y-d.corners[i].y)<.01f);
  marker(235,150);aruco_detector::Profile moved;
  auto recovered=tracker.find(gray.data(),W,H,work,140,&moved);
  assert(recovered.valid&&moved.tracked&&moved.pixels>N); // same-frame full recovery
  aruco_detector::Profile periodic;assert(tracker.find(gray.data(),W,H,work,650,&periodic).valid&&!periodic.tracked);
  std::fill(gray.begin(),gray.end(),235);
  assert(!tracker.find(gray.data(),W,H,work,670).valid);
  marker(35,50);aruco_detector::Profile reacquire;
  assert(tracker.find(gray.data(),W,H,work,690,&reacquire).valid&&!reacquire.tracked);
  aruco_detector::Profile resized;
  assert(!tracker.find(gray.data(),160,120,work,700,&resized).valid&&!resized.tracked);
  // Pose remains accurate at several distances, including nonzero distortion.
  marker_pose::Calibration c;c.fx=241.3f;c.fy=238.7f;c.cx=159.4f;c.cy=120.2f;
  c.k1=-.08f;c.k2=.01f;c.p1=.001f;c.p2=-.002f;
  for(float z:{.3f,.8f,2.4f}){
    marker_pose::Point corners[4];const float xs[4]={-.1f,.1f,.1f,-.1f},ys[4]={-.1f,-.1f,.1f,.1f};
    for(int i=0;i<4;++i)corners[i]=marker_pose::project(xs[i]+.025f,ys[i]-.015f,z,c);
    auto pose=marker_pose::estimate(corners,.2f,c);
    assert(pose.valid&&fabsf(pose.translation[2]-z)<.002f&&fabsf(pose.translation[0]-.025f)<.001f);
  }
  // Exercise the actual formatter; this catches varargs field-order/type regressions.
  aruco_service::Result r;auto frame=std::make_shared<camera_service::Frame>();frame->id=42;frame->capturedMs=1000;r.frame=frame;
  r.detection.valid=true;r.detection.bitErrors=0;r.pose.valid=true;r.pose.translation[2]=1;
  r.pose.rotation[0]=r.pose.rotation[4]=r.pose.rotation[8]=1;
  r.decodeUs=12000;r.profile.prepareUs=2000;r.profile.searchUs=3000;r.profile.identifyUs=4000;r.poseUs=5000;
  r.profile.pixels=12345;r.profile.tracked=true;r.analysisFps=23;r.internalBytes=1280;r.externalBytes=500000;
  r.workspaceBytes=r.internalBytes+r.externalBytes;r.busyPercent=50;
  char json[3072];aruco_service::formatJson(json,sizeof(json),&r,1050,100000,6000000,nullptr);
  assert(strstr(json,"\"prepare_ms\":2.000")&&strstr(json,"\"search_ms\":3.000")&&strstr(json,"\"identify_ms\":4.000"));
  assert(strstr(json,"\"pose_ms\":5.000")&&strstr(json,"\"search_pixels\":12345")&&strstr(json,"\"heap_free\":100000"));
  assert(strstr(json,"\"tracked_search\":true")&&strstr(json,"\"command_valid\":true")&&strlen(json)<sizeof(json)-1);
  FILE* output=fopen("vision-metadata.json","wb");assert(output);fwrite(json,1,strlen(json),output);fclose(output);
  aruco_service::formatJson(json,sizeof(json),&r,2000,100000,6000000,nullptr);
  assert(strstr(json,"\"fresh\":false")&&strstr(json,"\"command_valid\":false")&&strstr(json,"\"corners\":null"));
  aruco_service::formatJson(json,sizeof(json),nullptr,2000,100000,6000000,"Starting");
  assert(strstr(json,"\"error\":\"Starting\"")&&strstr(json,"\"command_valid\":false"));
  puts("Rolling threshold, ROI recovery, pose precision and metadata checks passed");
}
inline std::vector<uint8_t> readPicture(const char* path){
  FILE* f=fopen(path,"rb");assert(f);fseek(f,0,SEEK_END);long size=ftell(f);rewind(f);
  std::vector<uint8_t> data(size);assert(fread(data.data(),1,data.size(),f)==data.size());fclose(f);return data;
}
inline void jpegSpeedTests(const char* colorPath,const char* monoPath,const char* markerPath){
  auto jpeg=readPicture(colorPath),mono=readPicture(monoPath);
  auto decoder=std::unique_ptr<aruco_image::GrayDecoder>(new aruco_image::GrayDecoder);
  std::vector<uint8_t> gray(320*240),mirror(gray.size());
  assert(decoder->decode(jpeg.data(),jpeg.size(),gray.data(),320,240,320,240));
  assert(decoder->decodedWidth()==320&&decoder->decodedHeight()==240);
  assert(decoder->decode(jpeg.data(),jpeg.size(),mirror.data(),320,240,320,240,true,true));
  for(int y=0;y<240;++y)for(int x=0;x<320;++x)assert(gray[y*320+x]==mirror[(239-y)*320+319-x]);
  assert(decoder->decode(jpeg.data(),jpeg.size(),gray.data(),320,240,160,120));
  assert(decoder->decodedWidth()==160&&decoder->decodedHeight()==120);
  assert(decoder->decode(jpeg.data(),jpeg.size(),gray.data(),320,240,80,60));
  assert(decoder->decodedWidth()==80&&decoder->decodedHeight()==60);
  assert(!decoder->decode(jpeg.data(),jpeg.size(),gray.data(),640,480,320,240));
  assert(!decoder->decode(jpeg.data(),jpeg.size()-10,gray.data(),320,240,320,240));
  assert(!decoder->decode(jpeg.data(),3,gray.data(),320,240,320,240));
  assert(decoder->decode(mono.data(),mono.size(),gray.data(),16,16,320,240));
  for(int i=0;i<16*16;++i)assert(gray[i]==128);
  auto marker=readPicture(markerPath);
  std::vector<uint32_t> columns(320),queue(320*240);std::vector<uint8_t> binary(320*240);
  std::vector<aruco_detector::Pixel> boundary(aruco_detector::MaxBoundary),hull(aruco_detector::MaxBoundary*2);
  aruco_detector::Workspace work{columns.data(),queue.data(),binary.data(),boundary.data(),hull.data()};
  for(auto dimensions:{std::pair<int,int>(320,240),{1024,768},{319,239}}){
    std::string file=markerPath;
    if(dimensions.first==1024)file.replace(file.size()-4,4,"-xga.jpg");
    if(dimensions.first==319)file.replace(file.size()-4,4,"-odd.jpg");
    auto data=readPicture(file.c_str());
    assert(decoder->decode(data.data(),data.size(),gray.data(),dimensions.first,dimensions.second,320,240));
    auto detection=aruco_detector::find(gray.data(),decoder->decodedWidth(),decoder->decodedHeight(),work);
    assert(detection.valid&&detection.bitErrors<=1);
  }
  puts("Real OV3660 JPEG, direct grayscale, scaling, parity and malformed-frame checks passed");
}
