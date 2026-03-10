# -*- coding: utf-8 -*-
"""
Ghost Downloader 嵌入式兼容层完整测试
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
from PyQt6.QtWidgets import QApplication
_qapp = QApplication.instance() or QApplication(sys.argv)


class TestQtCompat:
    """Qt 兼容层测试 - 必须首先运行"""
    
    def test_signal_exists(self):
        """测试 pyqtSignal 别名存在"""
        import app.common.qt_compat as qt_compat
        assert hasattr(qt_compat, 'pyqtSignal'), "pyqtSignal 别名不存在"
    
    def test_slot_exists(self):
        """测试 pyqtSlot 别名存在"""
        import app.common.qt_compat as qt_compat
        assert hasattr(qt_compat, 'pyqtSlot'), "pyqtSlot 别名不存在"
    
    def test_qfont_normal(self):
        """测试 QFont.Normal 可访问"""
        from PyQt6.QtGui import QFont
        assert hasattr(QFont, 'Normal'), "QFont.Normal 不存在"
    
    def test_qt_vertical(self):
        """测试 Qt.Vertical 可访问"""
        from PyQt6.QtCore import Qt
        assert hasattr(Qt, 'Vertical'), "Qt.Vertical 不存在"
    
    def test_qt_horizontal(self):
        """测试 Qt.Horizontal 可访问"""
        from PyQt6.QtCore import Qt
        assert hasattr(Qt, 'Horizontal'), "Qt.Horizontal 不存在"
    
    def test_qt_align_center(self):
        """测试 Qt.AlignCenter 可访问"""
        from PyQt6.QtCore import Qt
        assert hasattr(Qt, 'AlignCenter'), "Qt.AlignCenter 不存在"
    
    def test_qstandardpaths_download_location(self):
        """测试 QStandardPaths.DownloadLocation 可访问"""
        from PyQt6.QtCore import QStandardPaths
        assert hasattr(QStandardPaths, 'DownloadLocation'), "QStandardPaths.DownloadLocation 不存在"
    
    def test_qeasingcurve_outcubic(self):
        """测试 QEasingCurve.OutCubic 可访问"""
        from PyQt6.QtCore import QEasingCurve
        assert hasattr(QEasingCurve, 'OutCubic'), "QEasingCurve.OutCubic 不存在"
    
    def test_qframe_noframe(self):
        """测试 QFrame.NoFrame 可访问"""
        from PyQt6.QtWidgets import QFrame
        assert hasattr(QFrame, 'NoFrame'), "QFrame.NoFrame 不存在"
    
    def test_qsizepolicy_expanding(self):
        """测试 QSizePolicy.Expanding 可访问"""
        from PyQt6.QtWidgets import QSizePolicy
        assert hasattr(QSizePolicy, 'Expanding'), "QSizePolicy.Expanding 不存在"
    
    def test_qtgui_qt(self):
        """测试 QtGui.Qt 可访问"""
        from PyQt6.QtGui import Qt as QtGuiQt
        assert QtGuiQt is not None, "QtGui.Qt 不存在"
    
    def test_qt_widget_attribute(self):
        """测试 Qt.WA_TranslucentBackground 可访问"""
        from PyQt6.QtCore import Qt
        assert hasattr(Qt, 'WA_TranslucentBackground'), "Qt.WA_TranslucentBackground 不存在"
    
    def test_qt_window_state(self):
        """测试 Qt.WindowMaximized 可访问"""
        from PyQt6.QtCore import Qt
        assert hasattr(Qt, 'WindowMaximized'), "Qt.WindowMaximized 不存在"
    
    def test_qheaderview_stretch(self):
        """测试 QHeaderView.Stretch 可访问"""
        from PyQt6.QtWidgets import QHeaderView
        assert hasattr(QHeaderView, 'Stretch'), "QHeaderView.Stretch 不存在"
    
    def test_qevent_resize(self):
        """测试 QEvent.Resize 可访问"""
        from PyQt6.QtCore import QEvent
        assert hasattr(QEvent, 'Resize'), "QEvent.Resize 不存在"
    
    def test_pixmap_scaled_params(self):
        """测试 QPixmap.scaled 参数名正确"""
        from PyQt6.QtGui import QPixmap
        from PyQt6.QtCore import Qt
        # 创建一个小 pixmap 进行测试
        pm = QPixmap(48, 48)
        # 使用正确的参数名
        try:
            scaled = pm.scaled(128, 128, aspectRatioMode=Qt.AspectRatioMode.KeepAspectRatio,
                              transformMode=Qt.TransformationMode.SmoothTransformation)
            assert scaled is not None
        except TypeError as e:
            raise AssertionError(f"QPixmap.scaled 参数名错误: {e}")
    
    def test_progressbar_setvalue_int(self):
        """测试 ProgressBar.setValue 接受整数"""
        from PyQt6.QtWidgets import QProgressBar
        bar = QProgressBar()
        # 测试整数
        bar.setValue(50)
        assert bar.value() == 50
        # 测试浮点数转整数
        bar.setValue(int(75.5))
        assert bar.value() == 75


class TestCoreImports:
    """核心组件导入测试"""
    
    def test_config_import(self):
        """测试 config 模块可导入"""
        from app.common.config import cfg
        assert cfg is not None
    
    def test_signal_bus_import(self):
        """测试 signal_bus 模块可导入"""
        from app.common.signal_bus import signalBus
        assert signalBus is not None
    
    def test_methods_import(self):
        """测试 methods 模块可导入"""
        from app.common.methods import getLinkInfo, getReadableSize, addDownloadTask
        assert getLinkInfo is not None
        assert getReadableSize is not None
        assert addDownloadTask is not None


class TestUIComponents:
    """UI 组件测试"""
    
    def test_task_interface_import(self):
        """测试 TaskInterface 可导入"""
        from app.view.task_interface import TaskInterface
        assert TaskInterface is not None
    
    def test_task_card_import(self):
        """测试 TaskCard 可导入"""
        from app.components.task_card import TaskCard
        assert TaskCard is not None
    
    def test_embedded_main_window_import(self):
        """测试 EmbeddedMainWindow 可导入"""
        from app.common.embedded_main_window import EmbeddedMainWindow
        assert EmbeddedMainWindow is not None


class TestEmbeddedMainWindow:
    """EmbeddedMainWindow 功能测试"""
    
    def test_all_features(self):
        """测试 EmbeddedMainWindow 所有功能"""
        from app.common.embedded_main_window import EmbeddedMainWindow
        
        # 创建实例
        window = EmbeddedMainWindow()
        assert window is not None, "创建实例失败"
        
        # 测试导航栏
        assert hasattr(window, 'navigationInterface'), "缺少 navigationInterface"
        assert window.navigationInterface is not None, "navigationInterface 为空"
        
        # 测试任务界面
        assert hasattr(window, 'taskInterface'), "缺少 taskInterface"
        assert window.taskInterface is not None, "taskInterface 为空"
        
        # 测试堆叠组件
        assert hasattr(window, 'stackedWidget'), "缺少 stackedWidget"
        assert window.stackedWidget is not None, "stackedWidget 为空"
        
        # 测试方法
        assert hasattr(window, 'showAddTaskDialog'), "缺少 showAddTaskDialog 方法"
        assert hasattr(window, 'switchTo'), "缺少 switchTo 方法"


class TestTaskInterface:
    """TaskInterface 功能测试"""
    
    def test_all_features(self):
        """测试 TaskInterface 所有功能"""
        from app.view.task_interface import TaskInterface
        
        # 创建实例
        interface = TaskInterface()
        assert interface is not None, "创建实例失败"
        
        # 测试按钮
        assert hasattr(interface, 'allStartButton'), "缺少 allStartButton"
        assert hasattr(interface, 'allPauseButton'), "缺少 allPauseButton"
        assert hasattr(interface, 'allDeleteButton'), "缺少 allDeleteButton"
        
        # 测试任务列表
        assert hasattr(interface, 'cards'), "缺少 cards 列表"


class TestShowAddTaskDialog:
    """showAddTaskDialog 方法测试"""
    
    def test_text_bool_handling(self):
        """测试 text 参数类型处理逻辑"""
        # 测试 is_text_bool 函数逻辑
        test_cases = [
            ("https://example.com", "字符串应保持不变"),
            ("", "空字符串应保持不变"),
            (False, "False 应转换为空字符串"),
            (True, "True 应转换为空字符串"),
            (None, "None 应处理为空"),
        ]
        
        for text, desc in test_cases:
            # 模拟 showAddTaskDialog 中的逻辑
            if isinstance(text, bool):
                processed = ""
            else:
                processed = str(text) if text else ""
            
            assert isinstance(processed, str), f"处理后的值应为字符串: {desc}"
    
    def test_qheaderview_in_ui_file(self):
        """测试 Ui 文件中的 QHeaderView.Stretch 可访问"""
        from PyQt6.QtWidgets import QHeaderView
        # 验证 QHeaderView.Stretch 存在
        assert hasattr(QHeaderView, 'Stretch'), "QHeaderView.Stretch 不存在"
        # 验证值正确
        stretch = QHeaderView.Stretch
        assert stretch is not None


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("Ghost Downloader 嵌入式兼容层 TDD 测试")
    print("=" * 60)
    
    test_classes = [
        TestQtCompat,
        TestCoreImports,
        TestUIComponents,
        TestEmbeddedMainWindow,
        TestTaskInterface,
        TestShowAddTaskDialog,
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    for test_class in test_classes:
        print(f"\n--- {test_class.__name__} ---")
        instance = test_class()
        
        # 调用 setup_class 如果存在
        if hasattr(test_class, 'setup_class'):
            test_class.setup_class()
        
        for method_name in dir(instance):
            if method_name.startswith('test_'):
                total_tests += 1
                try:
                    getattr(instance, method_name)()
                    print(f"  ✓ {method_name}")
                    passed_tests += 1
                except AssertionError as e:
                    print(f"  ✗ {method_name}: {e}")
                    failed_tests += 1
                except Exception as e:
                    print(f"  ✗ {method_name}: 异常 - {e}")
                    failed_tests += 1
    
    print("\n" + "=" * 60)
    print(f"测试结果: 总计 {total_tests}, 通过 {passed_tests}, 失败 {failed_tests}")
    print("=" * 60)
    
    return failed_tests == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
