$ErrorActionPreference = 'Stop'
$viewer = (Resolve-Path (Join-Path $PSScriptRoot '../Code/Web Server/viewer.html')).Path
$viewerUri = ([System.Uri]::new($viewer)).AbsoluteUri
$chromePaths = @(
  (Join-Path $env:ProgramFiles 'Google/Chrome/Application/chrome.exe'),
  (Join-Path ${env:ProgramFiles(x86)} 'Google/Chrome/Application/chrome.exe'),
  (Join-Path $env:LOCALAPPDATA 'Google/Chrome/Application/chrome.exe')
)
$edgePaths = @(
  (Join-Path ${env:ProgramFiles(x86)} 'Microsoft/Edge/Application/msedge.exe'),
  (Join-Path $env:ProgramFiles 'Microsoft/Edge/Application/msedge.exe')
)
$browser = @($chromePaths + $edgePaths) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if ($browser) { Start-Process -FilePath $browser -ArgumentList $viewerUri }
else { Start-Process -FilePath $viewer }
Write-Output 'Connect the OTG USB-C port (not TTL), click Connect USB, and choose the Espressif USB JTAG/serial device. The video streams continuously; no Wi-Fi is needed.'
