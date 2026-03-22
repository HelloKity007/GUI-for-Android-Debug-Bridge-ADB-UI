# -*- coding: utf-8 -*-
"""
Ghost Downloader 嵌入式主界面
模拟 MSFluentWindow 布局，可嵌入到 Tab 页中
"""
import sys
from pathlib import Path

# 初始化兼容层（必须在导入 PySide6 模块之前）
import app.common.qt_compat as qt_compat

# 初始化日志
try:
    from app.common.logger_config import logger
except ImportError:
    import logging
    logger = logging.getLogger("embedded_main_window")

logger.info("初始化 EmbeddedMainWindow...")

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QLabel
)
from PySide6.QtCore import Qt

from qfluentwidgets import (
    FluentIcon as FIF, NavigationInterface, NavigationItemPosition,
    setTheme, Theme, isDarkTheme
)

from app.view.task_interface import TaskInterface
from app.common.config import cfg
from app.common.signal_bus import signalBus
from app.components.add_task_dialog import AddTaskOptionDialog


class EmbeddedMainWindow(QWidget):
    """
    嵌入式 Ghost Downloader 主界面
    模拟 MSFluentWindow 的导航布局，可嵌入到 Tab 中
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("EmbeddedMainWindow")
        
        # 创建任务界面
        self.taskInterface = TaskInterface(self)
        
        # 设置界面延迟加载（避免初始化时的类型问题）
        self._settingInterface = None
        
        self.setupUi()
        self.initNavigation()
        self._connect_signals()
        
        # 应用主题
        self._apply_theme()
    
    @property
    def settingInterface(self):
        """延迟加载设置界面"""
        if self._settingInterface is None:
            try:
                from app.view.setting_interface import SettingInterface
                self._settingInterface = SettingInterface(self)
                self.stackedWidget.addWidget(self._settingInterface)
            except Exception as e:
                print(f"加载设置界面失败: {e}")
                return None
        return self._settingInterface
    
    def setupUi(self):
        """设置界面布局"""
        self.hBoxLayout = QHBoxLayout(self)
        self.hBoxLayout.setSpacing(0)
        self.hBoxLayout.setContentsMargins(0, 0, 0, 0)
        
        # 导航栏
        self.navigationInterface = NavigationInterface(
            self, showReturnButton=False, collapsible=True
        )
        self.navigationInterface.setExpandWidth(200)
        
        # 内容区域
        self.stackedWidget = QStackedWidget(self)
        self.stackedWidget.addWidget(self.taskInterface)
        
        # 布局
        self.hBoxLayout.addWidget(self.navigationInterface)
        self.hBoxLayout.addWidget(self.stackedWidget, 1)
        
        # 设置样式
        self.setStyleSheet("""
            EmbeddedMainWindow {
                background-color: transparent;
            }
            QStackedWidget {
                background-color: transparent;
                border: none;
            }
        """)
    
    def initNavigation(self):
        """初始化导航"""
        # 任务列表
        self.navigationInterface.addItem(
            routeKey=self.taskInterface.objectName(),
            text=self.tr("任务列表"),
            icon=FIF.DOWNLOAD,
            onClick=lambda: self.switchTo(self.taskInterface)
        )
        
        # 新建任务按钮
        self.navigationInterface.addItem(
            routeKey='addTaskButton',
            text=self.tr('新建任务'),
            selectable=False,
            icon=FIF.ADD,
            onClick=self.showAddTaskDialog,
            position=NavigationItemPosition.TOP,
        )
        
        # 设置
        self.navigationInterface.addItem(
            routeKey='settingInterface',
            text=self.tr("设置"),
            icon=FIF.SETTING,
            onClick=self._switch_to_settings,
            position=NavigationItemPosition.BOTTOM
        )
        
        # 默认选中任务列表
        self.navigationInterface.setCurrentItem(self.taskInterface.objectName())
    
    def _switch_to_settings(self):
        """切换到设置界面"""
        settings = self.settingInterface
        if settings:
            self.switchTo(settings)
    
    def _connect_signals(self):
        """连接信号"""
        # 连接新建任务信号
        signalBus.addTaskSignal.connect(self._on_add_task)
    
    def switchTo(self, widget):
        """切换到指定界面"""
        self.stackedWidget.setCurrentWidget(widget)
        self.navigationInterface.setCurrentItem(widget.objectName() if hasattr(widget, 'objectName') else 'settingInterface')
    
    def showAddTaskDialog(self, text: str = "", headers: dict = None):
        """显示新建任务对话框"""
        # 处理 text 可能是 bool 类型的情况
        if isinstance(text, bool):
            text = ""
        text_preview = str(text)[:50] if text else 'None'
        logger.info(f"showAddTaskDialog 被调用, text={text_preview}...")
        try:
            from app.components.add_task_dialog import AddTaskOptionDialog
            logger.debug("AddTaskOptionDialog 导入成功")
            AddTaskOptionDialog.showAddTaskOptionDialog(text, self.window(), headers)
            logger.info("对话框显示成功")
        except Exception as e:
            logger.error(f"showAddTaskDialog 失败: {e}")
            from app.common.logger_config import log_exception
            log_exception(e, "showAddTaskDialog")
            raise
    
    def _on_add_task(self, url, fileName, filePath, headers, status, preBlockNum, notCreateHistoryFile, fileSize):
        """处理任务添加信号 - 转发到 TaskInterface"""
        # TaskInterface 已连接 signalBus，这里不需要额外处理
        pass
    
    def _apply_theme(self):
        """应用主题设置"""
        try:
            if cfg.customThemeMode.value == 'Dark':
                setTheme(Theme.DARK, save=False)
            elif cfg.customThemeMode.value == 'Light':
                setTheme(Theme.LIGHT, save=False)
            else:
                setTheme(Theme.AUTO, save=False)
        except Exception:
            pass
    
    def tr(self, text):
        """翻译（简化实现）"""
        return text
