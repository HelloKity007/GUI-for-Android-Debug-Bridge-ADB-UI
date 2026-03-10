# -*- coding: utf-8 -*-
"""
Plugin Framework - 插件系统核心模块
"""
from .plugin_interface import (
    PluginInterface, 
    PluginMetadata, 
    PluginStatus,
    UIPluginInterface,
    ServicePluginInterface
)
from .plugin_manager import PluginManager
from .plugin_api import PluginAPI

__all__ = [
    'PluginInterface', 
    'PluginMetadata', 
    'PluginStatus', 
    'UIPluginInterface',
    'ServicePluginInterface',
    'PluginManager', 
    'PluginAPI'
]
