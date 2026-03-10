@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
echo ==========================================
echo  ADB GUI 依赖包安装脚本
echo ==========================================
echo.

:: 配置国内镜像源
set PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
set PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

echo [配置] 使用清华镜像源: %PIP_INDEX_URL%
echo.

:: 检查本地依赖目录
if not exist "..\deps" (
    echo [警告] 未找到 deps 目录，将使用在线安装
echo.
    set USE_LOCAL=0
) else (
    echo [1] 本地安装 - 从 deps 目录安装（推荐，速度快）
    echo [2] 在线安装 - 从 pip 远程下载（自动使用清华镜像）
    echo.
    set /p choice="请选择安装方式 [1-2，默认1]: "
    if "!choice!"=="" set choice=1
    if "!choice!"=="2" (
        set USE_LOCAL=0
    ) else (
        set USE_LOCAL=1
    )
)

echo.
if "%USE_LOCAL%"=="1" (
    echo [信息] 正在从本地 deps 目录安装依赖...
    pip install --no-index --find-links=..\deps -r ..\requirements.txt
    if %errorlevel% neq 0 (
        echo.
        echo [错误] 本地安装失败，请检查 deps 目录是否完整
        pause
        exit /b 1
    )
) else (
    echo [信息] 正在从 pip 远程下载安装（清华镜像源）...
    pip install -r ..\requirements.txt -i %PIP_INDEX_URL% --trusted-host %PIP_TRUSTED_HOST%
    if %errorlevel% neq 0 (
        echo.
        echo [错误] 在线安装失败，请检查网络连接
        pause
        exit /b 1
    )
)

echo.
echo [信息] 安装 QFluentWidgets（需要从GitHub下载）...
pip install git+https://github.com/zhiyiYo/PyQt-Fluent-Widgets.git

echo.
echo [完成] 依赖安装结束
echo.
pause
