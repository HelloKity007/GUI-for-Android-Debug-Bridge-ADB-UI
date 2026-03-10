@echo off
chcp 65001 >nul
cd /d "%~dp0"

:: 获取版本号
for /f "tokens=*" %%a in ('python -c "import sys; sys.path.insert(0, 'scripts'); from version import get_version_manager; vm=get_version_manager(); print(vm.full_version)" 2^>nul') do (
    set VERSION=%%a
)
if not defined VERSION set VERSION=Unknown

title ADB GUI Tool v%VERSION%
echo ========================================
echo     ADB GUI Tool v%VERSION%
echo ========================================
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请确保 Python 3.8+ 已安装并添加到 PATH
    pause
    exit /b 1
)

:: 启动程序
echo [信息] 正在启动 ADB GUI Tool v%VERSION%...
python adb_gui.py

if errorlevel 1 (
    echo.
    echo [错误] 程序异常退出，请检查日志文件
    pause
)
