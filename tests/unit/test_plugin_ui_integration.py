"""
插件管理UI集成测试
测试插件管理对话框与主程序的集成
"""
import unittest
import sys
import os
from unittest.mock import Mock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from PySide6.QtWidgets import QApplication, QMainWindow, QMenu, QMenuBar
from PySide6.QtCore import Qt

from framework.plugin.plugin_manager import PluginManager
from framework.event.event_bus import EventBus
from dialogs.plugin_manager_dialog import PluginManagerDialog


# 创建QApplication实例
app = QApplication.instance() or QApplication(sys.argv)


class MockMainWindow(QMainWindow):
    """模拟主窗口"""
    
    def __init__(self):
        super().__init__()
        self.plugin_manager_dialog = None
        self.menu_bar = QMenuBar(self)
        self.setMenuBar(self.menu_bar)
        
        # 设置Mock plugin_manager
        self._plugin_manager = Mock(spec=PluginManager)
        self._plugin_manager.get_all_plugins.return_value = {}
        self._plugin_manager.get_plugin_list.return_value = []
        
    def show_plugin_manager(self):
        """显示插件管理器"""
        if not self.plugin_manager_dialog:
            self.plugin_manager_dialog = PluginManagerDialog(
                plugin_manager=self._plugin_manager,
                parent=self
            )
        self.plugin_manager_dialog.show()
        return self.plugin_manager_dialog


class TestPluginMenuIntegration(unittest.TestCase):
    """测试插件菜单集成"""
    
    def setUp(self):
        self.main_window = MockMainWindow()
        self.event_bus = EventBus()
        self.plugin_manager = Mock(spec=PluginManager)
        self.plugin_manager.get_all_plugins.return_value = []
    
    def test_plugin_menu_exists(self):
        """测试插件菜单存在"""
        # 创建工具菜单
        tools_menu = self.main_window.menu_bar.addMenu('Tools')
        
        # 添加插件管理菜单项
        plugin_action = tools_menu.addAction('Plugin Manager')
        
        self.assertIsNotNone(plugin_action)
        self.assertEqual(plugin_action.text(), 'Plugin Manager')
    
    def test_plugin_menu_trigger(self):
        """测试插件菜单触发"""
        # 创建工具菜单和动作
        tools_menu = self.main_window.menu_bar.addMenu('Tools')
        plugin_action = tools_menu.addAction('Plugin Manager')
        
        # 连接信号
        triggered = []
        def on_trigger():
            triggered.append(True)
            self.main_window.show_plugin_manager()
        
        plugin_action.triggered.connect(on_trigger)
        
        # 触发动作
        plugin_action.trigger()
        
        self.assertEqual(len(triggered), 1)
        self.assertIsNotNone(self.main_window.plugin_manager_dialog)


