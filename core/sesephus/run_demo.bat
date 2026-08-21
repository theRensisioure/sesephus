@echo off
title Sesephus Suite Demo Runner
echo ====================================================================
echo             Sesephus Client-Server Alarm ^& Audio System            
echo ====================================================================
echo.

rem Check if zig is in PATH
where zig >nul 2>nul
if %errorlevel% neq 0 (
    echo [System] 'zig' was not found in your system PATH.
    echo [System] If winget just installed it, you may need to restart this terminal.
    echo [System] Checking standard winget installation directories...
    
    if exist "%USERPROFILE%\AppData\Local\Microsoft\WinGet\Links\zig.exe" (
        set ZIG_PATH="%USERPROFILE%\AppData\Local\Microsoft\WinGet\Links\zig.exe"
        echo [System] Found local Zig in WinGet Links.
    ) else (
        echo [System] Could not locate zig.exe automatically. Please ensure Zig is installed and on PATH.
        pause
        exit /b 1
    )
) else (
    set ZIG_PATH=zig
)

echo [System] Found Zig compiler. Compiling sesefus.exe (one binary, host+client roles)...
%ZIG_PATH% build
if %errorlevel% neq 0 (
    echo [System] Compilation failed. Please inspect build output.
    pause
    exit /b 1
)
echo [System] Compilation successful!
echo.
echo ====================================================================
echo   Need zig-out\bin\sesefus.exe  (not host.exe / client.exe)
echo ====================================================================
echo.
echo Launching the host role in a new window...
start cmd /k "zig-out\bin\sesefus.exe --role host"

echo.
echo Launching the client role in a new window...
start cmd /k "zig-out\bin\sesefus.exe --role client --name laptop-01"

echo.
echo ====================================================================
echo   DEMO INSTRUCTIONS:
echo   1. Host: vault password if prompted (hardcoded default still exists; issue #63).
echo   2. Client should register as laptop-01.
echo   3. On the host REPL:
echo      alarm schedule laptop-01 5 play_sound 1.5
echo   4. Circadia is not done — journal/rhythm REPL commands are stubs.
echo   5. Inspect vault later:
echo      zig-out\bin\sesefus.exe --role host --read-vault
echo ====================================================================
echo.
pause
