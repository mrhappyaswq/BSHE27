#pragma once
#include <vector>
#include "aruco_detector.h"
#include "aruco_preview.h"
#include "aruco_image.h"
inline void arucoTests(){
  for(bool mirror:{false,true})for(bool flip:{false,true}){
    double x=13.25,y=71.75;aruco_image::map(x,y,320,240,mirror,flip);
    assert(fabs(x-(mirror?305.75:13.25))<1e-6&&fabs(y-(flip?167.25:71.75))<1e-6);
    aruco_image::map(x,y,320,240,mirror,flip);assert(x==13.25&&y==71.75);
  }
  constexpr int W=320,H=240,N=W*H;
  std::vector<uint8_t> gray(N,230),binary(N);
  std::vector<uint32_t> integral((W+1)*(H+1)),queue(N);
  std::vector<aruco_detector::Pixel> boundary(aruco_detector::MaxBoundary),hull(aruco_detector::MaxBoundary*2);
  aruco_detector::Workspace workspace{integral.data(),queue.data(),binary.data(),boundary.data(),hull.data()};
  // Independently sampled from the user's photograph, rotated 180 degrees.
  const char* photo[7]={"1010100","0001010","0111010","0101001","1011000","1110101","0111011"};
  for(int rotation=0;rotation<4;++rotation){
    std::fill(gray.begin(),gray.end(),230);
    for(int y=0;y<108;++y)for(int x=0;x<108;++x){
      int gx=x/12,gy=y/12;bool white=false;
      if(gx>0&&gy>0&&gx<8&&gy<8){int xx=gx-1,yy=gy-1;for(int r=0;r<rotation;++r){int t=xx;xx=6-yy;yy=t;}white=photo[yy][xx]=='1';}
      gray[(y+60)*W+x+100]=white?235:20;
    }
    auto d=aruco_detector::find(gray.data(),W,H,workspace);assert(d.valid&&d.bitErrors==0);
    marker_pose::Calibration c;c.fx=c.fy=240;c.cx=159.5;c.cy=119.5;
    auto p=marker_pose::estimate(d.corners,.2,c);assert(p.valid&&fabs(p.translation[2]-.2*240/108)<.01);
    if(rotation==0){
      auto flipCell=[&](int cell){for(int y=72;y<84;++y)for(int x=112+12*cell;x<124+12*cell;++x)gray[y*W+x]=255-gray[y*W+x];};
      flipCell(0);auto corrected=aruco_detector::find(gray.data(),W,H,workspace);assert(corrected.valid&&corrected.bitErrors==1);
      flipCell(1);assert(!aruco_detector::find(gray.data(),W,H,workspace).valid);
      flipCell(0);flipCell(1);
    }
    // A vertical reflection is not a valid rotation of this ArUco marker.
    for(int y=0;y<H/2;++y)for(int x=0;x<W;++x)std::swap(gray[y*W+x],gray[(H-1-y)*W+x]);
    assert(!aruco_detector::find(gray.data(),W,H,workspace).valid);
  }
  std::fill(gray.begin(),gray.end(),128);assert(!aruco_detector::find(gray.data(),W,H,workspace).valid);
  // Independent pinhole renderer: tilted plane, off-axis center, uneven light.
  const double angle=.6,side=.2,tx=.04,ty=-.02,tz=.65;
  for(int y=0;y<H;++y)for(int x=0;x<W;++x){
    double rx=(x-159.5)/240,ry=(y-119.5)/240;
    double lambda=(sin(angle)*tx+cos(angle)*tz)/(sin(angle)*rx+cos(angle));
    double baseX=cos(angle)*(lambda*rx-tx)-sin(angle)*(lambda-tz),baseY=lambda*ry-ty;
    double qx=cos(.37)*baseX+sin(.37)*baseY,qy=-sin(.37)*baseX+cos(.37)*baseY;
    int gx=int(floor((qx/side+.5)*9)),gy=int(floor((qy/side+.5)*9));
    bool inside=gx>=0&&gy>=0&&gx<9&&gy<9;
    bool white=!inside||(gx>0&&gy>0&&gx<8&&gy<8&&photo[gy-1][gx-1]=='1');
    gray[y*W+x]=uint8_t((white?190:15)+x/8+(x*13+y*7)%5);
  }
  auto tilted=aruco_detector::find(gray.data(),W,H,workspace);assert(tilted.valid);
  marker_pose::Calibration camera;camera.fx=camera.fy=240;camera.cx=159.5;camera.cy=119.5;
  auto tiltedPose=marker_pose::estimate(tilted.corners,side,camera);
  assert(tiltedPose.valid&&fabs(tiltedPose.translation[2]-tz)<.025&&fabs(tiltedPose.tilt-angle)<.1);
  std::fill(gray.begin(),gray.end(),235);for(int y=60;y<168;++y)for(int x=100;x<208;++x)gray[y*W+x]=20;
  assert(!aruco_detector::find(gray.data(),W,H,workspace).valid);
  marker_pose::Pose p;p.valid=true;p.translation[0]=.3;p.translation[1]=-.2;p.translation[2]=1;
  auto command=aruco_preview::propose(p,true);assert(command.valid&&command.right>0&&command.forward>0&&command.down==0);
  assert(!aruco_preview::propose(p,false).valid);
  p.translation[0]=p.translation[1]=0;command=aruco_preview::propose(p,true);assert(command.down>0);
  p.yaw=.5;command=aruco_preview::propose(p,true);assert(command.yaw>0&&command.down==0);
  p.tilt=1.3;assert(!aruco_preview::propose(p,true).valid);
}
inline void arucoPhotoTest(const char* path){
  FILE* file=fopen(path,"rb");assert(file);int w,h,max;assert(fscanf(file,"P5 %d %d %d",&w,&h,&max)==3&&max==255);fgetc(file);
  std::vector<uint8_t> gray(w*h),binary(w*h);assert(fread(gray.data(),1,gray.size(),file)==gray.size());fclose(file);
  std::vector<uint32_t> integral((w+1)*(h+1)),queue(w*h);
  std::vector<aruco_detector::Pixel> boundary(aruco_detector::MaxBoundary),hull(aruco_detector::MaxBoundary*2);
  aruco_detector::Workspace workspace{integral.data(),queue.data(),binary.data(),boundary.data(),hull.data()};
  auto d=aruco_detector::find(gray.data(),w,h,workspace);assert(d.valid&&d.bitErrors==0);
  // Exercise the worker's configured grayscale-to-detector mapping too. Sensor
  // settings::Flip remains true on this board and must not cause another flip.
  std::vector<uint8_t> mapped(gray.size());
  for(int y=0;y<h;++y)for(int x=0;x<w;++x){int gx=x,gy=y;aruco_image::map(gx,gy,w,h,aruco_config::DetectorMirrorX,aruco_config::DetectorFlipY);mapped[gy*w+gx]=gray[y*w+x];}
  assert(aruco_detector::find(mapped.data(),w,h,workspace).valid);
  puts("Photograph/frame fixture: ArUco 7x7 ID 0 detected, zero bit errors");
}
