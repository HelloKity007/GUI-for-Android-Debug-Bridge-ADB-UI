# ADB调试工具 产品需求文档 (PRD)

**文档版本**: 2.2  
**日期**: 2026-02-13  
**状态**: 正式版

---

### 变更历史

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| 2.2 | 2026-02-13 | 新增Settings快捷键：开发者选项、屏幕休眠时间、系统设置；新增ADB Keycode Keyboard虚拟按键键盘（30+按键） |
| 2.1 | 2026-02-13 | 补充遗漏功能：Quick Actions、文件管理增强、测试增强、集群控制增强、主题系统、Scrcpy高级选项等 |
| 2.0 | 2026-02-13 | 新增AI功能需求、MCP协议、性能分析工具、内核调试工具、快捷按键配置系统 |
| 1.0 | 初始版本 | 基础ADB GUI功能需求 |

---

## 1. 产品概述

### 1.1 产品定位
ADB Tool for Windows 是一款面向Android开发工程师的专业调试工具，集成设备管理、应用管理、日志分析、性能监控、自动化测试等核心能力，并通过AI功能实现智能化调试与分析。

### 1.2 目标用户
| 用户类型 | 使用场景 | 核心需求 |
|---------|---------|---------|
| Android开发工程师 | 日常开发调试 | 快速安装、日志查看、性能分析 |
| 测试工程师 | 自动化测试 | 脚本执行、集群控制、报告生成 |
| 技术支持人员 | 问题排查 | 日志收集、崩溃分析、远程协助 |
| 嵌入式系统工程师 | Kernel调试 | 内核追踪、驱动调试、性能优化 |

### 1.3 技术栈
- **语言**: Python 3.8+
- **UI框架**: PyQt6
- **架构模式**: MVP + 插件化
- **外部依赖**: ADB Platform Tools, Scrcpy (可选)

---

## 2. 现有功能清单

### 2.1 设备管理模块

| 功能 | 描述 | 状态 |
|------|------|------|
| 自动发现设备 | 扫描并列出已连接的Android设备 | ✅ 已实现 |
| 设备信息查看 | 显示设备型号、Android版本、序列号等 | ✅ 已实现 |
| 静默刷新 | 每5秒自动刷新设备列表，无日志干扰 | ✅ 已实现 |
| 设备选择切换 | 多设备环境下选择目标设备 | ✅ 已实现 |
| ADB路径配置 | 首次启动引导配置ADB路径 | ✅ 已实现 |
| ADB连接测试 | 测试ADB是否正常工作 | ✅ 已实现 |
| 设备详细信息弹窗 | 弹窗展示完整设备属性 | ✅ 已实现 |
| 设备型号解析 | 自动解析设备model和product | ✅ 已实现 |
| 制造商信息 | 获取设备制造商信息 | ✅ 已实现 |
| 设备状态显示 | 实时显示设备连接状态 | ✅ 已实现 |

### 2.2 文件传输模块

| 功能 | 描述 | 状态 |
|------|------|------|
| Push文件 | 推送本地文件到Android设备 | ✅ 已实现 |
| Pull文件 | 从Android设备拉取文件到本地 | ✅ 已实现 |
| 文件浏览器 | 可视化浏览设备文件系统 | ✅ 已实现 |
| 拖拽传输 | 支持拖拽文件进行传输 | ✅ 已实现 |
| 路径空格处理 | 自动处理路径中的空格字符 | ✅ 已实现 |
| 目标路径输入 | 手动输入设备目标路径 | ✅ 已实现 |
| 保存对话框 | 选择本地保存位置 | ✅ 已实现 |
| 异步传输 | 后台线程传输不阻塞UI | ✅ 已实现 |
| 传输状态反馈 | 实时显示传输进度和结果 | ✅ 已实现 |

### 2.3 应用管理模块

| 功能 | 描述 | 状态 |
|------|------|------|
| APK安装 | 安装APK文件到设备 | ✅ 已实现 |
| APK卸载 | 卸载已安装应用 | ✅ 已实现 |
| 应用列表 | 列出已安装应用（支持过滤） | ✅ 已实现 |
| 应用启用/禁用 | 启用或禁用应用 | ✅ 已实现 |
| 应用详情查看 | 显示应用包名、版本、权限等信息 | ✅ 已实现 |
| 清除应用数据 | 清除应用数据和缓存 | ✅ 已实现 |
| 当前用户卸载 | 使用--user 0参数卸载系统应用 | ✅ 已实现 |
| 安装超时设置 | 支持自定义安装超时时间 | ✅ 已实现 |
| 安装结果反馈 | 弹窗显示安装成功/失败 | ✅ 已实现 |
| APK文件夹快捷打开 | 快速打开apks文件夹 | ✅ 已实现 |

### 2.4 设备操作模块

| 功能 | 描述 | 状态 |
|------|------|------|
| 屏幕截图 | 截取设备屏幕并保存到本地 | ✅ 已实现 |
| 屏幕录制 | 录制设备屏幕视频 | ✅ 已实现 |
| 屏幕镜像(Scrcpy) | 通过Scrcpy实时显示设备屏幕 | ✅ 已实现 |
| Scrcpy高级选项 | 自定义分辨率、码率、录制等 | ✅ 已实现 |
| 多模式重启 | 支持普通重启、Recovery、Bootloader | ✅ 已实现 |
| 输入模拟 | 模拟点击、滑动、按键输入 | ✅ 已实现 |

