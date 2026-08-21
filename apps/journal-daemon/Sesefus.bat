@echo off
REM Sesefus journal — pin THIS or Start Menu shortcut, never a live python.exe window.
cd /d "%~dp0"
set "LOG=%LOCALAPPDATA%\Sesefus\last-launch.log"
if not exist "%LOCALAPPDATA%\Sesefus" mkdir "%LOCALAPPDATA%\Sesefus"
echo ==== %DATE% %TIME% Sesefus.bat ==== >> "%LOG%"
echo APP=%CD%>> "%LOG%"

set PYW=
set PY=
if exist "%LocalAppData%\Programs\Python\Python312\pythonw.exe" set "PYW=%LocalAppData%\Programs\Python\Python312\pythonw.exe"
if exist "%LocalAppData%\Programs\Python\Python311\pythonw.exe" if not defined PYW set "PYW=%LocalAppData%\Programs\Python\Python311\pythonw.exe"
if exist "%LocalAppData%\Programs\Python\Python314\pythonw.exe" if not defined PYW set "PYW=%LocalAppData%\Programs\Python\Python314\pythonw.exe"
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PY=%LocalAppData%\Programs\Python\Python312\python.exe"
if exist "%LocalAppData%\Programs\Python\Python311\python.exe" if not defined PY set "PY=%LocalAppData%\Programs\Python\Python311\python.exe"
if exist "%LocalAppData%\Programs\Python\Python314\python.exe" if not defined PY set "PY=%LocalAppData%\Programs\Python\Python314\python.exe"
if not defined PY where python >nul 2>&1 && set PY=python
if not defined PYW if defined PY (
  for %%I in ("%PY%") do if exist "%%~dpIpythonw.exe" set "PYW=%%~dpIpythonw.exe"
)

if not defined PYW if not defined PY (
  echo No Python found. Install Python 3.11+ >> "%LOG%"
  echo No Python found. Install Python 3.11+
  pause
  exit /b 1
)

set "HOST=%~dp0ui_host.py"
if defined PYW (
  echo using PYW=%PYW%>> "%LOG%"
  start "" "%PYW%" "%HOST%" %*
) else (
  echo using PY=%PY%>> "%LOG%"
  start "" "%PY%" "%HOST%" %*
)
exit /b 0
