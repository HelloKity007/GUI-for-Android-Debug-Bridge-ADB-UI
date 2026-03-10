# -*- coding: utf-8 -*-
"""
Ghost Downloader 嵌入式界面
用于嵌入到 ADB Tool 的 Tab 页中
"""
import sys
import os

# 在导入任何 PyQt6 模块之前，先设置兼容层
import app.common.qt_compat as qt_compat

# Path 必须在 qt_compat 之后导入，避免被通配符导入覆盖
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QTextEdit, QFileDialog, QMessageBox, QScrollArea, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

# 导入 Ghost Downloader 核心组件
try:
    from qfluentwidgets import FluentIcon as FIF
    HAS_QFLUENTWIDGETS = True
except ImportError:
    HAS_QFLUENTWIDGETS = False

from app.common.config import cfg, Headers
from app.common.methods import getLinkInfo, getReadableSize, addDownloadTask
from app.common.signal_bus import signalBus


class EmbeddedDownloaderWidget(QWidget):
    """嵌入式下载器组件"""
    
    status_changed = pyqtSignal(str)
    
    def __init__(self, project_dir: str, parent=None):
        super().__init__(parent)
        self.project_dir = project_dir
        self.download_tasks = []
        self.task_cards = []
        
        self._init_ghost_config()
        self.setup_ui()
        self._connect_signals()
    
    def _init_ghost_config(self):
        """初始化 Ghost Downloader 配置"""
        config_file = Path(self.project_dir) / "extensions" / "Ghost-Downloader-3" / "Ghost Downloader 配置文件.json"
        try:
            from qfluentwidgets import qconfig
            if config_file.exists():
                qconfig.load(str(config_file), cfg)
            cfg.appPath = str(config_file.parent)
        except Exception as e:
            print(f"初始化配置失败: {e}")
    
    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 工具栏
        toolbar_layout = QHBoxLayout()
        
        self.add_task_btn = QPushButton("➕ 新建任务")
        self.add_task_btn.setMinimumHeight(36)
        self.add_task_btn.clicked.connect(self._show_add_task_dialog)
        toolbar_layout.addWidget(self.add_task_btn)
        
        self.open_folder_btn = QPushButton("📂 打开目录")
        self.open_folder_btn.setMinimumHeight(36)
        self.open_folder_btn.clicked.connect(self._open_download_folder)
        toolbar_layout.addWidget(self.open_folder_btn)
        
        self.settings_btn = QPushButton("⚙️ 打开完整界面")
        self.settings_btn.setMinimumHeight(36)
        self.settings_btn.clicked.connect(self._open_full_window)
        toolbar_layout.addWidget(self.settings_btn)
        
        toolbar_layout.addStretch()
        layout.addLayout(toolbar_layout)
        
        # 下载路径显示
        path_layout = QHBoxLayout()
        path_label = QLabel("下载目录:")
        path_layout.addWidget(path_label)
        self.path_display = QLabel(self._get_download_folder())
        self.path_display.setStyleSheet("color: #0078d4; font-weight: bold;")
        path_layout.addWidget(self.path_display, 1)
        layout.addLayout(path_layout)
        
        # 任务列表区域
        self.task_list_widget = QWidget()
        self.task_list_layout = QVBoxLayout(self.task_list_widget)
        self.task_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.task_list_layout.setSpacing(5)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.task_list_widget)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(scroll, 1)
        
        # 状态栏
        self.status_label = QLabel("总速度: 0 KB/s | 活动任务: 0")
        self.status_label.setStyleSheet("color: #666; font-size: 10pt;")
        layout.addWidget(self.status_label)
        
        # 定时器更新状态
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_status)
        self.update_timer.start(1000)
    
    def _connect_signals(self):
        """连接信号"""
        signalBus.addTaskSignal.connect(self._on_add_task)
    
    def _get_download_folder(self) -> str:
        """获取下载目录"""
        try:
            return cfg.downloadFolder.value
        except:
            from PyQt6.QtCore import QStandardPaths
            return QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
    
    def _show_add_task_dialog(self):
        """显示添加任务对话框"""
        url, ok = QInputDialog.getText(self, "新建下载任务", "输入下载链接:")
        if ok and url and url.strip():
            self._add_download_task(url.strip())
    
    def _add_download_task(self, url: str):
        """添加下载任务"""
        addDownloadTask(url, headers=Headers)
        self.status_changed.emit(f"已添加任务: {url[:50]}...")
    
    def _open_download_folder(self):
        """打开下载目录"""
        import subprocess
        folder = self._get_download_folder()
        if Path(folder).exists():
            folder_path = str(Path(folder).resolve())
            if sys.platform == "win32":
                subprocess.run(["explorer.exe", folder_path], check=False)
            elif sys.platform == "darwin":
                subprocess.run(["open", folder_path], check=False)
            else:
                subprocess.run(["xdg-open", folder_path], check=False)
    
    def _open_full_window(self):
        """打开完整界面"""
        import subprocess
        main_script = Path(self.project_dir) / "extensions" / "Ghost-Downloader-3" / "Ghost-Downloader-3.py"
        if main_script.exists():
            if sys.platform == "win32":
                subprocess.Popen([sys.executable, str(main_script)], 
                               cwd=str(main_script.parent),
                               creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                subprocess.Popen([sys.executable, str(main_script)], cwd=str(main_script.parent))
    
    def _on_add_task(self, url, fileName, filePath, headers, status, preBlockNum, notCreateHistoryFile, fileSize):
        """处理任务添加信号"""
        self._create_task_card(url, fileName or "", filePath or self._get_download_folder(), 
                              headers, status, preBlockNum, int(fileSize) if fileSize else -1)
    
    def _create_task_card(self, url, fileName, filePath, headers, status, preBlockNum, fileSize):
        """创建任务卡片"""
        try:
            from app.components.task_card import TaskCard
            card = TaskCard(url, fileName, filePath, preBlockNum, headers, status, True, fileSize, self.task_list_widget)
            self.task_cards.append(card)
            self.task_list_layout.addWidget(card)
            card.show()
        except Exception as e:
            print(f"创建任务卡片失败: {e}")
            # 创建简单的任务显示
            simple_card = QLabel(f"📥 {fileName or url[:50]}")
            simple_card.setStyleSheet("padding: 10px; background: #f0f0f0; border-radius: 5px;")
            self.task_list_layout.addWidget(simple_card)
    
    def _update_status(self):
        """更新状态显示"""
        total_speed = 0
        active_count = 0
        
        for card in self.task_cards:
            if hasattr(card, 'status') and card.status == 'working':
                active_count += 1
                if hasattr(card, 'task') and card.task and hasattr(card.task, 'historySpeed'):
                    speed = sum(card.task.historySpeed) / 10 if card.task.historySpeed else 0
                    total_speed += speed
        
        speed_str = self._format_speed(total_speed)
        self.status_label.setText(f"总速度: {speed_str}/s | 活动任务: {active_count}")
        self.path_display.setText(self._get_download_folder())
    
    def _format_speed(self, speed: int) -> str:
        """格式化速度"""
        if speed < 1024:
            return f"{speed:.0f} B"
        elif speed < 1024 * 1024:
            return f"{speed / 1024:.1f} KB"
        elif speed < 1024 * 1024 * 1024:
            return f"{speed / (1024 * 1024):.1f} MB"
        else:
            return f"{speed / (1024 * 1024 * 1024):.2f} GB"
