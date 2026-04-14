@echo off
cd /d "%~dp0"
if exist "sync_log.txt" (
    type sync_log.txt | more
) else (
    echo No log file yet - run sync_scheduler.bat first
)
pause
