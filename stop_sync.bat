@echo off
echo Stopping RadarCap SAP Auto-Sync...
schtasks /delete /tn "RadarCap_SAP_Sync" /f
if errorlevel 1 (
    echo [FAIL] Could not stop task
) else (
    echo [OK] Auto-sync stopped
)
pause
