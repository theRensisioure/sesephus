<#
.SYNOPSIS
Launch vertically split WT: left = inference harness, right = GPU HUD.

.USAGE
.\tools\launch-split.ps1 -Harness "your-command" -RefreshMs 1000
#>
param(
    [string]$Harness = "powershell.exe -NoExit -Command `\"cd C:\dev\sesephus; .\tools\voice.py --say 'test' --duration 30 --backend heuristic`\"",
    [int]$RefreshMs = 1000
)

$hudCmd = "powershell.exe -NoExit -Command `\"cd C:\dev\sesephus; .\tools\gpu-hud.ps1 -RefreshMs $RefreshMs`\""

wt.exe `
    -p "PowerShell" `
    -d "C:\dev\sesephus" `
    split-pane -V `
    -p "PowerShell" `
    -d "C:\dev\sesephus" `
    `$hudCmd `
    ; `
    new-tab `
    -p "PowerShell" `
    -d "C:\dev\sesephus" `
    `$Harness