# ADB GUI Tool 用户指南

## 概述

ADB GUI Tool 是一款基于 PySide6 开发的 Windows 桌面应用程序，为 Android Debug Bridge (ADB) 操作提供图形化界面。支持设备管理、文件传输、应用管理、GPIO控制等功能。

**技术栈**: Python 3.8+, PySide6, ADB, Scrcpy

---

## 功能模块

### 1. 设备管理

- 自动检测已连接的Android设备
- 设备状态实时刷新
- 支持多设备切换
- 设备信息查看（型号、序列号、Android版本等）

### 2. 文件传输

| 功能 | 说明 |
|------|------|
| Push File | 将本地文件推送到设备 |
| Pull File | 从设备拉取文件到本地 |
| File Manager | 高级文件管理器，支持浏览、删除、移动等操作 |

### 3. 应用管理

| 功能 | 说明 |
|------|------|
| Install APK | 安装APK文件到设备 |
| Uninstall App | 卸载应用程序 |
| List Apps | 列出已安装的应用 |
| App Manager | 应用列表管理器，支持批量操作 |
| DeGoogle | 移除Google服务框架 |

### 4. 设备操作

| 功能 | 说明 |
|------|------|
| Screenshot | 截取设备屏幕 |
| Screen Record | 录制设备屏幕（30秒） |
| Reboot Device | 重启设备 |
| Reboot Recovery | 重启到Recovery模式 |
| Reboot Bootloader | 重启到Bootloader模式 |
| ADB Root & Remount | 获取root权限并重新挂载 |

### 5. GPIO Control (新增)

GPIO控制功能，支持Eywa和Middleware接口，用于控制GPIO电平输出和读取。

#### 5.1 配置选项

| 配置项 | 选项 | 说明 |
|--------|------|------|
| 接口类型 | eywa / middleware | 选择命令接口 |
| 命令前缀 | xbhfunc / xbhfunc_new | 选择命令前缀 |
| 平台类型 | SOC / MCU | 选择GPIO平台 |
| SOC型号 | rk35xx / rk33xx / rk31xx / rk30xx | 仅SOC时显示 |

#### 5.2 GPIO输入格式

**SOC平台**（Rockchip处理器）

格式：`GPIO{bank}_{port}{pin}`

| 示例 | 计算方式 | 编号 |
|------|---------|------|
| GPIO0_B0 | 0*32+8 | 8 |
| GPIO0_B1 | 0*32+9 | 9 |
| GPIO3_D2 | 3*32+26 | 122 |
| GPIO7_B4 | 7*32+12 | 236 |

**MCU平台**（PCA9555等）

格式：`P{letter}{pin}`

| 示例 | 编号 |
|------|------|
| PA0-PA7 | 0-7 |
| PB0-PB7 | 8-15 |
| PC0-PC7 | 16-23 |
| ... | ... |
| PZ0-PZ7 | 200-207 |

**通用格式**

纯数字：`8`, `236`, `394`

#### 5.3 电平控制命令

**Eywa接口**

```
拉高电平：xbhfunc_new XbhApi_setGpioOutputValue {number} 1
拉低电平：xbhfunc_new XbhApi_setGpioOutputValue {number} 0
读输出电平：xbhfunc_new XbhApi_getGpioOutputValue {number}
读输入电平：xbhfunc_new XbhApi_getGpioInputValue {number}
```

**Middleware接口**

```
拉高电平：xbhfunc_new setGpioOutputValue {number} true
拉低电平：xbhfunc_new setGpioOutputValue {number} false
读输出电平：xbhfunc_new getGpioOutputValue {number}
读输入电平：xbhfunc_new getGpioInputValue {number}
```

#### 5.4 GPIO计算器

支持GPIO名称与编号互算：

- 名称→编号：输入 `PB7`，输出 `15`
- 编号→名称：输入 `236`，输出 `GPIO7_B4`

### 6. 开发者选项

| 功能 | 说明 |
|------|------|
| 打开开发者选项 | 启用开发者模式 |
| 关闭开发者选项 | 禁用开发者模式 |
| 获取屏幕休眠时间 | 查看当前屏幕超时设置 |
| 设置屏幕休眠时间 | 修改屏幕超时时间 |
| 启动系统设置 | 打开Android设置界面 |
| ADB按键键盘 | 模拟按键输入 |

### 7. 快捷操作

| 功能 | 说明 |
|------|------|
| Clear Logcat | 清空日志缓冲区 |
| Toggle Airplane Mode | 切换飞行模式 |
| Quick Screenshot | 快速截图 |
| Screen Record | 录制屏幕30秒 |

### 8. 设备信息

| 功能 | 说明 |
|------|------|
| Battery Status | 查看电池状态 |
| Device Info | 查看设备详细信息 |
| Display Info | 查看屏幕分辨率 |
| CPU Info | 查看CPU信息 |
| Storage Info | 查看存储空间 |
| Memory Info | 查看内存信息 |
| Top Processes | 查看进程列表 |
| IP Address | 查看IP地址 |
| WiFi Info | 查看WiFi信息 |

