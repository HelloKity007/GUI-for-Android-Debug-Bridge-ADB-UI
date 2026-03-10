# -*- coding: utf-8 -*-
"""
Plugin API - 插件API接口层
向插件暴露主程序能力，实现权限控制
"""
from typing import Dict, Any, List, Optional, Callable
from core import ADBManager, ScrcpyManager


class PluginAPI:
    """
    插件API接口
    封装主程序功能，提供给插件使用
    实现权限控制和安全隔离
    """
    
    def __init__(self, adb_manager: ADBManager, scrcpy_manager: ScrcpyManager, 
                 config_manager: Any, event_bus: Any):
        """
        初始化插件API
        
        Args:
            adb_manager: ADB管理器
            scrcpy_manager: Scrcpy管理器
            config_manager: 配置管理器
            event_bus: 事件总线
        """
        self._adb = adb_manager
        self._scrcpy = scrcpy_manager
        self._config = config_manager
        self._event_bus = event_bus
        self._permissions: Dict[str, List[str]] = {}  # 插件ID -> 权限列表
        
        # API版本
        self.version = "1.0.0"
    
    # ==================== 权限管理 ====================
    
    def grant_permission(self, plugin_id: str, permission: str):
        """授予插件权限"""
        if plugin_id not in self._permissions:
            self._permissions[plugin_id] = []
        if permission not in self._permissions[plugin_id]:
            self._permissions[plugin_id].append(permission)
    
    def revoke_permission(self, plugin_id: str, permission: str):
        """撤销插件权限"""
        if plugin_id in self._permissions and permission in self._permissions[plugin_id]:
            self._permissions[plugin_id].remove(permission)
    
    def has_permission(self, plugin_id: str, permission: str) -> bool:
        """检查插件是否有某权限"""
        return plugin_id in self._permissions and permission in self._permissions[plugin_id]
    
    def _check_permission(self, plugin_id: str, permission: str):
        """检查权限，无权限抛出异常"""
        if not self.has_permission(plugin_id, permission):
            raise PermissionError(f"Plugin '{plugin_id}' does not have '{permission}' permission")
    
    # ==================== ADB 相关API ====================
    
    def adb_execute_command(self, command: str, timeout: int = 30, 
                           plugin_id: str = None) -> Dict[str, Any]:
        """
        执行ADB命令
        
        Args:
            command: ADB命令
            timeout: 超时时间
            plugin_id: 插件ID（用于权限检查）
            
        Returns:
            命令执行结果
        """
        if plugin_id:
            self._check_permission(plugin_id, "adb.execute")
        
        result = self._adb.run_command(command, timeout)
        
        # 发布事件
        self._event_bus.publish(
            "command.executed",
            {"command": command, "result": result, "plugin": plugin_id}
        )
        
        return result
    
    def adb_get_devices(self, plugin_id: str = None) -> List[Dict[str, Any]]:
        """
        获取连接的设备列表
        
        Returns:
            设备列表
        """
        return self._adb.get_devices(silent=True)
    
    def adb_get_device_info(self, device_id: str, plugin_id: str = None) -> Dict[str, str]:
        """
        获取设备信息
        
        Args:
            device_id: 设备ID
            
        Returns:
            设备信息字典
        """
        return self._adb.get_device_info(device_id)
    
    def adb_install_apk(self, device_id: str, apk_path: str, 
                       plugin_id: str = None) -> Dict[str, Any]:
        """
        安装APK
        
        Args:
            device_id: 设备ID
            apk_path: APK路径
            plugin_id: 插件ID
            
        Returns:
            安装结果
        """
        if plugin_id:
            self._check_permission(plugin_id, "adb.install_apk")
        
        command = f'-s {device_id} install "{apk_path}"'
        return self._adb.run_command(command)
    
    def adb_uninstall_package(self, device_id: str, package_name: str,
                             plugin_id: str = None) -> Dict[str, Any]:
        """
        卸载应用
        
        Args:
            device_id: 设备ID
            package_name: 包名
            plugin_id: 插件ID
            
        Returns:
            卸载结果
        """
        if plugin_id:
            self._check_permission(plugin_id, "adb.uninstall")
        
        command = f'-s {device_id} uninstall {package_name}'
        return self._adb.run_command(command)
    
    def adb_push_file(self, device_id: str, local_path: str, remote_path: str,
                     plugin_id: str = None) -> Dict[str, Any]:
        """
        推送文件到设备
        
        Args:
            device_id: 设备ID
            local_path: 本地路径
            remote_path: 远程路径
            plugin_id: 插件ID
            
        Returns:
            执行结果
        """
        if plugin_id:
            self._check_permission(plugin_id, "adb.file_transfer")
        
        command = f'-s {device_id} push "{local_path}" "{remote_path}"'
        return self._adb.run_command(command)
    
    def adb_pull_file(self, device_id: str, remote_path: str, local_path: str,
                     plugin_id: str = None) -> Dict[str, Any]:
        """
        从设备拉取文件
        
        Args:
            device_id: 设备ID
            remote_path: 远程路径
            local_path: 本地路径
            plugin_id: 插件ID
            
        Returns:
            执行结果
        """
        if plugin_id:
            self._check_permission(plugin_id, "adb.file_transfer")
        
        command = f'-s {device_id} pull "{remote_path}" "{local_path}"'
        return self._adb.run_command(command)
    
    # ==================== Scrcpy 相关API ====================
    
    def scrcpy_is_available(self) -> bool:
        """检查Scrcpy是否可用"""
        return self._scrcpy.is_available()
    
    def scrcpy_get_path(self) -> str:
        """获取Scrcpy路径"""
        return self._scrcpy.scrcpy_path
    
    # ==================== 配置相关API ====================
    
    def config_get(self, section: str, key: str, fallback: Any = None) -> Any:
        """
        获取配置项
        
        Args:
            section: 配置节
            key: 配置键
            fallback: 默认值
            
        Returns:
            配置值
        """
        # 假设config_manager有get方法
        if hasattr(self._config, 'get'):
            return self._config.get(section, key, fallback=fallback)
        return fallback
    
    def config_set(self, section: str, key: str, value: Any, plugin_id: str = None):
        """
        设置配置项（需要权限）
        
        Args:
            section: 配置节
            key: 配置键
            value: 配置值
            plugin_id: 插件ID
        """
        if plugin_id:
            self._check_permission(plugin_id, "config.write")
        
        if hasattr(self._config, 'set'):
            self._config.set(section, key, str(value))
    
    # ==================== 事件相关API ====================
    
    def event_subscribe(self, event_type: str, callback: Callable):
        """
        订阅事件
        
        Args:
            event_type: 事件类型
            callback: 回调函数
        """
        self._event_bus.subscribe(event_type, callback)
    
    def event_unsubscribe(self, event_type: str, callback: Callable):
        """
        取消订阅事件
        
        Args:
            event_type: 事件类型
            callback: 回调函数
        """
        self._event_bus.unsubscribe(event_type, callback)
    
    def event_publish(self, event_type: str, data: Dict[str, Any] = None, 
                     plugin_id: str = None):
        """
        发布事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
            plugin_id: 插件ID
        """
        self._event_bus.publish(event_type, data, source=plugin_id or "plugin")
    
    # ==================== 日志相关API ====================
    
    def log_info(self, message: str, plugin_id: str = None):
        """记录信息日志"""
        prefix = f"[{plugin_id}]" if plugin_id else "[Plugin]"
        print(f"{prefix} INFO: {message}")
    
    def log_warning(self, message: str, plugin_id: str = None):
        """记录警告日志"""
        prefix = f"[{plugin_id}]" if plugin_id else "[Plugin]"
        print(f"{prefix} WARNING: {message}")
    
    def log_error(self, message: str, plugin_id: str = None):
        """记录错误日志"""
        prefix = f"[{plugin_id}]" if plugin_id else "[Plugin]"
        print(f"{prefix} ERROR: {message}")


# 权限常量定义
class Permissions:
    """插件权限定义"""
    
    # ADB权限
    ADB_EXECUTE = "adb.execute"                 # 执行ADB命令
    ADB_INSTALL_APK = "adb.install_apk"        # 安装APK
    ADB_UNINSTALL = "adb.uninstall"            # 卸载应用
    ADB_FILE_TRANSFER = "adb.file_transfer"    # 文件传输
    ADB_SHELL = "adb.shell"                    # Shell命令
    
    # 配置权限
    CONFIG_READ = "config.read"                # 读取配置
    CONFIG_WRITE = "config.write"              # 写入配置
    
    # UI权限
    UI_CREATE_WINDOW = "ui.create_window"      # 创建窗口
    UI_SHOW_DIALOG = "ui.show_dialog"          # 显示对话框
    UI_ADD_MENU = "ui.add_menu"                # 添加菜单
    
    # 系统权限
    SYSTEM_FILE_ACCESS = "system.file_access"  # 文件系统访问
    SYSTEM_NETWORK = "system.network"          # 网络访问
