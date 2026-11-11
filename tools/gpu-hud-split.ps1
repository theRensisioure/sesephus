<# 
.SYNOPSIS
Launches a vertically split PowerShell session: left pane for inference harness, right pane for GPU/memory HUD.

.DESCRIPTION
Creates a Windows Terminal profile (or uses existing) with two vertical panes:
- Pane 1 (left): Runs your inference command/harness
- Pane 2 (right): Live GPU utilization, VRAM, power, clocks, temps via nvidia-smi + custom memory plumbing

.PARAMETER HarnessCommand
The command to run in the inference pane (default: "lmstudio" or your harness)

.PARAMETER RefreshMs
HUD refresh interval in milliseconds (default: 1000)
#>
param(
    [string]$HarnessCommand = "lmstudio",
    [int]$RefreshMs = 1000
)

$wtProfile = @"
{
    "name": "Inference + GPU HUD",
    "commandline": "powershell.exe",
    "splitMode": "vertical",
    "splitPane": {
        "profile": "Inference Harness",
        "commandline": "powershell.exe -NoExit -Command `"$HarnessCommand`""
    },
    "pane": {
        "profile": "GPU HUD",
        "commandline": "powershell.exe -NoExit -Command `".\tools\gpu-hud.ps1 -RefreshMs $RefreshMs`""
    }
}
"@

$profilesPath = "$env:LOCALAPPDATA\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json"
if (-not (Test-Path $profilesPath)) {
    Write-Error "Windows Terminal not found or settings.json missing at $profilesPath"
    exit 1
}

$settings = Get-Content $profilesPath -Raw | ConvertFrom-Json
$profiles = $settings.profiles.list

$inferenceProfile = @{
    name        = "Inference Harness"
    commandline = "powershell.exe"
    startingDirectory = "C:\dev\sesephus"
}

$hudProfile = @{
    name        = "GPU HUD"
    commandline = "powershell.exe"
    startingDirectory = "C:\dev\sesephus"
}

$profiles += $inferenceProfile, $hudProfile
$settings.profiles.list = $profiles

$settings | ConvertTo-Json -Depth 10 | Set-Content $profilesPath

Write-Host "Profiles added. Launch with: wt -p 'Inference + GPU HUD'" -ForegroundColor Green