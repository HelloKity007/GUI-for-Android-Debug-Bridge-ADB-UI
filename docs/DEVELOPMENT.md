# ADB GUI 开发约束

## 版本

- 文档版本: 1.0.0
- 适用于: v2.003.010+
- 最后更新: 2026-03-23

---

## 1. 强制约束 (MUST)

### 1.1 线程安全

```python
# 必须: 阻塞操作放在工作线程
def on_button_click(self):
    def do_work():
        result = self.adb.run_command(cmd)
        QTimer.singleShot(0, lambda r=result: self._update_ui(r))
    threading.Thread(target=do_work, daemon=True).start()

# 禁止: 主线程直接调用阻塞操作
def on_button_click(self):
    result = self.adb.run_command(cmd)  # 禁止!
```

### 1.2 Lambda 闭包

```python
# 必须: 使用默认参数捕获值
QTimer.singleShot(0, lambda d=data, s=status: self.update(d, s))

# 禁止: 直接引用变量
QTimer.singleShot(0, lambda: self.update(data, status))  # 禁止!
```

### 1.3 信号断开重连

修改 ComboBox 内容前必须断开信号，修改后重连：

```python
# 必须
try:
    self.combo.currentTextChanged.disconnect()
except RuntimeError:
    pass

self.combo.clear()
self.combo.addItems(items)

self.combo.currentTextChanged.connect(self.on_selection)
```

### 1.4 版本号

每次修改代码必须更新版本号：

```python
APP_VERSION = "2.003.XXX"  # XXX 递增
```

---

## 2. 推荐约束 (SHOULD)

### 2.1 批量 UI 更新

```python
# 推荐: 批量更新时暂停重绘
self.widget.setUpdatesEnabled(False)
try:
    for item in items:
        self.widget.append(item)
finally:
    self.widget.setUpdatesEnabled(True)
```

### 2.2 回调方法命名

```python
# 推荐命名
def _on_xxx_complete(self, result):  # 完成回调
def _on_xxx_error(self, error):       # 错误回调
def _on_xxx_status(self, status):     # 状态回调
```

### 2.3 日志记录

```python
# 推荐: 关键操作记录日志
self.log(f"操作开始: {operation}", "INFO")
self.log(f"操作失败: {error}", "ERROR")
```

---

## 3. 禁止约束 (MUST NOT)

### 3.1 主线程阻塞

以下操作**禁止**在主线程执行：

- `subprocess.run()` / `subprocess.Popen().wait()`
- `adb.run_command()` / `adb.get_devices()`
- `process.wait(timeout=N)` (N > 0)
- `time.sleep(N)` (N > 0.1)
- 大文件 `open()` / `read()` / `write()`
- 网络请求 `requests.get()` / `socket.connect()`

### 3.2 跨线程 UI 操作

工作线程**禁止**直接操作 UI：

```python
# 禁止
def worker_thread():
    self.label.setText("...")      # 禁止!
    self.button.setEnabled(False)  # 禁止!
    QMessageBox.information(...)   # 禁止!
```

### 3.3 无保护的信号断开

```python
# 禁止: 不处理可能的 RuntimeError
self.combo.currentTextChanged.disconnect()  # 可能抛异常!

# 必须: 使用 try-except
try:
    self.combo.currentTextChanged.disconnect()
except RuntimeError:
    pass
```

---

## 4. 代码模板

### 4.1 异步按钮操作

```python
def on_xxx_button(self):
    """按钮点击 - 异步执行"""
    if not self.current_device:
        QMessageBox.warning(self, "警告", "请先选择设备")
        return

    def do_work():
        try:
            cmd = f"{self.get_device_flag()} shell xxx"
            result = self.adb.run_command(cmd)
            QTimer.singleShot(0, lambda r=result: self._on_xxx_complete(r))
        except Exception as e:
            QTimer.singleShot(0, lambda err=str(e): self._on_xxx_error(err))

    threading.Thread(target=do_work, daemon=True).start()

def _on_xxx_complete(self, result):
    """操作完成 - 主线程"""
    if result['success']:
        self.log("操作成功", "INFO")
    else:
        self.log(f"操作失败: {result.get('stderr', '')}", "ERROR")

def _on_xxx_error(self, error: str):
    """操作错误 - 主线程"""
    self.log(f"错误: {error}", "ERROR")
    QMessageBox.critical(self, "错误", error)
```

### 4.2 异步列表加载

```python
def load_xxx_list(self):
    """异步加载列表"""
    self.update_status("加载中...")

    def do_load():
        try:
            items = fetch_items()  # 阻塞操作
            QTimer.singleShot(0, lambda i=items: self._on_list_loaded(i))
        except Exception as e:
            QTimer.singleShot(0, lambda err=str(e): self._on_list_error(err))

    threading.Thread(target=do_load, daemon=True).start()

def _on_list_loaded(self, items: list):
    """列表加载完成 - 主线程"""
    try:
        self.listbox.currentTextChanged.disconnect()
    except RuntimeError:
        pass

    self.listbox.clear()
    self.listbox.addItems(items)

    self.listbox.currentTextChanged.connect(self.on_item_selected)
    self.update_status(f"已加载 {len(items)} 项")
```

---

## 5. 检查清单

### 5.1 新功能开发前

- [ ] 阅读 `docs/ARCHITECTURE.md`
- [ ] 确认功能是否涉及阻塞操作
- [ ] 设计异步执行方案

### 5.2 代码提交前

- [ ] 更新版本号 `APP_VERSION`
- [ ] 无主线程阻塞操作
- [ ] Lambda 使用默认参数
- [ ] 信号断开有异常处理
- [ ] 添加必要日志

### 5.3 测试验证

- [ ] UI 响应流畅 (< 100ms)
- [ ] 按钮点击立即响应
- [ ] 无界面卡顿
- [ ] 错误正确显示

---

## 6. 常见问题

### Q1: 为什么 Lambda 必须用默认参数?

Python lambda 闭包捕获的是变量**引用**而非**值**。在异步场景下，变量可能在 lambda 执行前已改变。

```python
# 问题示例
for i in range(3):
    QTimer.singleShot(0, lambda: print(i))  # 全部输出 2

# 正确示例
for i in range(3):
    QTimer.singleShot(0, lambda x=i: print(x))  # 输出 0, 1, 2
```

### Q2: 什么时候用 QThread vs threading.Thread?

| 场景 | 推荐 |
|------|------|
| 一次性短任务 | `threading.Thread` |
| 持续性任务 | `QThread` |
| 需要复杂信号 | `QThread` |
| 简单回调 | `threading.Thread` + `QTimer.singleShot` |

### Q3: 为什么需要 setUpdatesEnabled?

批量更新时，每次 `append()` 都会触发重绘。暂停更新可以合并为一次重绘，大幅提升性能。

---

## 7. 参考实现

- **异步 Logcat**: `utils/logcat_manager.py`
- **异步刷新设备**: `adb_gui.py` → `refresh_devices()` + `_on_refresh_complete()`
