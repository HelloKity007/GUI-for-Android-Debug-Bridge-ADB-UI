# -*- coding: utf-8 -*-
"""
Plugin System Unit Tests
插件系统单元测试
"""
import sys
import os
import unittest
from unittest.mock import Mock, MagicMock, patch

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from framework.event import EventBus, Event, EventTypes, EventPriority
from framework.plugin import PluginInterface, PluginMetadata, PluginManager, PluginAPI


class TestEventBus(unittest.TestCase):
    """事件总线测试"""
    
    def setUp(self):
        self.event_bus = EventBus()
    
    def test_subscribe_and_publish(self):
        """测试订阅和发布"""
        received_events = []
        
        def callback(event: Event):
            received_events.append(event)
        
        # 订阅事件
        self.event_bus.subscribe("test.event", callback)
        
        # 发布事件
        self.event_bus.publish("test.event", {"key": "value"})
        
        # 验证
        self.assertEqual(len(received_events), 1)
        self.assertEqual(received_events[0].type, "test.event")
        self.assertEqual(received_events[0].data["key"], "value")
    
    def test_unsubscribe(self):
        """测试取消订阅"""
        received_events = []
        
        def callback(event: Event):
            received_events.append(event)
        
        # 订阅后取消
        self.event_bus.subscribe("test.event", callback)
        self.event_bus.unsubscribe("test.event", callback)
        
        # 发布事件
        self.event_bus.publish("test.event", {"key": "value"})
        
        # 验证没有收到事件
        self.assertEqual(len(received_events), 0)
    
    def test_priority(self):
        """测试事件优先级"""
        call_order = []
        
        def high_callback(event: Event):
            call_order.append("high")
        
        def normal_callback(event: Event):
            call_order.append("normal")
        
        def low_callback(event: Event):
            call_order.append("low")
        
        # 按相反顺序订阅
        self.event_bus.subscribe("test.event", low_callback, EventPriority.LOW)
        self.event_bus.subscribe("test.event", normal_callback, EventPriority.NORMAL)
        self.event_bus.subscribe("test.event", high_callback, EventPriority.HIGH)
        
        # 发布事件
        self.event_bus.publish("test.event")
        
        # 验证执行顺序
        self.assertEqual(call_order, ["high", "normal", "low"])
    
    def test_event_history(self):
        """测试事件历史"""
        # 发布多个事件
        self.event_bus.publish("test.event1", {"data": 1})
        self.event_bus.publish("test.event2", {"data": 2})
        self.event_bus.publish("test.event1", {"data": 3})
        
        # 获取所有历史
        all_history = self.event_bus.get_history()
        self.assertEqual(len(all_history), 3)
        
        # 获取特定类型历史
        event1_history = self.event_bus.get_history("test.event1")
        self.assertEqual(len(event1_history), 2)


class TestPluginAPI(unittest.TestCase):
    """插件API测试"""
    
    def setUp(self):
        # Mock依赖
        self.mock_adb = Mock()
        self.mock_scrcpy = Mock()
        self.mock_config = Mock()
        self.mock_event_bus = Mock()
        
        self.api = PluginAPI(
            self.mock_adb,
            self.mock_scrcpy,
            self.mock_config,
            self.mock_event_bus
        )
    
    def test_permission_grant_and_check(self):
        """测试权限授予和检查"""
        plugin_id = "test_plugin"
        permission = "adb.execute"
        
        # 初始无权限
        self.assertFalse(self.api.has_permission(plugin_id, permission))
        
        # 授权
        self.api.grant_permission(plugin_id, permission)
        self.assertTrue(self.api.has_permission(plugin_id, permission))
        
        # 撤销
        self.api.revoke_permission(plugin_id, permission)
        self.assertFalse(self.api.has_permission(plugin_id, permission))
    
    def test_adb_execute_with_permission(self):
        """测试带权限的ADB命令执行"""
        plugin_id = "test_plugin"
        
        # 授权
        self.api.grant_permission(plugin_id, "adb.execute")
        
        # Mock返回值
        self.mock_adb.run_command.return_value = {
            'success': True,
            'stdout': 'output',
            'stderr': ''
        }
        
        # 执行命令
        result = self.api.adb_execute_command("devices", plugin_id=plugin_id)
        
        # 验证
        self.assertTrue(result['success'])
        self.mock_adb.run_command.assert_called_once()
    
    def test_adb_execute_without_permission(self):
        """测试无权限执行ADB命令"""
        plugin_id = "test_plugin"
        
        # 不授权，直接执行
        with self.assertRaises(PermissionError):
            self.api.adb_execute_command("devices", plugin_id=plugin_id)
    
    def test_adb_get_devices(self):
        """测试获取设备列表"""
        # Mock返回值
        self.mock_adb.get_devices.return_value = [
            {'id': 'device1', 'status': 'device'},
            {'id': 'device2', 'status': 'device'}
        ]
        
        # 调用
        devices = self.api.adb_get_devices()
        
        # 验证
        self.assertEqual(len(devices), 2)
        self.mock_adb.get_devices.assert_called_once()


class MockPlugin(PluginInterface):
    """Mock插件用于测试"""
    
    def __init__(self):
        super().__init__()
        self.loaded = False
        self.enabled = False
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="mock_plugin",
            name="Mock Plugin",
            version="1.0.0",
            author="Test",
            description="Test plugin"
        )
    
    def on_load(self, api, event_bus) -> bool:
        self.loaded = True
        return True
    
    def on_unload(self) -> bool:
        self.loaded = False
        return True
    
    def on_enable(self) -> bool:
        self.enabled = True
        return True
    
    def on_disable(self) -> bool:
        self.enabled = False
        return True


class TestPluginManager(unittest.TestCase):
    """插件管理器测试"""
    
    def setUp(self):
        # Mock依赖
        self.mock_api = Mock(spec=PluginAPI)
        self.mock_event_bus = Mock(spec=EventBus)
        
        # 使用临时目录
        self.plugin_dir = os.path.join(project_root, "plugins")
        
        self.manager = PluginManager(
            [self.plugin_dir],
            self.mock_api,
            self.mock_event_bus
        )
    
    def test_discover_plugins(self):
        """测试插件发现"""
        plugins = self.manager.discover_plugins()
        
        # 验证至少发现了示例插件
        self.assertGreater(len(plugins), 0)
        
        # 检查是否包含device_monitor_plugin
        plugin_names = [os.path.basename(p) for p in plugins]
        self.assertIn("device_monitor_plugin.py", plugin_names)
    
    def test_plugin_lifecycle(self):
        """测试插件生命周期"""
        # 创建Mock插件实例（实际使用中会从文件加载）
        # 这里我们直接测试生命周期逻辑
        plugin = MockPlugin()
        
        # 验证初始状态
        self.assertFalse(plugin.loaded)
        self.assertFalse(plugin.enabled)
        
        # 加载
        result = plugin.on_load(self.mock_api, self.mock_event_bus)
        self.assertTrue(result)
        self.assertTrue(plugin.loaded)
        
        # 启用
        result = plugin.on_enable()
        self.assertTrue(result)
        self.assertTrue(plugin.enabled)
        
        # 禁用
        result = plugin.on_disable()
        self.assertTrue(result)
        self.assertFalse(plugin.enabled)
        
        # 卸载
        result = plugin.on_unload()
        self.assertTrue(result)
        self.assertFalse(plugin.loaded)


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试用例
    suite.addTests(loader.loadTestsFromTestCase(TestEventBus))
    suite.addTests(loader.loadTestsFromTestCase(TestPluginAPI))
    suite.addTests(loader.loadTestsFromTestCase(TestPluginManager))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
