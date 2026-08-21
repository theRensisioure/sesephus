@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "INSTALL_ROOT=%CD%"
set "MODE=update"
set "HAD_REMNANTS=0"
set "STEP=0"
set "TOTAL=6"

echo ============================================================
echo   SESEFUS 0.9.3 alpha — installer
echo ============================================================
echo   Folder: %INSTALL_ROOT%
echo.
echo   Re-run safe: this script expects you may have run it
echo   before. It will show remnants, then let you choose
echo   update vs clean reinstall before touching anything.
echo ============================================================
echo.
echo Press any key to start the check...
pause >nul
echo.

rem --- Python on PATH -------------------------------------------------
where python >nul 2>nul
if errorlevel 1 (
    echo [!] Python not found on PATH.
    echo     Install Python 3.10+ from https://www.python.org/downloads/
    echo     and check "Add python.exe to PATH", then re-run this.
    goto :end_fail
)
for /f "delims=" %%V in ('python -c "import sys; print(sys.version.split()[0])" 2^>nul') do set "PY_VER=%%V"
if not defined PY_VER set "PY_VER=unknown"
echo [ok] Python: %PY_VER%
echo.

rem --- Remnant scan (re-run / half-finished installs) -----------------
echo --- Remnant scan (what is already here) ---
set "HAS_VENV=0"
set "HAS_DOTVENV=0"
set "HAS_PIP=0"
set "HAS_CFG=0"
set "HAS_ATLAS=0"
set "HAS_PYC=0"
set "VENV_BROKEN=0"

if exist "venv\Scripts\python.exe" (
    set "HAS_VENV=1"
    echo   [found] venv\               ^<- primary install env
) else if exist "venv\" (
    set "HAS_VENV=1"
    set "VENV_BROKEN=1"
    echo   [found] venv\               ^<- BROKEN ^(no Scripts\python.exe^)
) else (
    echo   [   - ] venv\               not present
)

if exist ".venv\" (
    set "HAS_DOTVENV=1"
    set "HAD_REMNANTS=1"
    echo   [found] .venv\              ^<- alternate/old env ^(not used by voice.bat^)
) else (
    echo   [   - ] .venv\              not present
)

if exist "venv\Scripts\pip.exe" (
    set "HAS_PIP=1"
) else if "!HAS_VENV!"=="1" (
    set "VENV_BROKEN=1"
    echo   [warn ] venv exists but pip is missing
)

if exist "sesefus.config.json" (
    set "HAS_CFG=1"
    set "HAD_REMNANTS=1"
    echo   [found] sesefus.config.json ^<- kept on re-run ^(not overwritten^)
) else (
    echo   [   - ] sesefus.config.json not present
)

if exist "tools\atlas\sesefus-atlas.html" (
    set "HAS_ATLAS=1"
    echo   [found] tools\atlas\sesefus-atlas.html
) else (
    echo   [   - ] tools\atlas\sesefus-atlas.html
)

rem Count __pycache__ under repo root (shallow: common leftover dirs)
for /d %%D in (tools dashboard shredder core utils audio simulator) do (
    if exist "%%D\__pycache__\" set "HAS_PYC=1"
)
if exist "__pycache__\" set "HAS_PYC=1"
if "!HAS_PYC!"=="1" (
    set "HAD_REMNANTS=1"
    echo   [found] __pycache__\ dirs   ^<- bytecode leftovers from prior runs
) else (
    echo   [   - ] __pycache__\        none spotted in usual places
)

if exist "aurgio\" (
    set "HAD_REMNANTS=1"
    echo   [found] aurgio\             ^<- YOUR voice data ^(never deleted by install^)
)

if "!HAS_VENV!"=="1" set "HAD_REMNANTS=1"
if "!VENV_BROKEN!"=="1" set "HAD_REMNANTS=1"

