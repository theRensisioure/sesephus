# Install Start Menu + Desktop shortcuts named "Sesefus" (Windows search).
# Does NOT enable Startup by default — that path has failed before; use
# install-startup.ps1 only if you want a best-effort daemon-only try.
param(
  [switch]$Desktop = $true,
  [switch]$StartMenu = $true
)

$ErrorActionPreference = "Stop"
$App = $PSScriptRoot
$Vbs = Join-Path $App "Sesefus.vbs"
if (-not (Test-Path $Vbs)) { throw "Missing Sesefus.vbs in $App" }

function New-Shortcut([string]$Path, [string]$Target, [string]$WorkDir, [string]$Desc) {
  $w = New-Object -ComObject WScript.Shell
  $s = $w.CreateShortcut($Path)
  $s.TargetPath = "wscript.exe"
  $s.Arguments = "`"$Target`""
  $s.WorkingDirectory = $WorkDir
  $s.Description = $Desc
  $s.WindowStyle = 7
  $s.Save()
  Write-Host "wrote $Path"
}

if ($StartMenu) {
  $dir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  New-Shortcut (Join-Path $dir "Sesefus.lnk") $Vbs $App "Sesefus journal · record + alarms"
  # searchable aliases
  New-Shortcut (Join-Path $dir "Sesefus Journal.lnk") $Vbs $App "Sesefus journal dual module"
}

if ($Desktop) {
  $desk = [Environment]::GetFolderPath("Desktop")
  New-Shortcut (Join-Path $desk "Sesefus.lnk") $Vbs $App "Sesefus journal · record + alarms"
}

Write-Host ""
Write-Host "Search Windows for: Sesefus"
Write-Host "Pin the Start Menu entry (not a live python window)."
Write-Host "Startup is OPTIONAL and often flaky - see install-startup.ps1"
