@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "VCVARS="
if exist "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" (
  set "VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
)
if not defined VCVARS if exist "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" (
  set "VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
)
if not defined VCVARS (
  echo vcvars64.bat not found
  exit /b 1
)

echo Using: %VCVARS%
call "%VCVARS%"
if errorlevel 1 (
  echo vcvars failed
  exit /b 1
)

if not exist out mkdir out
echo Compiling...
cl /nologo /EHsc /O2 /std:c++17 /W3 /Fe:out\sesefus-record.exe src\main.cpp /link bcrypt.lib ws2_32.lib
if errorlevel 1 (
  echo compile failed
  exit /b 1
)

if not exist out\ui mkdir out\ui
copy /Y ui\index.html out\ui\index.html >nul
echo.
echo built out\sesefus-record.exe
dir out\sesefus-record.exe
endlocal
