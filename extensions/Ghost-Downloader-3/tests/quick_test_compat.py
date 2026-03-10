# -*- coding: utf-8 -*-
"""快速测试脚本 - 验证直接嵌入 TaskInterface"""
import sys
import os

# 添加项目根目录到 sys.path
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_dir)

print('=== 测试 1: QFont.Normal 问题 ===')
from PyQt6.QtGui import QFont
print(f'QFont 有 Weight 属性: {hasattr(QFont, "Weight")}')
if hasattr(QFont, 'Weight'):
    print(f'QFont.Weight 有 Normal 属性: {hasattr(QFont.Weight, "Normal")}')
print(f'QFont 直接有 Normal 属性: {hasattr(QFont, "Normal")}')

print()
print('=== 测试 2: pyqtSignal/pyqtSlot 问题 ===')
from PyQt6.QtCore import pyqtSignal, pyqtSlot
print(f'pyqtSignal 可用: True')
print(f'pyqtSlot 可用: True')

print()
print('=== 测试 3: qt_compat 兼容层 ===')
import app.common.qt_compat as qt_compat
print(f'pyqtSignal 在 qt_compat 中: {hasattr(qt_compat, "pyqtSignal")}')
print(f'pyqtSlot 在 qt_compat 中: {hasattr(qt_compat, "pyqtSlot")}')

# 测试 QFont 兼容
print(f'QFont.Normal 可访问: {hasattr(QFont, "Normal")}')

# 测试 Qt 枚举兼容
from PyQt6.QtCore import Qt
print(f'Qt.Vertical 可访问: {hasattr(Qt, "Vertical")}')
print(f'Qt.AlignCenter 可访问: {hasattr(Qt, "AlignCenter")}')

# 测试 QStandardPaths 兼容
from PyQt6.QtCore import QStandardPaths
print(f'QStandardPaths.DownloadLocation 可访问: {hasattr(QStandardPaths, "DownloadLocation")}')

# 测试 QEasingCurve 兼容
from PyQt6.QtCore import QEasingCurve
print(f'QEasingCurve.OutCubic 可访问: {hasattr(QEasingCurve, "OutCubic")}')

print()
print('=== 测试 4: 初始化配置 ===')
try:
    from pathlib import Path
    from qfluentwidgets import qconfig
    from app.common.config import cfg
    config_file = Path(project_dir) / "Ghost Downloader 配置文件.json"
    if config_file.exists():
        qconfig.load(str(config_file), cfg)
    cfg.appPath = project_dir
    print(f'配置加载成功! appPath = {cfg.appPath}')
except Exception as e:
    print(f'配置加载失败: {e}')

print()
print('=== 测试 5: 直接导入 TaskInterface ===')
try:
    from app.view.task_interface import TaskInterface
    print('TaskInterface 导入成功!')
except Exception as e:
    print(f'TaskInterface 导入失败: {e}')

print()
print('=== 测试 6: 创建 EmbeddedMainWindow 实例（需要 QApplication） ===')
try:
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    
    from app.common.embedded_main_window import EmbeddedMainWindow
    embedded_main = EmbeddedMainWindow()
    print(f'EmbeddedMainWindow 实例创建成功!')
    print(f'  - 包含导航栏: {hasattr(embedded_main, "navigationInterface")}')
    print(f'  - 包含任务界面: {hasattr(embedded_main, "taskInterface")}')
    print(f'  - 包含设置界面: {hasattr(embedded_main, "settingInterface")}')
except Exception as e:
    print(f'EmbeddedMainWindow 实例创建失败: {e}')

print()
print('=== 测试 7: 完整导入 Ghost Downloader 组件 ===')
try:
    from app.common.config import cfg
    print('config 导入成功!')
except Exception as e:
    print(f'config 导入失败: {e}')

try:
    from app.common.signal_bus import signalBus
    print('signal_bus 导入成功!')
except Exception as e:
    print(f'signal_bus 导入失败: {e}')

try:
    from app.common.methods import getLinkInfo, getReadableSize, addDownloadTask
    print('methods 导入成功!')
except Exception as e:
    print(f'methods 导入失败: {e}')

try:
    from app.components.task_card import TaskCard
    print('TaskCard 导入成功!')
except Exception as e:
    print(f'TaskCard 导入失败: {e}')

print()
print('=== 所有测试完成 ===')
