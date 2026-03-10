# -*- coding: utf-8 -*-
"""
Configuration Manager - JSON配置管理器
支持点号路径、自动保存、备份恢复、线程安全
"""
import json
import os
import shutil
import threading
from typing import Any, Dict, Optional
from datetime import datetime
from pathlib import Path


class ConfigManager:
    """
    JSON配置管理器
    
    特性:
    - 支持点号路径访问 (如 "app.name")
    - 自动保存选项
    - 备份和恢复
    - 线程安全
    - Schema验证
    - 相对/绝对路径转换
    """
    
    # 默认配置模板
    DEFAULT_CONFIG = {
        "app": {
            "name": "ADB Tool",
            "version": "2.0.0",
            "dark_mode": False,
            "language": "zh_CN"
        },
        "adb": {
            "auto_refresh_devices": True,
            "refresh_interval": 5
        },
        "extensions": {
            "directory": "extensions",
            "items": {
                "adb": {
                    "path": "extensions/android-tools-win-v34/adb.exe",
                    "enabled": True,
                    "description": "Android调试桥"
                },
                "scrcpy": {
                    "path": "extensions/scrcpy-win64-v3.3.3/scrcpy.exe",
                    "enabled": True,
                    "description": "Android屏幕投屏"
                },
                "jadx": {
                    "path": "extensions/jadx_decompiler/jadx-gui-dev.exe",
                    "enabled": True,
                    "description": "APK反编译工具"
                },
                "awesome_adb": {
                    "path": "extensions/awesome-adb-readme/README.md",
                    "enabled": True,
                    "description": "ADB命令手册"
                }
            },
            "plugins": {
                "directory": "plugins",
                "auto_load": True,
                "enabled": [],
                "disabled": []
            }
        },
        "ui": {
            "window_size": [1200, 800],
            "window_position": [100, 100],
            "log_level": "INFO"
        }
    }
    
    def __init__(self, config_file: str, auto_save: bool = False):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径
            auto_save: 是否自动保存
        """
        self.config_file = config_file
        self.auto_save = auto_save
        self._config: Dict = {}
        self._lock = threading.RLock()
        self._base_dir = os.path.dirname(os.path.abspath(config_file))
        
        # 加载或创建配置
        self._load()
    
    def _load(self):
        """加载配置文件"""
        with self._lock:
            if os.path.exists(self.config_file):
                try:
                    with open(self.config_file, 'r', encoding='utf-8') as f:
                        loaded_config = json.load(f)
                    
                    # 合并默认配置和加载的配置
                    self._config = self._deep_merge(self._deep_copy(self.DEFAULT_CONFIG), loaded_config)
                except Exception as e:
                    print(f"[ConfigManager] Error loading config: {e}")
                    self._config = self._deep_copy(self.DEFAULT_CONFIG)
            else:
                # 使用默认配置
                self._config = self._deep_copy(self.DEFAULT_CONFIG)
                self.save()
    
    def save(self):
        """保存配置到文件"""
        with self._lock:
            try:
                # 确保目录存在
                os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
                
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(self._config, f, indent=2, ensure_ascii=False)
                return True
            except Exception as e:
                print(f"[ConfigManager] Error saving config: {e}")
                return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值（支持点号路径）
        
        Args:
            key: 配置键，支持点号分隔的路径
            default: 默认值
            
        Returns:
            配置值
        """
        with self._lock:
            keys = key.split('.')
            value = self._config
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            
            return value
    
    def set(self, key: str, value: Any):
        """
        设置配置值（支持点号路径）
        
        Args:
            key: 配置键
            value: 配置值
        """
        with self._lock:
            keys = key.split('.')
            config = self._config
            
            # 导航到最后一级的父节点
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            
            # 设置值
            config[keys[-1]] = value
            
            # 自动保存
            if self.auto_save:
                self.save()
    
    def has(self, key: str) -> bool:
        """
        检查键是否存在
        
        Args:
            key: 配置键
            
        Returns:
            是否存在
        """
        with self._lock:
            keys = key.split('.')
            value = self._config
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return False
            
            return True
    
    def delete(self, key: str):
        """
        删除配置键
        
        Args:
            key: 配置键
        """
        with self._lock:
            keys = key.split('.')
            config = self._config
            
            # 导航到父节点
            for k in keys[:-1]:
                if k not in config:
                    return
                config = config[k]
            
            # 删除键
            if keys[-1] in config:
                del config[keys[-1]]
                
                if self.auto_save:
                    self.save()
    
    def get_section(self, section: str) -> Optional[Dict]:
        """
        获取整个配置节
        
        Args:
            section: 节名称
            
        Returns:
            配置节字典
        """
        value = self.get(section)
        return value if isinstance(value, dict) else None
    
    def update_section(self, section: str, data: Dict):
        """
        更新整个配置节
        
        Args:
            section: 节名称
            data: 新数据
        """
        self.set(section, data)
    
    def merge(self, new_config: Dict):
        """
        合并新配置（深度合并）
        
        Args:
            new_config: 新配置字典
        """
        with self._lock:
            self._config = self._deep_merge(self._config, new_config)
            
            if self.auto_save:
                self.save()
    
    def reset(self):
        """重置为默认配置"""
        with self._lock:
            self._config = self._deep_copy(self.DEFAULT_CONFIG)
            self.save()
    
    def _deep_copy(self, obj):
        """深度复制"""
        if isinstance(obj, dict):
            return {k: self._deep_copy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._deep_copy(item) for item in obj]
        else:
            return obj
    def backup(self, backup_dir: Optional[str] = None) -> str:
        """
        备份当前配置
        
        Args:
            backup_dir: 备份目录（默认为配置文件同目录）
            
        Returns:
            备份文件路径
        """
        if backup_dir is None:
            backup_dir = os.path.dirname(self.config_file)
        
        # 先保存当前配置
        self.save()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(
            backup_dir,
            f"config_backup_{timestamp}.json"
        )
        
        with self._lock:
            shutil.copy2(self.config_file, backup_file)
        
        return backup_file
    
    def restore(self, backup_file: str) -> bool:
        """
        从备份恢复配置
        
        Args:
            backup_file: 备份文件路径
            
        Returns:
            是否成功
        """
        if not os.path.exists(backup_file):
            return False
        
        try:
            with self._lock:
                shutil.copy2(backup_file, self.config_file)
                self._load()
            return True
        except Exception as e:
            print(f"[ConfigManager] Error restoring from backup: {e}")
            return False
    
    def validate(self, schema: Dict) -> bool:
        """
        验证配置是否符合Schema
        
        Args:
            schema: Schema定义
            
        Returns:
            是否有效
        """
        with self._lock:
            return self._validate_recursive(self._config, schema)
    
    def get_absolute_path(self, key: str, base_dir: Optional[str] = None) -> Optional[str]:
        """
        获取绝对路径（自动转换相对路径）
        
        Args:
            key: 配置键
            base_dir: 基础目录（默认为配置文件目录）
            
        Returns:
            绝对路径
        """
        path = self.get(key)
        if not path:
            return None
        
        if os.path.isabs(path):
            return path
        
        if base_dir is None:
            base_dir = self._base_dir
        
        return os.path.abspath(os.path.join(base_dir, path))
    
    def to_dict(self) -> Dict:
        """返回配置字典的副本"""
        with self._lock:
            return self._config.copy()
    
    # 辅助方法
    
    def _deep_merge(self, base: Dict, update: Dict) -> Dict:
        """深度合并字典"""
        result = base.copy()
        
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _validate_recursive(self, config: Any, schema: Any) -> bool:
        """递归验证配置"""
        if isinstance(schema, dict):
            if not isinstance(config, dict):
                return False
            
            for key, expected_type in schema.items():
                if key not in config:
                    return False
                
                if isinstance(expected_type, dict):
                    if not self._validate_recursive(config[key], expected_type):
                        return False
                elif isinstance(expected_type, type):
                    if not isinstance(config[key], expected_type):
                        return False
        
        return True
    
    # ==================== 扩展配置便捷方法 ====================
    
    def get_extension_path(self, name: str, project_dir: str = '') -> str:
        """
        获取扩展的绝对路径
        
        Args:
            name: 扩展名称 (如 'adb', 'scrcpy', 'jadx', 'awesome_adb')
            project_dir: 项目根目录，用于转换相对路径
            
        Returns:
            绝对路径，如果未配置返回空字符串
        """
        path = self.get(f'extensions.items.{name}.path', '')
        if path and project_dir and not os.path.isabs(path):
            return os.path.normpath(os.path.join(project_dir, path))
        return path
    
    def set_extension_path(self, name: str, path: str, project_dir: str = '') -> None:
        """
        设置扩展路径（自动转为相对路径）
        
        Args:
            name: 扩展名称
            path: 绝对路径或相对路径
            project_dir: 项目根目录
        """
        if path and project_dir and os.path.isabs(path):
            path = os.path.relpath(path, project_dir)
        self.set(f'extensions.items.{name}.path', path)
    
    def is_extension_enabled(self, name: str) -> bool:
        """检查扩展是否启用"""
        return self.get(f'extensions.items.{name}.enabled', False)
    
    def set_extension_enabled(self, name: str, enabled: bool) -> None:
        """设置扩展启用状态"""
        self.set(f'extensions.items.{name}.enabled', enabled)
    
    def get_extension_description(self, name: str) -> str:
        """获取扩展描述"""
        return self.get(f'extensions.items.{name}.description', '')
    
    def get_all_extensions(self) -> Dict[str, Dict]:
        """获取所有扩展配置"""
        return self.get('extensions.items', {})
