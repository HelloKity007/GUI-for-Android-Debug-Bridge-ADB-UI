# -*- coding: utf-8 -*-
"""
Plugin Manager - 插件管理器
负责插件的加载、卸载和生命周期管理
"""
import os
import sys
import importlib
import importlib.util
from typing import Dict, List, Optional, Type
from pathlib import Path
import json
import threading

from .plugin_interface import PluginInterface, PluginMetadata, PluginStatus
from .plugin_api import PluginAPI
from framework.event import EventBus, EventTypes


class PluginManager:
    """
    插件管理器
    实现插件的动态加载、卸载和生命周期管理
    """
    
    def __init__(self, plugin_dirs: List[str], api: PluginAPI, event_bus: EventBus):
        """
        初始化插件管理器
        
        Args:
            plugin_dirs: 插件目录列表
            api: 插件API接口
            event_bus: 事件总线
        """
        self.plugin_dirs = plugin_dirs
        self.api = api
        self.event_bus = event_bus
        
        self._plugins: Dict[str, PluginInterface] = {}  # plugin_id -> plugin_instance
        self._plugin_modules: Dict[str, any] = {}       # plugin_id -> module
        self._lock = threading.RLock()
        
        # 插件配置文件路径
        self._config_file = os.path.join(plugin_dirs[0] if plugin_dirs else ".", "plugins_config.json")
        self._load_plugin_config()
    
    def _load_plugin_config(self):
        """加载插件配置"""
        self._plugin_config = {}
        if os.path.exists(self._config_file):
            try:
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    self._plugin_config = json.load(f)
            except Exception as e:
                print(f"[PluginManager] Failed to load plugin config: {e}")
    
    def _save_plugin_config(self):
        """保存插件配置"""
        try:
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(self._plugin_config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[PluginManager] Failed to save plugin config: {e}")
    
    def discover_plugins(self) -> List[str]:
        """
        发现所有可用插件
        
        Returns:
            插件文件路径列表
        """
        plugin_files = []
        
        for plugin_dir in self.plugin_dirs:
            if not os.path.exists(plugin_dir):
                continue
            
            for item in os.listdir(plugin_dir):
                item_path = os.path.join(plugin_dir, item)
                
                # 检查Python文件
                if item.endswith('.py') and not item.startswith('_'):
                    plugin_files.append(item_path)
                
                # 检查插件目录（包含__init__.py）
                elif os.path.isdir(item_path):
                    init_file = os.path.join(item_path, '__init__.py')
                    if os.path.exists(init_file):
                        plugin_files.append(item_path)
        
        return plugin_files
    
    def load_plugin(self, plugin_path: str) -> bool:
        """
        加载单个插件
        
        Args:
            plugin_path: 插件路径
            
        Returns:
            是否加载成功
        """
        try:
            # 动态导入模块
            module_name = self._get_module_name(plugin_path)
            spec = importlib.util.spec_from_file_location(module_name, plugin_path)
            if spec is None or spec.loader is None:
                print(f"[PluginManager] Failed to load plugin spec: {plugin_path}")
                return False
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # 查找插件类
            plugin_class = self._find_plugin_class(module)
            if plugin_class is None:
                print(f"[PluginManager] No plugin class found in: {plugin_path}")
                return False
            
            # 实例化插件
            plugin_instance: PluginInterface = plugin_class()
            metadata = plugin_instance.get_metadata()
            
            # 检查依赖
            if not self._check_dependencies(metadata):
                print(f"[PluginManager] Plugin dependencies not met: {metadata.id}")
                return False
            
            # 加载插件
            with self._lock:
                plugin_instance.status = PluginStatus.LOADING
                
                if not plugin_instance.on_load(self.api, self.event_bus):
                    print(f"[PluginManager] Plugin on_load failed: {metadata.id}")
                    return False
                
                plugin_instance._api = self.api
                plugin_instance._event_bus = self.event_bus
                plugin_instance.status = PluginStatus.LOADED
                
                self._plugins[metadata.id] = plugin_instance
                self._plugin_modules[metadata.id] = module
            
            # 自动启用（如果配置允许）
            if self._plugin_config.get(metadata.id, {}).get('enabled', metadata.enabled):
                self.enable_plugin(metadata.id)
            
            # 发布事件
            self.event_bus.publish(EventTypes.PLUGIN_LOADED, {
                'plugin_id': metadata.id,
                'plugin_name': metadata.name,
                'version': metadata.version
            })
            
            print(f"[PluginManager] Plugin loaded: {metadata.name} v{metadata.version}")
            return True
            
        except Exception as e:
            print(f"[PluginManager] Error loading plugin {plugin_path}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def unload_plugin(self, plugin_id: str) -> bool:
        """
        卸载插件
        
        Args:
            plugin_id: 插件ID
            
        Returns:
            是否卸载成功
        """
        with self._lock:
            if plugin_id not in self._plugins:
                return False
            
            plugin = self._plugins[plugin_id]
            
            # 先禁用
            if plugin.status == PluginStatus.RUNNING:
                self.disable_plugin(plugin_id)
            
            # 调用卸载钩子
            try:
                plugin.on_unload()
            except Exception as e:
                print(f"[PluginManager] Error unloading plugin {plugin_id}: {e}")
            
            # 移除插件
            plugin.status = PluginStatus.UNLOADED
            del self._plugins[plugin_id]
            
            if plugin_id in self._plugin_modules:
                del self._plugin_modules[plugin_id]
            
            # 发布事件
            self.event_bus.publish(EventTypes.PLUGIN_UNLOADED, {'plugin_id': plugin_id})
            
            print(f"[PluginManager] Plugin unloaded: {plugin_id}")
            return True
    
    def enable_plugin(self, plugin_id: str) -> bool:
        """启用插件"""
        with self._lock:
            if plugin_id not in self._plugins:
                return False
            
            plugin = self._plugins[plugin_id]
            
            if plugin.status == PluginStatus.RUNNING:
                return True
            
            try:
                if plugin.on_enable():
                    plugin.status = PluginStatus.RUNNING
                    
                    # 保存状态
                    if plugin_id not in self._plugin_config:
                        self._plugin_config[plugin_id] = {}
                    self._plugin_config[plugin_id]['enabled'] = True
                    self._save_plugin_config()
                    
                    # 发布事件
                    self.event_bus.publish(EventTypes.PLUGIN_ENABLED, {'plugin_id': plugin_id})
                    
                    return True
            except Exception as e:
                print(f"[PluginManager] Error enabling plugin {plugin_id}: {e}")
                plugin.status = PluginStatus.ERROR
                return False
        
        return False
    
    def disable_plugin(self, plugin_id: str) -> bool:
        """禁用插件"""
        with self._lock:
            if plugin_id not in self._plugins:
                return False
            
            plugin = self._plugins[plugin_id]
            
            try:
                if plugin.on_disable():
                    plugin.status = PluginStatus.STOPPED
                    
                    # 保存状态
                    if plugin_id not in self._plugin_config:
                        self._plugin_config[plugin_id] = {}
                    self._plugin_config[plugin_id]['enabled'] = False
                    self._save_plugin_config()
                    
                    # 发布事件
                    self.event_bus.publish(EventTypes.PLUGIN_DISABLED, {'plugin_id': plugin_id})
                    
                    return True
            except Exception as e:
                print(f"[PluginManager] Error disabling plugin {plugin_id}: {e}")
                return False
        
        return False
    
    def load_all_plugins(self):
        """加载所有发现的插件"""
        plugin_files = self.discover_plugins()
        
        for plugin_file in plugin_files:
            self.load_plugin(plugin_file)
    
    def get_plugin(self, plugin_id: str) -> Optional[PluginInterface]:
        """获取插件实例"""
        return self._plugins.get(plugin_id)
    
    def get_all_plugins(self) -> Dict[str, PluginInterface]:
        """获取所有插件"""
        return self._plugins.copy()
    
    def get_plugin_list(self) -> List[Dict[str, any]]:
        """获取插件列表信息"""
        plugins_info = []
        
        for plugin_id, plugin in self._plugins.items():
            metadata = plugin.get_metadata()
            plugins_info.append({
                'id': metadata.id,
                'name': metadata.name,
                'version': metadata.version,
                'author': metadata.author,
                'description': metadata.description,
                'status': plugin.status.value,
                'enabled': plugin.status == PluginStatus.RUNNING
            })
        
        return plugins_info
    
    def _get_module_name(self, plugin_path: str) -> str:
        """生成模块名"""
        if os.path.isfile(plugin_path):
            return f"plugin_{Path(plugin_path).stem}"
        else:
            return f"plugin_{Path(plugin_path).name}"
    
    def _find_plugin_class(self, module) -> Optional[Type[PluginInterface]]:
        """在模块中查找插件类"""
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and 
                issubclass(attr, PluginInterface) and 
                attr is not PluginInterface):
                return attr
        return None
    
    def _check_dependencies(self, metadata: PluginMetadata) -> bool:
        """检查插件依赖"""
        for dep_id in metadata.dependencies:
            if dep_id not in self._plugins:
                print(f"[PluginManager] Missing dependency: {dep_id}")
                return False
        return True