#### 2.4.1 Scrcpy高级选项明细

| 选项 | 描述 | 默认值 |
|------|------|--------|
| 分辨率限制 | 限制镜像分辨率（如1024） | 无限制 |
| 码率设置 | 视频码率（如4M） | 8M |
| 帧率限制 | 最大帧率 | 60fps |
| 录制屏幕 | 镜像同时录制视频文件 | 关闭 |
| 录制格式 | MP4/MKV格式选择 | MP4 |
| 无声音模式 | 禁用音频转发 | 关闭 |
| 保持屏幕唤醒 | 防止设备休眠 | 关闭 |
| 显示触摸 | 显示触摸操作点 | 关闭 |
| 禁用屏幕保真 | 关闭设备屏幕显示 | 关闭 |
| 边框无标题 | 隐藏窗口标题栏 | 关闭 |
| 全屏模式 | 全屏显示镜像 | 关闭 |

### 2.5 Shell命令模块

| 功能 | 描述 | 状态 |
|------|------|------|
| 交互式Shell | 提供Linux风格的Shell终端 | ✅ 已实现 |
| Linux语法支持 | 支持标准Linux命令语法 | ✅ 已实现 |
| 自动前缀处理 | 自动剥离/添加adb shell前缀 | ✅ 已实现 |
| 命令历史 | 记录执行过的命令 | ✅ 已实现 |
| 快捷命令 | 预定义常用命令快捷方式 | ✅ 已实现 |
| 多行命令输入 | 支持输入多行命令脚本 | ✅ 已实现 |
| 命令帮助提示 | 显示Linux命令使用说明 | ✅ 已实现 |
| 异步执行 | 后台线程执行不阻塞UI | ✅ 已实现 |
| 执行结果展示 | 格式化显示命令输出和错误 | ✅ 已实现 |

### 2.6 Logcat日志模块

| 功能 | 描述 | 状态 |
|------|------|------|
| 实时日志流 | 实时显示设备日志输出 | ✅ 已实现 |
| 日志启停控制 | 开始/暂停日志收集 | ✅ 已实现 |
| 清空日志缓冲 | 清除logcat缓冲区 | ✅ 已实现 |
| 日志过滤 | 按级别、标签、关键词过滤 | ✅ 已实现 |
| 日志导出 | 导出日志到文件 | ✅ 已实现 |
| 错误高亮 | ERROR/FATAL级别日志高亮显示 | ✅ 已实现 |
| 级别下拉过滤 | Verbose/Debug/Info/Warning/Error/Fatal | ✅ 已实现 |
| 关键词搜索 | 实时过滤匹配日志内容 | ✅ 已实现 |
| 自动滚动 | 新日志自动滚动到底部 | ✅ 已实现 |
| 日志存储 | 内存中存储所有日志用于过滤 | ✅ 已实现 |
| 时间戳导出 | 导出文件带时间戳命名 | ✅ 已实现 |

### 2.7 DeGoogle工具模块

| 功能 | 描述 | 状态 |
|------|------|------|
| 安全分级卸载 | 按风险等级分类卸载Google服务 | ✅ 已实现 |
| 安全分级禁用 | 按风险等级禁用Google服务 | ✅ 已实现 |
| Undo恢复 | 恢复已卸载/禁用的Google服务 | ✅ 已实现 |
| 状态持久化 | 记录DeGoogle操作状态 | ✅ 已实现 |
| 应用搜索选择 | 搜索并选择要恢复的应用 | ✅ 已实现 |
| 当前用户卸载 | 使用--user 0参数卸载 | ✅ 已实现 |
| 批量操作进度 | 显示批量操作进度 | ✅ 已实现 |

**DeGoogle风险分级**：
- **高风险**：Google Play Services、Play Store等核心服务
- **中风险**：Gmail、Maps、YouTube等Google应用
- **低风险**：Google框架组件、辅助服务

### 2.8 集群控制模块

| 功能 | 描述 | 状态 |
|------|------|------|
| 多设备管理 | 同时管理多台Android设备 | ✅ 已实现 |
| 批量命令执行 | 在多台设备上同步执行命令 | ✅ 已实现 |
| 设备分组 | 按项目/用途分组管理设备 | ✅ 已实现 |
| 集群状态监控 | 实时监控所有设备状态 | ✅ 已实现 |
| 设备分组持久化 | 分组配置保存到JSON文件 | ✅ 已实现 |
| 全选/全不选 | 快速选择所有设备 | ✅ 已实现 |
| 命令模板 | 预置常用命令模板选择 | ✅ 已实现 |
| 实时日志输出 | 控制台实时显示执行结果 | ✅ 已实现 |

### 2.9 自动化测试模块

