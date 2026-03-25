@echo off
chcp 65001 > nul
echo ===================================
echo   ADB GUI Tool - 快速发布
echo ===================================
echo.

cd /d "%~dp0"

echo [信息] 当前目录: %CD%
echo.

echo [选择] 选择发布模式:
echo   1. 标准发布（目录模式 + ZIP）
echo   2. 单文件发布（单 EXE + ZIP）
echo   3. 仅打包现有构建到 release
echo   4. 递增 patch 版本号后发布
echo.

set /p choice="请输入选项 (1-4): "

if "%choice%"=="1" (
    echo.
    echo [执行] 标准发布...
    python release.py
) else if "%choice%"=="2" (
    echo.
    echo [执行] 单文件发布...
    python release.py --onefile
) else if "%choice%"=="3" (
    echo.
    echo [执行] 打包现有构建...
    python release.py --skip-build
) else if "%choice%"=="4" (
    echo.
    echo [执行] 递增版本号并发布...
    python release.py --bump patch
) else (
    echo.
    echo [错误] 无效选项！
    goto end
)

:end
echo.
echo 按任意键退出...
pause > nul
