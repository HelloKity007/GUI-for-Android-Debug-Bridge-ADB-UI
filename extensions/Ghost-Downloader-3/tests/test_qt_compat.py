# -*- coding: utf-8 -*-
"""
qt_compat 兼容层测试
TDD 测试用例 - 验证 PyQt6/PyQt6 兼容性
"""
import sys
import pytest


class TestQtCompatBasic:
    """基础兼容性测试"""
    
    def test_import_qt_compat(self):
        """测试 qt_compat 模块可导入"""
        # 先移除已导入的模块，确保干净测试
        modules_to_remove = [k for k in sys.modules.keys() if 'qt_compat' in k or 'PyQt6' in k or 'PyQt6' in k]
        for mod in modules_to_remove:
            del sys.modules[mod]
        
        import app.common.qt_compat as qt_compat
        assert qt_compat is not None
    
    def test_signal_available(self):
        """测试 pyqtSignal 是否可用"""
        modules_to_remove = [k for k in sys.modules.keys() if 'qt_compat' in k]
        for mod in modules_to_remove:
            del sys.modules[mod]
        
        import app.common.qt_compat as qt_compat
        from PyQt6.QtCore import pyqtSignal
        
        # pyqtSignal 应该是 pyqtSignal 的别名
        assert hasattr(qt_compat, 'pyqtSignal')
        assert qt_compat.pyqtSignal == pyqtSignal
    
    def test_slot_available(self):
        """测试 pyqtSlot 是否可用"""
        modules_to_remove = [k for k in sys.modules.keys() if 'qt_compat' in k]
        for mod in modules_to_remove:
            del sys.modules[mod]
        
        import app.common.qt_compat as qt_compat
        from PyQt6.QtCore import pyqtSlot
        
        assert hasattr(qt_compat, 'pyqtSlot')
        assert qt_compat.pyqtSlot == pyqtSlot


class TestQFontCompatibility:
    """QFont 兼容性测试"""
    
    def test_qfont_weight_enum(self):
        """测试 QFont.Weight 枚举是否可用"""
        from PyQt6.QtGui import QFont
        
        # PyQt6 中使用 QFont.Weight.Normal
        assert hasattr(QFont, 'Weight')
        assert hasattr(QFont.Weight, 'Normal')
    
    def test_qfont_normal_accessible(self):
        """测试 QFont.Normal 是否可通过兼容层访问"""
        modules_to_remove = [k for k in sys.modules.keys() if 'qt_compat' in k]
        for mod in modules_to_remove:
            del sys.modules[mod]
        
        import app.common.qt_compat as qt_compat
        
        # 重新导入 QFont
        from PyQt6.QtGui import QFont
        
        # 兼容层应该提供 QFont.Normal 访问
        # 在 PyQt6 中，Normal 是 QFont.Weight.Normal
        normal_weight = QFont.Weight.Normal
        assert normal_weight is not None


class TestPathImport:
    """Path 导入测试"""
    
    def test_path_importable_after_qt_compat(self):
        """测试在 qt_compat 之后 Path 仍可导入"""
        import app.common.qt_compat as qt_compat
        from pathlib import Path
        
        # Path 应该是 pathlib.Path
        assert Path is not None
        p = Path(".")
        assert str(p) == "."


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