| 功能 | 描述 | 状态 |
|------|------|------|
| 测试脚本管理 | 创建、编辑、管理测试脚本 | ✅ 已实现 |
| 脚本录制 | 录制用户操作生成测试脚本 | ✅ 已实现 |
| 脚本执行 | 执行自动化测试脚本 | ✅ 已实现 |
| 测试报告 | 生成测试执行报告 | ✅ 已实现 |
| Monkey测试 | 集成Monkey压力测试 | ✅ 已实现 |

### 2.10 反编译模块

| 功能 | 描述 | 状态 |
|------|------|------|
| APK反编译 | 集成JADX反编译工具 | ✅ 已实现 |
| 源码查看 | 查看反编译后的Java源码 | ✅ 已实现 |
| 资源查看 | 查看APK资源文件 | ✅ 已实现 |
| 缓存管理 | 反编译结果缓存 | ✅ 已实现 |
| GUI模式启动 | 启动JADX-GUI界面 | ✅ 已实现 |
| 命令行反编译 | 后台命令行反编译 | ✅ 已实现 |
| 进度显示 | 反编译进度实时反馈 | ✅ 已实现 |
| 从设备拉取APK | 直接从设备拉取APK反编译 | ✅ 已实现 |
| APK缓存目录 | 本地APK缓存管理 | ✅ 已实现 |
| 反编译输出目录 | 自定义反编译输出路径 | ✅ 已实现 |

### 2.11 Quick Actions模块

| 功能 | 描述 | 状态 |
|------|------|------|
| 电池状态快查 | 快速查看电池详细信息 | ✅ 已实现 |
| 设备信息快查 | 快速查看设备属性（型号、品牌、版本等） | ✅ 已实现 |
| 显示屏信息 | 查看屏幕分辨率、DPI、刷新率 | ✅ 已实现 |
| 存储信息快查 | 快速查看存储使用情况 | ✅ 已实现 |
| CPU信息快查 | 查看CPU核心数、频率信息 | ✅ 已实现 |
| 内存信息快查 | 查看内存使用情况 | ✅ 已实现 |
| Top进程列表 | 查看CPU占用最高的进程 | ✅ 已实现 |
| IP地址查看 | 查看网络IP地址 | ✅ 已实现 |
| WiFi信息查看 | 查看WiFi连接状态和SSID | ✅ 已实现 |
| 清空Logcat | 一键清空日志缓冲区 | ✅ 已实现 |
| 飞行模式切换 | 快速开关飞行模式 | ✅ 已实现 |
| 快速截图 | 一键截图并保存 | ✅ 已实现 |
| 快速录屏30秒 | 一键录制30秒屏幕视频 | ✅ 已实现 |
| 打开开发者选项 | 执行settings put global development_settings_enabled 1 | ✅ 已实现 |
| 关闭开发者选项 | 执行settings put global development_settings_enabled 0 | ✅ 已实现 |
| 获取屏幕休眠时间 | 执行settings get system screen_off_timeout | ✅ 已实现 |
| 设置屏幕休眠时间 | 执行settings put system screen_off_timeout (ms) | ✅ 已实现 |
| 启动系统设置 | 执行am start -a android.settings.SETTINGS | ✅ 已实现 |
| ADB按键键盘 | 虚拟键盘发送按键事件(keyevent) | ✅ 已实现 |

### 2.12 UI特性模块

| 功能 | 描述 | 状态 |
|------|------|------|
| 暗色模式 | 支持亮色/暗色主题切换 | ✅ 已实现 |
| 实时状态显示 | 显示连接状态、设备信息 | ✅ 已实现 |
| 日志时间戳 | 日志输出带时间戳 | ✅ 已实现 |
| 多标签页界面 | 功能模块分标签展示 | ✅ 已实现 |
| 响应式布局 | 自适应窗口大小 | ✅ 已实现 |

### 2.12.1 主题样式系统

| 功能 | 描述 | 状态 |
|------|------|------|
| 亮色主题 | LIGHT_COLORS配色方案 | ✅ 已实现 |
| 暗色主题 | DARK_COLORS配色方案 | ✅ 已实现 |
| 全局样式表 | 30+组件的完整样式定义 | ✅ 已实现 |
| 主题切换 | 运行时动态切换主题 | ✅ 已实现 |

**支持的样式组件**：
- QMainWindow/QDialog - 主窗口背景
- QGroupBox - 分组框边框和标题
- QPushButton - 按钮常规/悬停/按下/强调状态
- QLineEdit/QTextEdit - 输入框焦点边框
- QComboBox - 下拉框展开箭头
- QScrollBar - 滚动条圆角样式
- QTabWidget/QTabBar - 标签页选中/未选中状态
- QCheckBox - 复选框选中样式
- QLabel - 标签颜色
- QListWidget/QTreeWidget - 列表选中高亮
- QProgressBar - 进度条样式

### 2.13 文件管理增强模块

| 功能 | 描述 | 状态 |
|------|------|------|
| 文件浏览器 | 可视化浏览设备文件系统 | ✅ 已实现 |
| 剪贴板操作 | 复制/粘贴/剪切文件 | ✅ 已实现 |
| 文件重命名 | 重命名设备上的文件 | ✅ 已实现 |
| 回收站机制 | 删除文件先移至回收站，支持恢复 | ✅ 已实现 |
| 收藏夹功能 | 常用路径收藏，快速导航 | ✅ 已实现 |
| 存储信息显示 | 显示设备存储空间使用情况 | ✅ 已实现 |
| 导航历史 | 前进/后退/上级目录导航 | ✅ 已实现 |
| Root路径访问 | 直接导航到根目录 | ✅ 已实现 |
| 拖拽传输 | 支持拖拽文件进行传输 | ✅ 已实现 |

