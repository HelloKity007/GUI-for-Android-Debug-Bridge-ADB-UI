# -*- coding: utf-8 -*-
"""
qt_compat 兼容层测试
TDD 测试用例 - 验证 PySide6 兼容性
"""
import sys
import pytest


class TestQtCompatBasic:
    """基础兼容性测试"""

    def test_import_qt_compat(self):
        """测试 qt_compat 模块可导入"""
        import app.common.qt_compat as qt_compat
        assert qt_compat is not None

    def test_signal_available(self):
        """测试 Signal 是否可用"""
        import app.common.qt_compat as qt_compat
        from PySide6.QtCore import Signal

        # Signal 应该在兼容层中可用
        assert hasattr(qt_compat, 'Signal')
        assert qt_compat.Signal == Signal

    def test_slot_available(self):
        """测试 Slot 是否可用"""
        import app.common.qt_compat as qt_compat
        from PySide6.QtCore import Slot

        assert hasattr(qt_compat, 'Slot')
        assert qt_compat.Slot == Slot

    def test_pyqtsignal_alias(self):
        """测试 pyqtSignal 别名是否可用"""
        import app.common.qt_compat as qt_compat
        from PySide6.QtCore import Signal

        assert hasattr(qt_compat, 'pyqtSignal')
        assert qt_compat.pyqtSignal == Signal

    def test_pyqtslot_alias(self):
        """测试 pyqtSlot 别名是否可用"""
        import app.common.qt_compat as qt_compat
        from PySide6.QtCore import Slot

        assert hasattr(qt_compat, 'pyqtSlot')
        assert qt_compat.pyqtSlot == Slot


class TestQFontCompatibility:
    """QFont 兼容性测试"""

    def test_qfont_weight_enum(self):
        """测试 QFont.Weight 枚举可访问"""
        from PySide6.QtGui import QFont
        assert hasattr(QFont, 'Weight')
        assert hasattr(QFont.Weight, 'Normal')
        assert hasattr(QFont.Weight, 'Bold')


class TestQtEnumCompatibility:
    """Qt 枚举兼容性测试"""

    def test_qt_orientation(self):
        """测试 Qt.Vertical 和 Qt.Horizontal"""
        from PySide6.QtCore import Qt
        assert hasattr(Qt, 'Vertical')
        assert hasattr(Qt, 'Horizontal')

    def test_qt_alignment(self):
        """测试 Qt 对齐枚举"""
        from PySide6.QtCore import Qt
        assert hasattr(Qt, 'AlignCenter')
        assert hasattr(Qt, 'AlignLeft')
        assert hasattr(Qt, 'AlignRight')

    def test_qstandardpaths_location(self):
        """测试 QStandardPaths 位置枚举"""
        from PySide6.QtCore import QStandardPaths
        assert hasattr(QStandardPaths, 'DownloadLocation')
        assert hasattr(QStandardPaths, 'HomeLocation')

    def test_qeasingcurve_type(self):
        """测试 QEasingCurve 类型枚举"""
        from PySide6.QtCore import QEasingCurve
        assert hasattr(QEasingCurve, 'OutCubic')
        assert hasattr(QEasingCurve, 'InOutCubic')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
