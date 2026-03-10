"""
应用管理插件
将应用管理功能插件化
"""
from typing import Dict, Any, List
import re

from framework.plugin.plugin_interface import UIPluginInterface, PluginMetadata
from framework.event.event_bus import EventBus


class AppManagerPlugin(UIPluginInterface):
    """应用管理插件 - 提供应用安装/卸载/管理功能"""
    
    def __init__(self):
        self._metadata = PluginMetadata(
            id="app_manager",
            name="应用管理器",
            version="1.0.0",
            author="ADB Tool Team",
            description="应用安装、卸载、启用/禁用管理功能"
        )
        self._api = None
        self._event_bus = None
    
    def get_metadata(self) -> PluginMetadata:
        """获取插件元数据"""
        return self._metadata
    
    def on_load(self, api, event_bus: EventBus) -> bool:
        """插件加载"""
        self._api = api
        self._event_bus = event_bus
        return True
    
    def on_unload(self) -> bool:
        """插件卸载"""
        self._api = None
        self._event_bus = None
        return True
    
    def on_enable(self) -> bool:
        """插件启用"""
        return True
    
    def on_disable(self) -> bool:
        """插件禁用"""
        return True
    
    # === 应用操作功能 ===
    
    def list_apps(self, system_apps: bool = False) -> List[Dict[str, Any]]:
        """列出已安装应用"""
        if not self._api:
            return []
        
        cmd = 'shell pm list packages'
        if not system_apps:
            cmd += ' -3'  # 只显示第三方应用
        
        result = self._api.adb_execute_command(cmd)
        
        apps = []
        if result.get('success'):
            lines = result['stdout'].strip().split('\n')
            for line in lines:
                if line.startswith('package:'):
                    package = line[8:]
                    apps.append({
                        'package': package,
                        'name': package.split('.')[-1]
                    })
        
        return apps
    
    def install_app(self, apk_path: str) -> Dict[str, Any]:
        """安装APK"""
        if not self._api:
            return {'success': False, 'error': 'Plugin not loaded'}
        
        result = self._api.adb_execute_command(f'install "{apk_path}"')
        
        success = result.get('success') and 'Success' in result.get('stdout', '')
        
        if success:
            self._event_bus.publish(
                'app.installed',
                {'apk_path': apk_path}
            )
        
        return {
            'success': success,
            'output': result.get('stdout', ''),
            'error': result.get('stderr', '')
        }
    
    def uninstall_app(self, package_name: str, keep_data: bool = False) -> Dict[str, Any]:
        """卸载应用"""
        if not self._api:
            return {'success': False, 'error': 'Plugin not loaded'}
        
        cmd = 'uninstall'
        if keep_data:
            cmd += ' -k'
        cmd += f' {package_name}'
        
        result = self._api.adb_execute_command(cmd)
        
        success = result.get('success') and 'Success' in result.get('stdout', '')
        
        if success:
            self._event_bus.publish(
                'app.uninstalled',
                {'package': package_name}
            )
        
        return {
            'success': success,
            'output': result.get('stdout', ''),
            'error': result.get('stderr', '')
        }
    
    def disable_app(self, package_name: str) -> Dict[str, Any]:
        """禁用应用"""
        if not self._api:
            return {'success': False, 'error': 'Plugin not loaded'}
        
        result = self._api.adb_execute_command(
            f'shell pm disable-user --user 0 {package_name}'
        )
        
        return result
    
    def enable_app(self, package_name: str) -> Dict[str, Any]:
        """启用应用"""
        if not self._api:
            return {'success': False, 'error': 'Plugin not loaded'}
        
        result = self._api.adb_execute_command(
            f'shell pm enable --user 0 {package_name}'
        )
        
        return result
    
    def get_app_info(self, package_name: str) -> Dict[str, Any]:
        """获取应用信息"""
        if not self._api:
            return {}
        
        result = self._api.adb_execute_command(
            f'shell dumpsys package {package_name}'
        )
        
        info = {'package': package_name}
        
        if result.get('success'):
            output = result['stdout']
            
            # 解析版本号
            version_match = re.search(r'versionName=([^\s]+)', output)
            if version_match:
                info['version'] = version_match.group(1)
            
            # 解析首次安装时间
            first_install_match = re.search(r'firstInstallTime=([^\n]+)', output)
            if first_install_match:
                info['first_install'] = first_install_match.group(1).strip()
            
            # 解析最后更新时间
            last_update_match = re.search(r'lastUpdateTime=([^\n]+)', output)
            if last_update_match:
                info['last_update'] = last_update_match.group(1).strip()
        
        return info
    
    def clear_app_data(self, package_name: str) -> Dict[str, Any]:
        """清除应用数据"""
        if not self._api:
            return {'success': False, 'error': 'Plugin not loaded'}
        
        result = self._api.adb_execute_command(
            f'shell pm clear {package_name}'
        )
        
        return result
    
    # === UI接口 ===
    
    def create_ui(self, parent_window) -> Any:
        """创建插件UI"""
        return None
    
    def get_menu_items(self) -> List[Dict[str, Any]]:
        """获取菜单项"""
        return [
            {
                'menu': 'Tools',
                'label': 'App Manager',
                'callback': self._show_app_manager,
                'icon': '📱'
            }
        ]
    
    def _show_app_manager(self):
        """显示应用管理器"""
        self._event_bus.publish(
            'ui.show_dialog',
            {'dialog_type': 'app_manager', 'plugin_id': self._metadata.id}
        )