### 2.14 自动化测试增强模块

| 功能 | 描述 | 状态 |
|------|------|------|
| 批量安装APK | 选择多个APK或文件夹批量安装 | ✅ 已实现 |
| 批量卸载应用 | 批量输入包名卸载多个应用 | ✅ 已实现 |
| 第三方应用备份 | 备份所有第三方应用APK到本地 | ✅ 已实现 |
| FPS/Jankiness测试 | 指定包名测试帧率和卡顿 | ✅ 已实现 |
| CPU/内存实时监控 | 持续采样监控CPU和内存使用 | ✅ 已实现 |
| 获取当前Activity | 获取前台应用Activity名称 | ✅ 已实现 |
| 拉取当前APK | 直接拉取前台应用的APK | ✅ 已实现 |
| 应用权限查看 | 查看指定应用的权限列表 | ✅ 已实现 |
| 批量截图 | 按间隔连续截取多张图片 | ✅ 已实现 |
| 屏幕录制 | 录制设备屏幕视频 | ✅ 已实现 |
| 日志收集导出 | 收集并导出日志文件 | ✅ 已实现 |

### 2.15 集群控制增强模块

| 功能 | 描述 | 状态 |
|------|------|------|
| 并行/串行执行 | 选择并行或串行执行批量命令 | ✅ 已实现 |
| 执行延迟设置 | 设置批量执行的设备间延迟 | ✅ 已实现 |
| 错误停止策略 | 遇错是否停止后续执行 | ✅ 已实现 |
| 脚本录制 | 录制操作序列为脚本 | ✅ 已实现 |
| 脚本回放 | 回放录制的脚本 | ✅ 已实现 |
| 同步输入文本 | 所有设备同步输入文本 | ✅ 已实现 |
| 同步按键事件 | 发送按键事件到所有设备 | ✅ 已实现 |
| 同步点击手势 | 所有设备同步点击坐标 | ✅ 已实现 |
| 同步滑动手势 | 所有设备同步滑动 | ✅ 已实现 |
| 快捷操作面板 | 截图、重启等快捷操作 | ✅ 已实现 |

### 2.16 应用管理增强模块

| 功能 | 描述 | 状态 |
|------|------|------|
| 运行应用 | 直接启动指定应用 | ✅ 已实现 |
| 提取APK | 提取已安装应用的APK文件 | ✅ 已实现 |
| 右键菜单 | 右键显示应用操作菜单 | ✅ 已实现 |
| 系统应用过滤 | 显示/隐藏系统应用 | ✅ 已实现 |

### 2.17 配置管理模块

| 功能 | 描述 | 状态 |
|------|------|------|
| 点号路径访问 | 支持 `app.name` 形式访问配置 | ✅ 已实现 |
| 自动保存 | 配置修改自动保存 | ✅ 已实现 |
| 备份恢复 | 配置备份和恢复 | ✅ 已实现 |
| Schema验证 | 配置格式验证 | ✅ 已实现 |
| 相对/绝对路径转换 | 自动转换相对路径为绝对路径 | ✅ 已实现 |
| 深度合并 | 配置项深度合并 | ✅ 已实现 |

### 2.18 帮助系统模块

| 功能 | 描述 | 状态 |
|------|------|------|
| ADB命令手册 | 集成awesome-adb文档 | ✅ 已实现 |
| Markdown渲染 | 渲染Markdown格式文档 | ✅ 已实现 |
| 命令搜索 | 关键词搜索ADB命令 | ✅ 已实现 |
| 一键复制 | 复制命令到剪贴板 | ✅ 已实现 |
| 文件变更监控 | 文档修改后自动刷新 | ✅ 已实现 |
| 搜索高亮 | 搜索时高亮匹配内容 | ✅ 已实现 |
| 开源组件清单 | 展示使用的开源组件 | ✅ 已实现 |

### 2.19 插件系统模块

| 功能 | 描述 | 状态 |
|------|------|------|
| 插件加载/卸载 | 动态加载和管理插件 | ✅ 已实现 |
| 插件生命周期 | 完整的生命周期钩子 | ✅ 已实现 |
| 权限控制 | 细粒度权限管理 | ✅ 已实现 |
| 事件总线 | 发布/订阅事件通信 | ✅ 已实现 |
| 插件配置持久化 | 保存插件配置状态 | ✅ 已实现 |
| 依赖检查 | 自动检查插件依赖 | ✅ 已实现 |

---

## 3. 新增功能需求

### 3.1 AI智能助手模块

#### 3.1.1 智能对话系统
| 功能 | 描述 | 优先级 |
|------|------|--------|
| 自然语言问答 | 基于ADB文档回答使用问题 | P0 |
| 上下文感知 | 结合当前设备状态回答问题 | P1 |
| 多轮对话 | 支持连续追问和深入探讨 | P1 |
| 对话历史 | 保存和查看对话历史 | P2 |

