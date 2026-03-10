# -*- coding: utf-8 -*-
"""
Configuration Manager Tests
配置管理器测试（TDD方式）
"""
import sys
import os
import unittest
import json
import tempfile
import shutil
from pathlib import Path

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.config_manager import ConfigManager


class TestConfigManager(unittest.TestCase):
    """配置管理器测试类"""
    
    def setUp(self):
        """每个测试前执行"""
        # 创建临时目录
        self.test_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.test_dir, "test_config.json")
        
        # 默认配置
        self.default_config = {
            "app": {
                "name": "ADB Tool",
                "version": "2.0.0",
                "dark_mode": False
            },
            "paths": {
                "adb_path": "",
                "scrcpy_path": "",
                "plugins_dir": "plugins"
            },
            "plugins": {
                "enabled": [],
                "disabled": []
            }
        }
    
    def tearDown(self):
        """每个测试后执行"""
        # 清理临时目录
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_create_default_config(self):
        """测试创建默认配置"""
        manager = ConfigManager(self.config_file)
        
        # 验证文件被创建
        self.assertTrue(os.path.exists(self.config_file))
        
        # 验证默认值
        self.assertEqual(manager.get("app.name"), "ADB Tool")
        self.assertEqual(manager.get("app.version"), "2.0.0")
        self.assertFalse(manager.get("app.dark_mode"))
    
    def test_load_existing_config(self):
        """测试加载已存在的配置"""
        # 先创建配置文件
        test_config = {
            "app": {"name": "Test App", "version": "1.0.0"},
            "custom": {"key": "value"}
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(test_config, f)
        
        # 加载配置
        manager = ConfigManager(self.config_file)
        
        # 验证加载成功
        self.assertEqual(manager.get("app.name"), "Test App")
        self.assertEqual(manager.get("custom.key"), "value")
    
    def test_get_with_dot_notation(self):
        """测试点号路径获取"""
        manager = ConfigManager(self.config_file)
        
        # 单层路径
        self.assertEqual(manager.get("app.name"), "ADB Tool")
        
        # 多层路径
        manager.set("deep.nested.value", 123)
        self.assertEqual(manager.get("deep.nested.value"), 123)
        
        # 不存在的路径，返回默认值
        self.assertIsNone(manager.get("not.exist"))
        self.assertEqual(manager.get("not.exist", "default"), "default")
    
    def test_set_with_dot_notation(self):
        """测试点号路径设置"""
        manager = ConfigManager(self.config_file)
        
        # 设置新值
        manager.set("app.dark_mode", True)
        self.assertTrue(manager.get("app.dark_mode"))
        
        # 设置深层嵌套
        manager.set("a.b.c.d", "deep_value")
        self.assertEqual(manager.get("a.b.c.d"), "deep_value")
        
        # 覆盖已有值
        manager.set("app.name", "New Name")
        self.assertEqual(manager.get("app.name"), "New Name")
    
    def test_has_key(self):
        """测试检查键是否存在"""
        manager = ConfigManager(self.config_file)
        
        # 存在的键
        self.assertTrue(manager.has("app.name"))
        self.assertTrue(manager.has("app"))
        
        # 不存在的键
        self.assertFalse(manager.has("not.exist"))
    
    def test_delete_key(self):
        """测试删除键"""
        manager = ConfigManager(self.config_file)
        
        # 删除存在的键
        manager.set("temp.key", "value")
        self.assertTrue(manager.has("temp.key"))
        
        manager.delete("temp.key")
        self.assertFalse(manager.has("temp.key"))
        
        # 删除不存在的键不报错
        manager.delete("not.exist")
    
    def test_save_and_reload(self):
        """测试保存和重新加载"""
        # 创建并修改配置
        manager1 = ConfigManager(self.config_file)
        manager1.set("test.value", "saved_data")
        manager1.save()
        
        # 重新加载
        manager2 = ConfigManager(self.config_file)
        self.assertEqual(manager2.get("test.value"), "saved_data")
    
    def test_get_section(self):
        """测试获取整个节"""
        manager = ConfigManager(self.config_file)
        
        # 获取节
        app_section = manager.get_section("app")
        self.assertIsInstance(app_section, dict)
        self.assertIn("name", app_section)
        self.assertIn("version", app_section)
        
        # 不存在的节
        self.assertIsNone(manager.get_section("not.exist"))
    
    def test_update_section(self):
        """测试更新整个节"""
        manager = ConfigManager(self.config_file)
        
        # 更新节
        new_app_config = {
            "name": "Updated App",
            "version": "3.0.0",
            "new_field": "new_value"
        }
        manager.update_section("app", new_app_config)
        
        # 验证更新
        self.assertEqual(manager.get("app.name"), "Updated App")
        self.assertEqual(manager.get("app.version"), "3.0.0")
        self.assertEqual(manager.get("app.new_field"), "new_value")
    
    def test_merge_config(self):
        """测试合并配置"""
        manager = ConfigManager(self.config_file)
        
        # 合并新配置
        new_config = {
            "app": {"theme": "dark"},
            "new_section": {"key": "value"}
        }
        manager.merge(new_config)
        
        # 验证合并结果
        self.assertEqual(manager.get("app.name"), "ADB Tool")  # 保留原有
        self.assertEqual(manager.get("app.theme"), "dark")     # 添加新的
        self.assertEqual(manager.get("new_section.key"), "value")  # 新节
    
    def test_reset_to_default(self):
        """测试重置为默认值"""
        manager = ConfigManager(self.config_file)
        
        # 修改配置
        manager.set("app.name", "Modified")
        manager.set("custom.key", "value")
        
        # 重置
        manager.reset()
        
        # 验证重置
        self.assertEqual(manager.get("app.name"), "ADB Tool")
        self.assertIsNone(manager.get("custom.key"))
    
    def test_auto_save(self):
        """测试自动保存"""
        manager = ConfigManager(self.config_file, auto_save=True)
        
        # 修改配置（自动保存）
        manager.set("auto.save", "test")
        
        # 重新加载验证
        manager2 = ConfigManager(self.config_file)
        self.assertEqual(manager2.get("auto.save"), "test")
    
    def test_backup_and_restore(self):
        """测试备份和恢复"""
        manager = ConfigManager(self.config_file)
        
        # 修改并备份
        manager.set("backup.test", "original")
        backup_file = manager.backup()
        
        self.assertTrue(os.path.exists(backup_file))
        
        # 继续修改
        manager.set("backup.test", "modified")
        self.assertEqual(manager.get("backup.test"), "modified")
        
        # 从备份恢复
        manager.restore(backup_file)
        self.assertEqual(manager.get("backup.test"), "original")
    
    def test_validate_schema(self):
        """测试配置校验"""
        manager = ConfigManager(self.config_file)
        
        # 定义schema (更新为新配置结构)
        schema = {
            "app": {"name": str, "version": str, "dark_mode": bool},
            "adb": {"path": str, "auto_refresh_devices": bool}
        }
        
        # 验证有效配置
        self.assertTrue(manager.validate(schema))
        
        # 破坏配置
        manager.set("app.dark_mode", "not_a_bool")
        self.assertFalse(manager.validate(schema))
    
    def test_relative_to_absolute_path(self):
        """测试相对路径转绝对路径"""
        manager = ConfigManager(self.config_file)
        
        # 设置相对路径
        manager.set("extensions.directory", "extensions")
        
        # 转换为绝对路径
        abs_path = manager.get_absolute_path("extensions.directory")
        
        # 验证是绝对路径
        self.assertTrue(os.path.isabs(abs_path))
        self.assertIn("extensions", abs_path)


class TestConfigManagerThreadSafety(unittest.TestCase):
    """配置管理器线程安全测试"""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.test_dir, "test_config.json")
    
    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_concurrent_writes(self):
        """测试并发写入"""
        import threading
        
        manager = ConfigManager(self.config_file)
        errors = []
        
        def write_config(index):
            try:
                for i in range(10):
                    manager.set(f"thread_{index}.value_{i}", i)
            except Exception as e:
                errors.append(e)
        
        # 创建多个线程
        threads = [threading.Thread(target=write_config, args=(i,)) for i in range(5)]
        
        # 启动所有线程
        for t in threads:
            t.start()
        
        # 等待完成
        for t in threads:
            t.join()
        
        # 验证没有错误
        self.assertEqual(len(errors), 0)
        
        # 验证数据完整性
        for i in range(5):
            for j in range(10):
                self.assertEqual(manager.get(f"thread_{i}.value_{j}"), j)


def run_config_tests():
    """运行配置管理器测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestConfigManager))
    suite.addTests(loader.loadTestsFromTestCase(TestConfigManagerThreadSafety))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_config_tests()
    sys.exit(0 if success else 1)