echo.
if "!HAD_REMNANTS!"=="0" (
    echo First-time look: no install remnants detected.
    set "MODE=fresh"
    echo Mode: fresh install.
    echo.
    echo Press any key to continue...
    pause >nul
    goto :run_steps
)

echo Prior install material is present. Choose how to proceed:
echo.
echo   [1] Update / repair  ^(default^)
echo       Keep venv, reinstall packages into it, refresh atlas + guards.
echo       Keeps sesefus.config.json and aurgio\ data.
echo.
echo   [2] Clean reinstall
echo       Delete venv\ and leftover .venv\, wipe common __pycache__.
echo       Then build a fresh venv + packages.
echo       Still keeps sesefus.config.json and aurgio\ ^(your data^).
echo.
echo   [3] Exit without changes
echo.
set "CHOICE=1"
set /p "CHOICE=Enter 1, 2, or 3 [default 1]: " || set "CHOICE=1"
rem strip spaces
set "CHOICE=!CHOICE: =!"
if "!CHOICE!"=="" set "CHOICE=1"
if /i "!CHOICE!"=="q" set "CHOICE=3"
if "!CHOICE!"=="3" (
    echo.
    echo Aborted. Nothing changed.
    goto :end_ok
)
if "!CHOICE!"=="2" (
    set "MODE=clean"
) else if "!CHOICE!"=="1" (
    set "MODE=update"
    if "!VENV_BROKEN!"=="1" (
        echo.
        echo [!] venv looks broken — switching to clean reinstall.
        set "MODE=clean"
    )
) else (
    echo.
    echo Unrecognized choice "!CHOICE!" — using update/repair.
    set "MODE=update"
)

echo.
if "!MODE!"=="clean" (
    echo You chose: CLEAN reinstall.
    echo This will remove: venv\  .venv\  ^(if present^)  common __pycache__
    echo This will KEEP:   sesefus.config.json  aurgio\  git history
    echo.
    set "CONFIRM=n"
    set /p "CONFIRM=Type YES to wipe those install remnants: "
    if /i not "!CONFIRM!"=="YES" (
        echo.
        echo Clean wipe cancelled. Falling back to update/repair.
        set "MODE=update"
    )
) else (
    echo You chose: UPDATE / repair.
)

echo.
echo Press any key to begin "!MODE!" install...
pause >nul
echo.

if "!MODE!"=="clean" goto :do_clean
goto :run_steps

:do_clean
echo --- Cleaning install remnants ---
if exist "venv\" (
    echo   removing venv\ ...
    rmdir /s /q "venv" 2>nul
    if exist "venv\" (
        echo [!] Could not fully remove venv\ — close any program using it
        echo     ^(terminals, IDEs, voice.bat^) and re-run install.bat.
        goto :end_fail
    )
    echo   removed venv\
)
if exist ".venv\" (
    echo   removing leftover .venv\ ...
    rmdir /s /q ".venv" 2>nul
    if exist ".venv\" (
        echo [!] Could not fully remove .venv\ — close anything using it.
        goto :end_fail
    )
    echo   removed .venv\
)
for /d %%D in (tools dashboard shredder core utils audio simulator) do (
    if exist "%%D\__pycache__\" (
        rmdir /s /q "%%D\__pycache__" 2>nul
        echo   removed %%D\__pycache__
    )
)
if exist "__pycache__\" (
    rmdir /s /q "__pycache__" 2>nul
    echo   removed __pycache__
)
echo   clean pass done. ^(config + aurgio left alone^)
echo.
echo Press any key for step 1...
pause >nul
echo.

:run_steps
rem ========== 1/6 venv ==========
call :step "create / verify venv"
if not exist "venv\Scripts\python.exe" (
    echo   creating venv with: python -m venv venv
    python -m venv venv
    if errorlevel 1 (
        echo [!] venv creation failed.
        goto :end_fail
    )
) else (
    echo   venv already usable — keeping it.
)
if not exist "venv\Scripts\python.exe" (
    echo [!] venv\Scripts\python.exe missing after create.
    goto :end_fail
)
echo   ok: venv\Scripts\python.exe
call :pause_next

