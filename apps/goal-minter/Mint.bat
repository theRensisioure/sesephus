@echo off
setlocal
cd /d "%~dp0"
for %%I in ("%~dp0..\..\venv\Scripts\python.exe") do set "SESEFUS_MINT_PYTHON=%%~fI"
if not exist "%SESEFUS_MINT_PYTHON%" for %%I in ("%~dp0..\..\.venv\Scripts\python.exe") do set "SESEFUS_MINT_PYTHON=%%~fI"
if not exist "%SESEFUS_MINT_PYTHON%" set "SESEFUS_MINT_PYTHON=python"
if "%~1"=="" (
  for %%I in ("%~dp0..\..\venv\Scripts\pythonw.exe") do set "UI_PY=%%~fI"
  if not exist "%UI_PY%" for %%I in ("%~dp0..\..\.venv\Scripts\pythonw.exe") do set "UI_PY=%%~fI"
  if not exist "%UI_PY%" set "UI_PY=pythonw"
  start "" "%UI_PY%" "%~dp0python\ui.py"
  goto :eof
)
"%SESEFUS_MINT_PYTHON%" "%~dp0python\cli.py" %*
