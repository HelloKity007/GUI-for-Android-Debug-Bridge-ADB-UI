# ADB Tool 插件开发指南

## 📚 目录
1. [架构概述](#架构概述)
2. [快速开始](#快速开始)
3. [插件接口详解](#插件接口详解)
4. [插件API使用](#插件api使用)
5. [事件系统](#事件系统)
6. [最佳实践](#最佳实践)
7. [示例插件](#示例插件)

---

## 架构概述

### 系统架构

```
┌─────────────────────────────────────────┐
│          View Layer (PyQt6)             │
│     主窗口 + 插件UI组件                   │
└──────────────┬──────────────────────────┘
               │ MVP 分层
┌──────────────┴──────────────────────────┐
│       Presenter Layer (逻辑层)           │
│     MainPresenter + PluginPresenters    │
└──────────────┬──────────────────────────┘
               │
┌──────────────┴──────────────────────────┐
│        Model Layer (数据/业务)           │
│      ADBModel + PluginModels            │
└──────────────┬──────────────────────────┘
               │
┌──────────────┴──────────────────────────┐
│         Plugin System                   │
│  ┌────────────────────────────┐        │
│  │   EventBus (事件总线)       │        │
│  │   - 发布/订阅解耦通信        │        │
│  └────────────────────────────┘        │
│  ┌────────────────────────────┐        │
│  │  PluginManager (管理器)     │        │
│  │  - 动态加载/卸载             │        │
│  │  - 生命周期管理              │        │
│  └────────────────────────────┘        │
│  ┌────────────────────────────┐        │
│  │  PluginAPI (接口层)         │        │
│  │  - ADB能力封装               │        │
│  │  - 权限控制                  │        │
│  └────────────────────────────┘        │
└─────────────────────────────────────────┘
```

### 核心特性

- ✅ **插件热插拔** - 动态加载/卸载插件
- ✅ **权限隔离** - 细粒度权限控制
- ✅ **事件驱动** - 低耦合的发布订阅模式
- ✅ **生命周期管理** - 完整的插件生命周期钩子
- ✅ **类型安全** - 强类型接口定义

---

## 快速开始

### 1. 创建插件文件

在 `plugins/` 目录下创建 `my_plugin.py`:

```python
from framework.plugin import UIPluginInterface, PluginMetadata
from typing import Dict, Any

class MyPlugin(UIPluginInterface):
    def __init__(self):
        super().__init__()
        self._metadata = PluginMetadata(
            id="my_plugin",
            name="我的插件",
            version="1.0.0",
            author="Your Name",
            description="插件描述",
            api_version="1.0"
        )
    
    def get_metadata(self) -> PluginMetadata:
        return self._metadata
    
    def on_load(self, api, event_bus) -> bool:
        self._api = api
        self._event_bus = event_bus
        return True
    
    def on_enable(self) -> bool:
        return True
    
    def on_disable(self) -> bool:
        return True
    
    def on_unload(self) -> bool:
        return True
    
    def create_ui(self, parent_window):
        # 创建UI组件
        pass
    
    def get_menu_items(self):
        return []

# 插件入口
PluginClass = MyPlugin
```

### 2. 使用插件API

```python
# 执行ADB命令
result = self._api.adb_execute_command("devices", plugin_id=self._metadata.id)

# 获取设备列表
devices = self._api.adb_get_devices()

# 订阅事件
self._event_bus.subscribe("device.connected", self.on_device_connected)

# 发布事件
self._event_bus.publish("my_event", {"data": "value"})
```

---

## 插件接口详解

### PluginInterface (基础接口)

所有插件必须实现的基础接口:

```python
class PluginInterface(ABC):
    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """返回插件元数据"""
        pass
    
    @abstractmethod
    def on_load(self, api, event_bus) -> bool:
        """插件加载时调用"""
        pass
    
    @abstractmethod
    def on_unload(self) -> bool:
        """插件卸载时调用"""
        pass
    
    @abstractmethod
    def on_enable(self) -> bool:
        """插件启用时调用"""
        pass
    
    @abstractmethod
    def on_disable(self) -> bool:
        """插件禁用时调用"""
        pass
```

### UIPluginInterface (UI插件接口)

带UI的插件继承此接口:

```python
class UIPluginInterface(PluginInterface):
    @abstractmethod
    def create_ui(self, parent_window):
        """创建UI组件"""
        pass
    
    @abstractmethod
    def get_menu_items(self):
        """返回菜单项"""
        pass
    
    def get_toolbar_actions(self):
        """返回工具栏动作(可选)"""
        return []
```

### ServicePluginInterface (服务插件接口)

后台服务插件继承此接口:

```python
class ServicePluginInterface(PluginInterface):
    @abstractmethod
    def start_service(self) -> bool:
        """启动服务"""
        pass
    
    @abstractmethod
    def stop_service(self) -> bool:
        """停止服务"""
        pass
    
    @abstractmethod
    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        pass
```

---

## 插件API使用

### ADB相关API

```python
# 执行ADB命令（需要权限）
result = api.adb_execute_command("shell ls", plugin_id="my_plugin")

# 获取设备列表
devices = api.adb_get_devices()

# 获取设备信息
info = api.adb_get_device_info("device_id")

# 安装APK（需要权限）
api.adb_install_apk("device_id", "/path/to/app.apk", plugin_id="my_plugin")

# 推送文件（需要权限）
api.adb_push_file("device_id", "/local/file", "/remote/path", plugin_id="my_plugin")
```

### 事件系统API

```python
# 订阅事件
api.event_subscribe("device.connected", callback_function)

# 取消订阅
api.event_unsubscribe("device.connected", callback_function)

# 发布事件
api.event_publish("custom.event", {"data": "value"}, plugin_id="my_plugin")
```

### 配置API

```python
# 读取配置
value = api.config_get("section", "key", fallback="default")

# 写入配置（需要权限）
api.config_set("section", "key", "value", plugin_id="my_plugin")
```

### 日志API

```python
api.log_info("信息日志", plugin_id="my_plugin")
api.log_warning("警告日志", plugin_id="my_plugin")
api.log_error("错误日志", plugin_id="my_plugin")
```

---

## 事件系统

### 标准事件类型

```python
from framework.event import EventTypes

# 设备事件
EventTypes.DEVICE_CONNECTED       # 设备连接
EventTypes.DEVICE_DISCONNECTED    # 设备断开
EventTypes.DEVICE_SELECTED        # 设备选中

# 命令事件
EventTypes.COMMAND_EXECUTED       # 命令执行
EventTypes.COMMAND_FAILED         # 命令失败

# 插件事件
EventTypes.PLUGIN_LOADED          # 插件加载
EventTypes.PLUGIN_UNLOADED        # 插件卸载
EventTypes.PLUGIN_ENABLED         # 插件启用
EventTypes.PLUGIN_DISABLED        # 插件禁用

# 应用事件
EventTypes.APP_STARTUP            # 应用启动
EventTypes.APP_SHUTDOWN           # 应用关闭
```

### 事件订阅示例

```python
def on_device_connected(event):
    device_id = event.data.get('device_id')
    print(f"Device connected: {device_id}")

# 订阅
self._event_bus.subscribe(EventTypes.DEVICE_CONNECTED, on_device_connected)
```

---

## 最佳实践

### 1. 权限管理

```python
# 在插件加载时请求必要权限
def on_load(self, api, event_bus):
    api.grant_permission(self._metadata.id, "adb.execute")
    api.grant_permission(self._metadata.id, "adb.file_transfer")
    return True
```

### 2. 资源清理

```python
def on_unload(self):
    # 取消所有事件订阅
    self._event_bus.unsubscribe(EventTypes.DEVICE_CONNECTED, self._callback)
    
    # 关闭打开的文件/连接
    if self._file:
        self._file.close()
    
    return True
```

### 3. 错误处理

```python
def on_enable(self):
    try:
        # 初始化逻辑
        result = self._api.adb_execute_command("devices")
        if not result['success']:
            self._api.log_error(f"Failed to get devices: {result['stderr']}")
            return False
        return True
    except Exception as e:
        self._api.log_error(f"Error enabling plugin: {e}")
        return False
```

### 4. 线程安全

```python
import threading

class MyPlugin(ServicePluginInterface):
    def __init__(self):
        super().__init__()
        self._lock = threading.Lock()
        self._data = {}
    
    def update_data(self, key, value):
        with self._lock:
            self._data[key] = value
```

---

## 示例插件

完整的设备监控插件示例，请查看: `plugins/device_monitor_plugin.py`

该插件演示了:
- ✅ 完整的生命周期管理
- ✅ 事件订阅和处理
- ✅ API调用
- ✅ 服务状态管理

---

## 附录

### 权限列表

```python
from framework.plugin.plugin_api import Permissions

# ADB权限
Permissions.ADB_EXECUTE          # 执行ADB命令
Permissions.ADB_INSTALL_APK      # 安装APK
Permissions.ADB_UNINSTALL        # 卸载应用
Permissions.ADB_FILE_TRANSFER    # 文件传输
Permissions.ADB_SHELL            # Shell命令

# 配置权限
Permissions.CONFIG_READ          # 读取配置
Permissions.CONFIG_WRITE         # 写入配置

# UI权限
Permissions.UI_CREATE_WINDOW     # 创建窗口
Permissions.UI_SHOW_DIALOG       # 显示对话框
Permissions.UI_ADD_MENU          # 添加菜单

# 系统权限
Permissions.SYSTEM_FILE_ACCESS   # 文件系统访问
Permissions.SYSTEM_NETWORK       # 网络访问
```

---

**更多文档和示例，请访问项目Wiki**
