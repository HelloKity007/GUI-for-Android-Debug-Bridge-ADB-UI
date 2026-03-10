# -*- coding: utf-8 -*-
"""
Event Bus - 事件总线系统
提供低耦合的发布订阅机制
"""
from typing import Callable, Dict, List, Any
from dataclasses import dataclass
from datetime import datetime
import threading
from enum import Enum


class EventPriority(Enum):
    """事件优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Event:
    """事件数据类"""
    type: str                          # 事件类型
    data: Dict[str, Any]              # 事件数据
    source: str = "system"            # 事件来源
    timestamp: float = None           # 时间戳
    priority: EventPriority = EventPriority.NORMAL
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().timestamp()


class EventBus:
    """
    事件总线
    实现发布订阅模式，用于主程序与插件间的解耦通信
    """
    
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()
        self._event_history: List[Event] = []
        self._max_history = 1000
    
    def subscribe(self, event_type: str, callback: Callable, priority: EventPriority = EventPriority.NORMAL):
        """
        订阅事件
        
        Args:
            event_type: 事件类型
            callback: 回调函数
            priority: 优先级
        """
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            
            # 按优先级排序
            self._subscribers[event_type].append((priority.value, callback))
            self._subscribers[event_type].sort(key=lambda x: x[0], reverse=True)
    
    def unsubscribe(self, event_type: str, callback: Callable):
        """
        取消订阅
        
        Args:
            event_type: 事件类型
            callback: 回调函数
        """
        with self._lock:
            if event_type in self._subscribers:
                self._subscribers[event_type] = [
                    (p, cb) for p, cb in self._subscribers[event_type] if cb != callback
                ]
                if not self._subscribers[event_type]:
                    del self._subscribers[event_type]
    
    def publish(self, event_type: str, data: Dict[str, Any] = None, source: str = "system", 
                priority: EventPriority = EventPriority.NORMAL):
        """
        发布事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
            source: 事件来源
            priority: 优先级
        """
        event = Event(
            type=event_type,
            data=data or {},
            source=source,
            priority=priority
        )
        
        # 保存历史
        with self._lock:
            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history.pop(0)
        
        # 通知订阅者
        self._notify_subscribers(event)
    
    def _notify_subscribers(self, event: Event):
        """通知所有订阅者"""
        with self._lock:
            subscribers = self._subscribers.get(event.type, [])
        
        for priority, callback in subscribers:
            try:
                callback(event)
            except Exception as e:
                print(f"[EventBus] Error in subscriber callback: {e}")
    
    def get_history(self, event_type: str = None, limit: int = 100) -> List[Event]:
        """
        获取事件历史
        
        Args:
            event_type: 事件类型过滤
            limit: 返回数量限制
            
        Returns:
            事件列表
        """
        with self._lock:
            if event_type:
                events = [e for e in self._event_history if e.type == event_type]
            else:
                events = self._event_history.copy()
            
            return events[-limit:] if len(events) > limit else events
    
    def clear_history(self):
        """清空事件历史"""
        with self._lock:
            self._event_history.clear()
    
    def get_subscriber_count(self, event_type: str = None) -> int:
        """获取订阅者数量"""
        with self._lock:
            if event_type:
                return len(self._subscribers.get(event_type, []))
            else:
                return sum(len(subs) for subs in self._subscribers.values())


# 预定义事件类型
class EventTypes:
    """标准事件类型定义"""
    
    # 设备事件
    DEVICE_CONNECTED = "device.connected"
    DEVICE_DISCONNECTED = "device.disconnected"
    DEVICE_SELECTED = "device.selected"
    DEVICE_INFO_UPDATED = "device.info_updated"
    DEVICE_LIST_UPDATED = "device.list_updated"
    
    # ADB命令事件
    COMMAND_EXECUTED = "command.executed"
    COMMAND_FAILED = "command.failed"
    
    # 插件事件
    PLUGIN_LOADED = "plugin.loaded"
    PLUGIN_UNLOADED = "plugin.unloaded"
    PLUGIN_ENABLED = "plugin.enabled"
    PLUGIN_DISABLED = "plugin.disabled"
    PLUGIN_ERROR = "plugin.error"
    
    # UI事件
    UI_THEME_CHANGED = "ui.theme_changed"
    UI_WINDOW_OPENED = "ui.window_opened"
    UI_WINDOW_CLOSED = "ui.window_closed"
    
    # 应用事件
    APP_STARTUP = "app.startup"
    APP_SHUTDOWN = "app.shutdown"
    APP_CONFIG_CHANGED = "app.config_changed"
    
    # 文件事件
    FILE_UPLOADED = "file.uploaded"
    FILE_DOWNLOADED = "file.downloaded"
    
    # 应用管理事件
    APP_INSTALLED = "app.installed"
    APP_UNINSTALLED = "app.uninstalled"
