"""
文件管理插件单元测试
TDD方式开发
"""
import unittest
import sys
import os
from unittest.mock import Mock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from framework.plugin.plugin_interface import UIPluginInterface, PluginMetadata
from framework.event.event_bus import EventBus, EventTypes


class TestFileManagerPlugin(unittest.TestCase):
    """文件管理插件测试"""
    
    def setUp(self):
        self.event_bus = EventBus()
        self.api = Mock()
        self.api.has_permission.return_value = True
        
    def test_plugin_metadata(self):
        """测试插件元数据"""
        from plugins.file_manager_plugin import FileManagerPlugin
        
        plugin = FileManagerPlugin()
        metadata = plugin.get_metadata()
        
        self.assertEqual(metadata.id, 'file_manager')
        self.assertEqual(metadata.name, '文件管理器')
        self.assertIsNotNone(metadata.version)
    
    def test_plugin_lifecycle(self):
        """测试插件生命周期"""
        from plugins.file_manager_plugin import FileManagerPlugin
        
        plugin = FileManagerPlugin()
        
        # 加载
        result = plugin.on_load(self.api, self.event_bus)
        self.assertTrue(result)
        
        # 启用
        result = plugin.on_enable()
        self.assertTrue(result)
        
        # 禁用
        result = plugin.on_disable()
        self.assertTrue(result)
        
        # 卸载
        result = plugin.on_unload()
        self.assertTrue(result)
    
    def test_file_operations(self):
        """测试文件操作"""
        from plugins.file_manager_plugin import FileManagerPlugin
        
        plugin = FileManagerPlugin()
        plugin.on_load(self.api, self.event_bus)
        
        # 模拟API返回
        self.api.adb_execute_command.return_value = {
            'success': True,
            'stdout': 'drwxrwx--- 2 root sdcard_rw 4096 2024-01-01 DCIM'
        }
        
        # 列出目录
        files = plugin.list_files('/sdcard')
        self.assertIsInstance(files, list)
        
        # 推送文件
        self.api.adb_execute_command.return_value = {'success': True}
        result = plugin.push_file('/local/file.txt', '/sdcard/file.txt')
        self.assertTrue(result['success'])
        
        # 拉取文件
        result = plugin.pull_file('/sdcard/file.txt', '/local/file.txt')
        self.assertTrue(result['success'])
    
    def test_menu_items(self):
        """测试菜单项"""
        from plugins.file_manager_plugin import FileManagerPlugin
        
        plugin = FileManagerPlugin()
        menu_items = plugin.get_menu_items()
        
        self.assertIsInstance(menu_items, list)
        self.assertGreater(len(menu_items), 0)


class TestAppManagerPlugin(unittest.TestCase):
    """应用管理插件测试"""
    
    def setUp(self):
        self.event_bus = EventBus()
        self.api = Mock()
        self.api.has_permission.return_value = True
    
    def test_plugin_metadata(self):
        """测试插件元数据"""
        from plugins.app_manager_plugin import AppManagerPlugin
        
        plugin = AppManagerPlugin()
        metadata = plugin.get_metadata()
        
        self.assertEqual(metadata.id, 'app_manager')
        self.assertEqual(metadata.name, '应用管理器')
    
    def test_app_operations(self):
        """测试应用操作"""
        from plugins.app_manager_plugin import AppManagerPlugin
        
        plugin = AppManagerPlugin()
        plugin.on_load(self.api, self.event_bus)
        
        # 模拟API返回
        self.api.adb_execute_command.return_value = {
            'success': True,
            'stdout': 'package:com.android.settings'
        }
        
        # 列出应用
        apps = plugin.list_apps()
        self.assertIsInstance(apps, list)
        
        # 安装应用
        self.api.adb_execute_command.return_value = {
            'success': True,
            'stdout': 'Success'
        }
        result = plugin.install_app('/path/to/app.apk')
        self.assertTrue(result['success'])
        
        # 卸载应用
        result = plugin.uninstall_app('com.example.app')
        self.assertTrue(result['success'])


class TestDeviceOpsPlugin(unittest.TestCase):
    """设备操作插件测试"""
    
    def setUp(self):
        self.event_bus = EventBus()
        self.api = Mock()
        self.api.has_permission.return_value = True
    
    def test_plugin_metadata(self):
        """测试插件元数据"""
        from plugins.device_ops_plugin import DeviceOpsPlugin
        
        plugin = DeviceOpsPlugin()
        metadata = plugin.get_metadata()
        
        self.assertEqual(metadata.id, 'device_ops')
        self.assertEqual(metadata.name, '设备操作')
    
    def test_device_operations(self):
        """测试设备操作"""
        from plugins.device_ops_plugin import DeviceOpsPlugin
        
        plugin = DeviceOpsPlugin()
        plugin.on_load(self.api, self.event_bus)
        
        # 模拟API返回
        self.api.adb_execute_command.return_value = {'success': True}
        
        # 截图
        result = plugin.take_screenshot('/sdcard/screenshot.png')
        self.assertTrue(result['success'])
        
        # 重启
        result = plugin.reboot()
        self.assertTrue(result['success'])
        
        # 重启到recovery
        result = plugin.reboot_recovery()
        self.assertTrue(result['success'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
