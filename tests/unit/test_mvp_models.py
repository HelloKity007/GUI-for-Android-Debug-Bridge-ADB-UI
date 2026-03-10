"""
MVP架构 Model层单元测试
TDD方式: 先写测试，后写实现
"""
import unittest
import sys
import os
import tempfile
import shutil
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, List, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from framework.mvp.models import DeviceModel, ADBModel, AppModel, FileModel
from framework.event.event_bus import EventBus, EventTypes


class TestDeviceModel(unittest.TestCase):
    """设备模型测试"""
    
    def setUp(self):
        self.event_bus = EventBus()
        self.model = DeviceModel(self.event_bus)
    
    def test_initial_state(self):
        """测试初始状态"""
        self.assertEqual(self.model.devices, [])
        self.assertIsNone(self.model.current_device)
        self.assertFalse(self.model.is_refreshing)
    
    def test_set_devices(self):
        """测试设置设备列表"""
        devices = [
            {'id': 'device1', 'status': 'device', 'name': 'Phone 1'},
            {'id': 'device2', 'status': 'device', 'name': 'Phone 2'}
        ]
        
        events_received = []
        self.event_bus.subscribe(EventTypes.DEVICE_LIST_UPDATED, 
                                lambda e: events_received.append(e))
        
        self.model.set_devices(devices)
        
        self.assertEqual(self.model.devices, devices)
        self.assertEqual(len(events_received), 1)
        self.assertEqual(events_received[0].data['devices'], devices)
    
    def test_set_current_device(self):
        """测试设置当前设备"""
        device = {'id': 'device1', 'status': 'device', 'name': 'Phone 1'}
        
        events_received = []
        self.event_bus.subscribe(EventTypes.DEVICE_SELECTED,
                                lambda e: events_received.append(e))
        
        self.model.set_current_device(device)
        
        self.assertEqual(self.model.current_device, device)
        self.assertEqual(len(events_received), 1)
        self.assertEqual(events_received[0].data['device'], device)
    
    def test_clear_devices(self):
        """测试清除设备列表"""
        devices = [{'id': 'device1', 'status': 'device'}]
        self.model.set_devices(devices)
        self.model.set_current_device(devices[0])
        
        self.model.clear_devices()
        
        self.assertEqual(self.model.devices, [])
        self.assertIsNone(self.model.current_device)
    
    def test_get_device_by_id(self):
        """测试通过ID获取设备"""
        devices = [
            {'id': 'device1', 'status': 'device'},
            {'id': 'device2', 'status': 'device'}
        ]
        self.model.set_devices(devices)
        
        device = self.model.get_device_by_id('device1')
        self.assertEqual(device['id'], 'device1')
        
        device = self.model.get_device_by_id('nonexistent')
        self.assertIsNone(device)
    
    def test_refreshing_state(self):
        """测试刷新状态"""
        self.model.set_refreshing(True)
        self.assertTrue(self.model.is_refreshing)
        
        self.model.set_refreshing(False)
        self.assertFalse(self.model.is_refreshing)


