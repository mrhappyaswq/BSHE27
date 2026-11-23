$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$vswhere = Join-Path ([Environment]::GetFolderPath('ProgramFilesX86')) 'Microsoft Visual Studio/Installer/vswhere.exe'
$vsPath = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vsPath) { throw 'Visual Studio C++ Build Tools are required' }
$vcvars = Join-Path $vsPath 'VC/Auxiliary/Build/vcvars64.bat'
$buildDir = Join-Path $repoRoot 'Saved Results/Code Checks'
New-Item -ItemType Directory -Force $buildDir | Out-Null
Push-Location $buildDir
try {
  $compile = '"{0}" >nul && cl /nologo /EHsc /std:c++17 /O2 /DNO_SIMD /I"{1}" /I"{2}/Code" /I"{2}/Code/Third Party/JPEGDEC/src" "{1}/test.cpp" "{2}/Code/Third Party/JPEGDEC/src/JPEGDEC.cpp" /Fe:tests.exe /Fo"./"' -f $vcvars, $PSScriptRoot, $repoRoot
  & cmd.exe /d /s /c $compile
  if ($LASTEXITCODE -ne 0) { throw 'C++ compilation failed' }
  & ./tests.exe (Join-Path $PSScriptRoot 'Test Pictures/aruco-real-usb-frame.pgm') (Join-Path $PSScriptRoot 'Test Pictures/ov3660-color.jpg') (Join-Path $PSScriptRoot 'Test Pictures/gray-16x16.jpg') (Join-Path $PSScriptRoot 'Test Pictures/marker.jpg')
  if ($LASTEXITCODE -ne 0) { throw 'C++ tests failed' }
  $metadata = Get-Content -LiteralPath 'vision-metadata.json' -Raw | ConvertFrom-Json
  if ($metadata.search_pixels -ne 12345 -or $metadata.pose_ms -ne 5 -or $metadata.heap_free -ne 100000) { throw 'Vision JSON fields failed' }
} finally { Pop-Location }
