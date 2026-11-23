#pragma once
#include "ArUco/marker_pose.h"
namespace aruco_config {
// REPLACE THESE PLACEHOLDERS before relying on metric measurements.
constexpr float MarkerSideM=.20f; // OUTER BLACK square; excludes white margin.
constexpr bool CalibrationVerified=false;
// Geometry transforms of the delivered JPEG, independent of sensor register
// settings. The live OV3660 JPEG already has readable marker parity: leave off.
constexpr bool DetectorMirrorX=false,DetectorFlipY=false;
// QVGA 320x240, in the unreflected detector image. Illustrative ~67 degree HFOV.
inline marker_pose::Calibration calibration() {
  marker_pose::Calibration c;c.fx=240;c.fy=240;c.cx=159.5f;c.cy=119.5f;
  c.k1=0;c.k2=0;c.p1=0;c.p2=0;c.k3=0;return c;
}
// This prototype recognizes the photographed OpenCV 7x7 ID 0, all rotations.
constexpr int TargetId=0;
constexpr uint32_t IdleYieldMs=2; // Process the latest new frame; yield between jobs.
constexpr uint32_t FullScanIntervalMs=500, TrackingMaxAgeMs=250;
constexpr uint32_t MaxAgeMs=700;
constexpr float MaxReprojectionPx=3;
// Command PREVIEW assumes downward camera, image top = drone forward.
// Confirm physical mounting and measured camera/body alignment before flight.
constexpr bool MountVerified=false;
constexpr float CameraTopClockwiseDeg=0;
constexpr float TargetHeightM=.75f,PositionDeadbandM=.05f;
constexpr float PositionGain=.5f,MaxHorizontalMps=.25f,MaxVerticalMps=.15f;
constexpr float YawGain=.5f,MaxYawRadps=.3f,YawDeadbandDeg=10;
}
