@echo off
chcp 65001 >nul
cd /d "%~dp0"

title ADB GUI Tool
echo ========================================
echo     ADB GUI Tool
echo ========================================
echo.

echo [Info] Starting ADB GUI Tool...
C:\Python313\python.exe -X utf8 adb_gui.py

if errorlevel 1 (
    echo.
    echo [Error] Program exited with error
    pause
)
