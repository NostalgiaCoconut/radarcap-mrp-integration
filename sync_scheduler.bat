@echo off
setlocal EnableDelayedExpansion
title RadarCap SAP Auto-Sync Scheduler

echo.
echo ============================================================
echo   RadarCap SAP Auto-Sync - Windows Task Scheduler Setup
echo ============================================================
echo.

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM ── How often to sync (change this) ──────────────────────────
set SYNC_HOURS=1
REM ─────────────────────────────────────────────────────────────

set TASK_NAME=RadarCap_SAP_Sync
set PYTHON_EXE=python
set SYNC_SCRIPT=%SCRIPT_DIR%pipeline\sync.py
set LOG_FILE=%SCRIPT_DIR%sync_log.txt

echo [INFO] Setting up auto-sync every %SYNC_HOURS% hour(s)
echo [INFO] Script: %SYNC_SCRIPT%
echo [INFO] Log:    %LOG_FILE%
echo.

REM Remove existing task if present
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1

REM Create the sync wrapper script
echo @echo off > "%SCRIPT_DIR%run_sync.bat"
echo cd /d "%SCRIPT_DIR%" >> "%SCRIPT_DIR%run_sync.bat"
echo echo %%date%% %%time%% - Starting SAP sync >> "%LOG_FILE%" >> "%SCRIPT_DIR%run_sync.bat"
echo python pipeline\sync.py >> "%LOG_FILE%" 2^>^&1 >> "%SCRIPT_DIR%run_sync.bat"
echo echo %%date%% %%time%% - Sync complete >> "%LOG_FILE%" >> "%SCRIPT_DIR%run_sync.bat"

REM Register with Windows Task Scheduler
schtasks /create ^
  /tn "%TASK_NAME%" ^
  /tr "\"%SCRIPT_DIR%run_sync.bat\"" ^
  /sc hourly ^
  /mo %SYNC_HOURS% ^
  /st 00:00 ^
  /ru "%USERNAME%" ^
  /rl HIGHEST ^
  /f

if errorlevel 1 (
    echo [FAIL] Could not create scheduled task
    echo        Try running as Administrator
    pause & exit /b 1
)

echo.
echo [OK] Scheduled task created: %TASK_NAME%
echo [OK] Runs every %SYNC_HOURS% hour(s) automatically
echo.

REM Run an immediate sync now
echo Running first sync now...
echo.
python pipeline\sync.py
echo.

REM Show next run time
echo.
echo ============================================================
echo   AUTO-SYNC IS ACTIVE
echo ============================================================
echo.
echo   Schedule:  Every %SYNC_HOURS% hour(s)
echo   Task name: %TASK_NAME%
echo   Log file:  %LOG_FILE%
echo   Output:    %SCRIPT_DIR%radarcap_imports\
echo.
echo   To change frequency: edit SYNC_HOURS at top of this file
echo   To stop auto-sync:   run stop_sync.bat
echo   To view log:         open sync_log.txt
echo.
schtasks /query /tn "%TASK_NAME%" /fo list | findstr /i "next run"
echo.
pause
