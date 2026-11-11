<#
.SYNOPSIS
Live GPU HUD: utilization, VRAM, power, clocks, temps, PCIe throughput, process breakdown.

.DESCRIPTION
Runs nvidia-smi in a loop with formatted output. Shows:
- GPU utilization % (compute + memory)
- VRAM used/total + bar
- Power draw / limit
- Core / memory clocks
- Temperature
- PCIe RX/TX throughput
- Top processes by VRAM
#>
param(
    [int]$RefreshMs = 1000
)

function Clear-HostEx {
    $host.UI.RawUI.CursorPosition = @{X=0;Y=0}
}

function Get-GPUStats {
    $query = "utilization.gpu,utilization.memory,memory.used,memory.total,power.draw,power.limit,clocks.gr,clocks.mem,temperature.gpu,pcie.tx.pcie,pcie.rx.pcie,processes.pid,processes.used_gpu_memory,processes.name"
    $csv = nvidia-smi --query-gpu=$query --format=csv,noheader,nounits 2>$null
    if (-not $csv) { return @() }
    $csv.Split("`n") | Where-Object { $_ -match '\S' } | ForEach-Object {
        $parts = $_ -split ',\s*'
        [pscustomobject]@{
            GPUUtil       = [int]$parts[0]
            MemUtil       = [int]$parts[1]
            VRAMUsed      = [int]$parts[2]
            VRAMTotal     = [int]$parts[3]
            PowerDraw     = [decimal]$parts[4]
            PowerLimit    = [decimal]$parts[5]
            CoreClock     = [int]$parts[6]
            MemClock      = [int]$parts[7]
            Temp          = [int]$parts[8]
            PCieTX        = [decimal]$parts[9]
            PCieRX        = [decimal]$parts[10]
            ProcPID       = $parts[11]
            ProcVRAM      = $parts[12]
            ProcName      = $parts[13]
        }
    }
}

function Draw-Bar ($used, $total, $width=30) {
    $pct = if ($total -gt 0) { $used / $total } else { 0 }
    $filled = [math]::Floor($pct * $width)
    $empty  = $width - $filled
    "█" * $filled + "░" * $empty + " {0:P0}" -f $pct
}

function Format-GPU ($g) {
    $vramBar = Draw-Bar $g.VRAMUsed $g.VRAMTotal
    $powerBar = Draw-Bar $g.PowerDraw $g.PowerLimit 20
    $pcieTot  = $g.PCieTX + $g.PCieRX
    
    @"
╔══════════════════════════════════════════════════════════════════════════════╗
║  GPU HUD  |  Refresh: {$RefreshMs}ms  |  {Get-Date -Format 'HH:mm:ss'}                                    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Compute:   { $g.GPUUtil }%   |  Memory: { $g.MemUtil }%                                              ║
║  VRAM:      { $g.VRAMUsed } / { $g.VRAMTotal } MiB  { $vramBar }                                      ║
║  Power:     { $g.PowerDraw } / { $g.PowerLimit } W   { $powerBar }                                     ║
║  Clocks:    Core { $g.CoreClock } MHz  |  Mem { $g.MemClock } MHz                                       ║
║  Temp:      { $g.Temp }°C                                                                               ║
║  PCIe:      RX { $g.PCieRX } GB/s  |  TX { $g.PCieTX } GB/s  |  Total { [math]::Round($pcieTot,2) } GB/s                     ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  TOP PROCESSES BY VRAM:                                                          ║
"@
}

function Draw-Processes ($gpus) {
    $procs = $gpus | Where-Object { $_.ProcPID -ne '-' -and $_.ProcPID } |
        Select-Object ProcPID, ProcName, @{N='VRAM';E={[int]$_.ProcVRAM}} |
        Sort-Object VRAM -Descending |
        Select-Object -First 8
    
    if (-not $procs) { return "  (no GPU processes)" }
    
    $procs | ForEach-Object {
        "  PID {0,-6}  {1,-30}  {2,6} MiB" -f $_.ProcPID, $_.ProcName.Substring(0,[math]::Min(30,$_.ProcName.Length)), $_.VRAM
    }
}

try {
    while ($true) {
        Clear-HostEx
        $gpus = Get-GPUStats
        if ($gpus.Count -eq 0) {
            Write-Host "No NVIDIA GPU detected or nvidia-smi not in PATH" -ForegroundColor Red
            Start-Sleep -Milliseconds $RefreshMs
            continue
        }
        
        foreach ($g in $gpus) {
            Format-GPU $g | Write-Host
            Draw-Processes $gpus | Write-Host
        }
        
        Write-Host "╚══════════════════════════════════════════════════════════════════════════════╝"
        Start-Sleep -Milliseconds $RefreshMs
    }
}
finally {
    Clear-Host
}