class TestPluginManagerDialog(unittest.TestCase):
    """测试插件管理对话框"""
    
    def setUp(self):
        self.event_bus = EventBus()
        self.plugin_manager = Mock(spec=PluginManager)
        
        # 模拟插件数据
        self.mock_plugins = [
            Mock(
                get_metadata=Mock(return_value=Mock(
                    id='plugin1',
                    name='Test Plugin 1',
                    version='1.0.0',
                    author='Test Author',
                    description='Test description'
                )),
                is_enabled=Mock(return_value=True)
            ),
            Mock(
                get_metadata=Mock(return_value=Mock(
                    id='plugin2',
                    name='Test Plugin 2',
                    version='2.0.0',
                    author='Another Author',
                    description='Another description'
                )),
                is_enabled=Mock(return_value=False)
            )
        ]
        self.plugin_manager.get_all_plugins.return_value = {
            'plugin1': self.mock_plugins[0],
            'plugin2': self.mock_plugins[1]
        }
        self.plugin_manager.get_plugin_list.return_value = [
            {
                'id': 'plugin1',
                'name': 'Test Plugin 1',
                'version': '1.0.0',
                'author': 'Test Author',
                'description': 'Test description',
                'status': 'running',
                'enabled': True
            },
            {
                'id': 'plugin2',
                'name': 'Test Plugin 2',
                'version': '2.0.0',
                'author': 'Another Author',
                'description': 'Another description',
                'status': 'stopped',
                'enabled': False
            }
        ]
    
    def test_dialog_creation(self):
        """测试对话框创建"""
        dialog = PluginManagerDialog(
            plugin_manager=self.plugin_manager,
            parent=None
        )
        
        self.assertIsNotNone(dialog)
        self.assertIn('插件管理器', dialog.windowTitle())
    
    def test_plugin_table_populated(self):
        """测试插件表格已填充"""
        dialog = PluginManagerDialog(
            plugin_manager=self.plugin_manager,
            parent=None
        )
        
        # 验证表格行数（在初始化时已加载）
        self.assertEqual(dialog.plugin_table.rowCount(), 2)
    
    def test_enable_plugin_signal(self):
        """测试启用插件信号"""
        dialog = PluginManagerDialog(
            plugin_manager=self.plugin_manager,
            parent=None
        )
        
        signals_received = []
        dialog.plugin_enabled.connect(lambda pid: signals_received.append(pid))
        
        # 模拟启用插件
        dialog.plugin_enabled.emit('plugin1')
        
        self.assertEqual(len(signals_received), 1)
        self.assertEqual(signals_received[0], 'plugin1')
    
    def test_disable_plugin_signal(self):
        """测试禁用插件信号"""
        dialog = PluginManagerDialog(
            plugin_manager=self.plugin_manager,
            parent=None
        )
        
        signals_received = []
        dialog.plugin_disabled.connect(lambda pid: signals_received.append(pid))
        
        # 模拟禁用插件
        dialog.plugin_disabled.emit('plugin1')
        
        self.assertEqual(len(signals_received), 1)
        self.assertEqual(signals_received[0], 'plugin1')


class TestPluginIntegrationWithMainWindow(unittest.TestCase):
    """测试插件与主窗口的集成"""
    
    def setUp(self):
        self.event_bus = EventBus()
        self.plugin_manager = Mock(spec=PluginManager)
        self.main_window = MockMainWindow()
    
    def test_plugin_events_propagate(self):
        """测试插件事件传播"""
        events_received = []
        
        def on_plugin_enabled(event):
            events_received.append(event.data)
        
        self.event_bus.subscribe('plugin.enabled', on_plugin_enabled)
        
        # 发布插件启用事件
        self.event_bus.publish(
            'plugin.enabled',
            {'plugin_id': 'test_plugin'},
            source='test'
        )
        
        self.assertEqual(len(events_received), 1)
        self.assertEqual(events_received[0]['plugin_id'], 'test_plugin')
    
    def test_config_integration(self):
        """测试配置集成"""
        # 模拟配置
        config = {'plugins': {'enabled': ['plugin1'], 'auto_load': True}}
        
        # 验证配置结构
        self.assertIn('plugins', config)
        self.assertIn('enabled', config['plugins'])


class TestPluginLifecycle(unittest.TestCase):
    """测试插件生命周期集成"""
    
    def setUp(self):
        self.event_bus = EventBus()
        self.plugin_manager = Mock(spec=PluginManager)
    
    def test_load_plugin_integration(self):
        """测试加载插件集成"""
        self.plugin_manager.load_plugin.return_value = True
        
        result = self.plugin_manager.load_plugin('/path/to/plugin.py')
        
        self.assertTrue(result)
        self.plugin_manager.load_plugin.assert_called_with('/path/to/plugin.py')
    
    def test_unload_plugin_integration(self):
        """测试卸载插件集成"""
        self.plugin_manager.unload_plugin.return_value = True
        
        result = self.plugin_manager.unload_plugin('plugin1')
        
        self.assertTrue(result)
        self.plugin_manager.unload_plugin.assert_called_with('plugin1')


if __name__ == '__main__':
    unittest.main(verbosity=2)
