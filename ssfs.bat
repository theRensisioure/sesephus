@echo off
setlocal
cd /d "%~dp0core\sesephus"
zig build
if %errorlevel% neq 0 (
    echo [ssfs] Build failed.
    exit /b %errorlevel%
)
cd /d "%~dp0"
"%~dp0core\sesephus\zig-out\bin\sesefus.exe" %*