#### 3.1.2 AI Agent自动化引擎
| 功能 | 描述 | 优先级 |
|------|------|--------|
| 自然语言转ADB | 解析自然语言执行ADB命令 | P0 |
| 任务规划 | 自动规划多步骤任务 | P1 |
| 批量设备操作 | 在集群设备上执行相同操作 | P1 |
| 智能工作流 | 组合多个操作形成工作流 | P2 |

#### 3.1.3 日志智能分析
| 功能 | 描述 | 优先级 |
|------|------|--------|
| 实时异常检测 | 自动识别ANR/Crash/Exception | P0 |
| 崩溃根因分析 | 分析堆栈定位问题代码 | P0 |
| 日志摘要生成 | 提取关键信息生成摘要 | P1 |
| 问题关联分析 | 关联历史类似问题 | P1 |

#### 3.1.4 AI自动化测试
| 功能 | 描述 | 优先级 |
|------|------|--------|
| 自然语言生成测试 | 从描述生成测试脚本 | P1 |
| 智能Monkey参数 | AI控制测试参数 | P1 |
| 测试报告分析 | 自动分析测试结果 | P1 |

#### 3.1.5 Skill技能系统
| 功能 | 描述 | 优先级 |
|------|------|--------|
| Skill创建 | 保存操作序列为Skill | P2 |
| Skill执行 | 执行预定义的Skill | P2 |
| Skill分享 | 导入/导出Skill配置 | P2 |

### 3.2 MCP协议接入模块

#### 3.2.1 知识库MCP
| 功能 | 描述 | 优先级 |
|------|------|--------|
| 文档检索 | 搜索知识库文档 | P0 |
| 错误案例匹配 | 匹配历史错误案例 | P0 |
| 解决方案推荐 | 推荐问题解决方案 | P0 |
| 案例入库 | 新问题自动入库 | P1 |

#### 3.2.2 Draw.io可视化MCP
| 功能 | 描述 | 优先级 |
|------|------|--------|
| 日志流程图 | 从日志生成流程图 | P1 |
| 崩溃路径图 | 生成崩溃调用链图 | P1 |
| 测试路径图 | 生成测试执行路径 | P1 |
| 时序图生成 | 生成交互时序图 | P2 |

#### 3.2.3 测试框架MCP
| 功能 | 描述 | 优先级 |
|------|------|--------|
| 测试执行 | 执行Monkey/UI测试 | P1 |
| 测试脚本生成 | AI生成测试脚本 | P1 |
| 覆盖率分析 | 分析测试覆盖率 | P2 |

### 3.3 性能分析工具模块

#### 3.3.1 系统级性能工具
| 功能 | 描述 | 优先级 |
|------|------|--------|
| Perfetto集成 | 系统追踪分析 | P0 |
| Simpleperf集成 | CPU性能采样 | P0 |
| gfxinfo集成 | 帧率/GPU性能 | P0 |
| Method Tracing | 方法级耗时追踪 | P1 |

#### 3.3.2 内存分析工具
| 功能 | 描述 | 优先级 |
|------|------|--------|
| meminfo增强 | 详细内存分析 | P0 |
| procrank集成 | 内存排名 | P0 |
| 内存泄漏检测 | 自动检测内存泄漏 | P1 |

#### 3.3.3 电源分析工具
| 功能 | 描述 | 优先级 |
|------|------|--------|
| Battery Historian | 电池消耗可视化 | P1 |
| batterystats | 电池统计采集 | P1 |
| 唤醒锁分析 | 分析耗电唤醒源 | P2 |

### 3.4 内核调试工具模块

#### 3.4.1 内核追踪工具
| 功能 | 描述 | 优先级 |
|------|------|--------|
| ftrace集成 | 内核函数追踪 | P0 |
| trace-cmd集成 | ftrace前端工具 | P0 |
| KernelShark可视化 | 内核追踪可视化 | P1 |

#### 3.4.2 内核调试工具
| 功能 | 描述 | 优先级 |
|------|------|--------|
| KGDB集成 | 内核GDB调试 | P1 |
| KASAN集成 | 内核内存检测 | P0 |
| KMEMLEAK集成 | 内核内存泄漏 | P0 |

#### 3.4.3 崩溃分析工具
| 功能 | 描述 | 优先级 |
|------|------|--------|
| pstore/ramoops | 崩溃日志持久化 | P0 |
| Crash Utility | 崩溃转储分析 | P0 |
| lockdep | 锁依赖检测 | P1 |

### 3.5 外部服务集成模块

#### 3.5.1 数据库接入
| 功能 | 描述 | 优先级 |
|------|------|--------|
| SQLite本地存储 | 本地数据持久化 | P0 |
| MySQL/PostgreSQL | 远程数据库支持 | P2 |
| MongoDB | 非结构化数据存储 | P2 |

#### 3.5.2 日志分析平台
| 功能 | 描述 | 优先级 |
|------|------|--------|
| ELK Stack集成 | 日志集中分析 | P2 |
| Sentry集成 | 崩溃追踪 | P2 |
| 自定义Webhook | 灵活对接内部系统 | P2 |