---

## 架构设计

### 分层架构

```
├── Core Layer        # ADB/Scrcpy 核心管理器
├── Framework Layer   # 插件系统、事件总线、MVP模式
├── UI Layer          # 主题管理、对话框、控件
├── Utils Layer       # 配置管理、日志、工具函数
└── Plugins           # 可扩展插件模块
```

### 关键设计模式

**MVP (Model-View-Presenter)**
- Model: `framework/mvp/models.py` - 数据模型
- View: 实现 `MainViewInterface` 接口
- Presenter: 协调Model与View的交互

**插件系统**
- 接口：`framework/plugin/plugin_interface.py`
- 管理器：`framework/plugin/plugin_manager.py`
- API：`framework/plugin/plugin_api.py`

**事件总线**
- 位置：`framework/event/event_bus.py`
- 模式：发布/订阅，实现组件解耦

---

## 目录结构

```
├── adb_gui.py              # 主程序入口
├── core/                   # ADB/Scrcpy核心
│   ├── adb_manager.py
│   └── scrcpy_manager.py
├── framework/              # 框架层
│   ├── event/             # 事件系统
│   ├── mvp/               # MVP组件
│   └── plugin/            # 插件基础设施
├── ui/                     # UI组件
├── dialogs/                # 对话框窗口
│   ├── app_manager.py
│   ├── file_manager.py
│   ├── gpio_control.py    # GPIO控制
│   └── ...
├── plugins/                # 插件实现
├── utils/                  # 工具函数
├── config/                 # 配置文件
│   ├── config.json
│   └── buttons_cmd.json
├── scripts/                # 构建脚本
│   ├── build.py
│   ├── release.py
│   └── version.py
└── extensions/             # 外部工具
    ├── scrcpy-win64-*/
    └── jadx_decompiler/
```

---

## 配置文件

### config.json

主配置文件，包含：
- 应用设置（名称、版本、主题）
- ADB设置（刷新间隔）
- 扩展工具路径（adb.exe, scrcpy.exe）
- 插件设置

### buttons_cmd.json

自定义按钮配置，支持：
- 按钮分组
- 拖拽排序
- 自定义命令

---

## 构建与发布

### 版本管理

```bash
cd scripts

# 查看当前版本
python version.py --version

# 递增版本号
python version.py --bump patch   # 2.0.0 → 2.0.1
python version.py --bump minor   # 2.0.1 → 2.1.0
python version.py --bump major   # 2.1.0 → 3.0.0
```

### 打包EXE

```bash
cd scripts

# 目录模式（推荐，启动快）
python build.py

# 单文件模式（便于分发）
python build.py --onefile

# 显示控制台（调试用）
python build.py --console
```

### 发布

```bash
cd scripts

# 标准发布
python release.py

# 单文件发布
python release.py --onefile

# 自动递增版本后发布
python release.py --bump patch
```

构建输出：`scripts/dist/`
发布输出：`release/v{version}_{date}/`

---

## 使用指南

### 启动应用

**开发模式**
```bash
python adb_gui.py
```

**打包版本**
```
双击 dist\ADB_GUI_Tool_v{version}\ADB_GUI_Tool_v{version}.exe
```

### GPIO Control 使用步骤

1. 启动应用并选择设备
2. 点击 "🔧 Gpio Control" 按钮
3. 配置接口类型（eywa/middleware）
4. 配置命令前缀（xbhfunc/xbhfunc_new）
5. 选择平台类型（SOC/MCU）
6. 输入GPIO编号或名称
7. 点击 "Validate" 验证输入
8. 使用控制按钮执行操作

### 快捷键

- `Ctrl+Q`: 退出应用
- `F5`: 刷新设备列表

---

## 常见问题

### Q: 设备无法连接？

A: 检查以下项：
1. USB调试是否开启
2. ADB驱动是否安装
3. USB线缆是否正常
4. 运行 `adb devices` 确认设备可见

### Q: GPIO Control 按钮不显示？

A: 检查 `buttons_cmd.json` 是否包含 `gpio_control` 配置项。

### Q: 打包后exe无法运行？

A: 尝试以下方案：
1. 使用目录模式打包（非单文件）
2. 检查是否缺少依赖DLL
3. 以管理员权限运行

---

## 更新日志

### v2.3.1.10 (2026-05-13)

- 新增 GPIO Control 功能
- 支持 Eywa 和 Middleware 接口
- 支持 SOC/MCU 平台选择
- GPIO 名称与编号互算
- 支持 xbhfunc 和 xbhfunc_new 命令前缀

---

## 技术支持

- GitHub: [GUI-for-Android-Debug-Bridge-ADB-UI](https://github.com/your-repo)
- 问题反馈: 请提交Issue

---

*文档版本: 1.0*
*更新时间: 2026-05-13*
