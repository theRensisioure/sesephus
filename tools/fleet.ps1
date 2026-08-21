<#
  fleet.ps1 - Sesefus Fleet Runner

  Brings up the three runtimes of "The Fleet" as one supervised unit:

      Engine  - Zig    - ssfs.bat --role host      - TCP 5000 / HTTP 3000
      Bridge  - Python - dashboard_server.py       - FastAPI 3001
      Glass   - React  - dashboard/ui  (vite dev)   - 5173

  All three run in the background; their stdout/stderr is multiplexed into this
  single console with [Engine]/[Bridge]/[Glass] prefixes.

  Usage:
    tools\fleet.ps1                 probe, launch all three, supervise
    tools\fleet.ps1 -ProbeOnly      just report resource/orphan state, launch nothing
    tools\fleet.ps1 -Reap           kill orphans holding fleet ports, then launch
    tools\fleet.ps1 -Watch          after launch, keep sampling RSS and warn on growth
    tools\fleet.ps1 -RssRunawayMB 120   tune the idle-growth threshold for the canary
#>
[CmdletBinding()]
param(
  [switch]$ProbeOnly,
  [switch]$Reap,
  [switch]$Watch,
  [int]$RssRunawayMB = 150,
  [int]$CanarySeconds = 6
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
$script:TornDown = $false

$Runtimes = @(
  [pscustomobject]@{
    Name = 'Engine'; Tag = 'Zig'
    File = 'cmd.exe'; Args = @('/c', "`"$Root\ssfs.bat`"", '--role', 'host')
    WorkDir = $Root
    ReadyPort = 5000; AltPorts = @(3000); ReadyTimeout = 120
  },
  [pscustomobject]@{
    Name = 'Bridge'; Tag = 'Python'
    File = (Join-Path $Root 'venv\Scripts\python.exe')
    Args = @((Join-Path $Root 'dashboard\dashboard_server.py'))
    WorkDir = $Root
    ReadyPort = 3001; AltPorts = @(); ReadyTimeout = 90
  },
  [pscustomobject]@{
    Name = 'Glass'; Tag = 'React'
    File = 'cmd.exe'; Args = @('/c', 'npm.cmd', 'run', 'dev')
    WorkDir = (Join-Path $Root 'dashboard\ui')
    ReadyPort = 5173; AltPorts = @(); ReadyTimeout = 60
  }
)
$AllPorts = @(5000, 3000, 3001, 5173)

$LogDir = Join-Path $env:TEMP "sesefus-fleet-$PID"
$LogOffsets = @{}

function Write-Head($t) { Write-Host "`n=== $t ===" -ForegroundColor Cyan }
function Write-Ok($t)   { Write-Host "  [ok]   $t" -ForegroundColor Green }
function Write-Warn2($t){ Write-Host "  [warn] $t" -ForegroundColor Yellow }
function Write-Bad($t)  { Write-Host "  [FAIL] $t" -ForegroundColor Red }

function Get-PortOwnerPid([int]$Port) {
  try {
    $c = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction Stop |
         Select-Object -First 1
    if ($c) { return [int]$c.OwningProcess }
  } catch {}
  return $null
}

function Get-ProcInfo([int]$ProcId) {
  try { return Get-Process -Id $ProcId -ErrorAction Stop } catch { return $null }
}

function Test-PortOpen([int]$Port, [string]$HostName = '127.0.0.1', [int]$TimeoutMs = 400) {
  $client = [System.Net.Sockets.TcpClient]::new()
  try {
    $iar = $client.BeginConnect($HostName, $Port, $null, $null)
    if ($iar.AsyncWaitHandle.WaitOne($TimeoutMs)) {
      $client.EndConnect($iar); return $true
    }
    return $false
  } catch { return $false }
  finally { $client.Close() }
}

function Test-PortListening([int]$Port) {
  if (Get-PortOwnerPid $Port) { return $true }
  if (Test-PortOpen $Port '127.0.0.1') { return $true }
  if (Test-PortOpen $Port '::1') { return $true }
  return $false
}

function Test-RuntimeHealthy([pscustomobject]$Runtime) {
  if (-not (Test-PortListening $Runtime.ReadyPort)) { return $false }
  foreach ($alt in $Runtime.AltPorts) {
    if (-not (Test-PortListening $alt)) { return $false }
  }
  return $true
}

function Get-RuntimePorts([pscustomobject]$Runtime) {
  @($Runtime.ReadyPort) + @($Runtime.AltPorts)
}

function Kill-Tree([int]$ProcId, [string]$Label) {
  if (-not $ProcId) { return }
  if (-not (Get-ProcInfo $ProcId)) { return }
  Write-Host "  taskkill /T /F PID $ProcId  ($Label)" -ForegroundColor DarkGray
  cmd.exe /c "taskkill /PID $ProcId /T /F >nul 2>&1"
}

function Ensure-LogDir {
  if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
  }
}

function Start-FleetProcess([pscustomobject]$Runtime) {
  Ensure-LogDir
  $stdout = Join-Path $LogDir ("{0}.out" -f $Runtime.Name)
  $stderr = Join-Path $LogDir ("{0}.err" -f $Runtime.Name)
  foreach ($path in @($stdout, $stderr)) {
    if (Test-Path $path) { Remove-Item $path -Force }
    $LogOffsets[$path] = 0
  }

  $proc = Start-Process -FilePath $Runtime.File -ArgumentList $Runtime.Args `
            -WorkingDirectory $Runtime.WorkDir -PassThru -NoNewWindow `
            -RedirectStandardOutput $stdout -RedirectStandardError $stderr

  [pscustomobject]@{
    Name = $Runtime.Name
    LauncherPid = $proc.Id
    OwnerPid = $proc.Id
    LogOut = $stdout
    LogErr = $stderr
    Process = $proc
  }
}

function Drain-Logs([object[]]$Entries) {
  foreach ($entry in $Entries) {
    foreach ($pair in @(
      @{ Path = $entry.LogOut; Stream = 'out' },
      @{ Path = $entry.LogErr; Stream = 'err' }
    )) {
      $path = $pair.Path
      if (-not (Test-Path $path)) { continue }

      $info = Get-Item $path
      $offset = if ($LogOffsets.ContainsKey($path)) { $LogOffsets[$path] } else { 0 }
      if ($info.Length -le $offset) { continue }

      $stream = [System.IO.File]::Open($path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
      try {
        $null = $stream.Seek($offset, [System.IO.SeekOrigin]::Begin)
        $reader = New-Object System.IO.StreamReader($stream)
        while ($null -ne ($line = $reader.ReadLine())) {
          if ($line.Length -eq 0) { continue }
          $color = if ($pair.Stream -eq 'err') { 'Yellow' } else { 'Gray' }
          Write-Host ("[{0}] {1}" -f $entry.Name, $line) -ForegroundColor $color
        }
        $LogOffsets[$path] = $stream.Position
      } finally {
        $stream.Close()
      }
    }
  }
}

# ===========================================================================
# PHASE 1 - PROBE
# ===========================================================================
Write-Head "PROBE - resource preflight"

$os = Get-CimInstance Win32_OperatingSystem
$freeGB  = [math]::Round($os.FreePhysicalMemory / 1MB, 1)
$totalGB = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
Write-Host ("  RAM free {0} GB / {1} GB total" -f $freeGB, $totalGB)
if ($freeGB -lt 3) {
  Write-Warn2 "Under 3 GB free - Whisper + Ollama may thrash. Consider closing things."
} else {
  Write-Ok "Memory headroom looks fine for the fleet."
}

$orphans = @()
foreach ($p in $AllPorts) {
  $ownerPid = Get-PortOwnerPid $p
  if ($ownerPid) {
    $pi = Get-ProcInfo $ownerPid
    $nm = if ($pi) { $pi.ProcessName } else { 'unknown' }
    $wsMB = if ($pi) { [math]::Round($pi.WorkingSet64 / 1MB) } else { 0 }
    $orphans += [pscustomobject]@{ Port = $p; ProcId = $ownerPid; Name = $nm; RssMB = $wsMB }
    Write-Bad ("port {0} already held by {1} (PID {2}, {3} MB) - leaked prior run" -f $p, $nm, $ownerPid, $wsMB)
  }
}
if (-not $orphans) { Write-Ok "All fleet ports (5000/3000/3001/5173) are free - no leaked run." }

if ($orphans -and $Reap -and -not $ProbeOnly) {
  Write-Head "REAP - clearing leaked processes"
  foreach ($o in ($orphans | Sort-Object ProcId -Unique)) {
    Kill-Tree $o.ProcId ("orphan on :" + $o.Port)
  }
  Start-Sleep -Milliseconds 800
  $still = @($AllPorts | Where-Object { Get-PortOwnerPid $_ })
  if ($still) {
    Write-Bad ("ports still held after reap: " + ($still -join ', ') + " - aborting.")
    exit 1
  }
  Write-Ok "Ports cleared."
  $orphans = @()
}

if ($ProbeOnly) {
  Write-Head "PROBE-ONLY - nothing launched"
  if ($orphans) { exit 1 } else { exit 0 }
}

if ($orphans) {
  Write-Head "REFUSING TO LAUNCH"
  Write-Host "  A prior fleet is still alive on the ports above. Launching now would stack"
  Write-Host "  a second copy and waste the machine. Re-run with -Reap to clear them first,"
  Write-Host "  or stop them yourself."
  exit 1
}

# ===========================================================================
# PHASE 2 - LAUNCH
# ===========================================================================
$Launched = New-Object System.Collections.ArrayList

function Teardown([string]$Why) {
  if ($script:TornDown) { return }
  $script:TornDown = $true
  Write-Head "TEARDOWN - $Why"
  for ($i = $Launched.Count - 1; $i -ge 0; $i--) {
    $r = $Launched[$i]
    Kill-Tree $r.OwnerPid    ("$($r.Name) server")
    Kill-Tree $r.LauncherPid ("$($r.Name) launcher")
  }
  foreach ($p in $AllPorts) {
    $op = Get-PortOwnerPid $p
    if ($op) { Kill-Tree $op "residual on :$p" }
  }
  Write-Ok "Fleet down. No processes left holding fleet ports."
}

try {
  foreach ($rt in $Runtimes) {
    Write-Head "LAUNCH - $($rt.Name) ($($rt.Tag))"

    if (($rt.File -like '*\*') -and -not (Test-Path $rt.File)) {
      Write-Bad "missing executable: $($rt.File)  (run install.bat?)"
      Teardown "prerequisite missing"; exit 1
    }
    if ($rt.Name -eq 'Glass' -and -not (Test-Path (Join-Path $rt.WorkDir 'node_modules'))) {
      Write-Bad "missing node_modules in dashboard\ui  (run: cd dashboard\ui && npm install)"
      Teardown "prerequisite missing"; exit 1
    }

    $entry = Start-FleetProcess $rt
    Write-Host "  launcher PID $($entry.LauncherPid); waiting up to $($rt.ReadyTimeout)s for :$($rt.ReadyPort)..."
    Write-Host "  logs: $($entry.LogOut)" -ForegroundColor DarkGray

    $ready = $false
    $deadline = (Get-Date).AddSeconds($rt.ReadyTimeout)
    while ((Get-Date) -lt $deadline) {
      Drain-Logs @($entry)

      if ($entry.Process.HasExited) {
        Drain-Logs @($entry)
        Write-Bad "$($rt.Name) exited during startup (code $($entry.Process.ExitCode)) - crash-loop, not launching the rest."
        [void]$Launched.Add($entry)
        Teardown "$($rt.Name) crashed on startup"; exit 1
      }
      if (Test-PortListening $rt.ReadyPort) { $ready = $true; break }
      Start-Sleep -Milliseconds 500
    }
    Drain-Logs @($entry)

    if (-not $ready) {
      Write-Bad "$($rt.Name) never opened :$($rt.ReadyPort) within $($rt.ReadyTimeout)s."
      [void]$Launched.Add($entry)
      Teardown "$($rt.Name) never became ready"; exit 1
    }

    $ownerPid = Get-PortOwnerPid $rt.ReadyPort
    $owner = if ($ownerPid) { Get-ProcInfo $ownerPid } else { $null }
    if (-not $owner) { $owner = $entry.Process; $ownerPid = $entry.LauncherPid }
    $entry.OwnerPid = $ownerPid
    Write-Ok "$($rt.Name) ready on :$($rt.ReadyPort)  (server PID $ownerPid, $($owner.ProcessName))"

    Start-Sleep -Seconds 1
    $samples = @()
    $cDeadline = (Get-Date).AddSeconds($CanarySeconds)
    while ((Get-Date) -lt $cDeadline) {
      Drain-Logs @($entry)
      $pi = Get-ProcInfo $ownerPid
      if (-not $pi) { break }
      $samples += [math]::Round($pi.WorkingSet64 / 1MB)
      Start-Sleep -Milliseconds 700
    }
    Drain-Logs @($entry)

    if ($samples.Count -ge 2) {
      $first = $samples[0]; $last = $samples[-1]; $peak = ($samples | Measure-Object -Maximum).Maximum
      $growth = $last - $first
      Write-Host ("  idle RSS: start {0}MB -> end {1}MB (peak {2}MB) over {3}s" -f $first, $last, $peak, $CanarySeconds)
      if ($growth -ge $RssRunawayMB) {
        Write-Bad ("$($rt.Name) grew {0}MB while idle (threshold {1}MB) - leak canary tripped." -f $growth, $RssRunawayMB)
        [void]$Launched.Add($entry)
        Teardown "$($rt.Name) leaking on idle"; exit 1
      }
      Write-Ok "$($rt.Name) idle memory is stable."
    }

    [void]$Launched.Add($entry)
  }

  # =========================================================================
  # PHASE 3 - SUPERVISE (single console, multiplexed daemon output)
  # =========================================================================
  Write-Head "FLEET UP - all three runtimes vetted and running"
  Write-Host "  Engine  http://127.0.0.1:3000   (TCP 5000)"
  Write-Host "  Bridge  http://127.0.0.1:3001   (API)"
  Write-Host "  Glass   http://127.0.0.1:5173   <- open this"
  Write-Host "  Log dir $LogDir"
  Write-Host "`n  Ctrl-C to bring the whole fleet down cleanly.`n" -ForegroundColor DarkGray

  $WatchRssLast = @{}

  while ($true) {
    Drain-Logs @($Launched)
    Start-Sleep -Milliseconds 400

    foreach ($r in $Launched) {
      $rt = $Runtimes | Where-Object Name -eq $r.Name
      if (-not (Test-RuntimeHealthy $rt)) {
        Drain-Logs @($Launched)
        $ports = Get-RuntimePorts $rt
        Write-Bad ("$($r.Name) went down (port(s) closed: " + ($ports -join ', ') + ").")
        Teardown "$($r.Name) died - no half-fleet left running"; exit 1
      }
    }

    if ($Watch) {
      $line = foreach ($r in $Launched) {
        $pi = Get-ProcInfo $r.OwnerPid
        $mb = if ($pi) { [math]::Round($pi.WorkingSet64 / 1MB) } else { 0 }
        if ($WatchRssLast.ContainsKey($r.Name)) {
          $growth = $mb - $WatchRssLast[$r.Name]
          if ($growth -ge $RssRunawayMB) {
            Write-Warn2 ("$($r.Name) grew {0}MB since last sample (now {1}MB)" -f $growth, $mb)
          }
        }
        $WatchRssLast[$r.Name] = $mb
        "{0} {1}MB" -f $r.Name, $mb
      }
      Write-Host ("  [watch] " + ($line -join '  |  ')) -ForegroundColor DarkGray
    }
  }
}
finally {
  if ($Launched.Count -gt 0) { Teardown "runner exiting" }
}
