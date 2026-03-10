# -*- coding: utf-8 -*-
"""
Ghost Downloader 嵌入式主窗口
用于嵌入到 ADB Tool 的 Tab 页中
"""
import sys
from pathlib import Path

# 已转换为原生 PyQt6，不再需要兼容层
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QLabel
)
from PyQt6.QtCore import Qt

from qfluentwidgets import (
    FluentIcon as FIF, NavigationInterface, NavigationItemPosition,
    NavigationWidget, MSFluentWindow
)

from app.common.config import cfg
from app.common.signal_bus import signalBus
from app.common.methods import addDownloadTask


class EmbeddedMainWindow(QWidget):
    """嵌入式主窗口 - 用于嵌入到其他应用程序中"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 初始化界面
        self.setupUi()
        
        # 创建子界面
        self.taskInterface = None
        self.settingInterface = None
        
        try:
            from app.view.task_interface import TaskInterface
            self.taskInterface = TaskInterface(self)
            self.stackedWidget.addWidget(self.taskInterface)
        except Exception as e:
            print(f"加载 TaskInterface 失败: {e}")
            placeholder = QLabel("任务界面加载失败")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.stackedWidget.addWidget(placeholder)
        
        try:
            from app.view.setting_interface import SettingInterface
            self.settingInterface = SettingInterface(self)
            self.stackedWidget.addWidget(self.settingInterface)
        except Exception as e:
            print(f"加载 SettingInterface 失败: {e}")
        
        self.initNavigation()
        
        if self.taskInterface:
            self.stackedWidget.setCurrentWidget(self.taskInterface)
    
    def setupUi(self):
        self.setObjectName("EmbeddedMainWindow")
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        self.navigationInterface = NavigationInterface(
            self, showReturnButton=False, showMenuButton=False
        )
        self.navigationInterface.setExpandWidth(200)
        self.navigationInterface.setCollapsible(False)
        self.layout.addWidget(self.navigationInterface)
        
        self.stackedWidget = QStackedWidget(self)
        self.stackedWidget.setObjectName("stackedWidget")
        self.layout.addWidget(self.stackedWidget, 1)
    
    def initNavigation(self):
        if self.taskInterface:
            self.navigationInterface.addItem(
                routeKey='taskInterface',
                icon=FIF.DOWNLOAD,
                text=self.tr("任务列表"),
                onClick=lambda: self.switchTo(self.taskInterface)
            )
        
        self.navigationInterface.addItem(
            routeKey='addTaskButton',
            text=self.tr('新建任务'),
            selectable=False,
            icon=FIF.ADD,
            onClick=self.showAddTaskDialog,
            position=NavigationItemPosition.TOP,
        )
        
        if self.settingInterface:
            self.navigationInterface.addItem(
                routeKey='settingInterface',
                icon=FIF.SETTING,
                text=self.tr("设置"),
                onClick=lambda: self.switchTo(self.settingInterface),
                position=NavigationItemPosition.BOTTOM
            )
    
    def switchTo(self, widget):
        if widget:
            self.stackedWidget.setCurrentWidget(widget)
    
    def showAddTaskDialog(self, text=""):
        from PyQt6.QtWidgets import QInputDialog
        
        if isinstance(text, bool):
            text = ""
        elif text is None:
            text = ""
        else:
            text = str(text) if text else ""
        
        url, ok = QInputDialog.getText(
            self, 
            self.tr("新建下载任务"), 
            self.tr("输入下载链接:"),
            text=text
        )
        
        if ok and url and url.strip():
            self._addDownloadTask(url.strip())
    
    def _addDownloadTask(self, url: str):
        try:
            from app.common.config import Headers
            addDownloadTask(url, headers=Headers)
        except Exception as e:
            print(f"添加任务失败: {e}")