#### 3.5.3 用户数据收集
| 功能 | 描述 | 优先级 |
|------|------|--------|
| 遥测数据收集 | 匿名使用统计 | P2 |
| 错误报告 | 自动上报错误 | P2 |
| 隐私保护 | 数据脱敏处理 | P2 |

### 3.6 使用手册系统模块

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 手册浏览器 | 统一的手册查看界面 | P0 |
| 分类导航 | 按类别浏览手册 | P0 |
| 全文搜索 | 搜索手册内容 | P1 |
| 工具手册 | 每个工具的独立手册 | P0 |

### 3.7 快捷按键配置系统模块

#### 3.7.1 按键配置管理
| 功能 | 描述 | 优先级 |
|------|------|--------|
| 配置文件定义 | 通过JSON/YAML文件定义所有快捷按键 | P0 |
| 按键显示/隐藏 | 控制按键在界面上的可见性 | P0 |
| 按键启用/禁用 | 控制按键是否可点击 | P0 |
| 按键顺序调整 | 自定义按键在界面上的排列顺序 | P1 |
| 分组管理 | 按键按功能分组（如：设备操作、文件传输等） | P0 |

#### 3.7.2 按键自定义
| 功能 | 描述 | 优先级 |
|------|------|--------|
| 修改命名 | 自定义按键显示名称（支持中英文） | P0 |
| 修改图标 | 自定义按键Emoji图标 | P1 |
| 修改执行功能 | 绑定到不同的ADB命令或Python函数 | P0 |
| 修改快捷键 | 设置键盘快捷键触发 | P2 |
| 修改确认提示 | 设置执行前是否需要用户确认 | P1 |

#### 3.7.3 按键增删管理
| 功能 | 描述 | 优先级 |
|------|------|--------|
| 新增按键 | 添加用户自定义按键 | P0 |
| 删除按键 | 移除不需要的按键 | P0 |
| 重置默认 | 恢复出厂默认按键配置 | P0 |
| 导入配置 | 从外部文件导入按键配置 | P1 |
| 导出配置 | 导出当前按键配置为文件 | P1 |

#### 3.7.4 配置文件格式示例
```json
{
  "button_groups": {
    "device_ops": {
      "name": "⚡ Device Operations",
      "order": 1,
      "buttons": [
        {
          "id": "screenshot",
          "name": "📸 Take Screenshot",
          "icon": "📸",
          "action": "take_screenshot",
          "visible": true,
          "enabled": true,
          "confirm": false,
          "shortcut": "Ctrl+Shift+S"
        },
        {
          "id": "reboot",
          "name": "🔄 Reboot Device",
          "icon": "🔄",
          "action": "reboot_device",
          "visible": true,
          "enabled": true,
          "confirm": true,
          "shortcut": null
        }
      ]
    },
    "quick_actions": {
      "name": "⚡ Quick Actions",
      "order": 4,
      "buttons": [
        {
          "id": "battery_status",
          "name": "🔋 Battery Status",
          "icon": "🔋",
          "action": "quick_battery_status",
          "visible": true,
          "enabled": true
        }
      ]
    },
    "settings": {
      "name": "⚙️ Settings",
      "order": 5,
      "buttons": [
        {
          "id": "dev_options_on",
          "name": "🔓 Enable Developer Options",
          "icon": "🔓",
          "action": "adb shell settings put global development_settings_enabled 1",
          "action_type": "adb_command",
          "visible": true,
          "enabled": true,
          "confirm": true
        },
        {
          "id": "dev_options_off",
          "name": "🔒 Disable Developer Options",
          "icon": "🔒",
          "action": "adb shell settings put global development_settings_enabled 0",
          "action_type": "adb_command",
          "visible": true,
          "enabled": true,
          "confirm": true
        },
        {
          "id": "screen_timeout_get",
          "name": "⏱️ Get Screen Timeout",
          "icon": "⏱️",
          "action": "adb shell settings get system screen_off_timeout",
          "action_type": "adb_command",
          "visible": true,
          "enabled": true,
          "confirm": false
        },
        {
          "id": "screen_timeout_set",
          "name": "⏰ Set Screen Timeout",
          "icon": "⏰",
          "action": "adb shell settings put system screen_off_timeout {timeout}",
          "action_type": "adb_command_with_input",
          "input_placeholder": "Timeout in ms (e.g. 60000)",
          "visible": true,
          "enabled": true,
          "confirm": true
        },
        {
          "id": "open_settings",
          "name": "⚙️ Open System Settings",
          "icon": "⚙️",
          "action": "adb shell am start -a android.settings.SETTINGS",
          "action_type": "adb_command",
          "visible": true,
          "enabled": true,
          "confirm": false
        },
        {
          "id": "virtual_keyboard",
          "name": "⌨️ ADB Keycode Keyboard",
          "icon": "⌨️",
          "action": "open_keycode_keyboard",
          "action_type": "dialog",
          "visible": true,
          "enabled": true,
          "confirm": false
        }
      ]
    },
    "keycode_keyboard": {
      "name": "⌨️ Keycode Keyboard",
      "order": 6,
      "buttons": [
        {
          "id": "KEYCODE_HOME",
          "name": "🏠 Home",
          "icon": "🏠",
          "action": "adb shell input keyevent 3",
          "action_type": "adb_command",
          "visible": true,
          "enabled": true,
          "shortcut": "H"
        },
        {
          "id": "KEYCODE_BACK",
          "name": "⬅️ Back",
          "icon": "⬅️",
          "action": "adb shell input keyevent 4",
          "action_type": "adb_command",
          "visible": true,
          "enabled": true,
          "shortcut": "B"
        },
        {
          "id": "KEYCODE_POWER",
          "name": "🔋 Power",
          "icon": "🔋",
          "action": "adb shell input keyevent 26",
          "action_type": "adb_command",
          "visible": true,
          "enabled": true,
          "shortcut": "P"
        }
      ]
    }
  }
}
```

