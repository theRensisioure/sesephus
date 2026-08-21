@echo off
cd /d "%~dp0"
if not exist venv (
    echo [!] Run install.bat first.
    pause
    exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\fleet.ps1" %*
if errorlevel 1 pause
exit /b %ERRORLEVEL%
