# -*- coding: utf-8 -*-
"""
Integration Tests - 集成测试
测试完整的插件系统工作流程
"""
import sys
import os
import unittest
import tempfile
import shutil

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from framework.plugin import PluginManager, PluginAPI
from framework.event import EventBus, EventTypes
from core import ADBManager, ScrcpyManager
from utils.config_manager import ConfigManager


class TestPluginSystemIntegration(unittest.TestCase):
    """插件系统集成测试"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时目录
        self.test_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.test_dir, "config.json")
        self.plugins_dir = os.path.join(self.test_dir, "plugins")
        os.makedirs(self.plugins_dir)
        
        # 初始化组件
        self.config = ConfigManager(self.config_file)
        self.event_bus = EventBus()
        
        # Mock ADB和Scrcpy
        from unittest.mock import Mock
        self.mock_adb = Mock(spec=ADBManager)
        self.mock_scrcpy = Mock(spec=ScrcpyManager)
        
        self.api = PluginAPI(
            self.mock_adb,
            self.mock_scrcpy,
            self.config,
            self.event_bus
        )
        
        self.manager = PluginManager(
            [self.plugins_dir],
            self.api,
            self.event_bus
        )
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_complete_workflow(self):
        """测试完整工作流：配置→事件→插件→API"""
        # 1. 配置管理
        self.config.set("plugins.auto_load", True)
        self.assertTrue(self.config.get("plugins.auto_load"))
        
        # 2. 事件总线
        received_events = []
        def event_handler(event):
            received_events.append(event)
        
        self.event_bus.subscribe(EventTypes.PLUGIN_LOADED, event_handler)
        
        # 3. 插件系统
        plugins = self.manager.discover_plugins()
        self.assertIsInstance(plugins, list)
        
        # 4. API权限
        self.api.grant_permission("test_plugin", "adb.execute")
        self.assertTrue(self.api.has_permission("test_plugin", "adb.execute"))
        
        # 验证集成
        self.assertIsNotNone(self.config)
        self.assertIsNotNone(self.event_bus)
        self.assertIsNotNone(self.manager)
        self.assertIsNotNone(self.api)
    
    def test_config_persistence(self):
        """测试配置持久化"""
        # 设置配置
        self.config.set("test.value", "persistent_data")
        self.config.save()
        
        # 重新加载
        new_config = ConfigManager(self.config_file)
        self.assertEqual(new_config.get("test.value"), "persistent_data")
    
    def test_event_propagation(self):
        """测试事件传播"""
        events_received = []
        
        def handler1(event):
            events_received.append(("handler1", event))
        
        def handler2(event):
            events_received.append(("handler2", event))
        
        # 订阅
        self.event_bus.subscribe("test.event", handler1)
        self.event_bus.subscribe("test.event", handler2)
        
        # 发布
        self.event_bus.publish("test.event", {"data": "test"})
        
        # 验证
        self.assertEqual(len(events_received), 2)
        self.assertEqual(events_received[0][1].data["data"], "test")
        self.assertEqual(events_received[1][1].data["data"], "test")


class TestSystemPerformance(unittest.TestCase):
    """系统性能测试"""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.test_dir, "config.json")
        self.config = ConfigManager(self.config_file)
        self.event_bus = EventBus()
    
    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_config_performance(self):
        """测试配置读写性能"""
        import time
        
        # 写入性能
        start = time.time()
        for i in range(1000):
            self.config.set(f"test.key_{i}", i)
        write_time = time.time() - start
        
        # 读取性能
        start = time.time()
        for i in range(1000):
            value = self.config.get(f"test.key_{i}")
        read_time = time.time() - start
        
        # 性能断言 (1000次操作应在1秒内完成)
        self.assertLess(write_time, 1.0)
        self.assertLess(read_time, 0.1)
    
    def test_event_performance(self):
        """测试事件性能"""
        import time
        
        counter = [0]
        def handler(event):
            counter[0] += 1
        
        self.event_bus.subscribe("test.event", handler)
        
        # 发布1000次事件
        start = time.time()
        for i in range(1000):
            self.event_bus.publish("test.event", {"index": i})
        elapsed = time.time() - start
        
        # 性能断言
        self.assertEqual(counter[0], 1000)
        self.assertLess(elapsed, 0.5)  # 1000次事件应在0.5秒内完成


def run_integration_tests():
    """运行所有集成测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestPluginSystemIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestSystemPerformance))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_integration_tests()
    sys.exit(0 if success else 1)
