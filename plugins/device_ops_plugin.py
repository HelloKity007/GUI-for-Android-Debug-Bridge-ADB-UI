"""
设备操作插件
将设备操作功能插件化
"""
from typing import Dict, Any, List
import os
from datetime import datetime

from framework.plugin.plugin_interface import UIPluginInterface, PluginMetadata
from framework.event.event_bus import EventBus


class DeviceOpsPlugin(UIPluginInterface):
    """设备操作插件 - 提供截图、重启等操作功能"""
    
    def __init__(self):
        self._metadata = PluginMetadata(
            id="device_ops",
            name="设备操作",
            version="1.0.0",
            author="ADB Tool Team",
            description="设备操作功能：截图、重启、关机等"
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
    
    # === 设备操作功能 ===
    
    def take_screenshot(self, save_path: str = None) -> Dict[str, Any]:
        """截图"""
        if not self._api:
            return {'success': False, 'error': 'Plugin not loaded'}
        
        # 默认保存路径
        if not save_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = f'/sdcard/screenshot_{timestamp}.png'
        
        # 截图到设备
        result = self._api.adb_execute_command(
            f'shell screencap -p "{save_path}"'
        )
        
        if result.get('success'):
            self._event_bus.publish(
                'device.screenshot_taken',
                {'path': save_path}
            )
        
        return result
    
    def pull_screenshot(self, local_dir: str = None) -> Dict[str, Any]:
        """截图并拉取到本地"""
        if not self._api:
            return {'success': False, 'error': 'Plugin not loaded'}
        
        # 截图
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        remote_path = f'/sdcard/screenshot_{timestamp}.png'
        
        result = self.take_screenshot(remote_path)
        if not result.get('success'):
            return result
        
        # 拉取到本地
        if not local_dir:
            local_dir = os.path.expanduser('~/Pictures')
        os.makedirs(local_dir, exist_ok=True)
        
        local_path = os.path.join(local_dir, f'screenshot_{timestamp}.png')
        
        result = self._api.adb_execute_command(
            f'pull "{remote_path}" "{local_path}"'
        )
        
        if result.get('success'):
            # 删除设备上的截图
            self._api.adb_execute_command(f'shell rm "{remote_path}"')
            
            return {
                'success': True,
                'local_path': local_path
            }
        
        return result
    
    def reboot(self) -> Dict[str, Any]:
        """重启设备"""
        if not self._api:
            return {'success': False, 'error': 'Plugin not loaded'}
        
        result = self._api.adb_execute_command('reboot')
        
        if result.get('success'):
            self._event_bus.publish('device.reboot', {})
        
        return result
    
    def reboot_recovery(self) -> Dict[str, Any]:
        """重启到Recovery"""
        if not self._api:
            return {'success': False, 'error': 'Plugin not loaded'}
        
        return self._api.adb_execute_command('reboot recovery')
    
    def reboot_bootloader(self) -> Dict[str, Any]:
        """重启到Bootloader"""
        if not self._api:
            return {'success': False, 'error': 'Plugin not loaded'}
        
        return self._api.adb_execute_command('reboot bootloader')
    
    def shutdown(self) -> Dict[str, Any]:
        """关机"""
        if not self._api:
            return {'success': False, 'error': 'Plugin not loaded'}
        
        return self._api.adb_execute_command('shell reboot -p')
    
    def get_device_info(self) -> Dict[str, str]:
        """获取设备信息"""
        if not self._api:
            return {}
        
        info = {}
        props = [
            ('model', 'ro.product.model'),
            ('brand', 'ro.product.brand'),
            ('android_version', 'ro.build.version.release'),
            ('sdk_version', 'ro.build.version.sdk'),
            ('device', 'ro.product.device'),
        ]
        
        for key, prop in props:
            result = self._api.adb_execute_command(f'shell getprop {prop}')
            if result.get('success'):
                info[key] = result['stdout'].strip()
        
        return info
    
    def get_battery_info(self) -> Dict[str, str]:
        """获取电池信息"""
        if not self._api:
            return {}
        
        result = self._api.adb_execute_command('shell dumpsys battery')
        
        info = {}
        if result.get('success'):
            output = result['stdout']
            
            # 解析电量
            level_match = __import__('re').search(r'level: (\d+)', output)
            if level_match:
                info['level'] = level_match.group(1)
            
            # 解析状态
            status_match = __import__('re').search(r'status: (\d+)', output)
            if status_match:
                status_map = {
                    '1': 'Unknown',
                    '2': 'Charging',
                    '3': 'Discharging',
                    '4': 'Not charging',
                    '5': 'Full'
                }
                info['status'] = status_map.get(status_match.group(1), 'Unknown')
        
        return info
    
    # === UI接口 ===
    
    def create_ui(self, parent_window) -> Any:
        """创建插件UI"""
        return None
    
    def get_menu_items(self) -> List[Dict[str, Any]]:
        """获取菜单项"""
        return [
            {
                'menu': 'Tools',
                'label': 'Take Screenshot',
                'callback': self._take_screenshot,
                'icon': '📸'
            },
            {
                'menu': 'Device',
                'label': 'Reboot',
                'callback': self._reboot_device,
                'icon': '🔄'
            }
        ]
    
    def _take_screenshot(self):
        """截图回调"""
        result = self.pull_screenshot()
        if result.get('success'):
            self._event_bus.publish(
                'ui.show_message',
                {'message': f'Screenshot saved to: {result["local_path"]}', 'type': 'success'}
            )
    
    def _reboot_device(self):
        """重启回调"""
        self.reboot()
