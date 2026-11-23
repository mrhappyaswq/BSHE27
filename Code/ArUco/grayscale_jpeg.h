#pragma once
#include <JPEGDEC.h>
#include <string.h>
#include <limits.h>
#include "ArUco/aruco_image.h"

namespace aruco_image {
// Persistent caller-owned decoder: never place JPEGDEC's large state on a task stack.
class GrayDecoder {
  JPEGDEC decoder;
  uint8_t* output=nullptr;
  int width=0,height=0;
  bool mirror=false,flip=false,valid=false;
  size_t written=0;
  static int draw(JPEGDRAW* block){
    auto& self=*static_cast<GrayDecoder*>(block->pUser);
    int used=block->iWidthUsed;
    if(block->iBpp!=8||block->x<0||block->y<0||used<=0||used>block->iWidth||
       block->x+used>self.width||block->y+block->iHeight>self.height){self.valid=false;return 0;}
    const auto* pixels=reinterpret_cast<const uint8_t*>(block->pPixels);
    for(int row=0;row<block->iHeight;++row){
      if(!self.mirror&&!self.flip){
        memcpy(self.output+(block->y+row)*self.width+block->x,pixels+row*block->iWidth,used);
      }else for(int col=0;col<used;++col){
        int x=block->x+col,y=block->y+row;
        map(x,y,self.width,self.height,self.mirror,self.flip);
        self.output[y*self.width+x]=pixels[row*block->iWidth+col];
      }
    }
    self.written+=used*block->iHeight;
    return 1;
  }
public:
  bool decode(const uint8_t* jpeg,size_t size,uint8_t* gray,int expectedWidth,int expectedHeight,
              int maxWidth,int maxHeight,bool mirrorX=false,bool flipY=false){
    if(!jpeg||!gray||size<4||size>INT_MAX||jpeg[0]!=0xff||jpeg[1]!=0xd8||jpeg[size-2]!=0xff||jpeg[size-1]!=0xd9)return false;
    if(!decoder.openRAM(const_cast<uint8_t*>(jpeg),int(size),draw))return false;
    bool dimensions=decoder.getWidth()==expectedWidth&&decoder.getHeight()==expectedHeight&&decoder.getJPEGType()==JPEG_MODE_BASELINE;
    int shift=0;
    while(((expectedWidth+((1<<shift)-1))>>shift)>maxWidth||
          ((expectedHeight+((1<<shift)-1))>>shift)>maxHeight){if(++shift>3){dimensions=false;break;}}
    width=(expectedWidth+((1<<shift)-1))>>shift;height=(expectedHeight+((1<<shift)-1))>>shift;
    written=0;output=gray;mirror=mirrorX;flip=flipY;valid=dimensions&&width>0&&height>0;
    int options=JPEG_LUMA_ONLY;
    if(shift==1)options|=JPEG_SCALE_HALF;else if(shift==2)options|=JPEG_SCALE_QUARTER;else if(shift==3)options|=JPEG_SCALE_EIGHTH;
    decoder.setPixelType(EIGHT_BIT_GRAYSCALE);decoder.setUserPointer(this);
    bool ok=valid&&decoder.decode(0,0,options);decoder.close();return ok&&valid&&written==size_t(width*height);
  }
  int decodedWidth()const{return width;}
  int decodedHeight()const{return height;}
};
}
