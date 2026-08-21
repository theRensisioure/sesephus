# OPTIONAL: put a Startup-folder shortcut that starts alarm daemon only (no UI).
# Honest: user reports "startup never worked" on this machine — this is best-effort.
# Prefer: Start Menu "Sesefus" after login, then "Start alarm daemon" in UI.
param(
  [switch]$Remove
)

$ErrorActionPreference = "Stop"
$App = $PSScriptRoot
$Startup = [Environment]::GetFolderPath("Startup")
$Lnk = Join-Path $Startup "Sesefus-alarm-daemon.lnk"
$LogDir = Join-Path $env:LOCALAPPDATA "Sesefus"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

if ($Remove) {
  if (Test-Path $Lnk) { Remove-Item $Lnk -Force; Write-Host "removed $Lnk" }
  else { Write-Host "no startup lnk" }
  exit 0
}

# Resolve pythonw
$pyw = @(
  "$env:LOCALAPPDATA\Programs\Python\Python312\pythonw.exe",
  "$env:LOCALAPPDATA\Programs\Python\Python311\pythonw.exe",
  "$env:LOCALAPPDATA\Programs\Python\Python314\pythonw.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $pyw) {
  $cmd = Get-Command pythonw -ErrorAction SilentlyContinue
  if ($cmd) { $pyw = $cmd.Source }
}
if (-not $pyw) { throw "pythonw not found — cannot install startup daemon" }

$hostPy = Join-Path $App "ui_host.py"
$w = New-Object -ComObject WScript.Shell
$s = $w.CreateShortcut($Lnk)
$s.TargetPath = $pyw
$s.Arguments = "`"$hostPy`" --daemon-only"
$s.WorkingDirectory = $App
$s.Description = "Sesefus alarm daemon only (optional startup — may fail silently)"
$s.WindowStyle = 7
$s.Save()

Write-Host "wrote $Lnk"
Write-Host "Target: $pyw $hostPy --daemon-only"
Write-Host ""
Write-Host "HONEST: if this does not fire after reboot, do not debug forever."
Write-Host "Use Start Menu → Sesefus → Start alarm daemon instead."
Write-Host "Log dir: $LogDir"
