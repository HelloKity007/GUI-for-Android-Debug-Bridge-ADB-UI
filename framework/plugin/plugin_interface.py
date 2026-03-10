# -*- coding: utf-8 -*-
"""
Plugin Interface - 插件统一接口定义
所有插件必须实现此接口
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum


class PluginStatus(Enum):
    """插件状态枚举"""
    UNLOADED = "unloaded"      # 未加载
    LOADING = "loading"        # 加载中
    LOADED = "loaded"          # 已加载
    RUNNING = "running"        # 运行中
    STOPPED = "stopped"        # 已停止
    ERROR = "error"            # 错误状态


@dataclass
class PluginMetadata:
    """插件元数据"""
    id: str                    # 插件唯一标识
    name: str                  # 插件名称
    version: str               # 版本号
    author: str                # 作者
    description: str           # 描述
    dependencies: list = None  # 依赖的其他插件ID列表
    api_version: str = "1.0"   # 需要的API版本
    enabled: bool = True       # 是否启用
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class PluginInterface(ABC):
    """
    插件基础接口
    所有插件必须继承此类并实现抽象方法
    """
    
    def __init__(self):
        self._metadata: Optional[PluginMetadata] = None
        self._status: PluginStatus = PluginStatus.UNLOADED
        self._api: Optional[Any] = None
        self._event_bus: Optional[Any] = None
    
    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """
        获取插件元数据
        必须在子类中实现
        """
        pass
    
    @abstractmethod
    def on_load(self, api: 'PluginAPI', event_bus: 'EventBus') -> bool:
        """
        插件加载时调用
        
        Args:
            api: 主程序提供的API接口
            event_bus: 事件总线
            
        Returns:
            bool: 加载成功返回True，失败返回False
        """
        pass
    
    @abstractmethod
    def on_unload(self) -> bool:
        """
        插件卸载时调用
        用于清理资源
        
        Returns:
            bool: 卸载成功返回True
        """
        pass
    
    @abstractmethod
    def on_enable(self) -> bool:
        """
        插件启用时调用
        
        Returns:
            bool: 启用成功返回True
        """
        pass
    
    @abstractmethod
    def on_disable(self) -> bool:
        """
        插件禁用时调用
        
        Returns:
            bool: 禁用成功返回True
        """
        pass
    
    # 可选钩子方法
    def on_device_connected(self, device_id: str) -> None:
        """设备连接时的钩子"""
        pass
    
    def on_device_disconnected(self, device_id: str) -> None:
        """设备断开时的钩子"""
        pass
    
    def on_command_executed(self, command: str, result: Dict[str, Any]) -> None:
        """命令执行后的钩子"""
        pass
    
    # 状态管理
    @property
    def status(self) -> PluginStatus:
        """获取插件当前状态"""
        return self._status
    
    @status.setter
    def status(self, value: PluginStatus):
        """设置插件状态"""
        self._status = value
    
    @property
    def api(self) -> Optional['PluginAPI']:
        """获取API接口"""
        return self._api
    
    @property
    def event_bus(self) -> Optional['EventBus']:
        """获取事件总线"""
        return self._event_bus


class UIPluginInterface(PluginInterface):
    """
    UI插件接口
    提供UI相关的额外方法
    """
    
    @abstractmethod
    def create_ui(self, parent_window) -> Any:
        """
        创建插件UI组件
        
        Args:
            parent_window: 父窗口
            
        Returns:
            UI组件对象（如QWidget）
        """
        pass
    
    @abstractmethod
    def get_menu_items(self) -> list:
        """
        获取菜单项配置
        
        Returns:
            菜单项列表，格式: [{'text': '菜单名', 'callback': 回调函数}, ...]
        """
        pass
    
    def get_toolbar_actions(self) -> list:
        """
        获取工具栏动作
        
        Returns:
            工具栏动作列表
        """
        return []


class ServicePluginInterface(PluginInterface):
    """
    服务插件接口
    用于后台服务、数据处理等无UI插件
    """
    
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
