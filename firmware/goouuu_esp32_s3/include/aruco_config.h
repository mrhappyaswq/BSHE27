#pragma once
#include "marker_pose.h"
namespace aruco_config {
// REPLACE THESE PLACEHOLDERS before relying on metric measurements.
constexpr double MarkerSideM=.20; // OUTER BLACK square; excludes white margin.
constexpr bool CalibrationVerified=false;
// Geometry transforms of the delivered JPEG, independent of sensor register
// settings. The live OV3660 JPEG already has readable marker parity: leave off.
constexpr bool DetectorMirrorX=false,DetectorFlipY=false;
// QVGA 320x240, in the unreflected detector image. Illustrative ~67 degree HFOV.
inline marker_pose::Calibration calibration() {
  marker_pose::Calibration c;c.fx=240;c.fy=240;c.cx=159.5;c.cy=119.5;
  c.k1=0;c.k2=0;c.p1=0;c.p2=0;c.k3=0;return c;
}
// This prototype recognizes the photographed OpenCV 7x7 ID 0, all rotations.
constexpr int TargetId=0;
constexpr uint32_t IntervalMs=200; // At most 5 analyzed frames/s initially.
constexpr uint32_t MaxAgeMs=700;
constexpr double MaxReprojectionPx=3;
// Command PREVIEW assumes downward camera, image top = drone forward.
// Confirm physical mounting and measured camera/body alignment before flight.
constexpr bool MountVerified=false;
constexpr double CameraTopClockwiseDeg=0;
constexpr double TargetHeightM=.75,PositionDeadbandM=.05;
constexpr double PositionGain=.5,MaxHorizontalMps=.25,MaxVerticalMps=.15;
constexpr double YawGain=.5,MaxYawRadps=.3,YawDeadbandDeg=10;
}