#### 3.7.5 预置快捷按键清单

**Screen Mirror (Scrcpy) 分组**
| ID | 默认名称 | 默认功能 |
|----|----------|----------|
| start_mirror | ▶️ Start Mirror | 启动Scrcpy默认镜像 |
| advanced | ⚙️ Advanced | 显示Scrcpy高级选项 |
| scrcpy_path | 📂 Path | 设置Scrcpy路径 |

**File Transfer 分组**
| ID | 默认名称 | 默认功能 |
|----|----------|----------|
| push_file | ⬆️ Push File to Device | 推送文件到设备 |
| pull_file | ⬇️ Pull File from Device | 从设备拉取文件 |
| file_manager | 🗂️ Advanced File Manager | 打开高级文件管理器 |

**App Management 分组**
| ID | 默认名称 | 默认功能 |
|----|----------|----------|
| install_apk | 📦 Install APK | 安装APK文件 |
| uninstall_app | 🗑️ Uninstall App | 卸载应用 |
| reinstall_user | ♻️ Reinstall for User | 为当前用户重装 |
| list_apps | 📋 List Installed Apps | 列出已安装应用 |
| app_manager | 📱 App List Manager | 打开应用管理器 |
| open_apks | 📂 Open APKs Folder | 打开APK文件夹 |
| degoogle | 🚫 DeGoogle Device | 执行DeGoogle |
| undo_degoogle | ↩️ Undo DeGoogle | 撤销DeGoogle |

**Device Operations 分组**
| ID | 默认名称 | 默认功能 |
|----|----------|----------|
| screenshot | 📸 Take Screenshot | 截取屏幕 |
| reboot | 🔄 Reboot Device | 重启设备 |
| reboot_recovery | 🔧 Reboot to Recovery | 重启到Recovery |
| reboot_bootloader | ⚙️ Reboot to Bootloader | 重启到Bootloader |
| test_scripts | 🧪 Test Scripts | 打开测试脚本 |
| jadx | 🔍 JADX Decompiler | 打开反编译器 |

**Quick Actions - Device Info 分组**
| ID | 默认名称 | 默认功能 |
|----|----------|----------|
| battery_status | 🔋 Battery Status | 查看电池状态 |
| device_info | ℹ️ Device Info | 查看设备信息 |
| display_info | 🖥️ Display Info | 查看显示信息 |
| storage_info | 💾 Storage Info | 查看存储信息 |

**Quick Actions - Performance 分组**
| ID | 默认名称 | 默认功能 |
|----|----------|----------|
| cpu_info | 📊 CPU Info | 查看CPU信息 |
| memory_info | 🧠 Memory Info | 查看内存信息 |
| top_processes | 📈 Top Processes | 查看进程列表 |

**Quick Actions - Network 分组**
| ID | 默认名称 | 默认功能 |
|----|----------|----------|
| ip_address | 🔍 IP Address | 查看IP地址 |
| wifi_info | 📶 WiFi Info | 查看WiFi信息 |

**Quick Actions - Actions 分组**
| ID | 默认名称 | 默认功能 |
|----|----------|----------|
| clear_logcat | 🗑️ Clear Logcat | 清空日志缓冲 |
| airplane_mode | ✈️ Toggle Airplane Mode | 切换飞行模式 |
| quick_screenshot | 📸 Quick Screenshot | 快速截图 |
| screen_record | 🎥 Screen Record (30s) | 录屏30秒 |

**Quick Actions - Settings 分组**
| ID | 默认名称 | 默认功能 |
|----|----------|----------|
| dev_options_on | 🔓 Enable Developer Options | 打开开发者选项 |
| dev_options_off | 🔒 Disable Developer Options | 关闭开发者选项 |
| screen_timeout_get | ⏱️ Get Screen Timeout | 获取屏幕休眠时间 |
| screen_timeout_set | ⏰ Set Screen Timeout | 设置屏幕休眠时间 |
| open_settings | ⚙️ Open System Settings | 启动系统设置 |
| virtual_keyboard | ⌨️ ADB Keycode Keyboard | ADB按键键盘 |

**ADB Keycode Keyboard 按键列表**

