#pragma once
namespace aruco_image {
// The same self-inverse mapping is used for grayscale input and overlay output.
// Do not infer these transforms from OV3660 sensor flip/mirror register flags.
template<class T> inline void map(T& x,T& y,int width,int height,bool mirrorX,bool flipY){
  if(mirrorX)x=T(width-1)-x;
  if(flipY)y=T(height-1)-y;
}
}
