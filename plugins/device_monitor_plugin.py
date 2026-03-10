# -*- coding: utf-8 -*-
"""
Device Monitor Plugin - 设备监控插件示例
监控设备连接状态并记录日志
"""
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework.plugin import PluginInterface, PluginMetadata, ServicePluginInterface
from framework.event import Event, EventTypes
from typing import Dict, Any


class DeviceMonitorPlugin(ServicePluginInterface):
    """
    设备监控插件
    演示插件开发的最佳实践
    """
    
    def __init__(self):
        super().__init__()
        self._metadata = PluginMetadata(
            id="device_monitor",
            name="设备监控器",
            version="1.0.0",
            author="ADB Tool Team",
            description="监控设备连接状态，记录设备变化日志",
            dependencies=[],
            api_version="1.0",
            enabled=True
        )
        self._device_cache = {}
        self._running = False
    
    def get_metadata(self) -> PluginMetadata:
        """返回插件元数据"""
        return self._metadata
    
    def on_load(self, api, event_bus) -> bool:
        """插件加载时调用"""
        self._api = api
        self._event_bus = event_bus
        
        # 订阅设备相关事件
        self._event_bus.subscribe(EventTypes.DEVICE_CONNECTED, self._on_device_connected)
        self._event_bus.subscribe(EventTypes.DEVICE_DISCONNECTED, self._on_device_disconnected)
        
        self._api.log_info("Device Monitor Plugin loaded", self._metadata.id)
        return True
    
    def on_unload(self) -> bool:
        """插件卸载时调用"""
        # 取消事件订阅
        self._event_bus.unsubscribe(EventTypes.DEVICE_CONNECTED, self._on_device_connected)
        self._event_bus.unsubscribe(EventTypes.DEVICE_DISCONNECTED, self._on_device_disconnected)
        
        self._api.log_info("Device Monitor Plugin unloaded", self._metadata.id)
        return True
    
    def on_enable(self) -> bool:
        """插件启用时调用"""
        self._running = True
        self._api.log_info("Device Monitor Plugin enabled", self._metadata.id)
        
        # 获取当前设备列表
        devices = self._api.adb_get_devices()
        for device in devices:
            self._device_cache[device['id']] = device
            self._api.log_info(f"Device detected: {device['id']} ({device.get('model', 'Unknown')})", 
                              self._metadata.id)
        
        return True
    
    def on_disable(self) -> bool:
        """插件禁用时调用"""
        self._running = False
        self._device_cache.clear()
        self._api.log_info("Device Monitor Plugin disabled", self._metadata.id)
        return True
    
    # ServicePluginInterface 实现
    def start_service(self) -> bool:
        """启动监控服务"""
        return self.on_enable()
    
    def stop_service(self) -> bool:
        """停止监控服务"""
        return self.on_disable()
    
    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            'running': self._running,
            'devices_monitored': len(self._device_cache),
            'device_list': list(self._device_cache.keys())
        }
    
    # 事件处理
    def _on_device_connected(self, event: Event):
        """设备连接事件处理"""
        device_id = event.data.get('device_id')
        if device_id and self._running:
            # 获取设备详细信息
            device_info = self._api.adb_get_device_info(device_id)
            self._device_cache[device_id] = device_info
            
            self._api.log_info(
                f"Device connected: {device_id} - {device_info.get('Model', 'Unknown')}",
                self._metadata.id
            )
    
    def _on_device_disconnected(self, event: Event):
        """设备断开事件处理"""
        device_id = event.data.get('device_id')
        if device_id and self._running:
            device_info = self._device_cache.pop(device_id, {})
            
            self._api.log_info(
                f"Device disconnected: {device_id}",
                self._metadata.id
            )
    
    # PluginInterface 钩子方法
    def on_device_connected(self, device_id: str):
        """设备连接钩子"""
        self._api.log_info(f"Hook: Device connected - {device_id}", self._metadata.id)
    
    def on_device_disconnected(self, device_id: str):
        """设备断开钩子"""
        self._api.log_info(f"Hook: Device disconnected - {device_id}", self._metadata.id)


# 插件入口点（供PluginManager发现）
PluginClass = DeviceMonitorPlugin
