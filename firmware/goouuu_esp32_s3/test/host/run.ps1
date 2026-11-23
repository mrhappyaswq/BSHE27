$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
$vsPath = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vsPath) { throw 'Visual Studio C++ Build Tools are required' }
$vcvars = Join-Path $vsPath 'VC/Auxiliary/Build/vcvars64.bat'
$buildDir = Join-Path $repoRoot 'local/cpp-host-tests'
New-Item -ItemType Directory -Force $buildDir | Out-Null
Push-Location $buildDir
try {
  $compile = '"{0}" >nul && cl /nologo /EHsc /std:c++17 /I"{1}/test/host" /I"{1}/include" "{1}/test/host/test.cpp" /Fe:tests.exe /Fo:tests.obj' -f $vcvars, $projectRoot
  & cmd.exe /d /s /c $compile
  if ($LASTEXITCODE -ne 0) { throw 'C++ compilation failed' }
  & ./tests.exe (Join-Path $projectRoot 'test/host/fixtures/aruco-real-usb-frame.pgm')
  if ($LASTEXITCODE -ne 0) { throw 'C++ tests failed' }
} finally { Pop-Location }
