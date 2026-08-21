$ErrorActionPreference = "Stop"
$msvc = "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Tools\MSVC\14.51.36231"
$sdk = "C:\Program Files (x86)\Windows Kits\10"
$ver = "10.0.26100.0"
$env:PATH = "$msvc\bin\Hostx64\x64;$sdk\bin\x64;$env:PATH"
$env:INCLUDE = "$msvc\include;$sdk\Include\$ver\ucrt;$sdk\Include\$ver\shared;$sdk\Include\$ver\um;$sdk\Include\$ver\winrt"
$env:LIB = "$msvc\lib\x64;$sdk\Lib\$ver\ucrt\x64;$sdk\Lib\$ver\um\x64"
Set-Location $PSScriptRoot
New-Item -ItemType Directory -Force -Path out, out\ui | Out-Null
Write-Host "cl..."
& cl /nologo /EHsc /O2 /std:c++17 /W3 /Fe:out\sesefus-record.exe src\main.cpp /link bcrypt.lib ws2_32.lib
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Copy-Item -Force ui\index.html out\ui\index.html
Write-Host "OK" (Get-Item out\sesefus-record.exe).FullName (Get-Item out\sesefus-record.exe).Length
