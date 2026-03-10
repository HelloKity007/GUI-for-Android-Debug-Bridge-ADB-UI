@echo off
chcp 65001 >nul
title ADB GUI Tool - 打包构建
cd /d "%~dp0"

:: 显示菜单
:menu
cls
echo ========================================
echo     ADB GUI Tool - 打包构建工具
echo ========================================
echo.

:: 显示当前版本
python -c "from version import get_version_manager; vm=get_version_manager(); print('当前版本: ' + vm.full_version)" 2>nul
if errorlevel 1 (
    echo [警告] 无法获取版本信息
)
echo.
echo  [1] 默认打包（目录模式，推荐）
echo  [2] 单文件打包（独立exe，启动较慢）
echo  [3] 调试模式打包（显示控制台）
echo  [4] 递增版本号并自动打包
echo  [5] 仅清理构建文件
echo  [6] 查看版本信息
echo  [0] 退出
echo.
echo ========================================
set /p choice="请选择操作 [0-6]: "

if "%choice%"=="1" goto build_dir
if "%choice%"=="2" goto build_onefile
if "%choice%"=="3" goto build_debug
if "%choice%"=="4" goto bump_and_build
if "%choice%"=="5" goto clean_only
if "%choice%"=="6" goto show_version
if "%choice%"=="0" goto exit
goto menu

:build_dir
echo.
echo [信息] 开始打包（目录模式）...
python build.py
goto done

:build_onefile
echo.
echo [信息] 开始打包（单文件模式）...
python build.py --onefile
goto done

:build_debug
echo.
echo [信息] 开始打包（调试模式，显示控制台）...
python build.py --console
goto done

:bump_and_build
echo.
echo 递增版本号类型（递增后自动打包）:
echo  [1] Major (主版本) - 如 2.3.0 -^> 3.0.0
echo  [2] Minor (次版本) - 如 2.3.0 -^> 2.4.0
echo  [3] Patch (补丁)   - 如 2.3.0 -^> 2.3.1
echo  [0] 返回
echo.
set /p bump_type="请选择 [0-3]: "

if "%bump_type%"=="1" (
    python build.py --bump major
    goto done
)
if "%bump_type%"=="2" (
    python build.py --bump minor
    goto done
)
if "%bump_type%"=="3" (
    python build.py --bump patch
    goto done
)
if "%bump_type%"=="0" goto menu
goto bump_and_build

:clean_only
echo.
echo [信息] 清理构建文件...
python build.py --clean
goto done

:show_version
echo.
python build.py --version
goto done

:done
echo.
echo 按任意键返回菜单...
pause >nul
goto menu

:exit
echo.
echo 感谢使用，再见！
timeout /t 1 >nul
