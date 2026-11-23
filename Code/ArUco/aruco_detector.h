#pragma once
#include <algorithm>
#include <stdint.h>
#include <stddef.h>
#include "ArUco/marker_pose.h"

// Bounded detector for OpenCV 7x7 ID 0. Coordinates always refer to the full image.
namespace aruco_detector {
using marker_pose::Point;
struct Pixel { int16_t x,y;bool operator<(const Pixel& p)const{return x==p.x?y<p.y:x<p.x;} };
constexpr int MaxBoundary=4096,MaxWidth=320,MaxHeight=240;
struct Workspace { uint32_t *columns,*queue;uint8_t* binary;Pixel *boundary,*hull; };
struct Region { int x,y,width,height;Region(int px=0,int py=0,int w=0,int h=0):x(px),y(py),width(w),height(h){} };
struct Profile {
  uint32_t prepareUs=0,searchUs=0,identifyUs=0,pixels=0,candidates=0,passes=0;
  bool tracked=false;
};
using Clock=uint32_t(*)();
inline uint32_t stamp(Clock clock){return clock?clock():0;}
struct Detection { bool valid=false;Point corners[4];int bitErrors=49;float area=0,contrast=0; };
inline int cross(Pixel a,Pixel b,Pixel c){return (b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x);}
inline float area(const Point* p){float a=0;for(int i=0;i<4;++i)a+=p[i].x*p[(i+1)%4].y-p[(i+1)%4].x*p[i].y;return a*.5f;}
inline bool homography(const Point* p,float* h) {
  float dx1=p[1].x-p[2].x,dx2=p[3].x-p[2].x,dy1=p[1].y-p[2].y,dy2=p[3].y-p[2].y;
  float sx=p[0].x-p[1].x+p[2].x-p[3].x,sy=p[0].y-p[1].y+p[2].y-p[3].y;
  float d=dx1*dy2-dx2*dy1;if(fabsf(d)<1e-9f)return false;
  h[6]=(sx*dy2-dx2*sy)/d;h[7]=(dx1*sy-sx*dy1)/d;h[8]=1;
  h[0]=p[1].x-p[0].x+h[6]*p[1].x;h[1]=p[3].x-p[0].x+h[7]*p[3].x;h[2]=p[0].x;
  h[3]=p[1].y-p[0].y+h[6]*p[1].y;h[4]=p[3].y-p[0].y+h[7]*p[3].y;h[5]=p[0].y;return true;
}
inline Point transform(const float* h,float x,float y){
  float inverse=1.f/(h[6]*x+h[7]*y+1.f);
  return {(h[0]*x+h[1]*y+h[2])*inverse,(h[3]*x+h[4]*y+h[5])*inverse};
}
inline bool referenceBit(int x,int y) {
  static constexpr uint8_t code[7]={221,92,108,165,202,10,1};int i=y*7+x;
  return i==48?(code[6]&1):((code[i/8]>>(7-i%8))&1);
}
inline Detection decode(const uint8_t* gray,int width,int height,const Point* quad) {
  Detection out;float h[9];if(!homography(quad,h))return out;
  uint16_t cells[81],lo=1275,hi=0;
  static constexpr float offsets[5][2]={{0,0},{-.18f,0},{.18f,0},{0,-.18f},{0,.18f}};
  for(int y=0;y<9;++y)for(int x=0;x<9;++x){
    uint16_t sum=0;
    for(auto& o:offsets){
      Point p=transform(h,(x+.5f+o[0])*(1.f/9),(y+.5f+o[1])*(1.f/9));
      if(!isfinite(p.x)||!isfinite(p.y))return out;
      int ix=int(lroundf(p.x)),iy=int(lroundf(p.y));if(ix<0||iy<0||ix>=width||iy>=height)return out;
      sum+=gray[iy*width+ix];
    }
    cells[y*9+x]=sum;lo=std::min(lo,sum);hi=std::max(hi,sum);
  }
  // Values remain sums of five pixels; comparisons are exactly equivalent to averages.
  if(hi-lo<200)return out;
  int threshold=lo+hi,borderErrors=0;
  for(int y=0;y<9;++y)for(int x=0;x<9;++x)
    if(x==0||y==0||x==8||y==8)borderErrors+=2*cells[y*9+x]>threshold;
  if(borderErrors>1)return out;
  for(int rotation=0;rotation<4;++rotation){
    int errors=0;
    for(int y=0;y<7;++y)for(int x=0;x<7;++x){
      int sx=x,sy=y;
      switch(rotation){case 1:sx=6-y;sy=x;break;case 2:sx=6-x;sy=6-y;break;case 3:sx=y;sy=6-x;break;}
      errors+=(2*cells[(sy+1)*9+sx+1]>threshold)!=referenceBit(x,y);
    }
    if(errors<out.bitErrors){out.bitErrors=errors;for(int i=0;i<4;++i)out.corners[i]=quad[(i+rotation)%4];}
  }
  out.valid=out.bitErrors<=1;out.area=area(quad);out.contrast=(hi-lo)*.2f;return out;
}
inline bool quadFromBoundary(Workspace& w,int n,Point* quad) {
  std::sort(w.boundary,w.boundary+n);int k=0;
  for(int i=0;i<n;++i){while(k>=2&&cross(w.hull[k-2],w.hull[k-1],w.boundary[i])<=0)--k;w.hull[k++]=w.boundary[i];}
  for(int i=n-2,t=k+1;i>=0;--i){while(k>=t&&cross(w.hull[k-2],w.hull[k-1],w.boundary[i])<=0)--k;w.hull[k++]=w.boundary[i];}
  if(--k<4||k>128)return false;
  while(k>4){int at=0,best=INT32_MAX;
    for(int i=0;i<k;++i){int a=abs(cross(w.hull[(i+k-1)%k],w.hull[i],w.hull[(i+1)%k]));if(a<best){best=a;at=i;}}
    for(int i=at;i<k-1;++i)w.hull[i]=w.hull[i+1];--k;
  }
  int start=0;for(int i=1;i<4;++i)if(w.hull[i].x+w.hull[i].y<w.hull[start].x+w.hull[start].y)start=i;
  Point center;for(int i=0;i<4;++i){center.x+=w.hull[i].x*.25f;center.y+=w.hull[i].y*.25f;}
  for(int i=0;i<4;++i){Pixel p=w.hull[(start+i)%4];float dx=p.x-center.x,dy=p.y-center.y,norm=hypotf(dx,dy);
    if(norm<10)return false;quad[i]={p.x+.65f*dx/norm,p.y+.65f*dy/norm};}
  if(area(quad)<400)return false;
  for(int i=0;i<4;++i)if(hypotf(quad[i].x-quad[(i+1)%4].x,quad[i].y-quad[(i+1)%4].y)<20)return false;
  return true;
}
// Rolling 15x15 mean, identical clipped neighborhoods to the former integral image.
// columns requires only width uint32 values instead of (width+1)*(height+1).
inline void threshold(const uint8_t* gray,int imageWidth,Region r,Workspace& w) {
  int width=r.width,height=r.height;
  std::fill(w.columns,w.columns+width,0);
  for(int y=0;y<std::min(height,8);++y)
    for(int x=0;x<width;++x)w.columns[x]+=gray[(r.y+y)*imageWidth+r.x+x];
  for(int y=0;y<height;++y){
    uint32_t sum=0;for(int x=0;x<std::min(width,8);++x)sum+=w.columns[x];
    int rows=std::min(height,y+8)-std::max(0,y-7);
    for(int x=0;x<width;++x){
      int cols=std::min(width,x+8)-std::max(0,x-7);
      w.binary[y*width+x]=gray[(r.y+y)*imageWidth+r.x+x]<int(sum/(rows*cols))-7;
      if(x>=7)sum-=w.columns[x-7];if(x+8<width)sum+=w.columns[x+8];
    }
    for(int x=0;x<width;++x){
      if(y>=7)w.columns[x]-=gray[(r.y+y-7)*imageWidth+r.x+x];
      if(y+8<height)w.columns[x]+=gray[(r.y+y+8)*imageWidth+r.x+x];
    }
  }
}
inline Detection find(const uint8_t* gray,int imageWidth,int imageHeight,Workspace& w,
                      Region r={},Profile* profile=nullptr,Clock clock=nullptr) {
  Detection best;
  if(!gray||imageWidth<=0||imageHeight<=0||imageWidth>MaxWidth||imageHeight>MaxHeight)return best;
  if(r.width==0&&r.height==0)r={0,0,imageWidth,imageHeight};
  if(r.x<0||r.y<0||r.width<=0||r.height<=0||r.x+r.width>imageWidth||r.y+r.height>imageHeight)return best;
  int width=r.width,height=r.height,count=width*height;
  uint32_t at=stamp(clock),hist[256]={};
  for(int y=0;y<height;++y)for(int x=0;x<width;++x)++hist[gray[(r.y+y)*imageWidth+r.x+x]];
  float weighted=0;for(int i=0;i<256;++i)weighted+=i*float(hist[i]);
  float leftSum=0,variance=-1;uint32_t left=0;int otsu=127;
  for(int i=0;i<255;++i){left+=hist[i];leftSum+=i*float(hist[i]);if(!left||left==uint32_t(count))continue;
    float delta=leftSum/left-(weighted-leftSum)/(count-left),v=float(left)*(count-left)*delta*delta;
    if(v>variance){variance=v;otsu=i;}}
  if(profile){profile->prepareUs+=stamp(clock)-at;profile->pixels+=count;}
  for(int pass=0;pass<2&&!best.valid;++pass){
    at=stamp(clock);
    if(pass==0)threshold(gray,imageWidth,r,w);
    else for(int y=0;y<height;++y)for(int x=0;x<width;++x)
      w.binary[y*width+x]=gray[(r.y+y)*imageWidth+r.x+x]<otsu+1;
    if(profile){profile->prepareUs+=stamp(clock)-at;++profile->passes;}
    at=stamp(clock);uint32_t identifyTime=0;int candidates=0;
    for(int seed=0;seed<count;++seed)if(w.binary[seed]==1){
      int head=0,tail=0,boundary=0,minX=width,minY=height,maxX=0,maxY=0;bool edge=false,overflow=false;
      w.queue[tail++]=seed;w.binary[seed]=2;
      while(head<tail){
        int pos=w.queue[head++],x=pos%width,y=pos/width;bool border=false;
        minX=std::min(minX,x);minY=std::min(minY,y);maxX=std::max(maxX,x);maxY=std::max(maxY,y);
        if(x==0||y==0||x==width-1||y==height-1)edge=true;
        auto visit=[&](int next){uint8_t v=w.binary[next];if(v==0)border=true;
          if(v==1){w.binary[next]=2;w.queue[tail++]=next;}};
        if(x>0)visit(pos-1);else border=true;
        if(x+1<width)visit(pos+1);else border=true;
        if(y>0)visit(pos-width);else border=true;
        if(y+1<height)visit(pos+width);else border=true;
        if(border){if(boundary<MaxBoundary)w.boundary[boundary++]={int16_t(x+r.x),int16_t(y+r.y)};else overflow=true;}
      }
      if(edge||overflow||tail<80||boundary<40||tail>count*3/4||maxX-minX<19||maxY-minY<19)continue;
      if(++candidates>64)break;
      Point quad[4];if(!quadFromBoundary(w,boundary,quad))continue;
      uint32_t decodeAt=stamp(clock);Detection found=decode(gray,imageWidth,imageHeight,quad);
      identifyTime+=stamp(clock)-decodeAt;
      if(found.valid&&found.area>best.area)best=found;
    }
    if(profile){profile->identifyUs+=identifyTime;profile->searchUs+=stamp(clock)-at-identifyTime;profile->candidates+=candidates;}
  }
  return best;
}
}
