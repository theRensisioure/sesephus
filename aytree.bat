@echo off
REM Sesefus suite — launch AyTree (Version Control / derivation map)
REM Usage: aytree.bat [open|map|tree|serve|status|help]
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" tools\aytree_launch.py %*
) else (
  python tools\aytree_launch.py %*
)
endlocal
