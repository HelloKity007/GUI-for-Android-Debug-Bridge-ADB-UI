"""
插件系统集成测试
测试插件与主程序的完整集成
"""
import unittest
import sys
import os
import tempfile
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from framework.plugin.plugin_manager import PluginManager
from framework.plugin.plugin_api import PluginAPI
from framework.event.event_bus import EventBus, EventTypes
from framework.mvp.models import DeviceModel, ADBModel


class TestPluginSystemIntegration(unittest.TestCase):
    """插件系统集成测试"""
    
    def setUp(self):
        self.event_bus = EventBus()
        
        # 创建模拟ADB模型
        self.adb_model = Mock()
        self.adb_model.run_command.return_value = {
            'success': True,
            'stdout': 'test output',
            'stderr': ''
        }
        
        # 创建模拟Scrcpy和Config
        self.scrcpy_model = Mock()
        self.config_manager = Mock()
        
        # 创建PluginAPI
        self.plugin_api = PluginAPI(
            self.adb_model, self.scrcpy_model, 
            self.config_manager, self.event_bus
        )
        
        # 创建PluginManager
        plugins_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'plugins')
        self.plugin_manager = PluginManager([plugins_dir], self.plugin_api, self.event_bus)
    
    def test_plugin_discovery(self):
        """测试插件发现"""
        plugins = self.plugin_manager.discover_plugins()
        
        # 验证发现了插件
        self.assertGreaterEqual(len(plugins), 3)
        
        # 验证包含我们的插件文件
        plugin_names = [os.path.basename(p) for p in plugins]
        self.assertTrue(any('file_manager' in name for name in plugin_names))
        self.assertTrue(any('app_manager' in name for name in plugin_names))
        self.assertTrue(any('device_ops' in name for name in plugin_names))
    
    def test_plugin_load_with_api(self):
        """测试插件加载并注入API"""
        from plugins.file_manager_plugin import FileManagerPlugin
        
        plugin = FileManagerPlugin()
        
        # 加载插件
        result = plugin.on_load(self.plugin_api, self.event_bus)
        self.assertTrue(result)
        
        # 验证API可用
        self.assertIsNotNone(plugin._api)
        self.assertIsNotNone(plugin._event_bus)
    
    def test_plugin_event_subscribe(self):
        """测试插件事件订阅"""
        from plugins.file_manager_plugin import FileManagerPlugin
        
        plugin = FileManagerPlugin()
        plugin.on_load(self.plugin_api, self.event_bus)
        
        # 发布设备选择事件
        self.event_bus.publish(
            'device.selected',
            {'device': {'id': 'test_device'}}
        )
        
        # 验证插件处理了事件（路径重置为/sdcard）
        self.assertEqual(plugin._current_path, '/sdcard')
    
    def test_plugin_permission_check(self):
        """测试插件权限检查"""
        # 授予权限
        self.plugin_api.grant_permission('file_manager', 'adb.execute')
        
        # 验证权限
        self.assertTrue(
            self.plugin_api.has_permission('file_manager', 'adb.execute')
        )
        self.assertFalse(
            self.plugin_api.has_permission('file_manager', 'adb.shell')
        )
    
    def test_plugin_execute_with_permission(self):
        """测试有权限的插件执行命令"""
        from plugins.file_manager_plugin import FileManagerPlugin
        
        plugin = FileManagerPlugin()
        plugin.on_load(self.plugin_api, self.event_bus)
        
        # 授予权限
        self.plugin_api.grant_permission('file_manager', 'adb.execute')
        
        # 执行命令
        result = plugin.list_files('/sdcard')
        
        # 验证命令执行
        self.assertIsInstance(result, list)
        self.adb_model.run_command.assert_called()


class TestPluginWorkflow(unittest.TestCase):
    """插件工作流测试"""
    
    def setUp(self):
        self.event_bus = EventBus()
        self.adb_model = Mock()
        self.adb_model.run_command.return_value = {
            'success': True,
            'stdout': 'test output',
            'stderr': ''
        }
        self.scrcpy_model = Mock()
        self.config_manager = Mock()
        self.plugin_api = PluginAPI(
            self.adb_model, self.scrcpy_model,
            self.config_manager, self.event_bus
        )
    
    def test_file_manager_workflow(self):
        """测试文件管理插件工作流"""
        from plugins.file_manager_plugin import FileManagerPlugin
        
        plugin = FileManagerPlugin()
        
        # 完整生命周期
        plugin.on_load(self.plugin_api, self.event_bus)
        plugin.on_enable()
        
        # 验证插件已加载
        self.assertIsNotNone(plugin._api)
        self.assertIsNotNone(plugin._event_bus)
        
        # 验证可以调用API
        result = plugin.list_files('/sdcard')
        self.assertIsInstance(result, list)
        
        # 禁用和卸载
        plugin.on_disable()
        plugin.on_unload()
    
    def test_app_manager_workflow(self):
        """测试应用管理插件工作流"""
        from plugins.app_manager_plugin import AppManagerPlugin
        
        plugin = AppManagerPlugin()
        
        # 完整生命周期
        plugin.on_load(self.plugin_api, self.event_bus)
        plugin.on_enable()
        
        # 验证插件已加载
        self.assertIsNotNone(plugin._api)
        self.assertIsNotNone(plugin._event_bus)
        
        # 验证可以调用API
        apps = plugin.list_apps()
        self.assertIsInstance(apps, list)
        
        # 禁用和卸载
        plugin.on_disable()
        plugin.on_unload()
    
    def test_device_ops_workflow(self):
        """测试设备操作插件工作流"""
        from plugins.device_ops_plugin import DeviceOpsPlugin
        
        plugin = DeviceOpsPlugin()
        
        # 完整生命周期
        plugin.on_load(self.plugin_api, self.event_bus)
        plugin.on_enable()
        
        # 模拟命令执行
        self.adb_model.execute_command.return_value = {'success': True}
        
        # 截图
        result = plugin.take_screenshot()
        self.assertTrue(result['success'])
        
        # 重启
        result = plugin.reboot()
        self.assertTrue(result['success'])
        
        # 禁用和卸载
        plugin.on_disable()
        plugin.on_unload()


class TestPluginEventPropagation(unittest.TestCase):
    """测试插件事件传播"""
    
    def setUp(self):
        self.event_bus = EventBus()
        self.events_received = []
    
    def test_cross_plugin_events(self):
        """测试跨插件事件"""
        from plugins.file_manager_plugin import FileManagerPlugin
        from plugins.app_manager_plugin import AppManagerPlugin
        
        file_plugin = FileManagerPlugin()
        app_plugin = AppManagerPlugin()
        
        # 订阅文件推送事件
        self.event_bus.subscribe('file.pushed', lambda e: self.events_received.append(e))
        
        # 模拟API
        mock_api = Mock()
        mock_api.adb_execute_command.return_value = {'success': True}
        
        file_plugin.on_load(mock_api, self.event_bus)
        
        # 推送文件
        file_plugin.push_file('/local/test.txt', '/sdcard/test.txt')
        
        # 验证事件传播
        self.assertEqual(len(self.events_received), 1)
        self.assertEqual(self.events_received[0].data['local_path'], '/local/test.txt')


if __name__ == '__main__':
    unittest.main(verbosity=2)