rem ========== 2/6 deps ==========
call :step "install Python dependencies"
if not exist "requirements-dev.txt" (
    echo [!] requirements-dev.txt missing in %INSTALL_ROOT%
    goto :end_fail
)
echo   pip install -r requirements-dev.txt
venv\Scripts\python -m pip install --upgrade pip >nul 2>nul
venv\Scripts\python -m pip install -r requirements-dev.txt
if errorlevel 1 (
    echo [!] dependency install failed.
    goto :end_fail
)
echo   ok: requirements-dev.txt
call :pause_next

rem ========== 3/6 whisper ==========
call :step "install Whisper ^(speech-to-text, often ~1-2 GB first time^)"
echo   This can take a while on a re-run if packages are already cached,
echo   or a long download on a true first install.
echo.
echo Press any key to start the Whisper install...
pause >nul
venv\Scripts\python -m pip install openai-whisper
if errorlevel 1 (
    echo [!] Whisper install failed. You can re-run install.bat later;
    echo     voice.bat --say still works with --backend heuristic without it.
    echo     Continuing with remaining steps...
) else (
    echo   ok: openai-whisper
)
call :pause_next

rem ========== 4/6 config ==========
call :step "starter config ^(sesefus.config.json^)"
if exist "sesefus.config.json" (
    echo   config already exists — leaving your settings alone.
    echo   path: %INSTALL_ROOT%\sesefus.config.json
) else (
    venv\Scripts\python -c "import sys; sys.path.insert(0,'tools'); from sesefus_config import write_default_config; print('  wrote', write_default_config())"
    if errorlevel 1 (
        echo [!] could not write config.
        goto :end_fail
    )
)
call :pause_next

rem ========== 5/6 atlas ==========
call :step "build repo atlas"
if exist "tools\atlas\build.py" (
    venv\Scripts\python tools\atlas\build.py
    if errorlevel 1 (
        echo [!] atlas build failed ^(non-fatal for voice journal^).
    ) else (
        echo   ok: tools\atlas\sesefus-atlas.html
    )
) else (
    echo   tools\atlas\build.py not found — skipping.
)
call :pause_next

rem ========== 6/6 guards ==========
call :step "arm git guards"
git rev-parse --is-inside-work-tree >nul 2>nul
if errorlevel 1 (
    echo   not a git clone; skipping guard arming.
) else (
    if exist ".githooks\" (
        git config core.hooksPath .githooks
        echo   guards armed: vault data + secrets blocked on commit.
    ) else (
        echo   .githooks\ missing — skipping.
    )
)

echo.
echo ============================================================
echo   Done. Mode was: !MODE!
echo ============================================================
echo   Next: double-click voice.bat and speak.
echo   Atlas: tools\atlas\sesefus-atlas.html
echo.
echo   Optional smarter scoring:
echo     install Ollama, then:  ollama pull qwen2.5:7b-instruct
echo     set "backend": "ollama" in sesefus.config.json
echo.
echo   Re-ran install a few times already?
echo     Run this again and pick [2] Clean reinstall to drop stale
echo     venv / .venv / __pycache__. Your aurgio\ memos stay put.
echo ============================================================
goto :end_ok

:step
set /a STEP+=1
echo.
echo --- [!STEP!/%TOTAL%] %~1 ---
exit /b 0

:pause_next
echo.
if !STEP! geq %TOTAL% exit /b 0
echo Press any key for next step...
pause >nul
exit /b 0

:end_fail
echo.
echo Install stopped with errors. Window stays open so you can read them.
echo Fix the issue above, then re-run install.bat ^(update or clean^).
pause
endlocal
exit /b 1

:end_ok
echo.
echo Press any key to close this window...
pause >nul
endlocal
exit /b 0