| 按键ID | 按键名称 | KeyCode值 | 功能说明 |
|--------|----------|----------|----------|
| KEYCODE_HOME | Home键 | 3 | 返回主屏幕 |
| KEYCODE_BACK | Back键 | 4 | 返回上一级 |
| KEYCODE_POWER | Power键 | 26 | 电源按钮 |
| KEYCODE_VOLUME_UP | Volume Up | 24 | 音量增加 |
| KEYCODE_VOLUME_DOWN | Volume Down | 25 | 音量减少 |
| KEYCODE_MUTE | Mute | 91 | 静音 |
| KEYCODE_MENU | Menu键 | 82 | 菜单 |
| KEYCODE_SEARCH | Search键 | 84 | 搜索 |
| KEYCODE_DPAD_UP | D-Pad Up | 19 | 方向键上 |
| KEYCODE_DPAD_DOWN | D-Pad Down | 20 | 方向键下 |
| KEYCODE_DPAD_LEFT | D-Pad Left | 21 | 方向键左 |
| KEYCODE_DPAD_RIGHT | D-Pad Right | 22 | 方向键右 |
| KEYCODE_DPAD_CENTER | D-Pad Center | 23 | 方向键确认 |
| KEYCODE_ENTER | Enter | 66 | 回车 |
| KEYCODE_DEL | Delete | 67 | 删除 |
| KEYCODE_TAB | Tab | 61 | Tab键 |
| KEYCODE_SPACE | Space | 62 | 空格 |
| KEYCODE_0 - KEYCODE_9 | Number 0-9 | 7-16 | 数字键 |
| KEYCODE_A - KEYCODE_Z | Letter A-Z | 29-54 | 字母键 |
| KEYCODE_CAMERA | Camera | 27 | 相机 |
| KEYCODE_CALL | Call | 5 | 拨打 |
| KEYCODE_ENDCALL | End Call | 6 | 挂断 |
| KEYCODE_PLAY | Play | 85 | 播放 |
| KEYCODE_PAUSE | Pause | 79 | 暂停 |
| KEYCODE_STOP | Stop | 86 | 停止 |
| KEYCODE_NEXT | Next | 87 | 下一首 |
| KEYCODE_PREVIOUS | Previous | 88 | 上一首 |
| KEYCODE_REWIND | Rewind | 89 | 倒带 |
| KEYCODE_FAST_FORWARD | Fast Forward | 90 | 快进 |
| KEYCODE_WAKEUP | Wakeup | 224 | 唤醒 |

**ADB Keycode Keyboard 功能特性**
- 可自定义按键图标、名称、显示/隐藏
- 支持快捷键绑定到物理键盘
- 支持长按模式（发送DOWN+UP事件）
- 支持自定义重复次数
- 按键执行前后可配置确认提示
- 支持导出/导入按键配置

---

## 4. 非功能性需求

### 4.1 性能要求
| 指标 | 目标值 |
|------|--------|
| AI响应时间（普通问答） | < 3秒 |
| AI响应时间（复杂分析） | < 10秒 |
| 日志实时分析延迟 | < 1秒 |
| 知识库检索时间 | < 500毫秒 |
| 工具启动时间 | < 2秒 |
| 内存占用（空闲） | < 200MB |

### 4.2 安全要求
| 要求 | 描述 |
|------|------|
| API Key加密 | 敏感配置加密存储 |
| 本地LLM支持 | 支持离线使用，数据不出境 |
| 隐私保护 | 遥测数据匿名化 |
| 权限最小化 | 插件权限最小化原则 |

### 4.3 可用性要求
| 要求 | 描述 |
|------|------|
| 用户可选择性退出 | 遥测/AI功能可关闭 |
| 多LLM支持 | 支持OpenAI/本地模型切换 |
| 离线可用 | 核心功能离线可用 |

### 4.4 兼容性要求
| 要求 | 描述 |
|------|------|
| Android版本 | Android 5.0+ |
| Python版本 | Python 3.8+ |
| 操作系统 | Windows 10/11 |

---

## 5. 成功指标

| 指标 | 目标值 | 测量方式 |
|------|--------|----------|
| AI问答准确率 | > 85% | 用户反馈评分 |
| 崩溃诊断准确率 | > 80% | 与人工诊断对比 |
| 自动化操作成功率 | > 90% | 执行统计 |
| 测试覆盖率 | 100% | TDD测试通过率 |
| 用户满意度 | > 4.0/5 | 问卷调查 |

---

## 6. 功能优先级汇总

### P0 - 核心必做
- AI智能对话系统（自然语言问答）
- 日志智能分析（异常检测、崩溃分析）
- MCP知识库接入
- Perfetto/Simpleperf/gfxinfo集成
- ftrace/KASAN/KMEMLEAK/pstore集成
- SQLite本地存储
- 使用手册浏览器
- **快捷按键配置系统（配置文件定义、显示/隐藏、启用/禁用、增删按键）**

### P1 - 强烈推荐
- AI Agent自动化引擎
- 上下文感知/多轮对话
- Draw.io可视化MCP
- 测试框架MCP
- Battery Historian
- KGDB/Crash Utility/lockdep
- **快捷按键高级配置（按键顺序、快捷键绑定、导入/导出）**

### P2 - 可选增强
- Skill技能系统
- 远程数据库支持
- ELK/Sentry集成
- 遥测数据收集
- **快捷按键键盘快捷键**