class TestADBModel(unittest.TestCase):
    """ADB模型测试"""
    
    def setUp(self):
        self.event_bus = EventBus()
        self.model = ADBModel(self.event_bus)
    
    def test_initial_state(self):
        """测试初始状态"""
        self.assertEqual(self.model.adb_path, 'adb')
        self.assertFalse(self.model.is_connected)
    
    def test_set_adb_path(self):
        """测试设置ADB路径"""
        events_received = []
        self.event_bus.subscribe('adb.path_changed',
                                lambda e: events_received.append(e))
        
        self.model.set_adb_path('/path/to/adb')
        
        self.assertEqual(self.model.adb_path, '/path/to/adb')
        self.assertEqual(len(events_received), 1)
        self.assertEqual(events_received[0].data['path'], '/path/to/adb')
    
    @patch('subprocess.run')
    def test_execute_command(self, mock_run):
        """测试执行命令"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='device1\tdevice\ndevice2\tdevice',
            stderr=''
        )
        
        result = self.model.execute_command('devices')
        
        self.assertEqual(result['returncode'], 0)
        self.assertEqual(result['stdout'], 'device1\tdevice\ndevice2\tdevice')
        self.assertTrue(result['success'])
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_execute_command_with_error(self, mock_run):
        """测试执行命令出错"""
        mock_run.return_value = Mock(
            returncode=1,
            stdout='',
            stderr='error: no devices/emulators found'
        )
        
        result = self.model.execute_command('shell ls')
        
        self.assertEqual(result['returncode'], 1)
        self.assertFalse(result['success'])
    
    @patch('subprocess.run')
    def test_execute_command_exception(self, mock_run):
        """测试执行命令异常"""
        mock_run.side_effect = Exception('Command not found')
        
        result = self.model.execute_command('devices')
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
    
    @patch('subprocess.run')
    def test_get_devices(self, mock_run):
        """测试获取设备列表"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='List of devices attached\ndevice1\tdevice\ndevice2\toffline',
            stderr=''
        )
        
        devices = self.model.get_devices()
        
        self.assertEqual(len(devices), 2)
        self.assertEqual(devices[0]['id'], 'device1')
        self.assertEqual(devices[0]['status'], 'device')
    
    @patch('subprocess.run')
    def test_get_device_info(self, mock_run):
        """测试获取设备信息"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='Pixel 6\n14',
            stderr=''
        )
        
        info = self.model.get_device_info('device1')
        
        self.assertEqual(info['model'], 'Pixel 6')
        self.assertEqual(info['android_version'], '14')


class TestAppModel(unittest.TestCase):
    """应用模型测试"""
    
    def setUp(self):
        self.event_bus = EventBus()
        self.adb_model = Mock()
        self.model = AppModel(self.event_bus, self.adb_model)
    
    def test_initial_state(self):
        """测试初始状态"""
        self.assertEqual(self.model.apps, [])
        self.assertIsNone(self.model.current_device)
    
    def test_set_device(self):
        """测试设置设备"""
        self.model.set_device('device1')
        self.assertEqual(self.model.current_device, 'device1')
    
    def test_load_apps(self):
        """测试加载应用列表"""
        self.model.set_device('device1')
        self.adb_model.execute_command.return_value = {
            'success': True,
            'stdout': 'package:com.android.settings\npackage:com.example.app'
        }
        
        apps = self.model.load_apps()
        
        self.assertEqual(len(apps), 2)
        self.assertEqual(apps[0]['package'], 'com.android.settings')
        self.adb_model.execute_command.assert_called_with(
            'shell pm list packages', 'device1'
        )
    
    def test_install_app(self):
        """测试安装应用"""
        self.model.set_device('device1')
        self.adb_model.execute_command.return_value = {
            'success': True,
            'stdout': 'Success'
        }
        
        result = self.model.install_app('/path/to/app.apk')
        
        self.assertTrue(result['success'])
        self.adb_model.execute_command.assert_called_with(
            'install "/path/to/app.apk"', 'device1'
        )
    
    def test_uninstall_app(self):
        """测试卸载应用"""
        self.model.set_device('device1')
        self.adb_model.execute_command.return_value = {
            'success': True,
            'stdout': 'Success'
        }
        
        result = self.model.uninstall_app('com.example.app')
        
        self.assertTrue(result['success'])
        self.adb_model.execute_command.assert_called_with(
            'uninstall com.example.app', 'device1'
        )
    
    def test_enable_disable_app(self):
        """测试启用/禁用应用"""
        self.model.set_device('device1')
        self.adb_model.execute_command.return_value = {
            'success': True,
            'stdout': ''
        }
        
        result = self.model.disable_app('com.example.app')
        self.assertTrue(result['success'])
        
        result = self.model.enable_app('com.example.app')
        self.assertTrue(result['success'])


class TestFileModel(unittest.TestCase):
    """文件模型测试"""
    
    def setUp(self):
        self.event_bus = EventBus()
        self.adb_model = Mock()
        self.model = FileModel(self.event_bus, self.adb_model)
    
    def test_initial_state(self):
        """测试初始状态"""
        self.assertEqual(self.model.current_path, '/sdcard')
        self.assertIsNone(self.model.current_device)
    
    def test_set_device(self):
        """测试设置设备"""
        self.model.set_device('device1')
        self.assertEqual(self.model.current_device, 'device1')
    
    def test_set_path(self):
        """测试设置路径"""
        self.model.set_path('/data/local')
        self.assertEqual(self.model.current_path, '/data/local')
    
    def test_list_directory(self):
        """测试列出目录"""
        self.model.set_device('device1')
        self.model.set_path('/sdcard')
        self.adb_model.execute_command.return_value = {
            'success': True,
            'stdout': 'drwxrwx--- 2 root sdcard_rw 4096 2024-01-01 10:00 DCIM\n-rw-rw---- 1 root sdcard_rw 1234 2024-01-01 11:00 file.txt',
            'stderr': ''
        }
        
        files = self.model.list_directory()
        
        self.assertEqual(len(files), 2)
        self.assertEqual(files[0]['name'], 'DCIM')
        self.assertTrue(files[0]['is_dir'])
        self.assertEqual(files[1]['name'], 'file.txt')
        self.assertFalse(files[1]['is_dir'])
    
    def test_push_file(self):
        """测试推送文件"""
        self.model.set_device('device1')
        self.model.set_path('/sdcard')
        self.adb_model.execute_command.return_value = {
            'success': True,
            'stdout': ''
        }
        
        result = self.model.push_file('/local/file.txt', 'file.txt')
        
        self.assertTrue(result['success'])
        self.adb_model.execute_command.assert_called_with(
            'push "/local/file.txt" "/sdcard/file.txt"', 'device1'
        )
    
    def test_pull_file(self):
        """测试拉取文件"""
        self.model.set_device('device1')
        self.model.set_path('/sdcard')
        self.adb_model.execute_command.return_value = {
            'success': True,
            'stdout': ''
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            local_path = os.path.join(tmpdir, 'file.txt')
            result = self.model.pull_file('file.txt', local_path)
            
            self.assertTrue(result['success'])
            self.adb_model.execute_command.assert_called_with(
                f'pull "/sdcard/file.txt" "{local_path}"', 'device1'
            )
    
    def test_delete_file(self):
        """测试删除文件"""
        self.model.set_device('device1')
        self.model.set_path('/sdcard')
        self.adb_model.execute_command.return_value = {
            'success': True,
            'stdout': ''
        }
        
        result = self.model.delete_file('file.txt')
        
        self.assertTrue(result['success'])
        self.adb_model.execute_command.assert_called_with(
            'shell rm -rf "/sdcard/file.txt"', 'device1'
        )
    
    def test_navigate_up(self):
        """测试向上导航"""
        self.model.set_path('/sdcard/DCIM/Camera')
        self.model.navigate_up()
        self.assertEqual(self.model.current_path, '/sdcard/DCIM')
        
        self.model.navigate_up()
        self.assertEqual(self.model.current_path, '/sdcard')
        
        # 测试根目录
        self.model.set_path('/')
        self.model.navigate_up()
        self.assertEqual(self.model.current_path, '/')


class TestModelIntegration(unittest.TestCase):
    """模型集成测试"""
    
    def setUp(self):
        self.event_bus = EventBus()
        self.device_model = DeviceModel(self.event_bus)
        self.adb_model = ADBModel(self.event_bus)
        self.app_model = AppModel(self.event_bus, self.adb_model)
        self.file_model = FileModel(self.event_bus, self.adb_model)
    
    def test_device_change_propagation(self):
        """测试设备变更传播"""
        device = {'id': 'device1', 'status': 'device'}
        
        # 设置设备应该传播到相关模型
        self.device_model.set_current_device(device)
        self.app_model.set_device(device['id'])
        self.file_model.set_device(device['id'])
        
        self.assertEqual(self.app_model.current_device, 'device1')
        self.assertEqual(self.file_model.current_device, 'device1')
    
    def test_event_flow(self):
        """测试事件流"""
        events = []
        self.event_bus.subscribe(EventTypes.DEVICE_LIST_UPDATED, lambda e: events.append(e.type))
        self.event_bus.subscribe('adb.path_changed', lambda e: events.append(e.type))
        
        # 触发一系列操作
        self.device_model.set_devices([{'id': 'd1'}])
        self.adb_model.set_adb_path('/new/path')
        
        self.assertEqual(len(events), 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
