@echo off
setlocal
cd /d "%~dp0"
if not exist venv (
    echo [!] Run install.bat first.
    exit /b 1
)
venv\Scripts\python tools\voice.py %*
endlocal
