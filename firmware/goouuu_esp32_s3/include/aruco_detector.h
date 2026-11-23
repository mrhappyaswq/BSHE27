#pragma once
#include <algorithm>
#include <stdint.h>
#include <stddef.h>
#include "marker_pose.h"

// Small, bounded-work detector for the photographed 7x7 ID 0. No OpenCV runtime.
// Exact reference bit pattern independently checked against OpenCV 4.10 ID 0.
namespace aruco_detector {
using marker_pose::Point;
struct Pixel { int16_t x,y;bool operator<(const Pixel& p)const{return x==p.x?y<p.y:x<p.x;} };
constexpr int MaxBoundary=4096;
struct Workspace { uint32_t *integral,*queue;uint8_t* binary;Pixel *boundary,*hull; };
struct Detection { bool valid=false;Point corners[4];int bitErrors=49;double area=0,contrast=0; };
inline int cross(Pixel a,Pixel b,Pixel c){return (b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x);}
inline double area(const Point* p){double a=0;for(int i=0;i<4;++i)a+=p[i].x*p[(i+1)%4].y-p[(i+1)%4].x*p[i].y;return a*.5;}
inline bool homography(const Point* p,double* h) {
  double dx1=p[1].x-p[2].x,dx2=p[3].x-p[2].x,dy1=p[1].y-p[2].y,dy2=p[3].y-p[2].y;
  double sx=p[0].x-p[1].x+p[2].x-p[3].x,sy=p[0].y-p[1].y+p[2].y-p[3].y;
  double d=dx1*dy2-dx2*dy1;if(fabs(d)<1e-9)return false;
  h[6]=(sx*dy2-dx2*sy)/d;h[7]=(dx1*sy-sx*dy1)/d;h[8]=1;
  h[0]=p[1].x-p[0].x+h[6]*p[1].x;h[1]=p[3].x-p[0].x+h[7]*p[3].x;h[2]=p[0].x;
  h[3]=p[1].y-p[0].y+h[6]*p[1].y;h[4]=p[3].y-p[0].y+h[7]*p[3].y;h[5]=p[0].y;return true;
}
inline Point transform(const double* h,double x,double y){double d=h[6]*x+h[7]*y+1;return {(h[0]*x+h[1]*y+h[2])/d,(h[3]*x+h[4]*y+h[5])/d};}
inline bool referenceBit(int x,int y) {
  // 49 row-major bits, white=1. Last byte stores only its low bit.
  const uint8_t code[7]={221,92,108,165,202,10,1};int i=y*7+x;
  return i==48?(code[6]&1):((code[i/8]>>(7-i%8))&1);
}
inline Detection decode(const uint8_t* gray,int width,int height,const Point* quad) {
  Detection out;double h[9];if(!homography(quad,h))return out;
  double cells[81],lo=255,hi=0;
  for(int y=0;y<9;++y)for(int x=0;x<9;++x){
    double sum=0;const double offsets[5][2]={{0,0},{-.18,0},{.18,0},{0,-.18},{0,.18}};
    for(auto& o:offsets){Point p=transform(h,(x+.5+o[0])/9,(y+.5+o[1])/9);
      int ix=int(lround(p.x)),iy=int(lround(p.y));if(ix<0||iy<0||ix>=width||iy>=height)return out;sum+=gray[iy*width+ix];}
    double v=sum/5;cells[y*9+x]=v;lo=fmin(lo,v);hi=fmax(hi,v);
  }
  if(hi-lo<40)return out;
  double threshold=(lo+hi)*.5;int borderErrors=0;
  for(int y=0;y<9;++y)for(int x=0;x<9;++x)if(x==0||y==0||x==8||y==8)borderErrors+=cells[y*9+x]>threshold;
  if(borderErrors>1)return out;
  for(int rotation=0;rotation<4;++rotation){
    int errors=0;
    for(int y=0;y<7;++y)for(int x=0;x<7;++x){
      int sx=x,sy=y;for(int r=0;r<rotation;++r){int t=sx;sx=6-sy;sy=t;}
      bool observed=cells[(sy+1)*9+sx+1]>threshold;errors+=observed!=referenceBit(x,y);
    }
    if(errors<out.bitErrors){out.bitErrors=errors;for(int i=0;i<4;++i)out.corners[i]=quad[(i+rotation)%4];}
  }
  out.valid=out.bitErrors<=1;out.area=area(quad);out.contrast=hi-lo;return out;
}
inline bool quadFromBoundary(Workspace& w,int n,Point* quad) {
  std::sort(w.boundary,w.boundary+n);int k=0;
  for(int i=0;i<n;++i){while(k>=2&&cross(w.hull[k-2],w.hull[k-1],w.boundary[i])<=0)--k;w.hull[k++]=w.boundary[i];}
  for(int i=n-2,t=k+1;i>=0;--i){while(k>=t&&cross(w.hull[k-2],w.hull[k-1],w.boundary[i])<=0)--k;w.hull[k++]=w.boundary[i];}
  if(--k<4||k>128)return false;
  while(k>4){int at=0;int best=INT32_MAX;
    for(int i=0;i<k;++i){int a=abs(cross(w.hull[(i+k-1)%k],w.hull[i],w.hull[(i+1)%k]));if(a<best){best=a;at=i;}}
    for(int i=at;i<k-1;++i)w.hull[i]=w.hull[i+1];--k;
  }
  int start=0;for(int i=1;i<4;++i)if(w.hull[i].x+w.hull[i].y<w.hull[start].x+w.hull[start].y)start=i;
  Point center;for(int i=0;i<4;++i){center.x+=w.hull[i].x*.25;center.y+=w.hull[i].y*.25;}
  for(int i=0;i<4;++i){Pixel p=w.hull[(start+i)%4];double dx=p.x-center.x,dy=p.y-center.y,norm=hypot(dx,dy);
    if(norm<10)return false;quad[i]={p.x+.65*dx/norm,p.y+.65*dy/norm};}
  if(area(quad)<400)return false;
  for(int i=0;i<4;++i){double length=hypot(quad[i].x-quad[(i+1)%4].x,quad[i].y-quad[(i+1)%4].y);if(length<20)return false;}
  return true;
}
inline Detection find(const uint8_t* gray,int width,int height,Workspace& w) {
  Detection best;int count=width*height,stride=width+1;uint32_t hist[256]={};
  for(int x=0;x<=width;++x)w.integral[x]=0;
  for(int y=0;y<height;++y){uint32_t sum=0;w.integral[(y+1)*stride]=0;
    for(int x=0;x<width;++x){uint8_t v=gray[y*width+x];++hist[v];sum+=v;w.integral[(y+1)*stride+x+1]=sum+w.integral[y*stride+x+1];}}
  double weighted=0;for(int i=0;i<256;++i)weighted+=i*double(hist[i]);
  double leftSum=0,variance=-1;uint32_t left=0;int otsu=127;
  for(int i=0;i<255;++i){left+=hist[i];leftSum+=i*double(hist[i]);if(!left||left==uint32_t(count))continue;
    double delta=leftSum/left-(weighted-leftSum)/(count-left),v=double(left)*(count-left)*delta*delta;if(v>variance){variance=v;otsu=i;}}
  // First adaptive, then a global threshold if needed. Each pixel enters a BFS once/pass.
  for(int pass=0;pass<2&&!best.valid;++pass){
    for(int y=0;y<height;++y)for(int x=0;x<width;++x){int threshold=otsu+1;
      if(pass==0){int x0=std::max(0,x-7),y0=std::max(0,y-7),x1=std::min(width,x+8),y1=std::min(height,y+8);
        uint32_t sum=w.integral[y1*stride+x1]-w.integral[y0*stride+x1]-w.integral[y1*stride+x0]+w.integral[y0*stride+x0];threshold=int(sum/((x1-x0)*(y1-y0)))-7;}
      w.binary[y*width+x]=gray[y*width+x]<threshold;}
    int candidates=0;
    for(int seed=0;seed<count;++seed)if(w.binary[seed]==1){
      int head=0,tail=0,boundary=0;bool edge=false,overflow=false;w.queue[tail++]=seed;w.binary[seed]=2;
      while(head<tail){int at=w.queue[head++],x=at%width,y=at/width;bool border=false;
        if(x==0||y==0||x==width-1||y==height-1)edge=true;
        const int dx[4]={-1,1,0,0},dy[4]={0,0,-1,1};
        for(int d=0;d<4;++d){int nx=x+dx[d],ny=y+dy[d];if(nx<0||ny<0||nx>=width||ny>=height){border=true;continue;}
          int next=ny*width+nx;if(w.binary[next]==0)border=true;
          if(w.binary[next]==1){w.binary[next]=2;w.queue[tail++]=next;}}
        if(border){if(boundary<MaxBoundary)w.boundary[boundary++]={int16_t(x),int16_t(y)};else overflow=true;}
      }
      if(edge||overflow||tail<80||boundary<40||tail>count*3/4)continue;
      if(++candidates>64)break;Point quad[4];if(!quadFromBoundary(w,boundary,quad))continue;
      Detection found=decode(gray,width,height,quad);if(found.valid&&found.area>best.area)best=found;
    }
  }
  return best;
}
}
