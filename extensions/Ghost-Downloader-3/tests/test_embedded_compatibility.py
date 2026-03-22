# -*- coding: utf-8 -*-
"""
Ghost Downloader PySide6 兼容层测试
TDD 测试驱动开发 - 所有功能必须通过测试
"""
import sys
import os

# 添加项目根目录到 sys.path
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_dir)

# ===== 关键：先初始化兼容层，再导入任何 Qt 模块 =====
import app.common.qt_compat as _qt_compat

# ===== 关键：创建 QApplication，再导入任何 UI 组件 =====
from PySide6.QtWidgets import QApplication
_qapp = QApplication.instance() or QApplication(sys.argv)


class TestQtCompat:
    """Qt 兼容层测试 - 必须首先运行"""

    def test_signal_exists(self):
        """测试 Signal 存在"""
        import app.common.qt_compat as qt_compat
        assert hasattr(qt_compat, 'Signal'), "Signal 不存在"

    def test_slot_exists(self):
        """测试 Slot 存在"""
        import app.common.qt_compat as qt_compat
        assert hasattr(qt_compat, 'Slot'), "Slot 不存在"

    def test_pyqtsignal_alias(self):
        """测试 pyqtSignal 别名存在"""
        import app.common.qt_compat as qt_compat
        assert hasattr(qt_compat, 'pyqtSignal'), "pyqtSignal 别名不存在"

    def test_qfont_weight(self):
        """测试 QFont.Weight 可访问"""
        from PySide6.QtGui import QFont
        assert hasattr(QFont, 'Weight'), "QFont.Weight 不存在"
        assert hasattr(QFont.Weight, 'Normal'), "QFont.Weight.Normal 不存在"

    def test_qt_vertical(self):
        """测试 Qt.Vertical 可访问"""
        from PySide6.QtCore import Qt
        assert hasattr(Qt, 'Vertical'), "Qt.Vertical 不存在"

    def test_qt_horizontal(self):
        """测试 Qt.Horizontal 可访问"""
        from PySide6.QtCore import Qt
        assert hasattr(Qt, 'Horizontal'), "Qt.Horizontal 不存在"

    def test_qt_aligncenter(self):
        """测试 Qt.AlignCenter 可访问"""
        from PySide6.QtCore import Qt
        assert hasattr(Qt, 'AlignCenter'), "Qt.AlignCenter 不存在"

    def test_qstandardpaths_downloadlocation(self):
        """测试 QStandardPaths.DownloadLocation 可访问"""
        from PySide6.QtCore import QStandardPaths
        assert hasattr(QStandardPaths, 'DownloadLocation'), "QStandardPaths.DownloadLocation 不存在"

    def test_qeasingcurve_outcubic(self):
        """测试 QEasingCurve.OutCubic 可访问"""
        from PySide6.QtCore import QEasingCurve
        assert hasattr(QEasingCurve, 'OutCubic'), "QEasingCurve.OutCubic 不存在"

    def test_qframe_shape(self):
        """测试 QFrame.Shape 可访问"""
        from PySide6.QtWidgets import QFrame
        assert hasattr(QFrame, 'Shape'), "QFrame.Shape 不存在"

    def test_qsizepolicy(self):
        """测试 QSizePolicy 可访问"""
        from PySide6.QtWidgets import QSizePolicy
        assert hasattr(QSizePolicy, 'Expanding'), "QSizePolicy.Expanding 不存在"


class TestEmbeddedMainWindow:
    """嵌入式主窗口测试"""

    def test_import_embedded_main_window(self):
        """测试导入 EmbeddedMainWindow"""
        try:
            from app.common.embedded_main_window import EmbeddedMainWindow
            assert True
        except Exception as e:
            assert False, f"导入 EmbeddedMainWindow 失败: {e}"

    def test_create_embedded_main_window(self):
        """测试创建 EmbeddedMainWindow 实例"""
        try:
            from app.common.embedded_main_window import EmbeddedMainWindow
            window = EmbeddedMainWindow()
            assert window is not None
        except Exception as e:
            assert False, f"创建 EmbeddedMainWindow 实例失败: {e}"


class TestTaskInterface:
    """任务界面测试"""

    def test_import_task_interface(self):
        """测试导入 TaskInterface"""
        try:
            from app.view.task_interface import TaskInterface
            assert True
        except Exception as e:
            assert False, f"导入 TaskInterface 失败: {e}"


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("Ghost Downloader PySide6 兼容层测试")
    print("=" * 60)

    test_classes = [TestQtCompat, TestEmbeddedMainWindow, TestTaskInterface]
    passed = 0
    failed = 0

    for test_class in test_classes:
        print(f"\n--- {test_class.__name__} ---")
        instance = test_class()
        for method_name in dir(instance):
            if method_name.startswith('test_'):
                method = getattr(instance, method_name)
                try:
                    method()
                    print(f"  [PASS] {method_name}")
                    passed += 1
                except AssertionError as e:
                    print(f"  [FAIL] {method_name}: {e}")
                    failed += 1
                except Exception as e:
                    print(f"  [ERROR] {method_name}: {e}")
                    failed += 1

    print("\n" + "=" * 60)
    print(f"结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    return failed == 0


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
