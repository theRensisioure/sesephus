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

echo [System] Found Zig compiler. Compiling Sesephus host and client...
%ZIG_PATH% build
if %errorlevel% neq 0 (
    echo [System] Compilation failed. Please inspect build output.
    pause
    exit /b 1
)
echo [System] Compilation successful!
echo.
echo ====================================================================
echo   Double check that both host.exe and client.exe are in zig-out\bin
echo ====================================================================
echo.
echo Launching the Sesephus Host Daemon in a new window...
start cmd /k "zig-out\bin\host.exe"

echo.
echo Launching the Sesephus Client Device in a new window...
start cmd /k "zig-out\bin\client.exe --name laptop-01"

echo.
echo ====================================================================
echo   DEMO INSTRUCTIONS:
echo   1. In the Host window, enter a password (e.g. 'admin123') to create/load the vault.
echo   2. The client will automatically connect and register with the host.
echo   3. In the Host window, schedule an alarm using the command:
echo      alarm laptop-01 5 record_audio 5.0
echo   4. In 5 seconds, watch the client receive the alarm, record 5 seconds
echo      of WAV audio (native WinMM or synthesized fallback), and upload it.
echo   5. The host will ingest the WAV, encrypt it, and append it to the vault database.
echo   6. To inspect the encrypted vault database contents later, close the host and run:
echo      zig-out\bin\host.exe --read-vault
echo ====================================================================
echo.
pause
