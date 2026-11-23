#pragma once
#include <math.h>
#include <stdint.h>

// Portable pose math: camera +X right, +Y down, +Z along the optical axis.
// Marker corners must be canonical TL, TR, BR, BL after decoding rotation.
// Marker +X right, +Y down, +Z away from its printed face.
namespace marker_pose {
struct Point { double x,y;Point(double px=0,double py=0):x(px),y(py){} };
struct Calibration {
  double fx=0,fy=0,cx=0,cy=0;
  double k1=0,k2=0,p1=0,p2=0,k3=0;
  bool valid() const {return isfinite(fx)&&isfinite(fy)&&fx>0&&fy>0&&isfinite(cx)&&isfinite(cy)&&
    isfinite(k1)&&isfinite(k2)&&isfinite(p1)&&isfinite(p2)&&isfinite(k3);}
};
struct Pose {
  bool valid=false;
  double translation[3]={},rotation[9]={}; // marker -> camera, row-major
  double distance=0,reprojectionPx=0,roll=0,pitch=0,yaw=0,tilt=0;
};
inline double dot(const double* a,const double* b) {return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
inline bool normalize(double* a) {
  double n=sqrt(dot(a,a));if(!isfinite(n)||n<1e-12)return false;
  for(int i=0;i<3;++i)a[i]/=n;return true;
}
inline Point undistort(Point pixel,const Calibration& c) {
  double xd=(pixel.x-c.cx)/c.fx,yd=(pixel.y-c.cy)/c.fy,x=xd,y=yd;
  for(int i=0;i<10;++i) {
    double r2=x*x+y*y,radial=1+c.k1*r2+c.k2*r2*r2+c.k3*r2*r2*r2;
    if(fabs(radial)<1e-12)return {NAN,NAN};
    double dx=2*c.p1*x*y+c.p2*(r2+2*x*x),dy=c.p1*(r2+2*y*y)+2*c.p2*x*y;
    x=(xd-dx)/radial;y=(yd-dy)/radial;
  }
  return {x,y};
}
inline Point project(double x,double y,double z,const Calibration& c) {
  x/=z;y/=z;double r2=x*x+y*y,radial=1+c.k1*r2+c.k2*r2*r2+c.k3*r2*r2*r2;
  return {c.fx*(x*radial+2*c.p1*x*y+c.p2*(r2+2*x*x))+c.cx,
          c.fy*(y*radial+c.p1*(r2+2*y*y)+2*c.p2*x*y)+c.cy};
}
inline Pose estimate(const Point* pixels,double side,const Calibration& c,double maxErrorPx=3) {
  Pose result;
  if(!c.valid()||!isfinite(side)||side<=0||!isfinite(maxErrorPx)||maxErrorPx<=0)return result;
  const Point model[4]={{-side/2,-side/2},{side/2,-side/2},{side/2,side/2},{-side/2,side/2}};
  double a[8][9]={};double area=0;
  for(int i=0;i<4;++i) {
    if(!isfinite(pixels[i].x)||!isfinite(pixels[i].y))return result;
    const Point& next=pixels[(i+1)%4];area+=pixels[i].x*next.y-next.x*pixels[i].y;
    Point p=undistort(pixels[i],c);if(!isfinite(p.x)||!isfinite(p.y))return result;
    double x=model[i].x,y=model[i].y;
    double rowX[9]={x,y,1,0,0,0,-p.x*x,-p.x*y,p.x};
    double rowY[9]={0,0,0,x,y,1,-p.y*x,-p.y*y,p.y};
    for(int j=0;j<9;++j){a[2*i][j]=rowX[j];a[2*i+1][j]=rowY[j];}
  }
  // Reject reversed/degenerate polygons; reflections must be corrected upstream.
  if(area<32)return result;
  for(int k=0;k<8;++k) {
    int pivot=k;for(int i=k+1;i<8;++i)if(fabs(a[i][k])>fabs(a[pivot][k]))pivot=i;
    if(fabs(a[pivot][k])<1e-12)return result;
    for(int j=k;j<9;++j){double t=a[k][j];a[k][j]=a[pivot][j];a[pivot][j]=t;}
    double divisor=a[k][k];for(int j=k;j<9;++j)a[k][j]/=divisor;
    for(int i=0;i<8;++i)if(i!=k){double scale=a[i][k];for(int j=k;j<9;++j)a[i][j]-=scale*a[k][j];}
  }
  double h[9];for(int i=0;i<8;++i)h[i]=a[i][8];h[8]=1;
  double r1[3]={h[0],h[3],h[6]},r2[3]={h[1],h[4],h[7]};
  double scale=2/(sqrt(dot(r1,r1))+sqrt(dot(r2,r2)));
  if(!isfinite(scale)||scale<=0||!normalize(r1))return result;
  double crossTerm=dot(r1,r2);for(int i=0;i<3;++i)r2[i]-=crossTerm*r1[i];
  if(!normalize(r2))return result;
  double r3[3]={r1[1]*r2[2]-r1[2]*r2[1],r1[2]*r2[0]-r1[0]*r2[2],r1[0]*r2[1]-r1[1]*r2[0]};
  result.translation[0]=h[2]*scale;result.translation[1]=h[5]*scale;result.translation[2]=scale;
  for(int i=0;i<3;++i){result.rotation[3*i]=r1[i];result.rotation[3*i+1]=r2[i];result.rotation[3*i+2]=r3[i];}
  double error=0;
  for(int i=0;i<4;++i) {
    double x=r1[0]*model[i].x+r2[0]*model[i].y+result.translation[0];
    double y=r1[1]*model[i].x+r2[1]*model[i].y+result.translation[1];
    double z=r1[2]*model[i].x+r2[2]*model[i].y+result.translation[2];
    if(z<=0)return Pose{};
    Point p=project(x,y,z,c);error+=(p.x-pixels[i].x)*(p.x-pixels[i].x)+(p.y-pixels[i].y)*(p.y-pixels[i].y);
  }
  result.reprojectionPx=sqrt(error/4);if(!isfinite(result.reprojectionPx)||result.reprojectionPx>maxErrorPx)return Pose{};
  result.distance=sqrt(dot(result.translation,result.translation));
  result.roll=atan2(result.rotation[7],result.rotation[8]);
  result.pitch=asin(fmax(-1.,fmin(1.,-result.rotation[6])));
  result.yaw=atan2(result.rotation[3],result.rotation[0]);
  result.tilt=acos(fmax(-1.,fmin(1.,result.rotation[8])));
  result.valid=true;return result;
}
}
