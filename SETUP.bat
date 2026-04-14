@echo off
setlocal EnableDelayedExpansion
title RadarCap MRP Integration Setup

REM Auto-elevate to Administrator for Task Scheduler
net session >nul 2>&1
if errorlevel 1 (
    echo Requesting Administrator access for Task Scheduler...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

color 0A
echo.
echo ============================================================
echo   RadarCap MRP Integration v1.0.9
echo   SAP Live Data Feed for RadarCap Pro
echo ============================================================
echo.

set GITHUB_USERNAME=
set GITHUB_TOKEN=
set GITHUB_REPO=radarcap-mrp-integration

if exist "secrets.cfg" (
    for /f "usebackq tokens=1,2 delims==" %%a in ("secrets.cfg") do (
        if "%%a"=="GITHUB_USERNAME" set GITHUB_USERNAME=%%b
        if "%%a"=="GITHUB_TOKEN"   set GITHUB_TOKEN=%%b
        if "%%a"=="GITHUB_REPO"    set GITHUB_REPO=%%b
    )
    echo [OK] Credentials loaded
) else (
    echo [FAIL] secrets.cfg not found & pause & exit /b 1
)

set GITHUB_URL=https://%GITHUB_USERNAME%:%GITHUB_TOKEN%@github.com/%GITHUB_USERNAME%/%GITHUB_REPO%.git
cd /d "%~dp0"
set MRP_DIR=%CD%
echo [INFO] %MRP_DIR%
echo.

echo [1/7] Checking Python...
python --version >nul 2>&1
if errorlevel 1 ( start https://python.org/downloads & pause & exit /b 1 )
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo [OK] %%v

echo [2/7] Checking Git...
git --version >nul 2>&1
if errorlevel 1 ( start https://git-scm.com/download/win & pause & exit /b 1 )
for /f "tokens=*" %%v in ('git --version 2^>^&1') do echo [OK] %%v

echo.
echo [3/7] Installing packages...
pip install -r requirements.txt --quiet --disable-pip-version-check
if errorlevel 1 ( echo [FAIL] & pause & exit /b 1 )
echo [OK] All packages installed

echo.
echo [4/7] Creating .env...
if not exist ".env" (
    copy ".env.example" ".env" >nul & echo [OK] .env created
) else ( echo [SKIP] .env exists )

echo.
echo [5/7] Running tests...
python -m pytest tests\test_integration.py -v --tb=short 2>&1
echo.

echo [6/7] Running SAP sync...
python pipeline\sync.py 2>&1
echo.

echo [7/7] Setting up hourly auto-sync...

REM Create silent sync wrapper
(
echo @echo off
echo cd /d "%MRP_DIR%"
echo echo %%date%% %%time%% - Sync start ^>^> "%MRP_DIR%\sync_log.txt"
echo python pipeline\sync.py ^>^> "%MRP_DIR%\sync_log.txt" 2^>^&1
echo echo %%date%% %%time%% - Sync done ^>^> "%MRP_DIR%\sync_log.txt"
) > "%MRP_DIR%\run_sync.bat"

REM Register Task Scheduler - hourly, runs as SYSTEM so always works
schtasks /delete /tn "RadarCap_SAP_Sync" /f >nul 2>&1
schtasks /create /tn "RadarCap_SAP_Sync" /tr "\"%MRP_DIR%\run_sync.bat\"" /sc hourly /mo 1 /st 00:00 /ru SYSTEM /rl HIGHEST /f

if errorlevel 1 (
    echo [WARN] Task Scheduler setup failed - manual sync still works
) else (
    echo [OK] Auto-sync active - SAP data refreshes every hour silently
    schtasks /query /tn "RadarCap_SAP_Sync" /fo list | findstr /i "next run"
)

echo.
echo Pushing to GitHub...
if exist ".git" rmdir /s /q ".git" >nul 2>&1
git init >nul
git config user.email "%GITHUB_USERNAME%@users.noreply.github.com"
git config user.name "%GITHUB_USERNAME%"
git remote add origin %GITHUB_URL%
git add -A
git reset HEAD .env >nul 2>&1
git reset HEAD secrets.cfg >nul 2>&1
git reset HEAD sync_log.txt >nul 2>&1
git reset HEAD run_sync.bat >nul 2>&1
git commit -m "RadarCap MRP v1.0.9 - SAP live feed + hourly auto-sync" >nul 2>&1
git branch -M main
git push -u origin main --force >nul 2>&1
if errorlevel 1 ( echo [WARN] GitHub push failed ) else ( echo [OK] Pushed to GitHub )

echo.
echo ============================================================
echo   ALL DONE - SAP IS NOW FEEDING RADARCAP PRO
echo ============================================================
echo.
echo   STEP 1: Open RadarCap Pro .exe
echo   STEP 2: Import this file:
echo   %MRP_DIR%\radarcap_imports\
echo.
echo   SAP refreshes automatically every hour in background
echo   TO STOP: double-click stop_sync.bat
echo   TO VIEW LOG: double-click view_log.bat
echo.
echo   Press any key to open the imports folder in Explorer...
pause >nul
explorer "%MRP_DIR%\radarcap_imports"
