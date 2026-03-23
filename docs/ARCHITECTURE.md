# ADB GUI 架构文档

## 版本

- 文档版本: 1.0.0
- 适用于: v2.003.010+
- 最后更新: 2026-03-23

---

## 1. 核心原则

### 1.1 零卡顿原则 (Zero-Lag Principle)

**所有可能阻塞的操作都必须在工作线程中执行，主线程只负责 UI 更新。**

```
主线程 (Main Thread)          工作线程 (Worker Thread)
    │                              │
    ├── UI 事件处理                │
    ├── 信号接收                   │
    ├── 控件更新                   │
    │                              ├── ADB 命令执行
    │                              ├── 文件 I/O
    │                              ├── 网络请求
    │                              └── 进程管理
```

### 1.2 阻塞操作清单

以下操作**必须**在工作线程中执行：

| 操作类型 | 示例 | 预期耗时 |
|---------|------|----------|
| ADB 命令 | `adb devices`, `adb shell` | 100ms - 30s |
| 文件读写 | `open()`, `shutil.copy()` | 10ms - 10s |
| 进程等待 | `process.wait()`, `subprocess.run()` | 10ms - 无限 |
| 网络请求 | HTTP, socket | 100ms - 60s |

---

## 2. 项目结构

```
ADB-GUI/
├── adb_gui.py              # 主 GUI 应用 (ADBToolGUI 类)
├── core/
│   ├── adb_manager.py      # ADB 命令执行器 (同步接口)
│   └── scrcpy_manager.py   # Scrcpy 管理器
├── utils/
│   ├── config_manager.py   # 配置管理
│   └── logcat_manager.py   # Logcat 异步管理器 (参考实现)
├── dialogs/
│   ├── app_manager.py      # 应用管理对话框
│   ├── file_manager.py     # 文件管理对话框
│   └── ...
├── extensions/
│   └── Ghost-Downloader-3/ # 下载器扩展
├── config/
│   ├── config.json         # 用户配置
│   └── buttons_cmd.json    # 自定义按钮命令
└── docs/
    ├── ARCHITECTURE.md     # 本文档
    └── DEVELOPMENT.md      # 开发约束
```

---

## 3. 异步模式

### 3.1 推荐模式: QThread + Signal

适用于**持续性任务**（如 logcat 流）：

```python
class Worker(QThread):
    result_ready = Signal(object)
    error_occurred = Signal(str)

    def run(self):
        try:
            result = do_blocking_work()
            self.result_ready.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))
```

参考实现: `utils/logcat_manager.py`

### 3.2 简化模式: threading + QTimer.singleShot

适用于**一次性任务**（如刷新设备列表）：

```python
def async_operation(self):
    def do_work():
        result = blocking_call()
        # 回到主线程更新 UI (使用默认参数捕获值!)
        QTimer.singleShot(0, lambda r=result: self._on_complete(r))

    threading.Thread(target=do_work, daemon=True).start()

def _on_complete(self, result):
    """主线程回调 - 更新 UI"""
    self.some_widget.setText(result)
```

**关键点**: Lambda 必须使用默认参数捕获值，避免闭包问题！

```python
# 错误 - 闭包捕获变量引用
QTimer.singleShot(0, lambda: self.update(data))

# 正确 - 默认参数捕获值
QTimer.singleShot(0, lambda d=data: self.update(d))
```

### 3.3 禁止模式

```python
# 禁止: 主线程直接调用阻塞操作
def on_button_click(self):
    result = self.adb.run_command("devices")  # 阻塞主线程!
    self.update_ui(result)

# 禁止: 工作线程直接操作 UI
def worker_thread():
    self.label.setText("...")  # 跨线程操作 UI!
```

---

## 4. 组件职责

### 4.1 ADBManager (`core/adb_manager.py`)

- **职责**: 封装 ADB 命令执行
- **接口**: 同步阻塞（调用方需在工作线程中使用）
- **关键方法**:
  - `run_command(cmd, timeout)` - 执行 ADB 命令
  - `get_devices(silent, full_info)` - 获取设备列表

### 4.2 LogcatManager (`utils/logcat_manager.py`)

- **职责**: 异步流式读取 logcat
- **模式**: QThread + 批量信号
- **特点**: 非阻塞 API，自动批量发送

### 4.3 ADBToolGUI (`adb_gui.py`)

- **职责**: 主界面和业务逻辑协调
- **原则**: 所有 ADB 调用必须通过异步包装

---

## 5. 信号/回调命名约定

| 前缀 | 用途 | 示例 |
|------|------|------|
| `_on_*` | 内部回调方法 | `_on_refresh_complete` |
| `*_ready` | 数据就绪信号 | `logs_ready`, `devices_ready` |
| `*_changed` | 状态变化信号 | `status_changed` |
| `*_error` | 错误信号 | `error_occurred` |

---

## 6. 批量 UI 更新

高频更新时必须使用批量模式：

```python
def _on_batch_logs(self, logs: list):
    # 暂停 UI 更新
    self.output_text.setUpdatesEnabled(False)
    try:
        for log in logs:
            self.output_text.append(log)
    finally:
        # 恢复 UI 更新
        self.output_text.setUpdatesEnabled(True)

    # 最后统一滚动
    if self.auto_scroll:
        scrollbar = self.output_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
```

---

## 7. 已异步化的功能

| 功能 | 方法 | 状态 |
|------|------|------|
| Logcat | `toggle_logcat()` | ✅ 已完成 |
| 刷新设备 | `refresh_devices()` | ✅ 已完成 |
| Push 文件 | `push_file()` | ✅ 已完成 |
| Pull 文件 | `pull_file()` | ✅ 已完成 |
| 安装 APK | `install_apk()` | ✅ 已完成 |
| 卸载应用 | `uninstall_app()` | ✅ 已完成 |
| 加载应用列表 | `show_uninstalled_apps()` | ✅ 已完成 |

---

## 8. 待异步化的功能

| 功能 | 方法 | 当前问题 |
|------|------|----------|
| 测试 ADB | `test_adb()` | 主线程调用 run_command |
| 显示包信息 | `show_package_info()` | 主线程调用 run_command |
| 显示包详情 | `show_package_details()` | 主线程调用 run_command |

---

## 9. 错误处理原则

1. **工作线程中的异常**必须捕获并通过信号传递
2. **主线程回调**中的异常必须捕获并记录日志
3. **用户可见错误**使用 `QMessageBox` 显示
4. **调试信息**使用 `self.log()` 记录

```python
def worker_thread():
    try:
        result = risky_operation()
        QTimer.singleShot(0, lambda r=result: self._on_success(r))
    except Exception as e:
        QTimer.singleShot(0, lambda err=str(e): self._on_error(err))
```

---

## 10. 性能指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| UI 响应时间 | < 100ms | 任何按钮点击后 UI 应立即响应 |
| 批量日志间隔 | 100ms | 日志批量发送最大间隔 |
| 批量日志大小 | 50 行 | 日志批量发送最大行数 |
| 线程启动延迟 | < 10ms | daemon 线程启动延迟 |

---

## 附录 A: 快速检查清单

开发新功能前，检查以下项目：

- [ ] 是否调用了 `adb.run_command()` 或 `subprocess`?
- [ ] 如果是，是否在工作线程中执行?
- [ ] UI 更新是否通过 `QTimer.singleShot` 回到主线程?
- [ ] Lambda 是否使用默认参数捕获值?
- [ ] 高频更新是否使用了批量模式?
- [ ] 异常是否正确捕获和传递?
