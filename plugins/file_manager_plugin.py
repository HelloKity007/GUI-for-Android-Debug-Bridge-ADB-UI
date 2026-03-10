"""
文件管理插件
将文件管理功能插件化
"""
from typing import Dict, Any, List, Optional
import os

from framework.plugin.plugin_interface import UIPluginInterface, PluginMetadata
from framework.event.event_bus import EventBus


class FileManagerPlugin(UIPluginInterface):
    """文件管理插件 - 提供文件传输和管理功能"""
    
    def __init__(self):
        self._metadata = PluginMetadata(
            id="file_manager",
            name="文件管理器",
            version="1.0.0",
            author="ADB Tool Team",
            description="文件传输和管理功能，支持Push/Pull/浏览"
        )
        self._api = None
        self._event_bus = None
        self._current_path = '/sdcard'
    
    def get_metadata(self) -> PluginMetadata:
        """获取插件元数据"""
        return self._metadata
    
    def on_load(self, api, event_bus: EventBus) -> bool:
        """插件加载"""
        self._api = api
        self._event_bus = event_bus
        
        # 订阅相关事件
        self._event_bus.subscribe('device.selected', self._on_device_selected)
        
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
    
    def _on_device_selected(self, event):
        """设备选择事件处理"""
        device = event.data.get('device')
        if device:
            self._current_path = '/sdcard'
    
    # === 文件操作功能 ===
    
    def list_files(self, path: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出目录内容"""
        if not self._api:
            return []
        
        target_path = path or self._current_path
        
        result = self._api.adb_execute_command(
            f'shell ls -la "{target_path}"'
        )
        
        files = []
        if result.get('success'):
            lines = result['stdout'].strip().split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split(None, 7)
                if len(parts) >= 8:
                    name = parts[7]
                    if name in ('.', '..'):
                        continue
                    
                    files.append({
                        'name': name,
                        'permissions': parts[0],
                        'is_dir': parts[0].startswith('d'),
                        'owner': parts[2] if len(parts) > 2 else '',
                        'size': parts[4] if len(parts) > 4 else '',
                        'path': f"{target_path}/{name}".replace('//', '/')
                    })
        
        return files
    
    def push_file(self, local_path: str, remote_path: str) -> Dict[str, Any]:
        """推送文件到设备"""
        if not self._api:
            return {'success': False, 'error': 'Plugin not loaded'}
        
        result = self._api.adb_execute_command(
            f'push "{local_path}" "{remote_path}"'
        )
        
        if result.get('success'):
            self._event_bus.publish(
                'file.pushed',
                {'local_path': local_path, 'remote_path': remote_path}
            )
        
        return result
    
    def pull_file(self, remote_path: str, local_path: str) -> Dict[str, Any]:
        """从设备拉取文件"""
        if not self._api:
            return {'success': False, 'error': 'Plugin not loaded'}
        
        result = self._api.adb_execute_command(
            f'pull "{remote_path}" "{local_path}"'
        )
        
        if result.get('success'):
            self._event_bus.publish(
                'file.pulled',
                {'remote_path': remote_path, 'local_path': local_path}
            )
        
        return result
    
    def delete_file(self, remote_path: str) -> Dict[str, Any]:
        """删除文件"""
        if not self._api:
            return {'success': False, 'error': 'Plugin not loaded'}
        
        result = self._api.adb_execute_command(
            f'shell rm -rf "{remote_path}"'
        )
        
        return result
    
    def create_directory(self, path: str) -> Dict[str, Any]:
        """创建目录"""
        if not self._api:
            return {'success': False, 'error': 'Plugin not loaded'}
        
        result = self._api.adb_execute_command(
            f'shell mkdir -p "{path}"'
        )
        
        return result
    
    # === UI接口 ===
    
    def create_ui(self, parent_window) -> Any:
        """创建插件UI"""
        # 返回None，使用菜单触发
        return None
    
    def get_menu_items(self) -> List[Dict[str, Any]]:
        """获取菜单项"""
        return [
            {
                'menu': 'Tools',
                'label': 'File Manager',
                'callback': self._show_file_manager,
                'icon': '📁'
            }
        ]
    
    def _show_file_manager(self):
        """显示文件管理器"""
        # 发布事件让主程序显示对话框
        self._event_bus.publish(
            'ui.show_dialog',
            {'dialog_type': 'file_manager', 'plugin_id': self._metadata.id}
        )
