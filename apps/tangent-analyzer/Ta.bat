@echo off
setlocal
cd /d "%~dp0"
for %%I in ("%~dp0..\..\venv\Scripts\python.exe") do set "PY=%%~fI"
if not exist "%PY%" set "PY=python"
"%PY%" "%~dp0python\ta_heavy.py" %*
