#pragma once
#include <stdint.h>
#include <math.h>
namespace exposure_math {
// OV3660 clock tree, matching Espressif's ov3660.c calc_sysclk().
inline double rowUs(uint32_t xclk,int r0,int r1,int r2,int r3,int hts) {
  if(!xclk || r0<0 || r1<0 || r2<0 || r3<0 || hts<=0) return 0;
  const int pre2[]={2,3,4,6},seld2[]={2,2,4,5};
  int sys=r2&15; if(!sys) sys=1;
  double vco=double(xclk)*(r1&31)*((r3&64)?2:1)*2/pre2[(r3>>4)&3];
  double pll=(r0&128)?xclk:vco*2/sys/seld2[r3&3];
  return pll>0 ? double(hts)*4000000/pll : 0;
}
inline int rowsForUs(double us,double row,int vts) {
  if(!isfinite(us) || !isfinite(row) || row<=0 || us<100 || us>20000 || vts<5) return -1;
  int rows=int(us/row+0.5);
  return rows>=1 && rows<=vts-4 ? rows : -1;
}
}
