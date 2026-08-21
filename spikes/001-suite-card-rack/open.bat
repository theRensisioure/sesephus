@echo off
REM Spike 001 — open the suite rack cleanly (no broken start quoting)
set PORT=8791
set DIR=%~dp0
cd /d "%DIR%"

REM Prefer existing server
curl -s -o NUL -m 1 "http://127.0.0.1:%PORT%/rack.html" 2>NUL
if %ERRORLEVEL%==0 goto OPEN

start "sesefus-rack-spike" /MIN python -m http.server %PORT% --directory "%DIR%"
timeout /t 1 /nobreak >NUL

:OPEN
start "" "http://127.0.0.1:%PORT%/rack.html"
echo Opened http://127.0.0.1:%PORT%/rack.html
