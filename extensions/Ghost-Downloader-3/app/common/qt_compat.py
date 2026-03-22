# -*- coding: utf-8 -*-
"""
@Description: PySide6 统一兼容层
@Version: 2.0.0
@Date: 2026-03-22
@Author: AI Assistant
@FilePath: extensions/Ghost-Downloader-3/app/common/qt_compat.py

统一使用 PySide6，提供与 PyQt6 兼容的别名
"""
import sys

def _log(msg):
    """简单日志输出"""
    try:
        from app.common.logger_config import logger
        logger.debug(f"[qt_compat] {msg}")
    except:
        pass

# ==================== PySide6 核心模块 ====================
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *

# 网络模块
try:
    from PySide6.QtNetwork import *
except ImportError:
    _log("QtNetwork not available")

# WebSockets 模块
try:
    from PySide6.QtWebSockets import *
except ImportError:
    _log("QtWebSockets not available")

# SVG 模块
try:
    from PySide6.QtSvg import *
except ImportError:
    _log("QtSvg not available")

try:
    from PySide6.QtSvgWidgets import *
except ImportError:
    _log("QtSvgWidgets not available")

# XML 模块
try:
    from PySide6.QtXml import *
except ImportError:
    _log("QtXml not available")

# ==================== PyQt6 兼容别名 ====================
# PyQt6 使用 pyqtSignal/pyqtSlot/pyqtProperty
# PySide6 使用 Signal/Slot/Property
pyqtSignal = Signal
pyqtSlot = Slot
pyqtProperty = Property

# 注入到 QtCore 模块
import PySide6.QtCore as _QtCore
_QtCore.pyqtSignal = Signal
_QtCore.pyqtSlot = Slot
_QtCore.pyqtProperty = Property

# 注入 Qt 到 QtGui（兼容某些代码从 QtGui 导入 Qt）
import PySide6.QtGui as _QtGui
_QtGui.Qt = Qt

_log("PySide6 兼容层初始化完成")
