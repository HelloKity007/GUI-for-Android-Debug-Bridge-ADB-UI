import sys
import subprocess
import threading
import os
import shlex
import tempfile
import json
from pathlib import Path
import logging

# 配置日志
from datetime import datetime
_log_dir = Path(__file__).parent / "logs"
_log_dir.mkdir(parents=True, exist_ok=True)
_log_file = _log_dir / f"adb_gui_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(_log_file), encoding='utf-8')
    ]
)
logger = logging.getLogger("adb_gui")
logger.info(f"日志文件: {_log_file}")

from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QTextEdit, QLineEdit, QFileDialog,
    QMessageBox, QInputDialog, QFrame, QScrollArea, QGroupBox, QSizePolicy,
    QDialog, QListWidget, QCheckBox, QRadioButton, QButtonGroup, QTabWidget
)
from PySide6.QtCore import Qt, QThread, Signal, Slot, QTimer, QProcess, QFileSystemWatcher, QMetaObject, Q_ARG, QMimeData
from PySide6.QtGui import QFont, QColor, QPalette, QDrag, QShortcut, QKeySequence

# PyQt6 兼容别名
pyqtSignal = Signal
pyqtSlot = Slot


class SmoothScrollArea(QScrollArea):
    """滚动区域子类：覆写 wheelEvent 以增大单次滚动步长，消除卡顿感"""
    SCROLL_STEP = 60  # 每次滚轮事件滚动的像素数

    def wheelEvent(self, event):
        bar = self.verticalScrollBar()
        delta = event.angleDelta().y()
        # angleDelta 单位为 1/8°，标准滚轮每格 120 单位（15°）
        steps = delta / 120
        bar.setValue(int(bar.value() - steps * self.SCROLL_STEP))
        event.accept()

# Import from organized modules
from core import ADBManager, ScrcpyManager
from ui import ThemeManager, MarkdownRenderer
from dialogs import (
    FileManagerDialog, AppManagerDialog, TestScriptsDialog,
    ClusterControlDialog, JadxDecompilerDialog, PluginManagerDialog
)

# Import plugin system
from framework.plugin.plugin_manager import PluginManager
from framework.event.event_bus import EventBus
from utils.config_manager import ConfigManager


class DraggableButton(QPushButton):
    """支持拖拽的按钮控件"""
    
    # 信号：拖拽排序
    reorder_requested = pyqtSignal(str, str, str)  # source_btn_id, target_btn_id, target_group_id
    
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setAcceptDrops(True)
        self.drag_start_pos = None
    
    def mousePressEvent(self, event):
        """记录拖拽起始位置"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.position().toPoint()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """开始拖拽"""
        if not self.drag_start_pos:
            return
        
        # 检查是否移动了足够距离
        distance = (event.position().toPoint() - self.drag_start_pos).manhattanLength()
        if distance < 10:
            return
        
        # 创建拖拽对象
        drag = QDrag(self)
        mime_data = QMimeData()
        btn_id = self.property('button_id') or ''
        group_id = self.property('group_id') or ''
        mime_data.setText(f"{btn_id}|{group_id}")
        mime_data.setData('application/x-button-id', btn_id.encode())
        mime_data.setData('application/x-group-id', group_id.encode())
        drag.setMimeData(mime_data)
        
        # 执行拖拽
        drag.exec(Qt.DropAction.MoveAction | Qt.DropAction.CopyAction)
    
    def dragEnterEvent(self, event):
        """接受拖拽进入"""
        if event.mimeData().hasFormat('application/x-button-id'):
            event.acceptProposedAction()
    
    def dragMoveEvent(self, event):
        """拖拽移动"""
        if event.mimeData().hasFormat('application/x-button-id'):
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        """处理拖放"""
        mime = event.mimeData()
        if mime.hasFormat('application/x-button-id'):
            source_btn_id = bytes(mime.data('application/x-button-id')).decode()
            target_btn_id = self.property('button_id') or ''
            target_group_id = self.property('group_id') or ''
            
            # 发送排序请求，包含源按钮、目标按钮和目标组
            if source_btn_id != target_btn_id:
                self.reorder_requested.emit(source_btn_id, target_btn_id, target_group_id)
        
        event.acceptProposedAction()


class DraggableGroupBox(QGroupBox):
    """支持拖拽的分组控件"""
    
    group_reordered = pyqtSignal(str, str)  # source_group_id, target_group_id
    button_dropped = pyqtSignal(str, str)  # button_id, target_group_id
    
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.setAcceptDrops(True)
        self.drag_start_pos = None
        self._dragging_group = False
    
    def mousePressEvent(self, event):
        """记录拖拽起始位置 - 只在标题栏区域"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 检查是否在标题栏区域（通常是顶部20-30像素）
            rect = self.rect()
            title_height = 25  # 标题栏高度
            if event.position().toPoint().y() < title_height:
                self.drag_start_pos = event.position().toPoint()
                self._dragging_group = True
            else:
                self._dragging_group = False
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """开始拖拽 - 只拖拽组"""
        if not self._dragging_group or not self.drag_start_pos:
            super().mouseMoveEvent(event)
            return
        
        distance = (event.position().toPoint() - self.drag_start_pos).manhattanLength()
        if distance < 10:
            super().mouseMoveEvent(event)
            return
        
        drag = QDrag(self)
        mime_data = QMimeData()
        group_id = self.property('group_id') or ''
        mime_data.setData('application/x-group-drag', group_id.encode())
        drag.setMimeData(mime_data)
        result = drag.exec(Qt.DropAction.MoveAction)
        self._dragging_group = False
    
    def mouseReleaseEvent(self, event):
        """鼠标释放"""
        self._dragging_group = False
        self.drag_start_pos = None
        super().mouseReleaseEvent(event)
    
    def dragEnterEvent(self, event):
        """接受拖拽进入"""
        mime = event.mimeData()
        if mime.hasFormat('application/x-group-drag'):
            event.acceptProposedAction()
        elif mime.hasFormat('application/x-button-id'):
            event.acceptProposedAction()
    
    def dragMoveEvent(self, event):
        """拖拽移动"""
        mime = event.mimeData()
        if mime.hasFormat('application/x-group-drag'):
            event.acceptProposedAction()
        elif mime.hasFormat('application/x-button-id'):
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        """处理拖放"""
        mime = event.mimeData()
        if mime.hasFormat('application/x-group-drag'):
            source_group_id = bytes(mime.data('application/x-group-drag')).decode()
            target_group_id = self.property('group_id') or ''
            if source_group_id != target_group_id:
                self.group_reordered.emit(source_group_id, target_group_id)
                event.acceptProposedAction()
                return
        elif mime.hasFormat('application/x-button-id'):
            button_id = bytes(mime.data('application/x-button-id')).decode()
            target_group_id = self.property('group_id') or ''
            self.button_dropped.emit(button_id, target_group_id)
            event.acceptProposedAction()
            return
        event.ignore()


class ADBGUI(QMainWindow):
    """Main GUI Application"""
    
    # Signal for showing custom dialog (must be defined at class level)
    custom_dialog_ready = pyqtSignal(dict)
    app_list_ready = pyqtSignal(list)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ADB Tool for Windows")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(1000, 700)
        
        # Color schemes
        self.light_colors = {
            'bg': '#f5f5f5',
            'fg': '#1f1f1f',
            'accent': '#0078d4',
            'accent_hover': '#106ebe',
            'success': '#107c10',
            'warning': '#ff8c00',
            'error': '#d13438',
            'card_bg': '#ffffff',
            'border': '#e1e1e1',
            'text_secondary': '#666666',
            'text_tertiary': '#999999',
        }
        
        self.dark_colors = {
            'bg': '#1e1e1e',
            'fg': '#e0e0e0',
            'accent': '#0078d4',
            'accent_hover': '#106ebe',
            'success': '#4ec9b0',
            'warning': '#ffaa44',
            'error': '#f48771',
            'card_bg': '#252526',
            'border': '#3e3e42',
            'text_secondary': '#cccccc',
            'text_tertiary': '#858585',
        }
        
        # Current color scheme (will be set by apply_theme)
        self.colors = self.light_colors.copy()
        
        # Get project directory - executable's directory if running as exe, script directory if from source
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            project_dir = os.path.dirname(sys.executable)
        else:
            # Running as script
            project_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.project_dir = project_dir
        
        # Load config.json
        config_file = os.path.join(project_dir, 'config.json')
        self.config = ConfigManager(config_file)
        
        # DeGoogle state storage
        self.degoogle_state_file = os.path.join(project_dir, 'degoogle_state.json')
        self.degoogle_state = self.load_degoogle_state()
        
        # Load dark mode preference from config.json
        self.dark_mode = self.config.get('app.dark_mode', False)
        
        # Apply theme based on preference
        self.apply_theme()
        
        # Check for saved ADB path from config.json
        saved_adb_path = self.config.get_extension_path('adb', self.project_dir)
        if not saved_adb_path or not os.path.exists(saved_adb_path):
            saved_adb_path = None
        
        # Initialize ScrcpyManager with config path
        scrcpy_path = self.config.get_extension_path('scrcpy', self.project_dir)
        scrcpy_enabled = self.config.is_extension_enabled('scrcpy')
        
        if scrcpy_enabled and scrcpy_path and os.path.exists(scrcpy_path):
            self.scrcpy = ScrcpyManager(scrcpy_path)
        else:
            self.scrcpy = ScrcpyManager(None)
        self.scrcpy_processes = []  # Track active scrcpy processes
        
        # If no saved path, prompt user to select it before creating ADBManager
        if not saved_adb_path or not os.path.exists(saved_adb_path):
            # Show dialog to select ADB path on first boot
            QMessageBox.information(
                self,
                "ADB Path Required",
                "Please select the ADB executable (adb.exe) to continue.\n\n"
                "This is typically located in the 'platform-tools' folder of your Android SDK."
            )
            
            # Prompt user to select ADB folder or executable
            adb_path = self.prompt_for_adb_path()
            if not adb_path:
                # User cancelled - use fallback
                QMessageBox.warning(
                    self,
                    "ADB Path Required",
                    "ADB path is required. The application will use 'adb' from PATH as fallback.\n\n"
                    "You can set the ADB path later using the 'ADB Path' button."
                )
                saved_adb_path = 'adb'  # Fallback
            else:
                # Save to config.json (auto convert to relative path)
                self.config.set_extension_path('adb', adb_path, self.project_dir)
                saved_adb_path = adb_path
        
        # Create ADBManager with saved path
        self.adb = ADBManager(adb_path=saved_adb_path)
        # Set up logging callback for ADB manager
        self.adb.log_callback = self.log
        self.current_device = None
        self.log_thread = None
        self.log_running = False
        self.log_file = None  # Log file handle for auto-save
        
        # Initialize log storage for filtering
        self.all_logs = []
        
        self.setup_ui()
        self.update_adb_path_display()
        self.refresh_devices()
        
        # Auto-refresh devices every 5 seconds (silent mode to avoid log spam)
        self.auto_refresh_timer = QTimer()
        self.auto_refresh_timer.timeout.connect(lambda: self.refresh_devices(silent=True))
        self.auto_refresh_timer.start(5000)
        
        # Connect signal for custom dialog
        self.custom_dialog_ready.connect(self._show_custom_dialog)
        # Connect signal for app list dialog
        self.app_list_ready.connect(self.show_app_list_window)
    
    def setup_ui(self):
        """Setup the modern user interface"""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # Header with title
        header_layout = QHBoxLayout()
        self.title_label = QLabel("ADB Tool")
        self.title_label.setFont(QFont('Segoe UI', 20, QFont.Weight.Bold))
        self.title_label.setStyleSheet(f"color: {self.colors['fg']};")
        header_layout.addWidget(self.title_label)
        
        self.subtitle_label = QLabel("Android Device Manager")
        self.subtitle_label.setFont(QFont('Segoe UI', 10))
        self.subtitle_label.setStyleSheet(f"color: {self.colors['text_secondary']};")
        header_layout.addWidget(self.subtitle_label)
        header_layout.addStretch()
        
        # Open source components button
        self.opensource_btn = QPushButton("📜")
        self.opensource_btn.setToolTip("开源组件清单 / Open Source Components")
        self.opensource_btn.setMaximumWidth(40)
        self.opensource_btn.clicked.connect(self.show_opensource_components)
        header_layout.addWidget(self.opensource_btn)
        
        # Dark mode toggle button
        self.dark_mode_btn = QPushButton("🌙 Dark Mode" if not self.dark_mode else "☀️ Light Mode")
        self.dark_mode_btn.setMaximumWidth(120)
        self.dark_mode_btn.clicked.connect(self.toggle_dark_mode)
        header_layout.addWidget(self.dark_mode_btn)
        
        # Plugin manager button
        self.plugin_btn = QPushButton("🔌 Plugins")
        self.plugin_btn.setMaximumWidth(100)
        self.plugin_btn.setToolTip("插件管理 / Plugin Manager")
        self.plugin_btn.clicked.connect(self.show_plugin_manager)
        header_layout.addWidget(self.plugin_btn)
        
        # Edit mode toggle button
        self.edit_mode = False
        self.edit_mode_btn = QPushButton("✏️ Edit")
        self.edit_mode_btn.setMaximumWidth(80)
        self.edit_mode_btn.setToolTip("切换编辑模式 / Toggle Edit Mode")
        self.edit_mode_btn.clicked.connect(self.toggle_edit_mode)
        header_layout.addWidget(self.edit_mode_btn)
        
        main_layout.addLayout(header_layout)
        
        # ============ 主 Tab 结构 ============
        self.main_tab_widget = QTabWidget()
        self.main_tab_widget.setDocumentMode(True)  # 更现代的外观
        main_layout.addWidget(self.main_tab_widget, 1)
        
        # ============ Tab 1: ADB 工具 ============
        adb_tab = QWidget()
        adb_layout = QVBoxLayout(adb_tab)
        adb_layout.setContentsMargins(0, 0, 0, 0)
        adb_layout.setSpacing(10)
        
        # Device selection card
        device_group = QGroupBox("📱 Device Management")
        # Styles are applied globally via apply_theme
        device_layout = QVBoxLayout(device_group)
        device_layout.setSpacing(10)
        
        # Device selection row
        device_row = QHBoxLayout()
        device_row.addWidget(QLabel("Connected Devices:"))
        
        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(400)
        self.device_combo.currentTextChanged.connect(self.on_device_selected)
        device_row.addWidget(self.device_combo)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_devices)
        device_row.addWidget(refresh_btn)
        
        info_btn = QPushButton("ℹ️ Info")
        info_btn.clicked.connect(self.show_device_info)
        device_row.addWidget(info_btn)
        
        cluster_btn = QPushButton("🎛️ Cluster")
        cluster_btn.clicked.connect(self.show_cluster_control)
        device_row.addWidget(cluster_btn)
        
        path_btn = QPushButton("📂 ADB Path")
        path_btn.clicked.connect(self.set_adb_path_dialog)
        device_row.addWidget(path_btn)
        
        test_btn = QPushButton("✓ Test")
        test_btn.clicked.connect(self.test_adb)
        device_row.addWidget(test_btn)
        device_layout.addLayout(device_row)
        
        # Device status row
        status_row = QHBoxLayout()
        self.device_info_label = QLabel("No device selected")
        self.device_info_label.setStyleSheet(f"color: {self.colors['text_secondary']};")
        status_row.addWidget(self.device_info_label)
        
        self.adb_path_label = QLabel("ADB: Checking...")
        self.adb_path_label.setStyleSheet(f"color: {self.colors['text_tertiary']};")
        status_row.addWidget(self.adb_path_label)
        status_row.addStretch()
        device_layout.addLayout(status_row)
        
        # Device info display row (showing detailed info below status)
        info_row = QHBoxLayout()
        self.device_detail_label = QLabel("")
        self.device_detail_label.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 9pt;")
        info_row.addWidget(self.device_detail_label)
        self.device_serial_label = QLabel("")
        self.device_serial_label.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 9pt;")
        info_row.addWidget(self.device_serial_label)
        self.device_android_label = QLabel("")
        self.device_android_label.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 9pt;")
        info_row.addWidget(self.device_android_label)
        info_row.addStretch()
        device_layout.addLayout(info_row)
        
        adb_layout.addWidget(device_group)
        
        # Main content area (operations + logs side by side)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(7)
        
        # Left side - Operations (scrollable)
        ops_scroll = SmoothScrollArea()
        ops_scroll.setWidgetResizable(True)
        ops_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        ops_widget = QWidget()
        self.ops_layout = QVBoxLayout(ops_widget)
        self.ops_layout.setSpacing(12)
        
        # Scrcpy operations
        scrcpy_group = self.create_card("🖥️ Screen Mirror (Scrcpy)")
        scrcpy_group.setProperty('group_id', 'screen_mirror')
        scrcpy_layout = scrcpy_group.layout()
        
        # Scrcpy status
        self.scrcpy_status_label = QLabel("Checking scrcpy availability...")
        self.scrcpy_status_label.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 8pt;")
        scrcpy_layout.addWidget(self.scrcpy_status_label)
        
        # Basic controls
        scrcpy_btn_layout = QHBoxLayout()
        self.scrcpy_btn = QPushButton("▶️ Start Mirror")
        self.scrcpy_btn.clicked.connect(self.start_scrcpy_default)
        scrcpy_btn_layout.addWidget(self.scrcpy_btn)
        
        self.scrcpy_advanced_btn = QPushButton("⚙️ Advanced")
        self.scrcpy_advanced_btn.clicked.connect(self.show_scrcpy_options)
        scrcpy_btn_layout.addWidget(self.scrcpy_advanced_btn)
        
        scrcpy_path_btn = QPushButton("📂 Path")
        scrcpy_path_btn.clicked.connect(self.set_scrcpy_path_dialog)
        scrcpy_btn_layout.addWidget(scrcpy_path_btn)
        scrcpy_layout.addLayout(scrcpy_btn_layout)
        
        self.ops_layout.addWidget(scrcpy_group)
        
        # 初始化组引用字典
        if not hasattr(self, 'group_widgets'):
            self.group_widgets = {}
        self.group_widgets['screen_mirror'] = scrcpy_group


        # Try to load buttons from JSON config first
        if not self.create_buttons_from_config(self.ops_layout):
            # Fallback: Use hardcoded buttons if JSON config fails
            # File operations
            file_group = self.create_card("📁 File Transfer")
            self.create_button(file_group, "⬆️ Push File to Device", self.push_file)
            self.create_button(file_group, "⬇️ Pull File from Device", self.pull_file)
            self.create_button(file_group, "🗂️ Advanced File Manager", self.show_file_browser, accent=True)
            self.ops_layout.addWidget(file_group)
            
            # App operations
            app_group = self.create_card("📱 App Management")
            self.create_button(app_group, "📦 Install APK", self.install_apk)
            self.create_button(app_group, "🗑️ Uninstall App", self.uninstall_app)
            self.create_button(app_group, "♻️ Reinstall for User", self.reinstall_for_user)
            self.create_button(app_group, "📋 List Installed Apps", self.list_apps)
            self.create_button(app_group, "📱 App List Manager", self.show_app_manager, accent=True)
            self.create_button(app_group, "📂 Open APKs Folder", self.open_apks_folder)
            
            # Separator
            self.separator = QFrame()
            self.separator.setFrameShape(QFrame.Shape.HLine)
            self.separator.setStyleSheet(f"color: {self.colors['border']};")
            app_group.layout().addWidget(self.separator)
            
            self.create_button(app_group, "🚫 DeGoogle Device", self.degoogle_device, accent=True)
            self.create_button(app_group, "↩️ Undo DeGoogle", self.undo_degoogle)
            self.ops_layout.addWidget(app_group)
        
        # Shell operations
        shell_group = self.create_card("💻 Shell Commands")
        shell_group.setProperty('group_id', 'shell_commands')
        shell_group.layout().addWidget(QLabel("Run commands ON YOUR ANDROID DEVICE (not Windows):"))
        help_text = ("⚠️ These commands run on your Android device (Linux), not on Windows!\n\n"
                    "Examples: 'ls /sdcard', 'pm list packages', 'dumpsys battery | grep level'\n"
                    "Use Linux commands: 'grep' (not 'findstr'), 'ls' (not 'dir'), 'cat' (not 'type')\n\n"
                    "Note: You can include 'adb shell' prefix, but it's not required (auto-stripped)")
        self.shell_help_label = QLabel(help_text)
        self.shell_help_label.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 8pt;")
        self.shell_help_label.setWordWrap(True)
        shell_group.layout().addWidget(self.shell_help_label)
        self.shell_entry = QTextEdit()
        self.shell_entry.setMaximumHeight(100)
        self.shell_entry.setMinimumHeight(80)
        self.shell_entry.setStyleSheet("padding: 6px; font-size: 10pt;")
        self.shell_entry.setPlaceholderText("Enter Android shell command (e.g., 'ls /sdcard' or 'adb shell pm list packages')\nYou can enter multi-line commands here...")
        # QTextEdit doesn't have returnPressed, so we'll use Ctrl+Enter or just the button
        shell_group.layout().addWidget(self.shell_entry)
        self.create_button(shell_group, "▶️ Run Command", self.run_shell_command, accent=True)
        self.ops_layout.addWidget(shell_group)
        
        # 存储shell_group引用
        self.group_widgets['shell_commands'] = shell_group
        
        self.ops_layout.addStretch()
        ops_scroll.setWidget(ops_widget)
        content_layout.addWidget(ops_scroll, 1)
        
        # Right side - Tabs for Logs and Command Reference
        right_tabs = QTabWidget()
        
        # Tab 1: Logs & Output
        logs_tab = QWidget()
        logs_layout = QVBoxLayout(logs_tab)
        logs_layout.setContentsMargins(0, 0, 0, 0)
        
        # Logcat controls with enhanced features
        log_controls = QHBoxLayout()
        
        self.log_button = QPushButton("▶️ Start Logcat")
        self.log_button.clicked.connect(self.toggle_logcat)
        log_controls.addWidget(self.log_button)
        
        # Log level filter
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["All", "Verbose", "Debug", "Info", "Warning", "Error", "Fatal", "Logcat"])
        self.log_level_combo.setMaximumWidth(100)
        self.log_level_combo.currentTextChanged.connect(self.filter_log_level)
        log_controls.addWidget(QLabel("Level:"))
        log_controls.addWidget(self.log_level_combo)
        
        # Log search filter
        self.log_filter_edit = QLineEdit()
        self.log_filter_edit.setPlaceholderText("Filter logs...")
        self.log_filter_edit.setMaximumWidth(200)
        self.log_filter_edit.textChanged.connect(self.filter_logs)
        log_controls.addWidget(self.log_filter_edit)
        
        clear_btn = QPushButton("🗑️ Clear")
        clear_btn.clicked.connect(self.clear_output)
        log_controls.addWidget(clear_btn)
        
        export_btn = QPushButton("💾 Export")
        export_btn.clicked.connect(self.export_logs)
        log_controls.addWidget(export_btn)
        
        # Auto-scroll checkbox
        self.auto_scroll_cb = QCheckBox("Auto-scroll")
        self.auto_scroll_cb.setChecked(True)
        log_controls.addWidget(self.auto_scroll_cb)
        
        # Auto-save to file checkbox
        self.auto_save_cb = QCheckBox("自动保存日志")
        self.auto_save_cb.setChecked(True)
        log_controls.addWidget(self.auto_save_cb)
        
        # Log file prefix input
        log_controls.addWidget(QLabel("前缀:"))
        self.log_file_prefix = QLineEdit()
        self.log_file_prefix.setText("adb_logcat")
        self.log_file_prefix.setMaximumWidth(120)
        self.log_file_prefix.setPlaceholderText("日志前缀")
        log_controls.addWidget(self.log_file_prefix)
        
        # Log file path label
        self.log_file_label = QLabel("")
        self.log_file_label.setStyleSheet("color: #888888;")
        self.log_file_label.setMaximumWidth(200)
        log_controls.addWidget(self.log_file_label)
        
        log_controls.addStretch()
        logs_layout.addLayout(log_controls)
        
        # Output text area
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont('Consolas', 9))
        logs_layout.addWidget(self.output_text)
        
        # Store all logs for filtering
        self.all_logs = []
        
        right_tabs.addTab(logs_tab, "📊 Logs")
        
        # Tab 2: ADB Command Reference
        ref_tab = QWidget()
        ref_layout = QVBoxLayout(ref_tab)
        ref_layout.setContentsMargins(5, 5, 5, 5)
        
        # Search bar
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("🔍 Search:"))
        self.ref_search = QLineEdit()
        self.ref_search.setPlaceholderText("Search commands...")
        self.ref_search.textChanged.connect(self.filter_command_reference)
        search_layout.addWidget(self.ref_search)
        ref_layout.addLayout(search_layout)
        
        # Command reference text - Use QTextBrowser for HTML/Markdown rendering
        from PySide6.QtWidgets import QTextBrowser
        self.ref_text = QTextBrowser()
        self.ref_text.setReadOnly(True)
        self.ref_text.setOpenExternalLinks(True)
        self.load_command_reference()
        ref_layout.addWidget(self.ref_text)
        
        # Link to source
        link_label = QLabel('<a href="https://github.com/mzlogin/awesome-adb">📖 Complete Guide (awesome-adb by mzlogin)</a>')
        link_label.setOpenExternalLinks(True)
        link_label.setStyleSheet(f"padding: 5px; color: {self.colors['accent']};")
        ref_layout.addWidget(link_label)
        
        right_tabs.addTab(ref_tab, "📚 Commands")
        
        # Tab 3: Quick Actions
        quick_tab = QWidget()
        quick_tab.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        quick_layout = QVBoxLayout(quick_tab)
        quick_layout.setContentsMargins(5, 5, 5, 5)
        quick_layout.setSpacing(10)
        
        # Device Info Section
        info_group = QGroupBox("📱 Device Info")
        info_layout = QVBoxLayout(info_group)
        
        btn_battery = QPushButton("🔋 Battery Status")
        btn_battery.clicked.connect(self.quick_battery_status)
        info_layout.addWidget(btn_battery)
        
        btn_device_info = QPushButton("ℹ️ Device Info")
        btn_device_info.clicked.connect(self.quick_device_info)
        info_layout.addWidget(btn_device_info)
        
        btn_display = QPushButton("🖥️ Display Info")
        btn_display.clicked.connect(self.quick_display_info)
        info_layout.addWidget(btn_display)
        
        btn_storage = QPushButton("💾 Storage Info")
        btn_storage.clicked.connect(self.quick_storage_info)
        info_layout.addWidget(btn_storage)
        
        quick_layout.addWidget(info_group)
        
        # Performance Section
        perf_group = QGroupBox("⚡ Performance")
        perf_layout = QVBoxLayout(perf_group)
        
        btn_cpu = QPushButton("📊 CPU Info")
        btn_cpu.clicked.connect(self.quick_cpu_info)
        perf_layout.addWidget(btn_cpu)
        
        btn_memory = QPushButton("🧠 Memory Info")
        btn_memory.clicked.connect(self.quick_memory_info)
        perf_layout.addWidget(btn_memory)
        
        btn_top = QPushButton("📈 Top Processes")
        btn_top.clicked.connect(self.quick_top_processes)
        perf_layout.addWidget(btn_top)
        
        quick_layout.addWidget(perf_group)
        
        # Network Section
        net_group = QGroupBox("🌐 Network")
        net_layout = QVBoxLayout(net_group)
        
        btn_ip = QPushButton("🔍 IP Address")
        btn_ip.clicked.connect(self.quick_ip_info)
        net_layout.addWidget(btn_ip)
        
        btn_wifi = QPushButton("📶 WiFi Info")
        btn_wifi.clicked.connect(self.quick_wifi_info)
        net_layout.addWidget(btn_wifi)
        
        quick_layout.addWidget(net_group)
        
        # Quick Actions Section
        actions_group = QGroupBox("⚡ Quick Actions")
        actions_layout = QVBoxLayout(actions_group)
        
        btn_clear_logcat = QPushButton("🗑️ Clear Logcat")
        btn_clear_logcat.clicked.connect(self.quick_clear_logcat)
        actions_layout.addWidget(btn_clear_logcat)
        
        btn_airplane = QPushButton("✈️ Toggle Airplane Mode")
        btn_airplane.clicked.connect(self.quick_airplane_mode)
        actions_layout.addWidget(btn_airplane)
        
        btn_screenshot_quick = QPushButton("📸 Quick Screenshot")
        btn_screenshot_quick.clicked.connect(self.take_screenshot)
        actions_layout.addWidget(btn_screenshot_quick)
        
        btn_screen_record = QPushButton("🎥 Screen Record (30s)")
        btn_screen_record.clicked.connect(self.quick_screen_record)
        actions_layout.addWidget(btn_screen_record)
        
        # Developer Options Section
        dev_group = QGroupBox("🔧 Developer Options")
        dev_layout = QVBoxLayout(dev_group)
        
        btn_dev_enable = QPushButton("🔓 打开开发者选项")
        btn_dev_enable.clicked.connect(self.quick_enable_dev_options)
        dev_layout.addWidget(btn_dev_enable)
        
        btn_dev_disable = QPushButton("🔒 关闭开发者选项")
        btn_dev_disable.clicked.connect(self.quick_disable_dev_options)
        dev_layout.addWidget(btn_dev_disable)
        
        # Display Settings Section
        display_group = QGroupBox("⏱️ Display Settings")
        display_layout = QVBoxLayout(display_group)
        
        btn_screen_timeout_get = QPushButton("⏱️ 获取屏幕休眠时间")
        btn_screen_timeout_get.clicked.connect(self.quick_get_screen_timeout)
        display_layout.addWidget(btn_screen_timeout_get)
        
        btn_screen_timeout_set = QPushButton("⏰ 设置屏幕休眠时间")
        btn_screen_timeout_set.clicked.connect(self.quick_set_screen_timeout)
        display_layout.addWidget(btn_screen_timeout_set)
        
        btn_open_settings = QPushButton("⚙️ 启动系统设置")
        btn_open_settings.clicked.connect(self.quick_open_settings)
        display_layout.addWidget(btn_open_settings)
        
        btn_adb_input = QPushButton("⌨️ ADB按键键盘")
        btn_adb_input.clicked.connect(self.quick_adb_input_key)
        display_layout.addWidget(btn_adb_input)
        
        quick_layout.addWidget(actions_group)
        quick_layout.addWidget(dev_group)
        quick_layout.addWidget(display_group)
        
        quick_layout.addStretch()
        
        # Wrap quick_tab in scroll area for responsive layout
        quick_scroll = SmoothScrollArea()
        quick_scroll.setWidget(quick_tab)
        quick_scroll.setWidgetResizable(True)
        quick_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content_layout.addWidget(right_tabs, 2)
        adb_layout.addLayout(content_layout, 1)
        
        # 将 ADB Tab 添加到主 Tab
        self.main_tab_widget.addTab(adb_tab, "📱 ADB 工具")
        
        # ============ Tab 2: 下载器 ============
        downloader_tab = self._create_downloader_tab()
        self.main_tab_widget.addTab(downloader_tab, "📥 下载器")
        
        # Status bar
        self.status_bar = QLabel("Ready")
        self.status_bar.setStyleSheet(f"""
            background-color: {self.colors['card_bg']};
            border: 1px solid {self.colors['border']};
            padding: 8px 15px;
            color: {self.colors['text_secondary']};
        """)
        main_layout.addWidget(self.status_bar)
    
    def _create_downloader_tab(self):
        """创建下载器 Tab 页 - 嵌入 Ghost Downloader（已转换为 PyQt6）"""
        logger.info("开始创建下载器 Tab...")
        downloader_tab = QWidget()
        layout = QVBoxLayout(downloader_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        try:
            # 从配置文件读取路径
            config_path = Path(self.project_dir) / "plugins" / "plugins_config.json"
            if config_path.exists():
                import json
                with open(config_path, 'r', encoding='utf-8') as f:
                    plugin_config = json.load(f)
                gd_config = plugin_config.get('ghost_downloader', {})
                module_path = gd_config.get('module_path', 'extensions/Ghost-Downloader-3')
            else:
                module_path = 'extensions/Ghost-Downloader-3'

            logger.info(f"Ghost Downloader 路径: {module_path}")

            gd3_path = Path(self.project_dir) / module_path
            if not gd3_path.exists():
                raise FileNotFoundError(f"Ghost Downloader 目录不存在: {gd3_path}")

            if str(gd3_path) not in sys.path:
                sys.path.insert(0, str(gd3_path))
            logger.info(f"添加到 sys.path: {gd3_path}")

            # 初始化配置（已转换为 PyQt6 的 qfluentwidgets）
            from qfluentwidgets import qconfig
            from app.common.config import cfg
            config_file = gd3_path / "Ghost Downloader 配置文件.json"
            if config_file.exists():
                qconfig.load(str(config_file), cfg)
            cfg.appPath = str(gd3_path)
            logger.info(f"配置初始化完成, appPath={cfg.appPath}")

            # 加载嵌入式主界面
            logger.info("加载 EmbeddedMainWindow...")
            from app.common.embedded_main_window import EmbeddedMainWindow
            self.ghost_downloader = EmbeddedMainWindow(downloader_tab)
            layout.addWidget(self.ghost_downloader)
            logger.info("下载器 Tab 创建成功!")
            self.ghost_config = cfg

        except Exception as e:
            logger.error(f"加载下载器失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

            # 降级：显示独立窗口启动按钮
            error_label = QLabel(
                f"无法嵌入下载器组件: {e}\n\n点击下方按钮以独立窗口启动。"
            )
            error_label.setWordWrap(True)
            error_label.setStyleSheet("padding: 20px; color: #d13438;")
            layout.addWidget(error_label)

            open_btn = QPushButton("打开独立下载器窗口")
            open_btn.clicked.connect(self.open_ghost_downloader_window)
            layout.addWidget(open_btn)

        return downloader_tab
    
    def create_card(self, title):
        """Create a modern card container"""
        group = DraggableGroupBox(title)
        group.group_reordered.connect(self._on_group_reordered)
        group.button_dropped.connect(self._on_button_dropped_to_group)
        # Styles are applied globally via apply_theme, no need for individual stylesheet
        layout = QVBoxLayout(group)
        layout.setContentsMargins(15, 20, 15, 15)
        layout.setSpacing(4)
        return group
    
    def create_button(self, parent, text, command, accent=False, params=None):
        """Create a modern button with optional params"""
        btn = DraggableButton(text)
        btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)  # 允许获取焦点
        
        # 包装命令函数，自动添加按钮点击日志
        button_label = text
        def wrapped_command():
            # 编辑模式下不执行命令
            if getattr(self, 'edit_mode', False):
                return
            btn.setFocus()  # 点击时获取焦点
            self.log(f"Button clicked: {button_label}", "INFO")
            command()
        
        btn.clicked.connect(wrapped_command)
        if accent:
            btn.setProperty("accent", "true")
        
        # 右键菜单
        btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        btn.customContextMenuRequested.connect(lambda pos, b=btn: self._show_button_context_menu(b, pos))
        
        # 拖拽信号
        btn.reorder_requested.connect(self._on_button_reorder_requested)
        
        parent.layout().addWidget(btn)
        
        # 如果有参数，创建参数输入区
        if params:
            self._create_param_widgets(parent, btn, params)
        
        return btn
    
    def _create_param_widgets(self, parent, btn, params):
        """Create parameter input widgets below the button"""
        # 加载已保存的参数
        saved_params = self.load_command_params()
        # 从按钮text提取button_id
        btn_text = btn.text()
        button_id = None
        for bid in ["push_file", "pull_file"]:
            if bid.replace("_", " ") in btn_text.lower() or bid.replace("_", "") in btn_text.lower().replace(" ", ""):
                button_id = bid
                break
        if not button_id:
            button_id = btn_text
        
        # 保存输入框引用，用于后续查找
        if not hasattr(self, '_param_inputs'):
            self._param_inputs = {}
        if button_id not in self._param_inputs:
            self._param_inputs[button_id] = {}
        
        for param in params:
            param_name = param.get('name', '')
            param_type = param.get('type', 'text')
            param_label = param.get('label', param_name)
            
            # 创建水平布局
            param_layout = QHBoxLayout()
            
            # 标签
            label = QLabel(param_label)
            label.setStyleSheet(f"color: {self.colors.get('text_secondary', '#888')}; font-size: 9pt;")
            label.setMinimumWidth(50)
            param_layout.addWidget(label)
            
            # 获取已保存的值
            saved_value = saved_params.get(button_id, {}).get(param_name, param.get('default', ''))
            
            # 创建输入框
            line_edit = QLineEdit(saved_value)
            line_edit.setStyleSheet("padding: 4px; font-size: 9pt;")
            
            # 编辑完成时自动保存参数
            line_edit.editingFinished.connect(
                lambda bid=button_id: self._on_param_edited(bid)
            )
            
            if param_type in ('file', 'folder'):
                # 文件或文件夹选择
                line_edit.setPlaceholderText("选择文件或文件夹...")
                param_layout.addWidget(line_edit, 1)
                
                select_btn = QPushButton("📂")
                select_btn.setFixedWidth(30)
                # 使用functools.partial或默认参数来正确绑定
                select_btn.clicked.connect(lambda checked, le=line_edit: self._select_file_or_folder(le))
                param_layout.addWidget(select_btn)
            else:
                # 文本输入
                line_edit.setPlaceholderText(param.get('placeholder', ''))
                param_layout.addWidget(line_edit, 1)
            
            # 保存引用
            self._param_inputs[button_id][param_name] = line_edit
            
            parent.layout().addLayout(param_layout)
    
    def _on_param_edited(self, button_id):
        """当参数输入框编辑完成时自动保存"""
        if not hasattr(self, '_param_inputs') or button_id not in self._param_inputs:
            return
        
        params = {}
        for param_name, line_edit in self._param_inputs[button_id].items():
            params[param_name] = line_edit.text()
        
        # 保存参数
        self.save_command_param(button_id, params)
    
    def _select_file_or_folder(self, line_edit):
        """Open dialog to select file or folder"""
        import subprocess
        
        # 先尝试选择文件夹
        ps_script_folder = '''
        Add-Type -AssemblyName System.Windows.Forms
        $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
        $dialog.Description = "选择文件夹"
        $dialog.ShowNewFolderButton = $true
        if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
            $dialog.SelectedPath
        }
        '''
        
        try:
            result = subprocess.run(
                ['powershell', '-Command', ps_script_folder],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                line_edit.setText(result.stdout.strip())
                return
        except Exception:
            pass
        
        # Fallback: 选择文件
        file_path, _ = QFileDialog.getOpenFileName(self, "选择文件", "", "所有文件 (*.*)")
        if file_path:
            line_edit.setText(file_path)
    
    def _select_file(self, line_edit):
        """Open file dialog and set path to line edit"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select file", "", "All Files (*.*)")
        if file_path:
            line_edit.setText(file_path)
    
    def _select_folder(self, line_edit):
        """Open folder dialog and set path to line edit"""
        folder_path = QFileDialog.getExistingDirectory(self, "Select folder")
        if folder_path:
            line_edit.setText(folder_path)
    
    def get_button_params(self, button_text):
        """Get parameter values from input widgets for a button"""
        # 从button text提取button_id
        button_id = None
        for btn_id in ["push_file", "pull_file"]:
            if btn_id.replace("_", " ") in button_text.lower() or btn_id.replace("_", "") in button_text.lower().replace(" ", ""):
                button_id = btn_id
                break
        
        if not button_id:
            button_id = button_text
        
        # 直接从保存的引用获取参数
        params = {}
        if hasattr(self, '_param_inputs') and button_id in self._param_inputs:
            for param_name, line_edit in self._param_inputs[button_id].items():
                params[param_name] = line_edit.text()
        
        return params
    
    def _find_layouts_with_button(self, button_id):
        """Find layouts that contain a button with given text"""
        layouts = []
        # 遍历所有子控件查找
        def search_widget(widget):
            if isinstance(widget, QWidget):
                for child in widget.findChildren(QPushButton):
                    # 大小写不敏感匹配
                    if button_id.lower() in child.text().lower().replace("_", " "):
                        # 找到按钮，向上查找其父布局
                        parent = child.parent()
                        while parent:
                            if isinstance(parent, (QVBoxLayout, QHBoxLayout)):
                                layouts.append(parent)
                            parent = parent.parent()
                # 递归搜索子控件
                for child in widget.children():
                    search_widget(child)
        
        if hasattr(self, 'central_widget'):
            search_widget(self.central_widget)
        return layouts
    
    def _update_param_display(self, button_text, params):
        """Update the display of parameter input widgets"""
        # 从button text提取button_id
        button_id = None
        for bid in ["push_file", "pull_file"]:
            if bid.replace("_", " ") in button_text.lower() or bid.replace("_", "") in button_text.lower().replace(" ", ""):
                button_id = bid
                break
        
        if not button_id:
            button_id = button_text
        
        # 直接更新保存的引用
        if hasattr(self, '_param_inputs') and button_id in self._param_inputs:
            for param_name, value in params.items():
                if param_name in self._param_inputs[button_id]:
                    self._param_inputs[button_id][param_name].setText(value)
    
    def load_command_reference(self):
        """Load ADB command reference from awesome-adb with Markdown rendering"""
        # 从config.json获取README路径
        readme_path = self.config.get_extension_path('awesome_adb', self.project_dir)
        
        # 如果config中没有配置,使用默认路径
        if not readme_path:
            readme_path = os.path.join(self.project_dir, 'extensions', 'awesome-adb-readme', 'README.md')
        
        # 保存路径供文件监控使用
        self.readme_path = readme_path
        
        # 设置文件监控 - 文件修改后自动刷新
        if not hasattr(self, 'readme_watcher'):
            self.readme_watcher = QFileSystemWatcher()
            self.readme_watcher.fileChanged.connect(self._on_readme_changed)
        
        # 添加文件到监控列表
        if os.path.exists(readme_path):
            # 先移除旧的监控路径
            watched_files = self.readme_watcher.files()
            if watched_files:
                self.readme_watcher.removePaths(watched_files)
            self.readme_watcher.addPath(readme_path)
        
        self._reload_readme_content()
    
    def _on_readme_changed(self, path):
        """Handle README file change - reload content"""
        # 有些编辑器保存时会先删除再创建文件，需要重新添加监控
        if os.path.exists(path):
            self.readme_watcher.addPath(path)
        
        # 使用QTimer延迟加载，避免文件写入过程中读取
        QTimer.singleShot(100, self._reload_readme_content)
    
    def _reload_readme_content(self):
        """Reload README content and refresh display"""
        readme_path = getattr(self, 'readme_path', '')
        
        if os.path.exists(readme_path):
            try:
                with open(readme_path, 'r', encoding='utf-8') as f:
                    readme_content = f.read()
                
                # 存储原始Markdown用于搜索
                self.full_reference = readme_content
                self.full_reference_html = self._markdown_to_html(readme_content)
                self.ref_text.setHtml(self.full_reference_html)
            except Exception as e:
                self.full_reference = self._get_fallback_reference()
                self.ref_text.setPlainText(self.full_reference)
        else:
            self.full_reference = self._get_fallback_reference()
            self.ref_text.setPlainText(self.full_reference)
    
    def _markdown_to_html(self, markdown_text):
        """Convert Markdown to HTML with styling - 紧凑布局"""
        import re
        
        # CSS样式 - 紧凑布局
        bg_color = self.colors.get('card_bg', '#ffffff')
        text_color = self.colors.get('fg', '#1f1f1f')
        accent_color = self.colors.get('accent', '#0078d4')
        code_bg = '#f6f8fa' if not self.dark_mode else '#2d2d2d'
        border_color = self.colors.get('border', '#e1e1e1')
        
        css = f"""
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', Helvetica, Arial, sans-serif;
                font-size: 14px;
                line-height: 1.5;
                color: {text_color};
                background-color: {bg_color};
                margin: 0;
                padding: 15px;
            }}
            h1 {{ font-size: 1.8em; margin: 0.8em 0 0.4em 0; padding-bottom: 0.3em; border-bottom: 1px solid {border_color}; color: {text_color}; }}
            h2 {{ font-size: 1.5em; margin: 0.8em 0 0.4em 0; padding-bottom: 0.3em; border-bottom: 1px solid {border_color}; color: {text_color}; }}
            h3 {{ font-size: 1.25em; margin: 0.6em 0 0.3em 0; color: {text_color}; }}
            h4, h5, h6 {{ font-size: 1em; margin: 0.5em 0 0.2em 0; color: {text_color}; }}
            p {{ margin: 0.4em 0; }}
            code {{
                background-color: {code_bg};
                padding: 0.2em 0.4em;
                border-radius: 3px;
                font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
                font-size: 0.9em;
            }}
            pre {{
                background-color: {code_bg};
                padding: 10px;
                border-radius: 6px;
                overflow-x: auto;
                margin: 0.5em 0;
                line-height: 1.4;
            }}
            pre code {{ background-color: transparent; padding: 0; }}
            a {{ color: {accent_color}; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            ul, ol {{ margin: 0.3em 0; padding-left: 2em; }}
            li {{ margin: 0.15em 0; }}
            table {{ border-collapse: collapse; margin: 0.5em 0; }}
            th, td {{ border: 1px solid {border_color}; padding: 6px 10px; text-align: left; }}
            th {{ background-color: {code_bg}; }}
            blockquote {{
                border-left: 4px solid {accent_color};
                padding: 0 0 0 1em;
                margin: 0.5em 0;
                color: {self.colors.get('text_secondary', '#666666')};
            }}
            hr {{ border: none; border-top: 1px solid {border_color}; margin: 1em 0; }}
        </style>
        """
        
        html = markdown_text
        
        # 移除图片
        html = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'[\1]', html)
        
        # 转换代码块
        def replace_code_block(match):
            lang = match.group(1) or ''
            code = match.group(2)
            code = code.replace('<', '&lt;').replace('>', '&gt;')
            return f'<pre><code class="{lang}">{code}</code></pre>'
        
        html = re.sub(r'```(\w*)\n(.*?)```', replace_code_block, html, flags=re.DOTALL)
        
        # 转换行内代码
        html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)
        
        # 转换标题
        html = re.sub(r'^###### (.+)$', r'<h6>\1</h6>', html, flags=re.MULTILINE)
        html = re.sub(r'^##### (.+)$', r'<h5>\1</h5>', html, flags=re.MULTILINE)
        html = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        
        # 转换粗体和斜体
        html = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', html)
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'(?<!\*)\*([^\*]+)\*(?!\*)', r'<em>\1</em>', html)
        
        # 转换链接
        html = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2">\1</a>', html)
        
        # 转换水平线 (在列表之前处理)
        html = re.sub(r'^---+$', r'<hr>', html, flags=re.MULTILINE)
        html = re.sub(r'^\*\*\*+$', r'<hr>', html, flags=re.MULTILINE)
        
        # 转换引用
        html = re.sub(r'^> (.+)$', r'<blockquote>\1</blockquote>', html, flags=re.MULTILINE)
        
        # 转换表格
        def convert_table(match):
            table_text = match.group(0)
            rows = table_text.strip().split('\n')
            if len(rows) < 2:
                return table_text
            
            html_table = '<table>'
            for i, row in enumerate(rows):
                if re.match(r'^[\|\s\-:]+$', row):
                    continue  # Skip separator row
                cells = [c.strip() for c in row.split('|') if c.strip()]
                if not cells:
                    continue
                if i == 0:
                    html_table += '<tr>' + ''.join(f'<th>{c}</th>' for c in cells) + '</tr>'
                else:
                    html_table += '<tr>' + ''.join(f'<td>{c}</td>' for c in cells) + '</tr>'
            html_table += '</table>'
            return html_table
        
        html = re.sub(r'(\|[^\n]+\|\n)+', convert_table, html)
        
        # 转换列表 - 改进版本
        lines = html.split('\n')
        result_lines = []
        in_ul = False
        in_ol = False
        
        for line in lines:
            stripped = line.strip()
            
            # 无序列表
            ul_match = re.match(r'^[\*\-\+]\s+(.+)$', stripped)
            # 有序列表
            ol_match = re.match(r'^(\d+)\.\s+(.+)$', stripped)
            
            if ul_match:
                if not in_ul:
                    if in_ol:
                        result_lines.append('</ol>')
                        in_ol = False
                    result_lines.append('<ul>')
                    in_ul = True
                result_lines.append(f'<li>{ul_match.group(1)}</li>')
            elif ol_match:
                if not in_ol:
                    if in_ul:
                        result_lines.append('</ul>')
                        in_ul = False
                    result_lines.append('<ol>')
                    in_ol = True
                result_lines.append(f'<li>{ol_match.group(2)}</li>')
            else:
                if in_ul:
                    result_lines.append('</ul>')
                    in_ul = False
                if in_ol:
                    result_lines.append('</ol>')
                    in_ol = False
                result_lines.append(line)
        
        if in_ul:
            result_lines.append('</ul>')
        if in_ol:
            result_lines.append('</ol>')
        
        html = '\n'.join(result_lines)
        
        # 处理段落 - 只在双换行处创建段落，不要把所有换行变成<br>
        # 先保护已有的HTML标签
        html = re.sub(r'\n\n+', '\n<p></p>\n', html)
        
        # 移除HTML标签之间的多余换行
        html = re.sub(r'>\s*\n\s*<', '><', html)
        
        # 非HTML标签行之间的单个换行变成空格或保留
        # 但不要在block元素前后加<br>
        block_tags = r'(?:h[1-6]|p|div|ul|ol|li|pre|table|tr|th|td|blockquote|hr)'
        html = re.sub(rf'(</{block_tags}>)\n', r'\1', html)
        html = re.sub(rf'\n(<{block_tags})', r'\1', html)
        
        # 包装完整HTML
        full_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">{css}</head>
<body>{html}</body></html>"""
        
        return full_html
    
    def _get_fallback_reference(self):
        """Fallback reference if README not found"""
        return """
╔═══════════════════════════════════════════════════════════════════════════════
║ ADB 命令使用手册 (基于 awesome-adb by mzlogin)
║ https://github.com/mzlogin/awesome-adb
║ 
║ 注意: 完整文档文件未找到,显示简化版本
║ 请确保 extensions/awesome-adb-readme/README.md 文件存在
╚═══════════════════════════════════════════════════════════════════════════════

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【基本用法】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

▸ 命令语法: adb [-d|-e|-s <serialNumber>] <command>
▸ 查看版本: adb version
▸ 启动/停止: adb start-server / adb kill-server
▸ Root权限: adb root / adb unroot

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【设备连接】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

▸ 查询设备: adb devices / adb devices -l
▸ 无线连接: adb tcpip 5555 → adb connect <IP>:5555
▸ 断开连接: adb disconnect

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【应用管理】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

▸ 列出应用: adb shell pm list packages [-s|-3]
▸ 安装应用: adb install [-r] <apk>
▸ 卸载应用: adb uninstall [-k] <package>
▸ 清除数据: adb shell pm clear <package>
▸ 启动应用: adb shell am start -n <package>/<activity>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【文件管理】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

▸ 推送文件: adb push <local> <remote>
▸ 拉取文件: adb pull <remote> [local]
▸ 列出文件: adb shell ls <path>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【模拟输入】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

▸ 按键: adb shell input keyevent <keycode>
  常用: 3=HOME 4=BACK 26=POWER 82=MENU
▸ 点击: adb shell input tap <x> <y>
▸ 滑动: adb shell input swipe <x1> <y1> <x2> <y2>
▸ 输入: adb shell input text <string>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【日志查看】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

▸ Logcat: adb logcat [-c|-v <format>|*:E]
▸ 内核日志: adb shell dmesg

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【设备信息】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

▸ 型号: adb shell getprop ro.product.model
▸ 版本: adb shell getprop ro.build.version.release
▸ 分辨率: adb shell wm size
▸ 电池: adb shell dumpsys battery

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【实用功能】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

▸ 截图: adb exec-out screencap -p > screen.png
▸ 录屏: adb shell screenrecord /sdcard/video.mp4
▸ 重启: adb reboot [recovery|bootloader]

💡 完整文档请访问: https://github.com/mzlogin/awesome-adb
"""
    
    def filter_command_reference(self):
        """Filter command reference based on search text with Markdown rendering"""
        search_text = self.ref_search.text().lower()
        if not search_text:
            # 恢复完整内容
            if hasattr(self, 'full_reference_html'):
                self.ref_text.setHtml(self.full_reference_html)
            else:
                self.ref_text.setPlainText(self.full_reference)
            return
        
        # Filter lines containing search text
        lines = self.full_reference.split('\n')
        filtered_lines = []
        context_lines = 3  # Show context around matches
        
        for i, line in enumerate(lines):
            if search_text in line.lower():
                # Add context before
                start = max(0, i - context_lines)
                for j in range(start, i):
                    if lines[j] not in filtered_lines:
                        filtered_lines.append(lines[j])
                
                # Add matching line with highlight
                if line not in filtered_lines:
                    filtered_lines.append(line)
                
                # Add context after
                end = min(len(lines), i + context_lines + 1)
                for j in range(i + 1, end):
                    if lines[j] not in filtered_lines:
                        filtered_lines.append(lines[j])
        
        if filtered_lines:
            # 渲染过滤后的Markdown
            filtered_markdown = '\n'.join(filtered_lines)
            filtered_html = self._markdown_to_html(filtered_markdown)
            
            # 高亮搜索词
            import re
            highlight_color = '#ffff00' if not self.dark_mode else '#665500'
            filtered_html = re.sub(
                f'({re.escape(search_text)})',
                f'<span style="background-color: {highlight_color}; padding: 1px 3px;">\\1</span>',
                filtered_html,
                flags=re.IGNORECASE
            )
            
            self.ref_text.setHtml(filtered_html)
        else:
            no_result_html = f"""
            <div style="padding: 20px; text-align: center; color: {self.colors.get('text_secondary', '#666666')};">
                <h3>未找到包含 '{search_text}' 的命令</h3>
                <p>请尝试其他关键词，如:</p>
                <p><code>install</code> <code>push</code> <code>shell</code> <code>logcat</code> <code>reboot</code></p>
            </div>
            """
            self.ref_text.setHtml(no_result_html)
    
    def log(self, message, level="INFO"):
        """Add message to output - thread safe"""
        timestamp = datetime.now().strftime("%y%m%d %H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] [{level}] {message}"
        self.all_logs.append(log_entry)
        
        # 使用QMetaObject.invokeMethod确保在主线程中执行
        QMetaObject.invokeMethod(self, "_append_log_qt", 
                                  Qt.ConnectionType.QueuedConnection,
                                  Q_ARG(str, log_entry))
    
    @pyqtSlot(str)
    def _append_log_qt(self, log_entry):
        """Qt槽函数 - 用于跨线程调用"""
        self._append_log(log_entry)
    
    def _append_log(self, log_entry):
        """实际添加日志到UI - 只能在主线程中调用"""
        self.output_text.append(log_entry)
        # Auto-scroll to bottom if enabled
        if self.auto_scroll_cb.isChecked():
            scrollbar = self.output_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        # Auto-save to file if enabled
        if self.auto_save_cb.isChecked() and self.log_file:
            try:
                self.log_file.write(log_entry + '\n')
                self.log_file.flush()
            except Exception:
                pass  # Ignore file write errors
    
    def clear_output(self):
        """Clear output text"""
        self.output_text.clear()
        self.all_logs = []
    
    def export_logs(self):
        """Export logs to file"""
        if not self.output_text.toPlainText():
            QMessageBox.information(self, "Info", "No logs to export")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Logs", 
            f"adb_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt);;All Files (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.output_text.toPlainText())
                QMessageBox.information(self, "Success", f"Logs exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to export logs:\n{e}")
    
    def filter_log_level(self):
        """Filter logs by level"""
        self.apply_log_filters()
    
    def filter_logs(self):
        """Filter logs by search text"""
        self.apply_log_filters()
    
    def apply_log_filters(self):
        """Apply all log filters"""
        level = self.log_level_combo.currentText()
        search_text = self.log_filter_edit.text().lower()
        
        filtered_logs = []
        
        for log in self.all_logs:
            # Level filter
            if level != "All":
                level_markers = {
                    "Verbose": " V ",
                    "Debug": " D ",
                    "Info": " I ",
                    "Warning": " W ",
                    "Error": " E ",
                    "Fatal": " F ",
                    "Logcat": "LOGCAT"
                }
                if level in level_markers and level_markers[level] not in log:
                    continue
            
            # Search filter
            if search_text and search_text not in log.lower():
                continue
            
            filtered_logs.append(log)
        
        self.output_text.setPlainText('\n'.join(filtered_logs))
        if self.auto_scroll_cb.isChecked():
            scrollbar = self.output_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
    
    def update_status(self, message):
        """Update status bar - thread safe"""
        QMetaObject.invokeMethod(self, "_update_status_qt",
                                  Qt.ConnectionType.QueuedConnection,
                                  Q_ARG(str, message))
    
    @pyqtSlot(str)
    def _update_status_qt(self, message):
        """Qt槽函数 - 用于跨线程调用"""
        self.status_bar.setText(message)
    
    def update_adb_path_display(self):
        """Update ADB path display label"""
        if os.path.exists(self.adb.adb_path):
            self.adb_path_label.setText(f"✓ ADB: {self.adb.adb_path}")
            self.adb_path_label.setStyleSheet(f"color: {self.colors['success']};")
        else:
            self.adb_path_label.setText("✗ ADB: Not found - Click 'ADB Path' to configure")
            self.adb_path_label.setStyleSheet(f"color: {self.colors['error']};")
        
        # Also check scrcpy availability
        self.check_scrcpy_availability()
    
    def refresh_devices(self, silent=False):
        """Refresh list of connected devices.

        Args:
            silent: If True, skip extra getprop calls and log spam (for auto-refresh)
        """
        if not silent:
            self.update_status("Refreshing devices...")

        # Test ADB connection first
        test_result = self.adb.run_command('version')
        if not test_result['success']:
            error_msg = test_result['stderr'] if test_result['stderr'] else "Unknown error"
            self.log(f"ADB test failed: {error_msg}", "ERROR")
            self.log(f"ADB path: {self.adb.adb_path}", "ERROR")
            self.update_status(f"ADB error: {error_msg[:50]}")
            self.device_info_label.setText(f"ADB Error: {error_msg[:100]}")
            self.device_info_label.setStyleSheet(f"color: {self.colors['error']};")
            return

        # silent 自动刷新只取设备列表（1条命令），手动刷新才取完整 xbh/serial/android 信息
        devices = self.adb.get_devices(silent=silent, full_info=not silent)

        # Get current device list for comparison
        current_device_ids = set()
        if hasattr(self, 'device_display_map'):
            current_device_ids = set(self.device_display_map.values())

        if devices:
            # Create display strings with device name/model
            device_list = []
            device_display_map = {}  # Map display string to device ID
            new_device_ids = set()

            # 初始化 android 版本缓存（跨刷新保留）
            if not hasattr(self, '_device_android_cache'):
                self._device_android_cache = {}

            for d in devices:
                device_id = d['id']
                new_device_ids.add(device_id)
                model = d.get('model')
                manufacturer = d.get('manufacturer', '')
                product = d.get('product')

                # Build display name
                if model:
                    if manufacturer:
                        display_name = f"{manufacturer} {model}"
                    else:
                        display_name = model
                elif product:
                    display_name = product.replace('_', ' ').title()
                else:
                    display_name = "Unknown Device"

                # 全量刷新时更新缓存；silent 刷新时从缓存补充版本
                android_ver = d.get('android_version', '')
                if android_ver:
                    self._device_android_cache[device_id] = android_ver
                else:
                    android_ver = self._device_android_cache.get(device_id, '')

                # Format: "Device Name (ID)" or "Device Name (ID, Android X)"
                if android_ver:
                    display_str = f"{display_name} ({device_id}, Android {android_ver})"
                else:
                    display_str = f"{display_name} ({device_id})"
                device_list.append(display_str)
                device_display_map[display_str] = device_id

            # Only log if device list changed
            devices_changed = current_device_ids != new_device_ids

            # Disconnect signal before modifying combo box to prevent unwanted triggers
            self.device_combo.currentTextChanged.disconnect()

            self.device_combo.clear()
            self.device_combo.addItems(device_list)
            self.device_display_map = device_display_map  # Store mapping for selection

            # Only auto-select if no device is currently selected
            was_no_device = not self.current_device
            if was_no_device and device_list:
                self.device_combo.setCurrentIndex(0)
                # Call on_device_selected directly with silent parameter (signal is disconnected so won't trigger)
                self.on_device_selected(silent=silent)  # Use silent parameter from refresh_devices
            elif self.current_device and device_list:
                # Device is already selected - just update the combo box index if needed
                # Find the current device in the new list
                current_display = None
                for display_str, device_id in device_display_map.items():
                    if device_id == self.current_device:
                        current_display = display_str
                        break

                if current_display:
                    index = self.device_combo.findText(current_display)
                    if index >= 0:
                        self.device_combo.setCurrentIndex(index)
                # Don't call on_device_selected when device is already selected (avoids redundant get_devices call)

            # Reconnect signal after all combo box operations are complete
            self.device_combo.currentTextChanged.connect(self.on_device_selected)

            if not silent or devices_changed:
                self.update_status(f"Found {len(devices)} device(s)")
                if devices_changed:
                    # Log with device names only when list changes
                    device_names = [f"{d.get('model', d.get('product', 'Unknown'))} ({d['id']})" for d in devices]
                    self.log(f"Found {len(devices)} device(s): {', '.join(device_names)}")
        else:
            had_devices = hasattr(self, 'device_display_map') and len(self.device_display_map) > 0
            self.device_combo.clear()
            self.current_device = None
            self.device_info_label.setText("No devices connected - Check USB connection and USB debugging")
            self.device_info_label.setStyleSheet(f"color: {self.colors['warning']};")
            if not silent or had_devices:
                self.update_status("No devices found")
                if had_devices:
                    self.log("No devices found. Make sure USB debugging is enabled and device is connected.", "WARNING")
    
    def on_device_selected(self, selection=None, silent=False):
        """Handle device selection
        
        Args:
            selection: Device selection string (if None, uses current combo selection)
            silent: If True, don't log the selection (for auto-refresh)
        """
        if selection is None:
            selection = self.device_combo.currentText()
        
        if selection:
            # Extract device ID from display string using the mapping
            if hasattr(self, 'device_display_map') and selection in self.device_display_map:
                self.current_device = self.device_display_map[selection]
            else:
                # Fallback: try to extract from parentheses
                if '(' in selection and ')' in selection:
                    self.current_device = selection.split('(')[1].split(')')[0].strip()
                else:
                    self.current_device = selection.split()[0]
            
            # Get device info for display
            # In silent mode, skip get_devices call to avoid redundant logging
            if silent:
                # In silent mode, just use the device ID we already have
                # Don't call get_devices to avoid logging
                device_info = None
                # Set a simple display text without calling get_devices
                display_text = f"Selected: {self.current_device}"
            else:
                # Not in silent mode, get full device info
                devices = self.adb.get_devices(silent=silent)
                device_info = next((d for d in devices if d['id'] == self.current_device), None)
            
            if device_info:
                model = device_info.get('model', 'Unknown')
                manufacturer = device_info.get('manufacturer', '')
                if manufacturer:
                    display_text = f"Selected: {manufacturer} {model} ({self.current_device})"
                else:
                    display_text = f"Selected: {model} ({self.current_device})"
            else:
                display_text = f"Selected: {self.current_device}"
            
            # Only update UI and log if not in silent mode (for auto-refresh)
            if not silent:
                self.device_info_label.setText(display_text)
                self.device_info_label.setStyleSheet(f"color: {self.colors['success']};")
                self.log(f"Selected device: {display_text}")
                
                # Update detailed info display
                if device_info:
                    xbh_model = device_info.get('xbh_model', '')
                    detail_text = f"XbhModel: {xbh_model}" if xbh_model else ""
                    self.device_detail_label.setText(detail_text)
                    serial = device_info.get('serial', '')
                    self.device_serial_label.setText(f"Serial: {serial}" if serial else "")
                    android_ver = device_info.get('android_version', '')
                    self.device_android_label.setText(f"Android: {android_ver}" if android_ver else "")
                else:
                    self.device_detail_label.setText("")
                    self.device_serial_label.setText("")
                    self.device_android_label.setText("")
            # In silent mode, only update the label if it's not already set correctly
            elif not hasattr(self, 'device_info_label') or self.device_info_label.text() != display_text:
                self.device_info_label.setText(display_text)
                self.device_info_label.setStyleSheet(f"color: {self.colors['success']};")
        else:
            self.current_device = None
    
    def show_device_info(self):
        """Show detailed device information"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        info = self.adb.get_device_info(self.current_device)
        info_text = "\n".join([f"{k}: {v}" for k, v in info.items()])
        QMessageBox.information(self, "Device Information", info_text)
    
    def test_adb(self):
        """Test ADB connection and show detailed output"""
        self.log("Testing ADB connection...", "INFO")
        self.update_status("Testing ADB...")
        
        # Test version
        version_result = self.adb.run_command('version')
        self.log(f"ADB Version Command:\nSuccess: {version_result['success']}\nReturn Code: {version_result['returncode']}", "DEBUG")
        if version_result['stdout']:
            self.log(f"Version Output:\n{version_result['stdout']}", "INFO")
        if version_result['stderr'] and version_result['stderr'].strip():
            self.log(f"Version Error:\n{version_result['stderr']}", "ERROR")
        
        # Test devices
        devices_result = self.adb.run_command('devices -l')
        self.log(f"ADB Devices Command:\nSuccess: {devices_result['success']}\nReturn Code: {devices_result['returncode']}", "DEBUG")
        if devices_result['stdout']:
            self.log(f"Devices Output:\n{devices_result['stdout']}", "INFO")
        if devices_result['stderr'] and devices_result['stderr'].strip():
            self.log(f"Devices Error:\n{devices_result['stderr']}", "ERROR")
        
        # Show summary
        if version_result['success']:
            self.update_status("ADB is working correctly")
            QMessageBox.information(
                self,
                "ADB Test",
                f"ADB Path: {self.adb.adb_path}\n\n"
                f"Version: {'✓ Working' if version_result['success'] else '✗ Failed'}\n"
                f"Devices: {'✓ Working' if devices_result['success'] else '✗ Failed'}\n\n"
                f"Check the output log for details."
            )
        else:
            self.update_status("ADB test failed - check output log")
            QMessageBox.critical(
                self,
                "ADB Test Failed",
                f"ADB Path: {self.adb.adb_path}\n\n"
                f"Error: {version_result['stderr'] or 'Unknown error'}\n\n"
                f"Please check:\n"
                f"1. ADB path is correct\n"
                f"2. ADB executable exists\n"
                f"3. Check output log for details"
            )
    
    def prompt_for_adb_path(self):
        """Prompt user to select ADB folder or executable (used on first boot)"""
        initial_dir = os.path.expanduser('~')
        
        # First, try folder selection (most common use case)
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select platform-tools folder (contains adb.exe)",
            initial_dir
        )
        
        if folder_path:
            adb_exe = os.path.join(folder_path, 'adb.exe')
            if os.path.exists(adb_exe):
                return adb_exe
            else:
                QMessageBox.warning(self, "Error", f"adb.exe not found in:\n{folder_path}\n\nPlease select the folder that contains adb.exe")
                return None
        
        # Allow file selection as alternative
        adb_path, _ = QFileDialog.getOpenFileName(
            self,
            "Or select ADB executable (adb.exe) directly",
            initial_dir,
            "Executable files (*.exe);;All files (*.*)"
        )
        
        if adb_path:
            if os.path.basename(adb_path).lower() == 'adb.exe':
                return adb_path
            else:
                QMessageBox.warning(self, "Warning", "Please select adb.exe file")
                return None
        
        return None
    
    def set_adb_path_dialog(self):
        """Open dialog to set ADB path"""
        # Get initial directory from saved path or use home directory
        saved_path = self.settings.get('adb_path', '')
        if saved_path and os.path.exists(saved_path):
            if os.path.isfile(saved_path):
                initial_dir = os.path.dirname(saved_path)
            else:
                initial_dir = saved_path
        else:
            initial_dir = os.path.expanduser('~')
        
        # First, try folder selection (most common use case)
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select platform-tools folder (contains adb.exe)",
            initial_dir
        )
        
        if folder_path:
            adb_exe = os.path.join(folder_path, 'adb.exe')
            if os.path.exists(adb_exe):
                if self.adb.set_adb_path(adb_exe):
                    # Save to config.json (auto convert to relative path)
                    self.config.set_extension_path('adb', adb_exe, self.project_dir)
                    
                    self.adb_path_label.setText(f"✓ ADB: {adb_exe}")
                    self.adb_path_label.setStyleSheet(f"color: {self.colors['success']};")
                    self.log(f"ADB path set to: {adb_exe}")
                    self.update_status("ADB path updated successfully")
                    QMessageBox.information(self, "Success", f"ADB path set to:\n{adb_exe}")
                    # Refresh devices to test the new path
                    self.refresh_devices()
                else:
                    QMessageBox.critical(self, "Error", "Failed to set ADB path")
            else:
                QMessageBox.warning(self, "Error", f"adb.exe not found in:\n{folder_path}\n\nPlease select the folder that contains adb.exe")
        else:
            # Allow file selection as alternative
            adb_path, _ = QFileDialog.getOpenFileName(
                self,
                "Or select ADB executable (adb.exe) directly",
                initial_dir,
                "Executable files (*.exe);;All files (*.*)"
            )
            
            if adb_path:
                if os.path.basename(adb_path).lower() == 'adb.exe':
                    if self.adb.set_adb_path(adb_path):
                        # Save to config.json (auto convert to relative path)
                        self.config.set_extension_path('adb', adb_path, self.project_dir)
                        
                        self.adb_path_label.setText(f"✓ ADB: {adb_path}")
                        self.adb_path_label.setStyleSheet(f"color: {self.colors['success']};")
                        self.log(f"ADB path set to: {adb_path}")
                        self.update_status("ADB path updated successfully")
                        QMessageBox.information(self, "Success", f"ADB path set to:\n{adb_path}")
                        # Refresh devices to test the new path
                        self.refresh_devices()
                    else:
                        QMessageBox.critical(self, "Error", "Failed to set ADB path")
                else:
                    QMessageBox.warning(self, "Warning", "Please select adb.exe file")
    
    def get_device_flag(self):
        """Get device flag for ADB commands"""
        return f"-s {self.current_device}" if self.current_device else ""
    
    def load_buttons_config(self):
        """Load buttons configuration from JSON file"""
        # 优先从 config 目录加载
        config_path = os.path.join(self.project_dir, 'config', 'buttons_cmd.json')
        if not os.path.exists(config_path):
            # 兼容旧路径
            config_path = os.path.join(self.project_dir, 'buttons_cmd.json')
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # Check if config is valid and has groups
                if not config or not config.get('groups'):
                    return False
                # Sort groups by order
                config['groups'] = sorted(config.get('groups', []), key=lambda x: x.get('order', 999))
                # Only log if output_text exists (after UI is initialized)
                if hasattr(self, 'output_text'):
                    self.log("Buttons config loaded from JSON", "INFO")
                return config
        except Exception as e:
            if hasattr(self, 'output_text'):
                self.log(f"Failed to load buttons config: {e}", "ERROR")
        return False
    
    def get_command_param_path(self):
        """Get the path to command param JSON file"""
        logs_dir = os.path.join(self.project_dir, 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        return os.path.join(logs_dir, '.param.history.json')
    
    def load_command_params(self):
        """Load saved command parameters"""
        param_path = self.get_command_param_path()
        try:
            if os.path.exists(param_path):
                with open(param_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}
    
    def save_command_param(self, button_id, params):
        """Save command parameters to JSON file"""
        param_path = self.get_command_param_path()
        all_params = self.load_command_params()
        all_params[button_id] = params
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(param_path), exist_ok=True)
            with open(param_path, 'w', encoding='utf-8') as f:
                json.dump(all_params, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.log(f"Failed to save params: {e}", "ERROR")
    
    def load_commands_config(self):
        """Load commands configuration from JSON file"""
        config = self.load_buttons_config()
        if config and config.get('commands'):
            return config['commands']
        return None
    
    def load_keyboard_config(self):
        """Load keyboard configuration from JSON file"""
        config = self.load_buttons_config()
        if config and config.get('keyboard'):
            return config['keyboard']
        return None
    
    def get_button_handler(self, action):
        """Map action name to handler method"""
        # Map action string to method
        action_map = {
            'push_file': self.push_file,
            'pull_file': self.pull_file,
            'show_file_browser': self.show_file_browser,
            'install_apk': self.install_apk,
            'uninstall_app': self.uninstall_app,
            'reinstall_for_user': self.reinstall_for_user,
            'list_apps': self.list_apps,
            'show_app_manager': self.show_app_manager,
            'open_apks_folder': self.open_apks_folder,
            'degoogle_device': self.degoogle_device,
            'undo_degoogle': self.undo_degoogle,
            'take_screenshot': self.take_screenshot,
            'reboot_device': self.reboot_device,
            'reboot_recovery': self.reboot_recovery,
            'reboot_bootloader': self.reboot_bootloader,
            'fastboot_oem_unlock': self.fastboot_oem_unlock,
            'fastboot_reboot': self.fastboot_reboot,
            'reboot_loader': self.reboot_loader,
            'adb_root_remount': self.adb_root_remount,
            'show_test_scripts': self.show_test_scripts,
            'show_jadx_decompiler': self.show_jadx_decompiler,
            'quick_enable_dev_options': self.quick_enable_dev_options,
            'quick_disable_dev_options': self.quick_disable_dev_options,
            'quick_get_screen_timeout': self.quick_get_screen_timeout,
            'quick_set_screen_timeout': self.quick_set_screen_timeout,
            'quick_open_settings': self.quick_open_settings,
            'quick_adb_input_key': self.quick_adb_input_key,
            'quick_clear_logcat': self.quick_clear_logcat,
            'quick_airplane_mode': self.quick_airplane_mode,
            'quick_screen_record': self.quick_screen_record,
            'quick_battery_status': self.quick_battery_status,
            'quick_device_info': self.quick_device_info,
            'quick_display_info': self.quick_display_info,
            'quick_storage_info': self.quick_storage_info,
            'quick_cpu_info': self.quick_cpu_info,
            'quick_memory_info': self.quick_memory_info,
            'quick_top_processes': self.quick_top_processes,
            'quick_ip_info': self.quick_ip_info,
            'quick_wifi_info': self.quick_wifi_info,
            'factory_menu': self.factory_menu,
        }
        return action_map.get(action)
    
    def create_buttons_from_config(self, ops_layout):
        """Create buttons from JSON configuration"""
        config = self.load_buttons_config()
        if not config:
            return False
        
        # 存储配置引用
        self.buttons_config = config
        self.group_widgets = {}  # group_id -> group_widget
        self.button_widgets = {}  # button_id -> button_widget
        self.button_configs = {}  # button_id -> btn_config
        self.group_layouts = {}  # group_id -> ops_layout (父布局)
        
        for group in config.get('groups', []):
            group_id = group.get('id', 'unknown')
            group_widget = self.create_card(group.get('name', 'Unknown'))
            group_widget.setProperty('group_id', group_id)
            
            # 存储组widget引用
            self.group_widgets[group_id] = group_widget
            
            for btn_config in group.get('buttons', []):
                btn_id = btn_config.get('id', '')
                label = btn_config.get('label', '')
                action = btn_config.get('action', '')
                accent = btn_config.get('accent', False)
                params = btn_config.get('params', None)
                
                handler = self.get_button_handler(action)
                if handler:
                    btn = self.create_button(group_widget, label, handler, accent=accent, params=params)
                    if btn:
                        btn.setProperty('button_id', btn_id)
                        btn.setProperty('group_id', group_id)
                        self.button_widgets[btn_id] = btn
                        self.button_configs[btn_id] = btn_config.copy()
                else:
                    self.log(f"Unknown action: {action}", "WARNING")
            
            ops_layout.addWidget(group_widget)
            self.group_layouts[group_id] = ops_layout
        
        # 保存布局引用
        self._ops_layout_ref = ops_layout
        
        return True
    
    def log_command(self, command, result=None, button_name=None):
        """Log the full ADB command being executed"""
        full_cmd = f"adb {command}"
        self.log(f"Executing: {full_cmd}", "CMD")
        if result:
            if result.get('success') and result.get('stdout'):
                # Show all lines of output with [Response] tag
                output_lines = result['stdout'].strip().split('\n')
                for line in output_lines[:50]:  # 最多显示50行
                    line = line[:200]
                    self.log(f"  -> {line}", "Response")
            elif not result.get('success'):
                error_msg = result.get('stderr') or result.get('stdout') or 'Unknown error'
                error_lines = error_msg.strip().split('\n')
                for line in error_lines[:50]:  # 最多显示50行
                    line = line[:200]
                    self.log(f"  -> {line}", "ERROR")
    
    def push_file(self):
        """Push file or folder to device"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        # 先尝试从参数输入区获取参数
        params = self.get_button_params("Push File")
        source = params.get('source', '')
        dest = params.get('dest', '')
        
        # 如果参数为空，弹窗询问
        if not source:
            file_paths, _ = QFileDialog.getOpenFileNames(
                self, "Select file(s) or folder to push", "", "All Files (*.*)"
            )
            if not file_paths:
                return
            source = file_paths[0] if len(file_paths) == 1 else ";".join(file_paths)
        
        if not dest:
            dest_path, ok = QInputDialog.getText(self, "Destination", "Enter destination path on device (e.g., /sdcard/folder/):")
            if not ok or not dest_path:
                return
            dest = dest_path
        
        # 保存参数到配置文件
        self.save_command_param("push_file", {"source": source, "dest": dest})
        
        # 更新参数输入区显示
        self._update_param_display("Push File", {"source": source, "dest": dest})
        
        # 解析源文件列表
        file_paths = source.split(";") if ";" in source else [source]
        
        self.log(f"Pushing {file_paths[0]} to {dest}...")
        self.update_status("Pushing file/folder...")
        
        def do_push():
            try:
                for file_path in file_paths:
                    # 使用引号包裹路径以处理空格
                    cmd = f'{self.get_device_flag()} push "{file_path}" "{dest}"'
                    self.log(f"Executing: adb {cmd}", "CMD")
                    result = self.adb.run_command(cmd, timeout=120)  # 2分钟超时
                    if result.get('success'):
                        output = result.get('stdout', '').strip()
                        self.log(f"Pushed: {file_path}", "INFO")
                        if output:
                            self.log(f"  -> {output[:200]}", "Response")
                    else:
                        error_msg = result.get('stderr') or result.get('stdout') or 'Unknown error'
                        self.log(f"Failed to push {file_path}: {error_msg}", "ERROR")
                self.log("Push completed", "INFO")
                self.update_status("Push completed")
            except Exception as e:
                self.log(f"Push error: {e}", "ERROR")
                self.update_status("Push failed")
        
        threading.Thread(target=do_push, daemon=True).start()
    
    def pull_file(self):
        """Pull file or folder from device"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        # 先尝试从参数输入区获取参数
        params = self.get_button_params("Pull File")
        source = params.get('source', '')
        dest = params.get('dest', '')
        
        # 如果参数为空，弹窗询问
        if not source:
            device_path, ok = QInputDialog.getText(self, "Source", "Enter file or folder path on device (e.g., /sdcard/folder/):")
            if not ok or not device_path:
                return
            source = device_path
        
        if not dest:
            dest_path = QFileDialog.getExistingDirectory(self, "Select folder to save")
            if not dest_path:
                return
            dest = dest_path
        
        # 保存参数到配置文件
        self.save_command_param("pull_file", {"source": source, "dest": dest})
        
        # 更新参数输入区显示
        self._update_param_display("Pull File", {"source": source, "dest": dest})
        
        self.log(f"Pulling {source} to {dest}...")
        self.update_status("Pulling file/folder...")
        
        def do_pull():
            try:
                # 使用引号包裹路径以处理空格和特殊字符
                cmd = f'{self.get_device_flag()} pull "{source}" "{dest}"'
                self.log(f"Executing: adb {cmd}", "CMD")
                result = self.adb.run_command(cmd, timeout=120)
                if result.get('success'):
                    output = result.get('stdout', '').strip()
                    self.log("File/folder pulled successfully", "INFO")
                    if output:
                        self.log(f"  -> {output[:200]}", "Response")
                    self.update_status("File/folder pulled successfully")
                else:
                    error_msg = result.get('stderr') or result.get('stdout') or 'Unknown error'
                    self.log(f"Error: {error_msg}", "ERROR")
                    self.update_status("Failed to pull file/folder")
            except Exception as e:
                self.log(f"Pull error: {e}", "ERROR")
                self.update_status("Pull failed")
        
        threading.Thread(target=do_pull, daemon=True).start()
    
    def install_apk(self):
        """Install APK file"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        apk_path, _ = QFileDialog.getOpenFileName(self, "Select APK file", "", "APK files (*.apk);;All files (*.*)")
        if not apk_path:
            return
        
        self.log(f"Installing {apk_path}...")
        self.update_status("Installing APK...")
        
        def do_install():
            result = self.adb.run_command(f"{self.get_device_flag()} install {apk_path}", timeout=120)
            if result['success']:
                self.log("APK installed successfully")
                self.update_status("APK installed successfully")
                QMessageBox.information(self, "Success", "APK installed successfully")
            else:
                self.log(f"Error: {result['stderr']}", "ERROR")
                self.update_status("Failed to install APK")
                QMessageBox.critical(self, "Error", f"Failed to install APK:\n{result['stderr']}")
        
        threading.Thread(target=do_install, daemon=True).start()
    
    def uninstall_app(self):
        """Uninstall app"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        package_name, ok = QInputDialog.getText(self, "Uninstall App", "Enter package name (e.g., com.example.app):")
        if not ok or not package_name:
            return
        
        reply = QMessageBox.question(self, "Confirm", f"Uninstall {package_name}?", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self.log(f"Uninstalling {package_name}...")
        self.update_status("Uninstalling app...")
        
        def do_uninstall():
            result = self.adb.run_command(f"{self.get_device_flag()} uninstall {package_name}")
            if result['success']:
                # Check if stdout contains success message
                output = result['stdout'].strip() if result['stdout'] else ''
                if 'Success' in output or 'success' in output.lower():
                    self.log("App uninstalled successfully")
                    self.update_status("App uninstalled successfully")
                    # Thread-safe messagebox - use QTimer to call from main thread
                    QTimer.singleShot(0, lambda: QMessageBox.information(self, "Success", "App uninstalled successfully"))
                else:
                    # Sometimes ADB returns success but stdout has info
                    self.log(f"Uninstall result: {output}")
                    self.update_status("Uninstall completed")
                    # Thread-safe messagebox - use QTimer to call from main thread
                    QTimer.singleShot(0, lambda: QMessageBox.information(self, "Success", f"Uninstall completed:\n{output}"))
            else:
                # Get error from stderr or stdout
                error_msg = result['stderr'] if result['stderr'] else result['stdout']
                if not error_msg or error_msg.strip() == '':
                    error_msg = "Unknown error"
                
                self.log(f"Regular uninstall failed: {error_msg}", "WARNING")
                
                # Try uninstalling for current user (works for system apps without root)
                self.log("Attempting to uninstall for current user (--user 0)...")
                result_user = self.adb.run_command(f"{self.get_device_flag()} shell pm uninstall --user 0 {package_name}")
                
                if result_user['success']:
                    output = result_user['stdout'].strip() if result_user['stdout'] else ''
                    if 'Success' in output or 'success' in output.lower() or output == '':
                        self.log("App uninstalled for current user successfully")
                        self.update_status("App uninstalled for current user")
                        # Thread-safe messagebox - use QTimer to call from main thread
                        QTimer.singleShot(0, lambda: QMessageBox.information(self, "Success", f"App uninstalled for current user successfully!\n\nNote: System apps are only removed for your user account, not from the device."))
                    else:
                        self.log(f"Uninstall result: {output}")
                        self.update_status("Uninstall completed")
                        # Thread-safe messagebox - use QTimer to call from main thread
                    QTimer.singleShot(0, lambda: QMessageBox.information(self, "Success", f"Uninstall completed:\n{output}"))
                else:
                    # Both methods failed
                    error_msg_user = result_user['stderr'] if result_user['stderr'] else result_user['stdout']
                    self.log(f"Error: {error_msg}", "ERROR")
                    self.log(f"User uninstall also failed: {error_msg_user}", "ERROR")
                    self.log(f"Return code: {result['returncode']}", "ERROR")
                    self.log(f"Full stdout: {result['stdout']}", "DEBUG")
                    self.log(f"Full stderr: {result['stderr']}", "DEBUG")
                    self.update_status("Failed to uninstall app")
                    
                    # Provide helpful message
                    if 'DELETE_FAILED_INTERNAL_ERROR' in error_msg or 'system app' in error_msg.lower() or 'package is a system package' in error_msg.lower():
                        help_text = f"Failed to uninstall {package_name}:\n\n{error_msg}\n\nTried both regular and user uninstall methods.\nYou can try disabling it instead (use 'Disable Selected')."
                    else:
                        help_text = f"Failed to uninstall {package_name}:\n\n{error_msg}"
                    
                    # Thread-safe messagebox - use QTimer to call from main thread
                    QTimer.singleShot(0, lambda: QMessageBox.critical(self, "Error", help_text))
        
        threading.Thread(target=do_uninstall, daemon=True).start()
    
    def get_app_label(self, package_name):
        """Get app label/name for a package"""
        # Method 1: Try using pm dump (faster and cleaner output)
        result = self.adb.run_command(f"{self.get_device_flag()} shell pm dump {package_name}")
        if result['success'] and result['stdout']:
            output = result['stdout']
            # Look for applicationLabel in pm dump output
            for line in output.split('\n'):
                line_lower = line.lower().strip()
                if 'applicationlabel=' in line_lower:
                    # Extract label - format is usually "applicationLabel=Label Name"
                    parts = line.split('=', 1)
                    if len(parts) == 2:
                        label = parts[1].strip()
                        # Clean up label - remove any trailing info
                        if label and label.lower() != 'null' and label != package_name:
                            # Remove resource IDs if present
                            if not label.startswith('res/') and not label.startswith('0x'):
                                return label
        
        # Method 2: Use dumpsys package (more detailed but slower)
        result = self.adb.run_command(f"{self.get_device_flag()} shell dumpsys package {package_name}")
        if result['success'] and result['stdout']:
            output = result['stdout']
            in_application_section = False
            
            # Try multiple patterns
            for line in output.split('\n'):
                line_stripped = line.strip()
                line_lower = line_stripped.lower()
                
                # Track if we're in the Application section
                if 'application {' in line_lower or 'application:' in line_lower:
                    in_application_section = True
                elif line_stripped.startswith('}') and in_application_section:
                    in_application_section = False
                
                # Pattern 1: applicationLabel=Label (most common)
                if 'applicationlabel=' in line_lower:
                    # Handle both "applicationLabel=Label" and "applicationLabel Label"
                    if '=' in line:
                        parts = line.split('=', 1)
                        if len(parts) == 2:
                            label = parts[1].strip()
                            # Remove resource references
                            if label.startswith('res/') or label.startswith('0x'):
                                continue
                            # Remove any trailing comments or extra info
                            if ' ' in label:
                                # Take first word if it looks like a resource ID
                                first_word = label.split()[0]
                                if not first_word.startswith('res/') and not first_word.startswith('0x'):
                                    label = first_word
                            if label and label.lower() != 'null' and label != package_name:
                                return label
                    elif 'applicationlabel' in line_lower:
                        # Format: "applicationLabel Label Name"
                        parts = line.split(None, 1)
                        if len(parts) == 2:
                            label = parts[1].strip()
                            if label and label.lower() != 'null' and label != package_name:
                                return label
                
                # Pattern 2: Look for labelRes or label in ApplicationInfo
                if in_application_section:
                    if 'label=' in line_lower and 'labelres=' not in line_lower:
                        parts = line.split('=', 1)
                        if len(parts) == 2:
                            label = parts[1].strip()
                            # Remove resource references like "res/0x7f0a0001"
                            if label.startswith('res/') or label.startswith('0x'):
                                continue
                            if label and label.lower() != 'null' and label != package_name:
                                return label
        
        # Last resort - return None to use package name as fallback
        # Note: If labels aren't showing, check the log output to see what dumpsys/pm dump returns
        return None
    
    def reinstall_for_user(self):
        """Reinstall app for current user (for apps uninstalled with --user 0)"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        self.log("Searching for apps...")
        self.update_status("Loading apps...")
        
        def load_apps():
            # Get all packages (including uninstalled for user)
            # Try to get uninstalled packages first, then fall back to all packages
            result = self.adb.run_command(f"{self.get_device_flag()} shell pm list packages -u")
            if not result['success']:
                # Fall back to all packages
                result = self.adb.run_command(f"{self.get_device_flag()} shell pm list packages")
            
            if not result['success']:
                self.log(f"Error: {result['stderr']}", "ERROR")
                # Thread-safe messagebox - use QTimer to call from main thread
                QTimer.singleShot(0, lambda: QMessageBox.critical(self, "Error", f"Failed to list packages:\n{result['stderr']}"))
                return
            
            packages = result['stdout'].strip().split('\n')
            packages = [p.replace('package:', '').strip() for p in packages if p.strip()]
            
            self.log(f"Found {len(packages)} packages. Getting app names...")
            
            # Get app labels (cache them)
            app_data = {}  # {package_name: (label, package_name)}
            
            # Get labels in batches to avoid too many calls
            for i, package in enumerate(packages):
                if i % 10 == 0:
                    self.log(f"Processing packages {i}/{len(packages)}...")
                
                label = self.get_app_label(package)
                if label:
                    app_data[package] = (label, package)
                else:
                    # Use package name as fallback
                    app_data[package] = (package, package)
            
            self.log(f"Loaded {len(app_data)} apps")
            QTimer.singleShot(0, lambda: self.show_app_search_dialog(app_data))
        
        threading.Thread(target=load_apps, daemon=True).start()
    
    def show_app_search_dialog(self, app_data):
        """Show searchable dialog to select app by name"""
        search_window = QDialog(self)
        search_window.setWindowTitle("Search App to Reinstall")
        search_window.setMinimumSize(600, 500)
        
        layout = QVBoxLayout(search_window)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Search label and entry
        search_label = QLabel("Search by app name (e.g., 'youtube' or 'YouTube'):")
        layout.addWidget(search_label)
        
        search_entry = QLineEdit()
        search_entry.setPlaceholderText("Type to search...")
        layout.addWidget(search_entry)
        
        # List widget
        listbox = QListWidget()
        layout.addWidget(listbox)
        
        # Store app data
        search_window.app_data = app_data
        search_window.filtered_data = []
        
        def update_list():
            """Update listbox based on search"""
            search_term = search_entry.text().lower()
            listbox.clear()
            search_window.filtered_data = []
            
            if not search_term:
                # Show all apps
                for package, (label, pkg) in sorted(app_data.items(), key=lambda x: x[1][0].lower()):
                    display_text = f"{label} ({pkg})"
                    listbox.addItem(display_text)
                    search_window.filtered_data.append((label, pkg))
            else:
                # Filter by search term
                for package, (label, pkg) in sorted(app_data.items(), key=lambda x: x[1][0].lower()):
                    if search_term in label.lower() or search_term in pkg.lower():
                        display_text = f"{label} ({pkg})"
                        listbox.addItem(display_text)
                        search_window.filtered_data.append((label, pkg))
        
        search_entry.textChanged.connect(update_list)
        search_entry.returnPressed.connect(select_app)
        listbox.itemDoubleClicked.connect(lambda: select_app())
        
        def select_app():
            """Select app and reinstall"""
            current_item = listbox.currentItem()
            if not current_item:
                QMessageBox.warning(self, "No Selection", "Please select an app from the list")
                return
            
            idx = listbox.row(current_item)
            if idx < len(search_window.filtered_data):
                label, package_name = search_window.filtered_data[idx]
                
                reply = QMessageBox.question(self, "Confirm Reinstall", 
                                            f"Reinstall {label} ({package_name}) for current user?\n\nThis will restore apps that were uninstalled for your user account.",
                                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply != QMessageBox.StandardButton.Yes:
                    return
                
                search_window.accept()
                self._do_reinstall_for_user(package_name, label)
        
        # Buttons
        button_layout = QHBoxLayout()
        reinstall_btn = QPushButton("Reinstall Selected")
        reinstall_btn.clicked.connect(select_app)
        button_layout.addWidget(reinstall_btn)
        button_layout.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(search_window.reject)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        # Initial population
        update_list()
        search_entry.setFocus()
        search_window.exec()
    
    def _do_reinstall_for_user(self, package_name, app_label=None):
        """Internal function to perform reinstall"""
        display_name = app_label or package_name
        self.log(f"Reinstalling {display_name} ({package_name}) for current user...")
        self.update_status("Reinstalling app for user...")
        
        def do_reinstall():
            # Use pm install-existing to reinstall apps uninstalled for the user
            result = self.adb.run_command(f"{self.get_device_flag()} shell pm install-existing {package_name}")
            if result['success']:
                output = result['stdout'].strip() if result['stdout'] else ''
                if 'Success' in output or 'success' in output.lower() or 'Package' in output:
                    self.log("App reinstalled for current user successfully")
                    self.update_status("App reinstalled for current user")
                    # Thread-safe messagebox - use QTimer to call from main thread
                    QTimer.singleShot(0, lambda: QMessageBox.information(self, "Success", f"{display_name} reinstalled for current user successfully!\n\n{package_name} is now available again."))
                else:
                    self.log(f"Reinstall result: {output}")
                    self.update_status("Reinstall completed")
                    # Thread-safe messagebox - use QTimer to call from main thread
                    QTimer.singleShot(0, lambda: QMessageBox.information(self, "Success", f"Reinstall completed:\n{output}"))
            else:
                error_msg = result['stderr'] if result['stderr'] else result['stdout']
                if not error_msg or error_msg.strip() == '':
                    error_msg = "Unknown error"
                self.log(f"Error: {error_msg}", "ERROR")
                self.update_status("Failed to reinstall app")
                # Thread-safe messagebox - use QTimer to call from main thread
                QTimer.singleShot(0, lambda: QMessageBox.critical(self, "Error", f"Failed to reinstall {display_name}:\n\n{error_msg}\n\nNote: This only works for apps that were previously installed but uninstalled for your user account."))
        
        threading.Thread(target=do_reinstall, daemon=True).start()
    
    def open_apks_folder(self):
        """Open the APKs folder in file explorer"""
        # Get project directory - executable's directory if running as exe, script directory if from source
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            project_dir = os.path.dirname(sys.executable)
        else:
            # Running as script
            project_dir = os.path.dirname(os.path.abspath(__file__))
        apks_dir = os.path.join(project_dir, 'apks')
        os.makedirs(apks_dir, exist_ok=True)
        
        # Open folder in file explorer
        if sys.platform == 'win32':
            os.startfile(apks_dir)
        elif sys.platform == 'darwin':
            subprocess.run(['open', apks_dir])
        else:
            subprocess.run(['xdg-open', apks_dir])
        
        self.log(f"Opened APKs folder: {apks_dir}")
    
    def show_file_browser(self):
        """Show advanced file manager"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        dialog = FileManagerDialog(self, self.adb, self.current_device, self.colors, self.project_dir)
        dialog.exec()
    
    def show_app_manager(self):
        """Show app list manager with详细功能"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        dialog = AppManagerDialog(self, self.adb, self.current_device, self.colors)
        dialog.exec()
    
    def show_test_scripts(self):
        """Show test scripts extension"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        dialog = TestScriptsDialog(self, self.adb, self.current_device, self.colors, self.project_dir)
        dialog.exec()
    
    def show_cluster_control(self):
        """Show cluster control for multi-device management"""
        # Note: Cluster control works with all connected devices, not just current device
        dialog = ClusterControlDialog(self, self.adb, self.current_device, self.colors, self.project_dir)
        dialog.exec()
    
    # ==================== Ghost Downloader 功能 ====================
    
    def launch_ghost_downloader(self):
        """启动 Ghost Downloader (带窗口)"""
        import subprocess
        from pathlib import Path
        
        extensions_dir = Path(self.project_dir) / "extensions" / "Ghost-Downloader-3"
        
        if not extensions_dir.exists():
            self.log_output("❌ 未找到 Ghost Downloader 路径")
            return
        
        main_script = extensions_dir / "Ghost-Downloader-3.py"
        if not main_script.exists():
            self.log_output("❌ 未找到 Ghost Downloader 主程序")
            return
        
        try:
            python_exe = self._get_ghost_venv_python()
            cmd = [python_exe, str(main_script)]
            cwd = str(extensions_dir)

            if sys.platform == "win32":
                self.download_process = subprocess.Popen(
                    cmd, cwd=cwd, creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                self.download_process = subprocess.Popen(cmd, cwd=cwd)

            self.log_output(f"📥 Ghost Downloader 已启动 (PID: {self.download_process.pid})")

        except Exception as e:
            self.log_output(f"❌ 启动 Ghost Downloader 失败: {e}")
    
    def _init_download_folder_path(self):
        """初始化下载路径显示"""
        try:
            from pathlib import Path
            # 尝试从 Ghost Downloader 配置文件读取下载路径
            config_path = Path(self.project_dir) / "extensions" / "Ghost-Downloader-3" / "Ghost Downloader 配置文件.json"
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    download_folder = config.get('Download', {}).get('DownloadFolder', '')
                    if download_folder:
                        self.download_path_display.setText(download_folder)
                        self._download_folder = download_folder
                        return
            
            # 默认使用系统下载目录
            from PySide6.QtCore import QStandardPaths
            default_download = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
            self.download_path_display.setText(default_download)
            self._download_folder = default_download
        except Exception as e:
            self.download_path_display.setText(f"获取失败: {e}")
            self._download_folder = None
    
    def open_download_folder(self):
        """打开下载文件夹"""
        import subprocess
        from pathlib import Path
        
        folder = getattr(self, '_download_folder', None)
        
        # 如果没有设置或目录不存在，使用系统默认下载目录
        if not folder or not Path(folder).exists():
            from PySide6.QtCore import QStandardPaths
            folder = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
        
        if folder and Path(folder).exists():
            try:
                # 转换为绝对路径并规范化（Windows 使用反斜杠）
                folder_path = Path(folder).resolve()
                folder_str = str(folder_path)
                
                if sys.platform == "win32":
                    # Windows 下使用 explorer 打开，确保路径格式正确
                    subprocess.run(["explorer.exe", folder_str], check=False, shell=True)
                elif sys.platform == "darwin":
                    subprocess.run(["open", folder_str], check=False)
                else:
                    subprocess.run(["xdg-open", folder_str], check=False)
                self.update_download_status(f"📂 已打开下载目录: {folder_str}")
            except Exception as e:
                self.update_download_status(f"❌ 打开失败: {e}")
        else:
            self.update_download_status("⚠️ 下载目录不存在，请先在 Ghost Downloader 中设置")
    
    class DownloadTaskThread(QThread):
        """异步下载任务线程"""
        status_signal = pyqtSignal(str)  # 状态消息
        finished_signal = pyqtSignal(int)  # 成功数量
        
        def __init__(self, links, project_dir, parent=None):
            super().__init__(parent)
            self.links = links
            self.project_dir = project_dir
            self.download_process = None
            
        def check_websocket_available(self, ws_url):
            try:
                import websocket
                ws = websocket.create_connection(ws_url, timeout=3)
                ws.close()
                return True
            except:
                return False
        
        def run(self):
            import subprocess
            import json
            import time
            import os
            from pathlib import Path
            
            WS_URL = "ws://127.0.0.1:14370"
            
            # 禁用代理
            os.environ['NO_PROXY'] = '127.0.0.1,localhost'
            os.environ.pop('HTTP_PROXY', None)
            os.environ.pop('HTTPS_PROXY', None)
            
            # 检查 WebSocket 服务是否可用
            if self.check_websocket_available(WS_URL):
                self.status_signal.emit("✅ 检测到 Ghost Downloader 服务已运行")
            else:
                # 启动 Ghost Downloader 后台服务
                extensions_dir = Path(self.project_dir) / "extensions" / "Ghost-Downloader-3"
                main_script = extensions_dir / "Ghost-Downloader-3.py"
                
                if not main_script.exists():
                    self.status_signal.emit("❌ 找不到 Ghost Downloader")
                    self.finished_signal.emit(0)
                    return
                
                try:
                    cmd = [sys.executable, str(main_script), "--headless"]
                    cwd = str(extensions_dir)
                    
                    if sys.platform == "win32":
                        self.download_process = subprocess.Popen(
                            cmd, cwd=cwd, creationflags=subprocess.CREATE_NO_WINDOW
                        )
                    else:
                        self.download_process = subprocess.Popen(cmd, cwd=cwd)
                    
                    self.status_signal.emit(f"🚀 后台服务已启动 (PID: {self.download_process.pid})")
                    self.status_signal.emit("⏳ 等待 WebSocket 服务就绪...")
                    
                    # 等待 WebSocket 服务启动（最多等待 15 秒）
                    max_wait = 15
                    for i in range(max_wait):
                        time.sleep(1)
                        if self.check_websocket_available(WS_URL):
                            self.status_signal.emit("✅ WebSocket 服务已就绪")
                            break
                        self.status_signal.emit(f"⏳ 等待中... ({i+1}/{max_wait})")
                    else:
                        self.status_signal.emit("❌ WebSocket 服务启动超时")
                        self.finished_signal.emit(0)
                        return
                except Exception as e:
                    self.status_signal.emit(f"❌ 启动失败: {e}")
                    self.finished_signal.emit(0)
                    return
            
            # 通过 WebSocket 发送任务
            try:
                import websocket
                
                os.environ['NO_PROXY'] = '127.0.0.1,localhost'
                if 'HTTP_PROXY' in os.environ:
                    del os.environ['HTTP_PROXY']
                if 'HTTPS_PROXY' in os.environ:
                    del os.environ['HTTPS_PROXY']
                
                success_count = 0
                for link in self.links:
                    task_data = {
                        "url": link,
                        "headers": {
                            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                        },
                        "filename": None,
                        "referer": None
                    }
                    message = json.dumps(task_data)
                    
                    try:
                        ws = websocket.create_connection(WS_URL, timeout=10)
                        ws.send(message)
                        response = ws.recv()
                        ws.close()
                        self.status_signal.emit(f"✅ 任务已添加: {link[:60]}...")
                        success_count += 1
                    except Exception as ws_error:
                        self.status_signal.emit(f"❌ 发送失败: {ws_error}")
                
                self.finished_signal.emit(success_count)
                
            except ImportError:
                self.status_signal.emit("❌ 缺少 websocket-client 库，正在安装...")
                import subprocess as sp
                sp.run([sys.executable, "-m", "pip", "install", "websocket-client", "-q"])
                self.status_signal.emit("✅ 已安装，请重新点击开始下载")
                self.finished_signal.emit(0)
            except Exception as e:
                self.status_signal.emit(f"❌ 发送任务失败: {e}")
                self.finished_signal.emit(0)
    
    def start_download_tasks(self):
        """开始下载任务（异步方式）"""
        links_text = self.download_links_input.toPlainText().strip()
        if not links_text:
            self.update_download_status("⚠️ 请先输入下载链接")
            return
        
        # 解析链接（每行一个）
        links = [line.strip() for line in links_text.split('\n') if line.strip() and line.strip().startswith('http')]
        
        if not links:
            self.update_download_status("⚠️ 未找到有效的下载链接")
            return
        
        # 禁用开始按钮，防止重复点击
        self.download_start_btn.setEnabled(False)
        self.update_download_status("🚀 正在启动下载任务...")
        
        # 创建异步线程
        self.download_task_thread = self.DownloadTaskThread(links, self.project_dir, self)
        self.download_task_thread.status_signal.connect(self.update_download_status)
        self.download_task_thread.finished_signal.connect(self._on_download_tasks_finished)
        self.download_task_thread.start()
    
    def _on_download_tasks_finished(self, success_count: int):
        """下载任务发送完成回调"""
        self.download_start_btn.setEnabled(True)
        
        if success_count > 0:
            self.download_tasks = [f"task_{i}" for i in range(success_count)]  # 更新任务计数
            self.update_download_stats()
            self.download_stop_btn.setEnabled(True)
            self.update_download_status(f"📊 已添加 {success_count} 个下载任务")
            
            # 显示下载目录提示
            if hasattr(self, '_download_folder'):
                self.update_download_status(f"📁 文件将保存到: {self._download_folder}")
            
            # 启动进度监控
            self._start_progress_monitor()
    
    def stop_all_downloads(self):
        """停止所有下载任务"""
        # 停止进度监控
        self._stop_progress_monitor()
        
        # Ghost Downloader 目前不支持外部停止，需要手动在程序中操作
        self.update_download_status("⚠️ 请在 Ghost Downloader 窗口中手动停止下载任务")
        self.update_download_status("💡 提示: 点击“打开主界面”按钮可以查看和控制下载任务")
    
    def _get_ghost_venv_python(self):
        """获取 Ghost Downloader 专用 venv 的 Python 解释器路径（本地路径，避免网络盘限制）"""
        if sys.platform == "win32":
            local_venv = Path.home() / ".venvs" / "ghost-downloader" / "Scripts" / "python.exe"
        else:
            local_venv = Path.home() / ".venvs" / "ghost-downloader" / "bin" / "python"
        # 若本地 venv 存在则使用，否则回退到当前解释器
        return str(local_venv) if local_venv.exists() else sys.executable

    def open_ghost_downloader_window(self):
        """打开 Ghost Downloader 主界面"""
        import subprocess

        # 从配置文件读取路径
        config_path = Path(self.project_dir) / "plugins" / "plugins_config.json"
        if config_path.exists():
            import json
            with open(config_path, 'r', encoding='utf-8') as f:
                plugin_config = json.load(f)
            gd_config = plugin_config.get('ghost_downloader', {})
            module_path = gd_config.get('module_path', 'extensions/Ghost-Downloader-3')
            main_script_name = gd_config.get('main_script', 'Ghost-Downloader-3.py')
        else:
            module_path = 'extensions/Ghost-Downloader-3'
            main_script_name = 'Ghost-Downloader-3.py'

        extensions_dir = Path(self.project_dir) / module_path
        main_script = extensions_dir / main_script_name

        if not main_script.exists():
            self.update_download_status("❌ 找不到 Ghost Downloader")
            return

        try:
            python_exe = self._get_ghost_venv_python()
            cmd = [python_exe, str(main_script)]
            cwd = str(extensions_dir)

            if sys.platform == "win32":
                subprocess.Popen(cmd, cwd=cwd, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                subprocess.Popen(cmd, cwd=cwd)

            self.update_download_status("✅ 已打开 Ghost Downloader 主界面")
        except Exception as e:
            self.update_download_status(f"❌ 打开失败: {e}")
    
    def clear_download_tasks(self):
        """清空下载任务列表"""
        self.download_links_input.clear()
        self.download_tasks.clear()
        self.update_download_status("🗑️ 任务列表已清空")
        self.update_download_stats()
    
    def delete_download_tasks_and_files(self):
        """删除下载任务和文件"""
        from PySide6.QtWidgets import QMessageBox
        
        reply = QMessageBox.question(
            self,
            "确认删除",
            "确定要删除所有下载任务及其对应的文件吗？\n此操作不可恢复！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.download_links_input.clear()
            self.download_tasks.clear()
            self.update_download_status("❌ 任务和文件已删除（请在 Ghost Downloader 中确认）")
            self.update_download_stats()
    
    def update_download_status(self, message: str, is_progress: bool = False):
        """更新下载状态显示
        
        Args:
            message: 状态消息
            is_progress: 是否为进度更新（进度更新会更新最后一行而不是添加新行）
        """
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if is_progress and hasattr(self, '_last_progress_line'):
            # 更新最后一行进度信息
            cursor = self.download_status_area.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.select(cursor.SelectionType.LineUnderCursor)
            cursor.removeSelectedText()
            cursor.deletePreviousChar()  # 删除换行符
            self.download_status_area.append(f"[{timestamp}] {message}")
        else:
            self.download_status_area.append(f"[{timestamp}] {message}")
        
        # 限制日志行数，防止刷屏
        doc = self.download_status_area.document()
        if doc.blockCount() > 100:
            cursor = self.download_status_area.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.movePosition(cursor.MoveOperation.Down, cursor.MoveMode.KeepAnchor, 20)
            cursor.removeSelectedText()
        
        # 自动滚动到底部
        scrollbar = self.download_status_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def update_download_stats(self, speed: str = "-- KB/s", active: int = None):
        """更新下载统计信息"""
        if active is None:
            active = len(self.download_tasks)
        self.download_stats_label.setText(f"总速度: {speed} | 活动任务: {active}")
    
    def _start_progress_monitor(self):
        """启动进度监控"""
        if not hasattr(self, '_progress_timer'):
            self._progress_timer = QTimer(self)
            self._progress_timer.timeout.connect(self._check_download_progress)
        self._progress_monitor_count = 0
        self._progress_timer.start(2000)  # 每2秒检查一次
    
    def _stop_progress_monitor(self):
        """停止进度监控"""
        if hasattr(self, '_progress_timer'):
            self._progress_timer.stop()
    
    def _check_download_progress(self):
        """检查下载进度（通过 WebSocket 接口）"""
        import time
        
        self._progress_monitor_count = getattr(self, '_progress_monitor_count', 0) + 1
        
        WS_URL = "ws://127.0.0.1:14370"
        
        try:
            import websocket
            import os
            
            # 禁用代理
            os.environ['NO_PROXY'] = '127.0.0.1,localhost'
            
            ws = websocket.create_connection(WS_URL, timeout=3)
            ws.send(json.dumps({"type": "get_progress"}))
            response = ws.recv()
            ws.close()
            
            data = json.loads(response)
            
            if data.get("type") == "progress" and "error" not in data:
                global_speed = data.get("globalSpeed", 0)
                active_count = data.get("activeCount", 0)
                tasks = data.get("tasks", [])
                
                # 更新速度显示
                speed_str = self._format_speed(global_speed)
                self.update_download_stats(speed=speed_str, active=active_count)
                
                # 显示每个任务的进度
                for task in tasks:
                    file_name = task.get('fileName', 'Unknown')
                    task_key = f"{file_name}_{task.get('url', '')}"
                    
                    if task.get("status") == "finished":
                        # 检查是否已经报告过完成
                        if not hasattr(self, '_finished_tasks'):
                            self._finished_tasks = set()
                        
                        if task_key not in self._finished_tasks:
                            self._finished_tasks.add(task_key)
                            file_size = task.get("fileSize", 0)
                            self.update_download_status(
                                f"✅ {file_name}: 已完成 ({self._format_size(file_size)})"
                            )
                    elif task.get("status") == "working":
                        progress = task.get("progress", 0)
                        file_size = task.get("fileSize", 0)
                        speed = task.get("speed", 0)
                        
                        # 显示进度：已下载/总大小
                        progress_str = f"{self._format_size(progress)}/{self._format_size(file_size)}"
                        speed_str = self._format_speed(speed)
                        
                        # 计算百分比
                        percent = (progress / file_size * 100) if file_size > 0 else 0
                        
                        # 使用进度模式更新（避免刷屏）
                        self._last_progress_line = True
                        self.update_download_status(
                            f"⬇️ {file_name}: {progress_str} ({percent:.1f}%) - {speed_str}/s",
                            is_progress=True
                        )
                
                # 如果没有活跃任务，显示提示
                if active_count == 0 and tasks:
                    finished_count = len([t for t in tasks if t.get("status") == "finished"])
                    if finished_count > 0:
                        self.update_download_status(f"🎉 所有下载任务已完成！共 {finished_count} 个文件")
                        self._stop_progress_monitor()
                
                # 更新下载路径（从响应中获取）
                if hasattr(self, '_download_folder') and self._download_folder:
                    pass  # 已设置
                    
        except Exception as e:
            # 如果 WebSocket 连接失败，使用文件监控作为备用方案
            self._check_download_progress_by_file()
    
    def _check_download_progress_by_file(self):
        """通过文件系统检查下载进度（备用方案）"""
        from pathlib import Path
        import time
        
        if hasattr(self, '_download_folder') and self._download_folder:
            download_path = Path(self._download_folder)
            if download_path.exists():
                try:
                    files = list(download_path.glob('*'))
                    # 过滤临时文件
                    real_files = [f for f in files if f.is_file() and f.suffix not in ['.ghd', '.tmp', '.part']]
                    
                    # 计算总大小和最近更新的文件
                    total_size = sum(f.stat().st_size for f in real_files)
                    recent_files = sorted(real_files, key=lambda f: f.stat().st_mtime, reverse=True)[:3]
                    
                    for f in recent_files:
                        size_mb = f.stat().st_size / (1024 * 1024)
                        mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%H:%M:%S")
                        
                        if time.time() - f.stat().st_mtime < 300:
                            self.update_download_status(f"📄 {f.name}: {size_mb:.2f} MB (更新: {mtime})")
                    
                except Exception as e:
                    pass
        
        # 超过30分钟自动停止监控
        if self._progress_monitor_count > 900:
            self._stop_progress_monitor()
            self.update_download_status("⏹️ 进度监控已自动停止（超时）")
    
    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    
    def _format_speed(self, speed_bytes: int) -> str:
        """格式化下载速度"""
        if speed_bytes < 1024:
            return f"{speed_bytes} B"
        elif speed_bytes < 1024 * 1024:
            return f"{speed_bytes / 1024:.1f} KB"
        elif speed_bytes < 1024 * 1024 * 1024:
            return f"{speed_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{speed_bytes / (1024 * 1024 * 1024):.2f} GB"
    
    def log_output(self, message: str):
        """输出日志到主日志区"""
        self.output_text.append(message)
        scrollbar = self.output_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def show_plugin_manager(self):
        """Show plugin manager dialog"""
        from framework.plugin.plugin_api import PluginAPI
        # Initialize plugin system if not already done
        if not hasattr(self, '_plugin_manager'):
            self._event_bus = EventBus()
            plugins_dir = os.path.join(self.project_dir, 'plugins')
            # Create plugin API
            self._plugin_api = PluginAPI(
                self.adb, 
                getattr(self, 'scrcpy_manager', None),
                self.config,
                self._event_bus
            )
            self._plugin_manager = PluginManager(
                [plugins_dir], 
                self._plugin_api, 
                self._event_bus
            )
            if os.path.exists(plugins_dir):
                self._plugin_manager.load_all_plugins()
        
        dialog = PluginManagerDialog(
            plugin_manager=self._plugin_manager,
            parent=self
        )
        dialog.exec()
    
    def show_jadx_decompiler(self, package_name=None):
        """Show JADX decompiler tool
        
        Args:
            package_name: Optional package name to auto-pull and decompile
        """
        dialog = JadxDecompilerDialog(
            self, 
            adb_path=self.adb.adb_path,
            device_id=self.current_device,
            package_name=package_name,
            dark_mode=self.dark_mode,
            colors=self.colors
        )
        dialog.exec()
    
    # Quick Actions Functions
    def quick_battery_status(self):
        """Show battery status"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        def do_battery():
            try:
                cmd = f"{self.get_device_flag()} shell dumpsys battery"
                result = self.adb.run_command(cmd)
                # 使用QTimer在主线程中处理结果
                QTimer.singleShot(0, lambda c=cmd, r=result: self._handle_battery_result(c, r))
            except Exception as e:
                QTimer.singleShot(0, lambda err=str(e): self.log(f"Error: {err}", "ERROR"))
        
        threading.Thread(target=do_battery, daemon=True).start()
    
    def _handle_battery_result(self, cmd, result):
        """处理Battery Status结果 - 在主线程中调用"""
        self.log_command(cmd, result, "Battery Status")
        if result.get('success'):
            self.log("Battery status retrieved", "INFO")
            QMessageBox.information(self, "Battery Status", result.get('stdout', 'No output'))
        else:
            error_msg = result.get('stderr') or result.get('stdout') or 'Unknown error'
            self.log(f"Failed to get battery status: {error_msg}", "ERROR")
    
    def quick_device_info(self):
        """Show device information"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        self.log("Getting device info...", "INFO")
        
        def do_info():
            try:
                cmd = f"{self.get_device_flag()} shell getprop"
                result = self.adb.run_command(cmd)
                
                # 在主线程中更新UI
                QTimer.singleShot(0, lambda: self._handle_device_info_result(cmd, result))
            except Exception as e:
                QTimer.singleShot(0, lambda: self.log(f"Error: {e}", "ERROR"))
        
        threading.Thread(target=do_info, daemon=True).start()
    
    def _handle_device_info_result(self, cmd, result):
        """处理Device Info结果 - 在主线程中调用"""
        self.log_command(cmd, result, "Device Info")
        if result.get('success'):
            props = result.get('stdout', '')
            
            # Extract key information
            info_lines = []
            xbh_model = None
            
            for line in props.split('\n'):
                # 提取 XbhModel
                if 'ro.product.xbh.customer.model' in line:
                    try:
                        xbh_model = line.split(']: [')[1].strip(']')
                    except:
                        pass
                
                # 提取其他关键信息
                if any(key in line for key in ['ro.product.model', 'ro.product.brand', 
                                                 'ro.build.version.release', 'ro.build.id',
                                                 'ro.product.manufacturer']):
                    info_lines.append(line.strip('[]').replace(']: [', ': '))
            
            # 添加 XbhModel 到显示信息
            if xbh_model:
                info_text = f"XbhModel: {xbh_model}\n" + '\n'.join(info_lines)
            else:
                info_text = '\n'.join(info_lines) if info_lines else "Device info not available"
            self.log("Device info retrieved", "INFO")
            QMessageBox.information(self, "Device Info", info_text)
        else:
            error_msg = result.get('stderr') or result.get('stdout') or 'Unknown error'
            self.log(f"Failed to get device info: {error_msg}", "ERROR")
    
    def quick_display_info(self):
        """Show display information"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        def do_display():
            try:
                cmd = f"{self.get_device_flag()} shell wm size"
                result = self.adb.run_command(cmd)
                result2 = self.adb.run_command(f"{self.get_device_flag()} shell wm density")
                QTimer.singleShot(0, lambda c=cmd, r=result, r2=result2: self._handle_display_result(c, r, r2))
            except Exception as e:
                QTimer.singleShot(0, lambda err=str(e): self.log(f"Error: {err}", "ERROR"))
        
        threading.Thread(target=do_display, daemon=True).start()
    
    def _handle_display_result(self, cmd, result, result2):
        """处理Display Info结果 - 在主线程中调用"""
        self.log_command(cmd, result, "Display Info")
        if result.get('success'):
            size_info = result.get('stdout', '').strip()
            density_info = result2.get('stdout', '').strip() if result2.get('success') else "N/A"
            info = f"{size_info}\n{density_info}"
            self.log("Display info retrieved", "INFO")
            QMessageBox.information(self, "Display Info", info)
        else:
            error_msg = result.get('stderr') or result.get('stdout') or 'Unknown error'
            self.log(f"Failed to get display info: {error_msg}", "ERROR")
    
    def quick_storage_info(self):
        """Show storage information"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        def do_storage():
            try:
                cmd = f"{self.get_device_flag()} shell df -h"
                result = self.adb.run_command(cmd)
                QTimer.singleShot(0, lambda c=cmd, r=result: self._handle_storage_result(c, r))
            except Exception as e:
                QTimer.singleShot(0, lambda err=str(e): self.log(f"Error: {err}", "ERROR"))
        
        threading.Thread(target=do_storage, daemon=True).start()
    
    def _handle_storage_result(self, cmd, result):
        """处理Storage Info结果 - 在主线程中调用"""
        self.log_command(cmd, result, "Storage Info")
        if result.get('success'):
            self.log("Storage info retrieved", "INFO")
            QMessageBox.information(self, "Storage Info", result.get('stdout', 'No output'))
        else:
            error_msg = result.get('stderr') or result.get('stdout') or 'Unknown error'
            self.log(f"Failed to get storage info: {error_msg}", "ERROR")
    
    def quick_cpu_info(self):
        """Show CPU information"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        def do_cpu():
            try:
                cmd = f"{self.get_device_flag()} shell cat /proc/cpuinfo"
                result = self.adb.run_command(cmd)
                QTimer.singleShot(0, lambda c=cmd, r=result: self._handle_cpu_result(c, r))
            except Exception as e:
                QTimer.singleShot(0, lambda err=str(e): self.log(f"Error: {err}", "ERROR"))
        
        threading.Thread(target=do_cpu, daemon=True).start()
    
    def _handle_cpu_result(self, cmd, result):
        """处理CPU Info结果 - 在主线程中调用"""
        self.log_command(cmd, result, "CPU Info")
        if result.get('success'):
            cpu_info = result.get('stdout', '')
            lines = [line for line in cpu_info.split('\n')[:50]]
            self.log("CPU info retrieved", "INFO")
            QMessageBox.information(self, "CPU Info", '\n'.join(lines))
        else:
            error_msg = result.get('stderr') or result.get('stdout') or 'Unknown error'
            self.log(f"Failed to get CPU info: {error_msg}", "ERROR")
    
    def quick_memory_info(self):
        """Show memory information"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        def do_memory():
            try:
                cmd = f"{self.get_device_flag()} shell cat /proc/meminfo"
                result = self.adb.run_command(cmd)
                QTimer.singleShot(0, lambda c=cmd, r=result: self._handle_memory_result(c, r))
            except Exception as e:
                QTimer.singleShot(0, lambda err=str(e): self.log(f"Error: {err}", "ERROR"))
        
        threading.Thread(target=do_memory, daemon=True).start()
    
    def _handle_memory_result(self, cmd, result):
        """处理Memory Info结果 - 在主线程中调用"""
        self.log_command(cmd, result, "Memory Info")
        if result.get('success'):
            mem_info = result.get('stdout', '')
            lines = [line for line in mem_info.split('\n')[:20]]
            self.log("Memory info retrieved", "INFO")
            QMessageBox.information(self, "Memory Info", '\n'.join(lines))
        else:
            error_msg = result.get('stderr') or result.get('stdout') or 'Unknown error'
            self.log(f"Failed to get memory info: {error_msg}", "ERROR")
    
    def quick_top_processes(self):
        """Show top processes"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        def do_top():
            cmd = f"{self.get_device_flag()} shell top -n 1"
            result = self.adb.run_command(cmd)
            self.log_command(cmd, result, "Top Processes")
            if result['success']:
                self.log("Top processes retrieved", "INFO")
                QTimer.singleShot(0, lambda: QMessageBox.information(
                    self, "Top Processes", result['stdout']
                ))
            else:
                self.log(f"Failed to get top processes: {result.get('stderr', '')}", "ERROR")
        
        threading.Thread(target=do_top, daemon=True).start()
    
    def quick_ip_info(self):
        """Show IP address information"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        def do_ip():
            cmd = f"{self.get_device_flag()} shell ip addr show wlan0"
            result = self.adb.run_command(cmd)
            self.log_command(cmd, result, "IP Address")
            if result['success']:
                ip_info = result['stdout']
                # Try to extract IP
                import re
                ip_match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', ip_info)
                if ip_match:
                    ip = ip_match.group(1)
                    self.log(f"Device IP: {ip}", "INFO")
                    QTimer.singleShot(0, lambda: QMessageBox.information(
                        self, "IP Address", f"WiFi IP: {ip}\n\nFull info:\n{ip_info}"
                    ))
                else:
                    self.log("IP address retrieved", "INFO")
                    QTimer.singleShot(0, lambda: QMessageBox.information(
                        self, "IP Address", ip_info
                    ))
            else:
                self.log(f"Failed to get IP info: {result.get('stderr', '')}", "ERROR")
        
        threading.Thread(target=do_ip, daemon=True).start()
    
    def quick_wifi_info(self):
        """Show WiFi information"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        def do_wifi():
            cmd = f"{self.get_device_flag()} shell dumpsys wifi"
            result = self.adb.run_command(cmd)
            self.log_command(cmd, result, "WiFi Info")
            if result['success']:
                wifi_info = result['stdout']
                # Extract key lines
                lines = []
                for line in wifi_info.split('\n'):
                    if any(key in line.lower() for key in ['ssid', 'ip', 'state', 'signal']):
                        lines.append(line.strip())
                        if len(lines) >= 30:  # Limit output
                            break
                
                info_text = '\n'.join(lines) if lines else wifi_info[:2000]
                self.log("WiFi info retrieved", "INFO")
                QTimer.singleShot(0, lambda: QMessageBox.information(
                    self, "WiFi Info", info_text
                ))
            else:
                self.log(f"Failed to get WiFi info: {result.get('stderr', '')}", "ERROR")
        
        threading.Thread(target=do_wifi, daemon=True).start()

    def factory_menu(self):
        """Open factory menu"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        self.log("Opening factory menu...")
        self.update_status("Opening factory menu...")
        
        def do_factory_menu():
            cmd = f"{self.get_device_flag()} shell am startservice -n com.xbh.factory.menu/.app.TvMenuWindowManagerService -e com.xbh.factory.menu.commmand com.xbh.factory.menu.commmand.factory_menu"
            result = self.adb.run_command(cmd)
            self.log_command(cmd, result, "Factory Menu")
            if result.get('success'):
                self.log("Factory menu opened", "INFO")
                self.update_status("Factory menu opened")
            else:
                error_msg = result.get('stderr') or result.get('stdout') or 'Unknown error'
                self.log(f"Error: {error_msg}", "ERROR")
                self.update_status("Failed to open factory menu")
        
        threading.Thread(target=do_factory_menu, daemon=True).start()
    
    def quick_clear_logcat(self):
        """Clear logcat buffer"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        def do_clear():
            cmd = f"{self.get_device_flag()} logcat -c"
            result = self.adb.run_command(cmd)
            self.log_command(cmd, result, "Clear Logcat")
            if result['success']:
                self.log("Logcat buffer cleared", "INFO")
                QTimer.singleShot(0, lambda: QMessageBox.information(
                    self, "Success", "Logcat buffer cleared"
                ))
            else:
                self.log(f"Failed to clear logcat: {result.get('stderr', '')}", "ERROR")
        
        threading.Thread(target=do_clear, daemon=True).start()
    
    def quick_airplane_mode(self):
        """Toggle airplane mode"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        def do_airplane():
            # Check current state
            cmd1 = f"{self.get_device_flag()} shell settings get global airplane_mode_on"
            self.log("Button clicked: Toggle Airplane Mode", "INFO")
            result = self.adb.run_command(cmd1)
            self.log_command(cmd1, result, "Toggle Airplane Mode")
            
            if result.get('success'):
                current_state = result.get('stdout', '').strip()
                new_state = "0" if current_state == "1" else "1"
                
                # Toggle
                cmd2 = f"{self.get_device_flag()} shell settings put global airplane_mode_on {new_state}"
                self.log_command(cmd2, None, "Toggle Airplane Mode")
                self.adb.run_command(cmd2)
                cmd3 = f"{self.get_device_flag()} shell am broadcast -a android.intent.action.AIRPLANE_MODE"
                self.log_command(cmd3, None, "Toggle Airplane Mode")
                self.adb.run_command(cmd3)
                
                mode = "ON" if new_state == "1" else "OFF"
                self.log(f"Airplane mode: {mode}", "INFO")
                QTimer.singleShot(0, lambda: QMessageBox.information(
                    self, "Success", f"Airplane mode: {mode}"
                ))
            else:
                self.log(f"Failed to toggle airplane mode: {result.get('stderr', '')}", "ERROR")
        
        threading.Thread(target=do_airplane, daemon=True).start()
    
    def quick_screen_record(self):
        """Record screen for 30 seconds"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        def do_record():
            remote_path = "/sdcard/screen_record.mp4"
            
            self.log("Starting screen recording (30s)...", "INFO")
            QTimer.singleShot(0, lambda: self.update_status("Recording screen..."))
            
            # Record
            cmd = f"{self.get_device_flag()} shell screenrecord --time-limit 30 {remote_path}"
            result = self.adb.run_command(cmd)
            self.log_command(cmd, result, "Screen Record")
            
            if result['success'] or result['returncode'] == 0:
                self.log("Recording complete", "INFO")
                
                # Ask to download
                reply = QMessageBox.question(
                    self, "Recording Complete", 
                    "Screen recording saved to device.\nDownload to computer?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    # Download
                    screenshots_dir = os.path.join(self.project_dir, 'screenshots')
                    os.makedirs(screenshots_dir, exist_ok=True)
                    
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    local_path = os.path.join(screenshots_dir, f"recording_{timestamp}.mp4")
                    
                    result2 = self.adb.run_command(
                        f'{self.get_device_flag()} pull "{remote_path}" "{local_path}"'
                    )
                    
                    if result2['success']:
                        self.log(f"Recording saved: {local_path}", "INFO")
                        QTimer.singleShot(0, lambda: QMessageBox.information(
                            self, "Success", f"Recording saved to:\n{local_path}"
                        ))
                    else:
                        self.log(f"Failed to download recording: {result2.get('stderr', '')}", "ERROR")
            else:
                self.log(f"Failed to record screen: {result.get('stderr', '')}", "ERROR")
            
            QTimer.singleShot(0, lambda: self.update_status("Ready"))
        
        threading.Thread(target=do_record, daemon=True).start()
    
    # ==================== New Quick Actions ====================
    
    def quick_enable_dev_options(self):
        """打开开发者选项"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        def do_enable():
            cmd = f"{self.get_device_flag()} shell settings put global development_settings_enabled 1"
            result = self.adb.run_command(cmd)
            self.log_command(cmd, result, "打开开发者选项")
            QTimer.singleShot(0, lambda: self._handle_dev_option_result(result, True))
        
        threading.Thread(target=do_enable, daemon=True).start()
    
    def quick_disable_dev_options(self):
        """关闭开发者选项"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        def do_disable():
            cmd = f"{self.get_device_flag()} shell settings put global development_settings_enabled 0"
            result = self.adb.run_command(cmd)
            self.log_command(cmd, result, "关闭开发者选项")
            QTimer.singleShot(0, lambda: self._handle_dev_option_result(result, False))
        
        threading.Thread(target=do_disable, daemon=True).start()
    
    def _handle_dev_option_result(self, result, enabled):
        """处理开发者选项设置结果"""
        if result['success']:
            status = "已打开" if enabled else "已关闭"
            QMessageBox.information(self, "Success", f"开发者选项{status}")
            self.log(f"Developer options {'enabled' if enabled else 'disabled'}", "INFO")
        else:
            QMessageBox.warning(self, "Error", f"操作失败: {result.get('stderr', 'Unknown error')}")
    
    def quick_get_screen_timeout(self):
        """获取屏幕休眠时间"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        def do_get():
            cmd = f"{self.get_device_flag()} shell settings get system screen_off_timeout"
            result = self.adb.run_command(cmd)
            self.log_command(cmd, result, "获取屏幕休眠时间")
            QTimer.singleShot(0, lambda: self._handle_screen_timeout_result(result, False))
        
        threading.Thread(target=do_get, daemon=True).start()
    
    def quick_set_screen_timeout(self):
        """设置屏幕休眠时间"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        # 弹出输入对话框
        timeout, ok = QInputDialog.getInt(
            self, "设置屏幕休眠时间", 
            "请输入休眠时间(毫秒):\n常用: 5000(5秒), 10000(10秒), 30000(30秒), 60000(1分钟), 300000(5分钟)",
            30000, 0, 600000
        )
        if not ok:
            return
        
        def do_set():
            cmd = f"{self.get_device_flag()} shell settings put system screen_off_timeout {timeout}"
            result = self.adb.run_command(cmd)
            self.log_command(cmd, result, "设置屏幕休眠时间")
            QTimer.singleShot(0, lambda: self._handle_screen_timeout_result(result, True, timeout))
        
        threading.Thread(target=do_set, daemon=True).start()
    
    def _handle_screen_timeout_result(self, result, is_set=False, timeout=0):
        """处理屏幕休眠时间设置结果"""
        if result['success']:
            if is_set:
                seconds = timeout // 1000
                QMessageBox.information(self, "Success", f"屏幕休眠时间已设置为 {seconds} 秒")
                self.log(f"Screen timeout set to {timeout}ms", "INFO")
            else:
                timeout_ms = result['stdout'].strip()
                try:
                    timeout_sec = int(timeout_ms) // 1000
                    QMessageBox.information(self, "Screen Timeout", f"当前屏幕休眠时间: {timeout_sec} 秒 ({timeout_ms} 毫秒)")
                except:
                    QMessageBox.information(self, "Screen Timeout", f"当前设置: {timeout_ms}")
        else:
            QMessageBox.warning(self, "Error", f"操作失败: {result.get('stderr', 'Unknown error')}")
    
    def quick_open_settings(self):
        """启动系统设置"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        def do_open():
            cmd = f"{self.get_device_flag()} shell am start -a android.settings.SETTINGS"
            result = self.adb.run_command(cmd)
            self.log_command(cmd, result, "启动系统设置")
            QTimer.singleShot(0, lambda: self._handle_open_settings_result(result))
        
        threading.Thread(target=do_open, daemon=True).start()
    
    def _handle_open_settings_result(self, result):
        """处理打开设置结果"""
        if result['success']:
            self.log("Opened system settings", "INFO")
        else:
            QMessageBox.warning(self, "Error", f"打开设置失败: {result.get('stderr', 'Unknown error')}")
    
    def quick_adb_input_key(self):
        """ADB按键键盘 - 显示全键盘界面"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        # 尝试从JSON加载键盘配置，否则使用默认值
        keyboard_config = self.load_keyboard_config()
        
        if keyboard_config:
            key_rows = keyboard_config.get('key_rows', [
                ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
                ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
                ["A", "S", "D", "F", "G", "H", "J", "K", "L"],
                ["Z", "X", "C", "V", "B", "N", "M"],
            ])
            func_keys = keyboard_config.get('func_keys', [
                {"key": "@", "label": "AT"},
                {"key": ".", "label": "."},
                {"key": "SPACE", "label": "空格"},
                {"key": "-", "label": "-"},
                {"key": "/", "label": "/"},
            ])
            special_keys = keyboard_config.get('special_keys', [
                {"keycode": "66", "label": "回车"},
                {"keycode": "67", "label": "删除"},
                {"keycode": "3", "label": "Home"},
                {"keycode": "6", "label": "End"},
                {"keycode": "4", "label": "返回"},
                {"keycode": "82", "label": "菜单"},
                {"keycode": "26", "label": "电源"},
                {"keycode": "24", "label": "音量+"},
                {"keycode": "25", "label": "音量-"},
                {"keycode": "27", "label": "相机"},
                {"keycode": "5", "label": "拨号"},
                {"keycode": "19", "label": "↑ 向上"},
                {"keycode": "20", "label": "↓ 向下"},
                {"keycode": "21", "label": "← 向左"},
                {"keycode": "22", "label": "→ 向右"},
            ])
        else:
            # 默认键盘配置
            key_rows = [
                ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
                ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
                ["A", "S", "D", "F", "G", "H", "J", "K", "L"],
                ["Z", "X", "C", "V", "B", "N", "M"],
            ]
            func_keys = [
                {"key": "@", "label": "AT"},
                {"key": ".", "label": "."},
                {"key": "SPACE", "label": "空格"},
                {"key": "-", "label": "-"},
                {"key": "/", "label": "/"},
            ]
            special_keys = [
                {"keycode": "66", "label": "回车"},
                {"keycode": "67", "label": "删除"},
                {"keycode": "3", "label": "Home"},
                {"keycode": "6", "label": "End"},
                {"keycode": "4", "label": "返回"},
                {"keycode": "82", "label": "菜单"},
                {"keycode": "26", "label": "电源"},
                {"keycode": "24", "label": "音量+"},
                {"keycode": "25", "label": "音量-"},
                {"keycode": "27", "label": "相机"},
                {"keycode": "5", "label": "拨号"},
                {"keycode": "19", "label": "↑ 向上"},
                {"keycode": "20", "label": "↓ 向下"},
                {"keycode": "21", "label": "← 向左"},
                {"keycode": "22", "label": "→ 向右"},
            ]
        
        # 创建键盘对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("ADB按键键盘")
        dialog.setMinimumSize(600, 500)
        
        layout = QVBoxLayout(dialog)
        
        def send_key(keycode, desc):
            """发送按键到设备"""
            def do_send():
                try:
                    cmd = f"{self.get_device_flag()} shell input keyevent {keycode}"
                    result = self.adb.run_command(cmd)
                    if result.get('success'):
                        self.log(f"Sent keyevent: {keycode} ({desc})", "INFO")
                    else:
                        error_msg = result.get('stderr') or result.get('stdout') or 'Unknown error'
                        self.log(f"Keyevent failed: {error_msg}", "ERROR")
                except Exception as e:
                    self.log(f"Keyevent error: {e}", "ERROR")
            threading.Thread(target=do_send, daemon=True).start()
        
        def send_text(text):
            """发送文本到设备"""
            def do_send():
                cmd = f"{self.get_device_flag()} shell input text {text}"
                result = self.adb.run_command(cmd)
                if result.get('success'):
                    self.log(f"Sent text: {text}", "INFO")
                else:
                    error_msg = result.get('stderr') or result.get('stdout') or 'Unknown error'
                    self.log(f"Text input failed: {error_msg}", "ERROR")
            threading.Thread(target=do_send, daemon=True).start()
        
        # 大小写切换状态
        is_upper = [False]  # 默认为小写
        
        # 数字和字母键盘
        letter_buttons = []  # 保存字母按钮以便更新
        for row in key_rows:
            row_layout = QHBoxLayout()
            row_btns = []
            for key in row:
                btn = QPushButton(key.lower())  # 默认小写
                btn.setMinimumHeight(40)
                btn.setProperty("key", key)  # 保存原始key
                btn.clicked.connect(lambda checked, b=btn: send_text(b.property("key").upper() if is_upper[0] else b.property("key").lower()))
                row_btns.append(btn)
                letter_buttons.append(row_btns)
                row_layout.addWidget(btn)
            layout.addLayout(row_layout)
        
        # 功能键行
        func_layout = QHBoxLayout()
        
        # 大小写切换按钮
        case_btn = QPushButton("⬇️ caps")
        case_btn.setMinimumHeight(35)
        case_btn.setStyleSheet("background-color: #e0e0e0; color: black;")
        case_btn.clicked.connect(lambda: (
            is_upper.__setitem__(0, not is_upper[0]),
            case_btn.setText("⬆️ Caps" if is_upper[0] else "⬇️ caps"),
            case_btn.setStyleSheet("background-color: #4a90d9; color: white;" if is_upper[0] else "background-color: #e0e0e0; color: black;"),
            [btn.setText(btn.property("key").upper() if is_upper[0] else btn.property("key").lower()) for row in letter_buttons for btn in row]
        ))
        func_layout.addWidget(case_btn)
        
        for item in func_keys:
            key = item.get('key', '')
            label = item.get('label', key)
            btn = QPushButton(label)
            btn.setMinimumHeight(35)
            key_val = key
            if key == "SPACE":
                btn.clicked.connect(lambda: send_text(" "))
            else:
                btn.clicked.connect(lambda _, k=key_val: send_text(k))
            func_layout.addWidget(btn)
        layout.addLayout(func_layout)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)
        
        # 特殊功能键标签
        special_label = QLabel("🔧 特殊功能键:")
        special_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(special_label)
        
        # 特殊功能键网格
        special_grid = QGridLayout()
        row, col = 0, 0
        for item in special_keys:
            keycode = item.get('keycode', '')
            label = item.get('label', keycode)
            btn = QPushButton(label)
            btn.setMinimumHeight(40)
            btn.setStyleSheet("background-color: #4a90d9; color: white;")
            key_val = keycode
            label_val = label
            btn.clicked.connect(lambda _, k=key_val, l=label_val: send_key(k, l))
            special_grid.addWidget(btn, row, col)
            col += 1
            if col >= 4:
                col = 0
                row += 1
        layout.addLayout(special_grid)
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.setMinimumHeight(40)
        close_btn.setStyleSheet("background-color: #666; color: white;")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)
        
        dialog.exec()
    
    def _handle_adb_input_result(self, result, key_name):
        """处理ADB按键结果"""
        if result['success']:
            QMessageBox.information(self, "Success", f"已发送按键: {key_name}")
            self.log(f"Sent keyevent: {key_name}", "INFO")
        else:
            QMessageBox.warning(self, "Error", f"发送按键失败: {result.get('stderr', 'Unknown error')}")
    
    def list_apps(self):
        """List installed apps with uninstall/reinstall options"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        self.log("Fetching installed apps...")
        self.update_status("Fetching apps...")
        
        def do_list():
            result = self.adb.run_command(f"{self.get_device_flag()} shell pm list packages")
            if result['success']:
                apps = result['stdout'].strip().split('\n')
                apps = [app.replace('package:', '') for app in apps if app.strip()]
                self.log(f"Found {len(apps)} installed apps")
                self.update_status(f"Found {len(apps)} apps")
                
                # Show in an interactive window (thread-safe via signal)
                self.app_list_ready.emit(sorted(apps))
            else:
                error_msg = result.get('stderr', 'Unknown error')
                # Only log stderr if it's not empty and contains actual error info
                if error_msg and error_msg.strip() and error_msg.strip() != '':
                    self.log(f"Error listing apps: {error_msg}", "ERROR")
                self.update_status("Failed to list apps")
                QTimer.singleShot(0, lambda: QMessageBox.warning(self, "Error", f"Failed to list installed apps:\n{error_msg}"))
        
        threading.Thread(target=do_list, daemon=True).start()
    
    def show_app_list_window(self, apps):
        """Show interactive app list window with uninstall/reinstall buttons"""
        app_window = QDialog(self)
        app_window.setWindowTitle("Installed Apps")
        app_window.setMinimumSize(700, 500)
        app_window.setModal(True)
        
        layout = QVBoxLayout(app_window)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Search frame
        search_layout = QHBoxLayout()
        search_label = QLabel("Search (by app name or package):")
        search_layout.addWidget(search_label)
        
        search_entry = QLineEdit()
        search_entry.setPlaceholderText("Type to search...")
        search_layout.addWidget(search_entry)
        
        # Filter checkbox
        filter_checkbox = QCheckBox("Show only disabled apps")
        search_layout.addWidget(filter_checkbox)
        layout.addLayout(search_layout)
        
        # List widget
        listbox = QListWidget()
        layout.addWidget(listbox)
        
        # Store original apps list in window attribute so refresh can access it
        app_window.original_apps = apps.copy()
        
        # Store app labels (package_name -> app_label)
        app_window.app_labels = {}
        
        # Store app status (enabled/disabled) - will be populated when checking status
        app_window.app_status = {}
        
        def check_app_status(package_name):
            """Check if app is disabled"""
            result = self.adb.run_command(f"{self.get_device_flag()} shell pm list packages -d {package_name}")
            return result['success'] and package_name in result['stdout']
        
        def update_list():
            """Update listbox based on search and filter"""
            search_term = search_entry.text().lower()
            filter_disabled = filter_checkbox.isChecked()
            listbox.clear()
            
            for app in app_window.original_apps:
                # Get app label (use package name as fallback)
                app_label = app_window.app_labels.get(app, app)
                
                # If label is same as package, just show package name (avoid "package (package)")
                if app_label == app:
                    display_label = app
                else:
                    display_label = f"{app_label} ({app})"
                
                # Check if app is disabled
                is_disabled = app_window.app_status.get(app, False)
                
                # Apply disabled filter
                if filter_disabled and not is_disabled:
                    continue
                
                # Check if search term matches app name or package name
                matches = False
                if not search_term:
                    matches = True
                elif search_term in app_label.lower() or search_term in app.lower():
                    matches = True
                
                if matches:
                    display_name = display_label
                    if is_disabled:
                        display_name += " [DISABLED]"
                    listbox.addItem(display_name)
        
        # Load app labels in background
        def load_app_labels():
            """Load app labels for all apps"""
            self.log("Loading app names...")
            labels_found = 0
            for i, package in enumerate(apps):
                if i % 20 == 0:
                    self.log(f"Loading app names {i}/{len(apps)}...")
                label = self.get_app_label(package)
                if label and label != package:
                    app_window.app_labels[package] = label
                    labels_found += 1
                    # Log first few successful extractions for debugging
                    if labels_found <= 3:
                        self.log(f"Found label for {package}: {label}", "DEBUG")
                else:
                    # Use package name as fallback
                    app_window.app_labels[package] = package
                    # Log first few failures for debugging
                    if i < 3:
                        self.log(f"Could not find label for {package}, using package name", "DEBUG")
            self.log(f"Loaded {len(app_window.app_labels)} app names ({labels_found} with custom labels)")
            if labels_found == 0:
                self.log("Warning: No app labels found. Labels may be stored as resource IDs.", "WARNING")
            QTimer.singleShot(0, lambda: update_list())
        
        search_entry.textChanged.connect(update_list)
        filter_checkbox.stateChanged.connect(lambda: update_list())
        
        # Start loading labels in background
        threading.Thread(target=load_app_labels, daemon=True).start()
        
        # Initial list (will show package names until labels load)
        update_list()
        
        # Buttons frame
        button_layout = QHBoxLayout()
        
        def get_selected_package():
            """Extract package name from listbox selection (handles app name and [DISABLED] marker)"""
            current_item = listbox.currentItem()
            if not current_item:
                return None
            display_text = current_item.text()
            # Remove [DISABLED] marker if present
            display_text = display_text.replace(' [DISABLED]', '').strip()
            # Extract package name from format "App Name (package.name)"
            if '(' in display_text and ')' in display_text:
                package_name = display_text.split('(')[-1].rstrip(')').strip()
                return package_name
            # Fallback: if no parentheses, assume it's just the package name
            return display_text
        
        def uninstall_selected():
            """Uninstall selected app"""
            package_name = get_selected_package()
            if not package_name:
                QMessageBox.warning(self, "No Selection", "Please select an app to uninstall")
                return
            app_label = app_window.app_labels.get(package_name, package_name)
            display_name = f"{app_label} ({package_name})" if app_label != package_name else package_name
            reply = QMessageBox.question(self, "Confirm Uninstall", f"Uninstall {display_name}?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            self.log(f"Uninstalling {package_name}...")
            self.update_status("Uninstalling app...")
            
            def do_uninstall():
                result = self.adb.run_command(f"{self.get_device_flag()} uninstall {package_name}")
                if result['success']:
                    # Check if stdout contains success message
                    output = result['stdout'].strip() if result['stdout'] else ''
                    if 'Success' in output or 'success' in output.lower() or output == '':
                        self.log("App uninstalled successfully")
                        self.update_status("App uninstalled successfully")
                        # Remove from the stored apps list
                        if package_name in app_window.original_apps:
                            app_window.original_apps.remove(package_name)
                        # Refresh the list
                        QTimer.singleShot(0, lambda: update_list())
                        # Thread-safe messagebox - use QTimer to call from main thread
                        QTimer.singleShot(0, lambda: QMessageBox.information(self, "Success", "App uninstalled successfully"))
                    else:
                        # Sometimes ADB returns success but stdout has info
                        self.log(f"Uninstall result: {output}")
                        self.update_status("Uninstall completed")
                        if package_name in app_window.original_apps:
                            app_window.original_apps.remove(package_name)
                        QTimer.singleShot(0, lambda: update_list())
                        # Thread-safe messagebox - use QTimer to call from main thread
                        QTimer.singleShot(0, lambda: QMessageBox.information(self, "Success", f"Uninstall completed:\n{output}"))
                else:
                    # Get error from stderr or stdout
                    error_msg = result['stderr'] if result['stderr'] else result['stdout']
                    if not error_msg or error_msg.strip() == '':
                        error_msg = "Unknown error"
                    
                    self.log(f"Regular uninstall failed: {error_msg}", "WARNING")
                    
                    # Try uninstalling for current user (works for system apps without root)
                    self.log("Attempting to uninstall for current user (--user 0)...")
                    result_user = self.adb.run_command(f"{self.get_device_flag()} shell pm uninstall --user 0 {package_name}")
                    
                    if result_user['success']:
                        output = result_user['stdout'].strip() if result_user['stdout'] else ''
                        if 'Success' in output or 'success' in output.lower() or output == '':
                            self.log("App uninstalled for current user successfully")
                            self.update_status("App uninstalled for current user")
                            # Thread-safe messagebox - use QTimer to call from main thread
                            QTimer.singleShot(0, lambda: QMessageBox.information(self, "Success", f"App uninstalled for current user successfully!\n\nNote: System apps are only removed for your user account, not from the device."))
                        else:
                            self.log(f"Uninstall result: {output}")
                            self.update_status("Uninstall completed")
                            # Thread-safe messagebox - use QTimer to call from main thread
                            QTimer.singleShot(0, lambda: QMessageBox.information(self, "Success", f"Uninstall completed:\n{output}"))
                    else:
                        # Both methods failed
                        error_msg_user = result_user['stderr'] if result_user['stderr'] else result_user['stdout']
                        self.log(f"Error: {error_msg}", "ERROR")
                        self.log(f"User uninstall also failed: {error_msg_user}", "ERROR")
                        self.log(f"Return code: {result['returncode']}", "ERROR")
                        self.log(f"Full stdout: {result['stdout']}", "DEBUG")
                        self.log(f"Full stderr: {result['stderr']}", "DEBUG")
                        self.update_status("Failed to uninstall app")
                        
                        # Provide helpful message
                        if 'DELETE_FAILED_INTERNAL_ERROR' in error_msg or 'system app' in error_msg.lower() or 'package is a system package' in error_msg.lower():
                            help_text = f"Failed to uninstall {package_name}:\n\n{error_msg}\n\nTried both regular and user uninstall methods.\nYou can try disabling it instead (use 'Disable Selected')."
                        else:
                            help_text = f"Failed to uninstall {package_name}:\n\n{error_msg}"
                        
                        # Thread-safe messagebox - use QTimer to call from main thread
                        QTimer.singleShot(0, lambda: QMessageBox.critical(self, "Error", help_text))
            
            threading.Thread(target=do_uninstall, daemon=True).start()
        
        def reinstall_selected():
            """Reinstall selected app"""
            package_name = get_selected_package()
            if not package_name:
                QMessageBox.warning(self, "No Selection", "Please select an app to reinstall")
                return
            app_label = app_window.app_labels.get(package_name, package_name)
            display_name = f"{app_label} ({package_name})" if app_label != package_name else package_name
            reply = QMessageBox.question(self, "Confirm Reinstall", f"Reinstall {display_name}?\n\nThis will uninstall and then reinstall the app.",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            self.log(f"Reinstalling {package_name}...")
            self.update_status("Reinstalling app...")
            
            def do_reinstall():
                # Step 1: Get APK path
                self.log(f"Getting APK path for {package_name}...")
                result = self.adb.run_command(f"{self.get_device_flag()} shell pm path {package_name}")
                if not result['success']:
                    error_msg = result['stderr'] or "Unknown error"
                    self.log(f"Error getting APK path: {error_msg}", "ERROR")
                    # Thread-safe messagebox - use QTimer to call from main thread
                    QTimer.singleShot(0, lambda: QMessageBox.critical(self, "Error", f"Failed to get APK path:\n{error_msg}"))
                    return
                
                # Parse APK path (format: package:/data/app/.../base.apk)
                # Handle multiple APK paths (split APKs)
                apk_paths = result['stdout'].strip().split('\n')
                apk_paths = [p.replace('package:', '').strip() for p in apk_paths if p.strip()]
                
                if not apk_paths:
                    self.log("Could not find APK path", "ERROR")
                    # Thread-safe messagebox - use QTimer to call from main thread
                    QTimer.singleShot(0, lambda: QMessageBox.critical(self, "Error", "Could not find APK path on device"))
                    return
                
                self.log(f"Found {len(apk_paths)} APK file(s)")
                if len(apk_paths) > 1:
                    self.log(f"Note: App uses split APKs. Will pull and install all {len(apk_paths)} APK files.", "INFO")
                
                # Step 2: Pull all APKs to local folder
                # Create apks folder in executable's directory (or script directory if running from source)
                # When running as PyInstaller executable, use the executable's directory
                if getattr(sys, 'frozen', False):
                    # Running as compiled executable
                    project_dir = os.path.dirname(sys.executable)
                else:
                    # Running as script
                    project_dir = os.path.dirname(os.path.abspath(__file__))
                apks_dir = os.path.join(project_dir, 'apks')
                os.makedirs(apks_dir, exist_ok=True)
                local_apks = []
                
                for i, apk_path in enumerate(apk_paths):
                    # Determine filename - base.apk for first, split_*.apk for others
                    if i == 0:
                        filename = f"{package_name}.apk"
                    else:
                        # Extract the split name from path (e.g., split_config.arm64_v8a.apk)
                        split_name = os.path.basename(apk_path)
                        filename = f"{package_name}_{split_name}"
                    
                    local_apk = os.path.join(apks_dir, filename)
                    local_apks.append(local_apk)
                    
                    self.log(f"Pulling APK {i+1}/{len(apk_paths)}: {os.path.basename(apk_path)}...")
                    result = self.adb.run_command(f"{self.get_device_flag()} pull {apk_path} {local_apk}")
                    if not result['success']:
                        error_msg = result['stderr'] or "Unknown error"
                        self.log(f"Error pulling APK {i+1}: {error_msg}", "ERROR")
                        # Thread-safe messagebox - use QTimer to call from main thread
                        QTimer.singleShot(0, lambda: QMessageBox.critical(self, "Error", f"Failed to pull APK {i+1}:\n{error_msg}"))
                        # Clean up already pulled APKs
                        for apk in local_apks:
                            try:
                                if os.path.exists(apk):
                                    os.remove(apk)
                            except:
                                pass
                        return
                
                self.log(f"Successfully pulled {len(local_apks)} APK file(s)")
                
                # Step 3: Uninstall app
                self.log(f"Uninstalling {package_name}...")
                result = self.adb.run_command(f"{self.get_device_flag()} uninstall {package_name}")
                if not result['success']:
                    error_msg = result['stderr'] or "Unknown error"
                    self.log(f"Error uninstalling: {error_msg}", "ERROR")
                    # Try to install anyway
                    self.log("Continuing with installation despite uninstall error...", "WARNING")
                else:
                    self.log("App uninstalled successfully")
                
                # Step 4: Install APK(s)
                self.log(f"Installing {package_name}...")
                
                # Use install-multiple for split APKs, regular install for single APK
                if len(local_apks) > 1:
                    # Install multiple APKs using install-multiple
                    apk_list = ' '.join(local_apks)
                    result = self.adb.run_command(f"{self.get_device_flag()} install-multiple {apk_list}", timeout=180)
                else:
                    # Single APK - use regular install
                    result = self.adb.run_command(f"{self.get_device_flag()} install {local_apks[0]}", timeout=120)
                
                if result['success']:
                    self.log("App reinstalled successfully")
                    self.update_status("App reinstalled successfully")
                    apk_locations = '\n'.join(local_apks)
                    # Thread-safe messagebox - use QTimer to call from main thread
                    QTimer.singleShot(0, lambda: QMessageBox.information(self, "Success", f"App reinstalled successfully!\n\nAPK(s) saved at:\n{apk_locations}"))
                    # Keep APKs in the folder for easy access - don't delete them
                else:
                    error_msg = result['stderr'] or "Unknown error"
                    self.log(f"Error installing: {error_msg}", "ERROR")
                    self.update_status("Failed to reinstall app")
                    apk_locations = '\n'.join(local_apks)
                    # Thread-safe messagebox - use QTimer to call from main thread
                    QTimer.singleShot(0, lambda: QMessageBox.critical(self, "Error", f"Failed to install app:\n{error_msg}\n\nAPK(s) saved at:\n{apk_locations}"))
            
            threading.Thread(target=do_reinstall, daemon=True).start()
        
        def disable_selected():
            """Disable selected app for current user"""
            package_name = get_selected_package()
            if not package_name:
                QMessageBox.warning(self, "No Selection", "Please select an app to disable")
                return
            
            # Validate package name
            if not package_name or package_name.strip() == '':
                self.log(f"Invalid package name extracted: '{package_name}'", "ERROR")
                QMessageBox.critical(self, "Error", "Could not extract package name from selection. Please try refreshing the list.")
                return
            
            app_label = app_window.app_labels.get(package_name, package_name)
            display_name = f"{app_label} ({package_name})" if app_label != package_name else package_name
            reply = QMessageBox.question(self, "Confirm Disable", f"Disable {display_name} for current user?\n\nThis will hide the app from the app drawer.",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            self.log(f"Disabling {package_name}...")
            self.update_status("Disabling app...")
            
            def do_disable():
                # First verify the package exists
                result_check = self.adb.run_command(f"{self.get_device_flag()} shell pm path {package_name}")
                if not result_check['success'] or not result_check['stdout'] or result_check['stdout'].strip() == '':
                    error_msg = "Package not found. The app may have been uninstalled or the package name is invalid."
                    self.log(f"Package check failed: {result_check.get('stderr', 'No output')}", "ERROR")
                    self.log(f"Package name used: '{package_name}'", "DEBUG")
                    self.update_status("Failed to disable app")
                    # Thread-safe messagebox - use QTimer to call from main thread
                    QTimer.singleShot(0, lambda: QMessageBox.critical(self, "Error", f"Failed to disable {display_name}:\n\n{error_msg}\n\nPackage: {package_name}"))
                    return
                
                result = self.adb.run_command(f"{self.get_device_flag()} shell pm disable-user {package_name}")
                if result['success']:
                    self.log("App disabled successfully")
                    self.update_status("App disabled successfully")
                    # Update status
                    app_window.app_status[package_name] = True
                    # Refresh the list
                    QTimer.singleShot(0, lambda: update_list())
                    # Thread-safe messagebox - use QTimer to call from main thread
                    QTimer.singleShot(0, lambda: QMessageBox.information(self, "Success", "App disabled successfully"))
                else:
                    error_msg = result['stderr'] if result['stderr'] else result['stdout']
                    if not error_msg or error_msg.strip() == '':
                        error_msg = "Unknown error"
                    self.log(f"Error: {error_msg}", "ERROR")
                    self.log(f"Package name used: '{package_name}'", "DEBUG")
                    self.update_status("Failed to disable app")
                    # Thread-safe messagebox - use QTimer to call from main thread
                    QTimer.singleShot(0, lambda: QMessageBox.critical(self, "Error", f"Failed to disable app:\n{error_msg}"))
            
            threading.Thread(target=do_disable, daemon=True).start()
        
        def enable_selected():
            """Enable selected app"""
            package_name = get_selected_package()
            if not package_name:
                QMessageBox.warning(self, "No Selection", "Please select an app to enable")
                return
            
            # Validate package name
            if not package_name or package_name.strip() == '':
                self.log(f"Invalid package name extracted: '{package_name}'", "ERROR")
                QMessageBox.critical(self, "Error", "Could not extract package name from selection. Please try refreshing the list.")
                return
            
            app_label = app_window.app_labels.get(package_name, package_name)
            display_name = f"{app_label} ({package_name})" if app_label != package_name else package_name
            reply = QMessageBox.question(self, "Confirm Enable", f"Enable {display_name}?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            self.log(f"Enabling {package_name}...")
            self.update_status("Enabling app...")
            
            def do_enable():
                # First verify the package exists
                result_check = self.adb.run_command(f"{self.get_device_flag()} shell pm path {package_name}")
                if not result_check['success'] or not result_check['stdout'] or result_check['stdout'].strip() == '':
                    error_msg = "Package not found. The app may have been uninstalled or the package name is invalid."
                    self.log(f"Package check failed: {result_check.get('stderr', 'No output')}", "ERROR")
                    self.log(f"Package name used: '{package_name}'", "DEBUG")
                    self.update_status("Failed to enable app")
                    # Thread-safe messagebox - use QTimer to call from main thread
                    QTimer.singleShot(0, lambda: QMessageBox.critical(self, "Error", f"Failed to enable {display_name}:\n\n{error_msg}\n\nPackage: {package_name}"))
                    return
                
                # Try to enable the app
                result = self.adb.run_command(f"{self.get_device_flag()} shell pm enable {package_name}")
                if result['success']:
                    output = result['stdout'].strip() if result['stdout'] else ''
                    # Check if the output indicates success
                    if 'Package' in output or 'enabled' in output.lower() or output == '':
                        self.log("App enabled successfully")
                        self.update_status("App enabled successfully")
                        # Update status
                        app_window.app_status[package_name] = False
                        # Refresh the list
                        QTimer.singleShot(0, lambda: update_list())
                        # Thread-safe messagebox - use QTimer to call from main thread
                        QTimer.singleShot(0, lambda: QMessageBox.information(self, "Success", "App enabled successfully"))
                    else:
                        # Sometimes ADB returns success but with info message
                        self.log(f"Enable result: {output}")
                        self.update_status("Enable completed")
                        app_window.app_status[package_name] = False
                        QTimer.singleShot(0, lambda: update_list())
                        # Thread-safe messagebox - use QTimer to call from main thread
                        QTimer.singleShot(0, lambda: QMessageBox.information(self, "Success", f"Enable completed:\n{output}"))
                else:
                    error_msg = result['stderr'] if result['stderr'] else result['stdout']
                    if not error_msg or error_msg.strip() == '':
                        error_msg = "Unknown error - The app may not exist or may require special permissions to enable."
                    
                    self.log(f"Error enabling {package_name}: {error_msg}", "ERROR")
                    self.log(f"Package name used: '{package_name}'", "DEBUG")
                    self.log(f"Return code: {result['returncode']}", "ERROR")
                    self.update_status("Failed to enable app")
                    
                    # Provide helpful message for common errors
                    if 'SecurityException' in error_msg or 'Shell cannot change component state' in error_msg:
                        help_text = f"Failed to enable {display_name}:\n\n{error_msg}\n\nThis error usually means:\n1. The app doesn't exist or was uninstalled\n2. The app requires root access to enable\n3. The package name is invalid\n\nTry refreshing the app list."
                    elif 'null' in error_msg.lower():
                        help_text = f"Failed to enable {display_name}:\n\n{error_msg}\n\nThe package name appears to be invalid. Try refreshing the app list."
                    else:
                        help_text = f"Failed to enable {display_name}:\n\n{error_msg}"
                    
                    # Thread-safe messagebox - use QTimer to call from main thread
                    QTimer.singleShot(0, lambda: QMessageBox.critical(self, "Error", help_text))
            
            threading.Thread(target=do_enable, daemon=True).start()
        
        def refresh_list():
            """Refresh the app list"""
            self.log("Refreshing app list...")
            self.update_status("Refreshing apps...")
            
            def do_refresh():
                # Get all packages
                result = self.adb.run_command(f"{self.get_device_flag()} shell pm list packages")
                if result['success']:
                    apps = result['stdout'].strip().split('\n')
                    apps = [app.replace('package:', '') for app in apps if app.strip()]
                    
                    # Get disabled packages
                    result_disabled = self.adb.run_command(f"{self.get_device_flag()} shell pm list packages -d")
                    disabled_apps = set()
                    if result_disabled['success']:
                        disabled_lines = result_disabled['stdout'].strip().split('\n')
                        disabled_apps = {line.replace('package:', '').strip() for line in disabled_lines if line.strip()}
                    
                    # Update status dictionary
                    for app in apps:
                        app_window.app_status[app] = app in disabled_apps
                    
                    self.log(f"Found {len(apps)} installed apps ({len(disabled_apps)} disabled)")
                    self.update_status(f"Found {len(apps)} apps")
                    QTimer.singleShot(0, lambda: self.refresh_app_list_window(app_window, sorted(apps), search_entry, listbox))
                else:
                    self.log(f"Error: {result['stderr']}", "ERROR")
                    self.update_status("Failed to refresh apps")
            
            threading.Thread(target=do_refresh, daemon=True).start()
        
        # Initial status check
        def check_initial_status():
            """Check status of all apps initially"""
            result_disabled = self.adb.run_command(f"{self.get_device_flag()} shell pm list packages -d")
            if result_disabled['success']:
                disabled_lines = result_disabled['stdout'].strip().split('\n')
                for line in disabled_lines:
                    if line.strip():
                        pkg = line.replace('package:', '').strip()
                        app_window.app_status[pkg] = True
            # Mark all others as enabled
            for app in apps:
                if app not in app_window.app_status:
                    app_window.app_status[app] = False
            update_list()
        
        # Check status in background
        threading.Thread(target=check_initial_status, daemon=True).start()
        
        def reinstall_for_user():
            """Reinstall app for current user (for apps uninstalled with --user 0)"""
            package_name = get_selected_package()
            if not package_name:
                QMessageBox.warning(self, "No Selection", "Please select an app to reinstall")
                return
            app_label = app_window.app_labels.get(package_name, package_name)
            display_name = f"{app_label} ({package_name})" if app_label != package_name else package_name
            reply = QMessageBox.question(self, "Confirm Reinstall", f"Reinstall {display_name} for current user?\n\nThis will restore apps that were uninstalled for your user account.",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            self.log(f"Reinstalling {package_name} for current user...")
            self.update_status("Reinstalling app for user...")
            
            def do_reinstall():
                # Use pm install-existing to reinstall apps uninstalled for the user
                result = self.adb.run_command(f"{self.get_device_flag()} shell pm install-existing {package_name}")
                if result['success']:
                    output = result['stdout'].strip() if result['stdout'] else ''
                    if 'Success' in output or 'success' in output.lower() or 'Package' in output:
                        self.log("App reinstalled for current user successfully")
                        self.update_status("App reinstalled for current user")
                        # Add back to the list if it was removed
                        if package_name not in app_window.original_apps:
                            app_window.original_apps.append(package_name)
                        # Refresh the list
                        QTimer.singleShot(0, lambda: update_list())
                        # Thread-safe messagebox - use QTimer to call from main thread
                        QTimer.singleShot(0, lambda: QMessageBox.information(self, "Success", f"App reinstalled for current user successfully!\n\n{package_name} is now available again."))
                    else:
                        self.log(f"Reinstall result: {output}")
                        self.update_status("Reinstall completed")
                        if package_name not in app_window.original_apps:
                            app_window.original_apps.append(package_name)
                        QTimer.singleShot(0, lambda: update_list())
                        # Thread-safe messagebox - use QTimer to call from main thread
                        QTimer.singleShot(0, lambda: QMessageBox.information(self, "Success", f"Reinstall completed:\n{output}"))
                else:
                    error_msg = result['stderr'] if result['stderr'] else result['stdout']
                    if not error_msg or error_msg.strip() == '':
                        error_msg = "Unknown error"
                    self.log(f"Error: {error_msg}", "ERROR")
                    self.update_status("Failed to reinstall app")
                    # Thread-safe messagebox - use QTimer to call from main thread
                    QTimer.singleShot(0, lambda: QMessageBox.critical(self, "Error", f"Failed to reinstall {package_name}:\n\n{error_msg}\n\nNote: This only works for apps that were previously installed but uninstalled for your user account."))
            
            threading.Thread(target=do_reinstall, daemon=True).start()
        
        uninstall_btn = QPushButton("Uninstall Selected")
        uninstall_btn.clicked.connect(uninstall_selected)
        button_layout.addWidget(uninstall_btn)
        
        reinstall_btn = QPushButton("Reinstall Selected")
        reinstall_btn.clicked.connect(reinstall_selected)
        button_layout.addWidget(reinstall_btn)
        
        reinstall_user_btn = QPushButton("Reinstall for User")
        reinstall_user_btn.clicked.connect(reinstall_for_user)
        button_layout.addWidget(reinstall_user_btn)
        
        disable_btn = QPushButton("Disable Selected")
        disable_btn.clicked.connect(disable_selected)
        button_layout.addWidget(disable_btn)
        
        enable_btn = QPushButton("Enable Selected")
        enable_btn.clicked.connect(enable_selected)
        button_layout.addWidget(enable_btn)
        
        refresh_btn = QPushButton("Refresh List")
        refresh_btn.clicked.connect(refresh_list)
        button_layout.addWidget(refresh_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(app_window.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        # Double-click to show app info
        listbox.itemDoubleClicked.connect(lambda item: self.show_app_details(get_selected_package()) if get_selected_package() else None)
        
        # Ensure dialog appears on top and is visible
        app_window.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint)
        app_window.raise_()
        app_window.activateWindow()
        app_window.exec()
    
    def refresh_app_list_window(self, app_window, apps, search_entry, listbox):
        """Refresh the app list in the existing window"""
        # Update the stored apps list
        app_window.original_apps = apps.copy()
        
        # Load app labels for new apps if needed
        def load_missing_labels():
            for app in apps:
                if app not in app_window.app_labels:
                    label = self.get_app_label(app)
                    app_window.app_labels[app] = label if label else app
            QTimer.singleShot(0, lambda: update_list())
        
        def update_list():
            """Update listbox with filtered apps"""
            search_term = search_entry.text().lower()
            # Get filter checkbox from the window
            filter_checkbox = app_window.findChild(QCheckBox)
            filter_disabled_value = filter_checkbox.isChecked() if filter_checkbox else False
            listbox.clear()
            
            for app in apps:
                # Get app label (use package name as fallback)
                app_label = app_window.app_labels.get(app, app)
                
                # If label is same as package, just show package name (avoid "package (package)")
                if app_label == app:
                    display_label = app
                else:
                    display_label = f"{app_label} ({app})"
                
                # Check if app is disabled
                is_disabled = app_window.app_status.get(app, False)
                
                # Apply disabled filter
                if filter_disabled_value and not is_disabled:
                    continue
                
                # Check if search term matches app name or package name
                matches = False
                if not search_term:
                    matches = True
                elif search_term in app_label.lower() or search_term in app.lower():
                    matches = True
                
                if matches:
                    display_name = display_label
                    if is_disabled:
                        display_name += " [DISABLED]"
                    listbox.addItem(display_name)
        
        # Load missing labels in background
        threading.Thread(target=load_missing_labels, daemon=True).start()
        # Update immediately with existing labels
        update_list()
    
    def show_app_details(self, package_name):
        """Show detailed information about an app"""
        if not self.current_device:
            return
        
        self.log(f"Getting details for {package_name}...")
        
        def get_details():
            # Get APK path (most reliable)
            result = self.adb.run_command(f"{self.get_device_flag()} shell pm path {package_name}")
            apk_path = "Unknown"
            if result['success'] and result['stdout']:
                apk_path = result['stdout'].strip().replace('package:', '').strip()
                # Handle multiple APK paths (split APKs)
                if '\n' in apk_path:
                    apk_path = apk_path.split('\n')[0]
            
            # Get package info using dumpsys
            result = self.adb.run_command(f"{self.get_device_flag()} shell dumpsys package {package_name}")
            version = "Unknown"
            app_label = "Unknown"
            enabled_state = "Unknown"
            
            if result['success'] and result['stdout']:
                output = result['stdout']
                # Extract version
                for line in output.split('\n'):
                    if 'versionName=' in line:
                        version = line.split('versionName=')[1].split()[0].strip()
                        break
                
                # Extract app label
                for line in output.split('\n'):
                    if 'applicationLabel=' in line.lower() or 'label=' in line.lower():
                        if 'applicationLabel' in line.lower():
                            app_label = line.split('=')[-1].strip()
                            break
                
                # Check if enabled/disabled
                if 'enabled=true' in output.lower():
                    enabled_state = "Enabled"
                elif 'enabled=false' in output.lower():
                    enabled_state = "Disabled"
            
            details = f"Package: {package_name}\n"
            details += f"Label: {app_label}\n"
            details += f"Version: {version}\n"
            details += f"Status: {enabled_state}\n"
            details += f"APK Path: {apk_path}"
            
            # Thread-safe messagebox - use QTimer to call from main thread
            QTimer.singleShot(0, lambda: QMessageBox.information(self, "App Details", details))
        
        threading.Thread(target=get_details, daemon=True).start()
    
    def take_screenshot(self):
        """Take screenshot"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        # Create screenshots folder in executable's directory (or script directory if running from source)
        # When running as PyInstaller executable, use the executable's directory
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            project_dir = os.path.dirname(sys.executable)
        else:
            # Running as script
            project_dir = os.path.dirname(os.path.abspath(__file__))
        
        screenshots_dir = os.path.join(project_dir, 'screenshots')
        os.makedirs(screenshots_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        dest_path = os.path.join(screenshots_dir, filename)
        
        self.log("Taking screenshot...")
        self.update_status("Taking screenshot...")
        
        def do_screenshot():
            try:
                # Take screenshot on device
                cmd1 = f"{self.get_device_flag()} shell screencap -p /sdcard/screenshot.png"
                result = self.adb.run_command(cmd1)
                self.log_command(cmd1, result)
                if result['success']:
                    # Pull screenshot
                    cmd2 = f"{self.get_device_flag()} pull /sdcard/screenshot.png {dest_path}"
                    result = self.adb.run_command(cmd2)
                    self.log_command(cmd2, result)
                    if result['success']:
                        self.log(f"Screenshot saved successfully: {dest_path}")
                        self.update_status("Screenshot saved")
                        # Use QTimer.singleShot to safely call QMessageBox from main thread
                        QTimer.singleShot(0, lambda: QMessageBox.information(self, "Success", f"Screenshot saved to:\n{dest_path}"))
                    else:
                        error_msg = result.get('stderr', 'Unknown error')
                        self.log(f"Error pulling screenshot: {error_msg}", "ERROR")
                        self.update_status("Failed to save screenshot")
                        QTimer.singleShot(0, lambda: QMessageBox.warning(self, "Error", f"Failed to save screenshot:\n{error_msg}"))
                else:
                    error_msg = result.get('stderr', 'Unknown error')
                    self.log(f"Error taking screenshot: {error_msg}", "ERROR")
                    self.update_status("Failed to take screenshot")
                    QTimer.singleShot(0, lambda: QMessageBox.warning(self, "Error", f"Failed to take screenshot:\n{error_msg}"))
            except Exception as e:
                error_msg = str(e)
                self.log(f"Exception in screenshot: {error_msg}", "ERROR")
                self.update_status("Screenshot failed")
                QTimer.singleShot(0, lambda: QMessageBox.critical(self, "Error", f"An error occurred:\n{error_msg}"))
        
        threading.Thread(target=do_screenshot, daemon=True).start()
    
    def reboot_device(self):
        """Reboot device"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        self.log("Rebooting device...")
        self.update_status("Rebooting device...")
        
        def do_reboot():
            cmd = f"{self.get_device_flag()} reboot"
            result = self.adb.run_command(cmd)
            self.log_command(cmd, result, "Reboot Device")
            if result.get('success'):
                self.log("Device rebooting...", "INFO")
                self.update_status("Device rebooting...")
            else:
                error_msg = result.get('stderr') or result.get('stdout') or 'Unknown error'
                self.log(f"Error: {error_msg}", "ERROR")
                self.update_status("Failed to reboot")
        
        threading.Thread(target=do_reboot, daemon=True).start()
    
    def start_scrcpy_default(self):
        """Start scrcpy with default settings"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        if not self.scrcpy.is_available():
            QMessageBox.critical(self, "Scrcpy Not Found", 
                               "Scrcpy is not installed or not found.\n\n"
                               "Please download from: https://github.com/Genymobile/scrcpy/releases\n"
                               "Or click 📂 Path to set scrcpy location.")
            return
        
        self.start_scrcpy([])
    
    def start_scrcpy(self, options):
        """Start scrcpy with specified options"""
        try:
            cmd = [self.scrcpy.scrcpy_path]
            
            # Add device serial if multiple devices
            if self.current_device:
                cmd.extend(['-s', self.current_device])
            
            # Add custom options
            cmd.extend(options)
            
            self.log(f"Starting scrcpy: {' '.join(cmd)}")
            
            # Start scrcpy process
            process = QProcess()
            process.setProgram(cmd[0])
            process.setArguments(cmd[1:])
            process.start()
            
            if process.waitForStarted(3000):
                self.scrcpy_processes.append(process)
                self.log("Scrcpy started successfully")
                self.update_status("Scrcpy running")
            else:
                self.log("Failed to start scrcpy", "ERROR")
                QMessageBox.warning(self, "Error", "Failed to start scrcpy")
                
        except Exception as e:
            self.log(f"Error starting scrcpy: {str(e)}", "ERROR")
            QMessageBox.critical(self, "Error", f"Failed to start scrcpy:\n{str(e)}")
    
    def show_scrcpy_options(self):
        """Show scrcpy advanced options dialog"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        if not self.scrcpy.is_available():
            QMessageBox.critical(self, "Scrcpy Not Found", 
                               "Scrcpy is not installed. Please set the path first.")
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Scrcpy Options")
        dialog.setMinimumWidth(500)
        layout = QVBoxLayout(dialog)
        
        # Options
        options = {}
        
        # Bitrate
        bitrate_layout = QHBoxLayout()
        bitrate_layout.addWidget(QLabel("Video Bitrate (Mbps):"))
        bitrate_input = QLineEdit("8")
        bitrate_input.setMaximumWidth(80)
        bitrate_layout.addWidget(bitrate_input)
        bitrate_layout.addStretch()
        layout.addLayout(bitrate_layout)
        
        # Max size
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Max Size (pixels):"))
        size_combo = QComboBox()
        size_combo.addItems(["Default", "1920", "1280", "1024", "800"])
        size_layout.addWidget(size_combo)
        size_layout.addStretch()
        layout.addLayout(size_layout)
        
        # Checkboxes
        stay_awake_cb = QCheckBox("Stay Awake")
        stay_awake_cb.setChecked(True)
        layout.addWidget(stay_awake_cb)
        
        turn_screen_off_cb = QCheckBox("Turn Screen Off")
        layout.addWidget(turn_screen_off_cb)
        
        show_touches_cb = QCheckBox("Show Touches")
        layout.addWidget(show_touches_cb)
        
        fullscreen_cb = QCheckBox("Fullscreen")
        layout.addWidget(fullscreen_cb)
        
        always_on_top_cb = QCheckBox("Always On Top")
        layout.addWidget(always_on_top_cb)
        
        no_control_cb = QCheckBox("Display Only (No Control)")
        layout.addWidget(no_control_cb)
        
        record_layout = QHBoxLayout()
        record_cb = QCheckBox("Record to File:")
        record_layout.addWidget(record_cb)
        record_input = QLineEdit()
        record_input.setPlaceholderText("video.mp4")
        record_layout.addWidget(record_input)
        layout.addLayout(record_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        start_btn = QPushButton("▶️ Start")
        cancel_btn = QPushButton("Cancel")
        btn_layout.addWidget(start_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        def on_start():
            options = []
            
            # Bitrate
            try:
                bitrate = int(bitrate_input.text())
                options.extend(['-b', f'{bitrate}M'])
            except:
                pass
            
            # Max size
            if size_combo.currentText() != "Default":
                options.extend(['-m', size_combo.currentText()])
            
            # Flags
            if stay_awake_cb.isChecked():
                options.append('--stay-awake')
            if turn_screen_off_cb.isChecked():
                options.append('--turn-screen-off')
            if show_touches_cb.isChecked():
                options.append('--show-touches')
            if fullscreen_cb.isChecked():
                options.append('--fullscreen')
            if always_on_top_cb.isChecked():
                options.append('--always-on-top')
            if no_control_cb.isChecked():
                options.append('--no-control')
            
            # Recording
            if record_cb.isChecked() and record_input.text():
                options.extend(['-r', record_input.text()])
            
            dialog.accept()
            self.start_scrcpy(options)
        
        start_btn.clicked.connect(on_start)
        cancel_btn.clicked.connect(dialog.reject)
        
        dialog.exec()
    
    def set_scrcpy_path_dialog(self):
        """Dialog to set scrcpy path"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select scrcpy executable",
            "",
            "Executable files (scrcpy.exe);;All files (*.*)"
        )
        
        if file_path and os.path.exists(file_path):
            if self.scrcpy.set_scrcpy_path(file_path):
                self.config.set_extension_path('scrcpy', file_path, self.project_dir)
                self.check_scrcpy_availability()
                QMessageBox.information(self, "Success", f"Scrcpy path set to:\n{file_path}")
            else:
                QMessageBox.warning(self, "Error", "Invalid scrcpy executable")
    
    def check_scrcpy_availability(self):
        """Check and update scrcpy status"""
        if self.scrcpy.is_available():
            try:
                result = subprocess.run([self.scrcpy.scrcpy_path, '--version'],
                                      capture_output=True, text=True, timeout=5,
                                      creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
                version = result.stdout.strip().split('\n')[0] if result.stdout else "Unknown"
                self.scrcpy_status_label.setText(f"✓ Scrcpy available: {version}")
                self.scrcpy_status_label.setStyleSheet(f"color: {self.colors['success']}; font-size: 8pt;")
                self.scrcpy_btn.setEnabled(True)
                self.scrcpy_advanced_btn.setEnabled(True)
            except:
                self.scrcpy_status_label.setText("✓ Scrcpy available")
                self.scrcpy_status_label.setStyleSheet(f"color: {self.colors['success']}; font-size: 8pt;")
                self.scrcpy_btn.setEnabled(True)
                self.scrcpy_advanced_btn.setEnabled(True)
        else:
            self.scrcpy_status_label.setText("✗ Scrcpy not found - Click 📂 Path to set location")
            self.scrcpy_status_label.setStyleSheet(f"color: {self.colors['warning']}; font-size: 8pt;")
            self.scrcpy_btn.setEnabled(False)
            self.scrcpy_advanced_btn.setEnabled(False)
    
    def reboot_recovery(self):
        """Reboot to recovery"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        self.log("Rebooting to recovery...")
        self.update_status("Rebooting to recovery...")
        
        def do_reboot():
            cmd = f"{self.get_device_flag()} reboot recovery"
            result = self.adb.run_command(cmd)
            self.log_command(cmd, result, "Reboot to Recovery")
            if result.get('success'):
                self.log("Device rebooting to recovery...", "INFO")
                self.update_status("Device rebooting to recovery...")
            else:
                error_msg = result.get('stderr') or result.get('stdout') or 'Unknown error'
                self.log(f"Error: {error_msg}", "ERROR")
                self.update_status("Failed to reboot")
        
        threading.Thread(target=do_reboot, daemon=True).start()
    
    def reboot_bootloader(self):
        """Reboot to bootloader"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        self.log("Rebooting to bootloader...")
        self.update_status("Rebooting to bootloader...")
        
        def do_reboot():
            cmd = f"{self.get_device_flag()} reboot bootloader"
            result = self.adb.run_command(cmd)
            self.log_command(cmd, result, "Reboot to Bootloader")
            if result.get('success'):
                self.log("Device rebooting to bootloader...", "INFO")
                self.update_status("Device rebooting to bootloader...")
            else:
                error_msg = result.get('stderr') or result.get('stdout') or 'Unknown error'
                self.log(f"Error: {error_msg}", "ERROR")
                self.update_status("Failed to reboot")
        
        threading.Thread(target=do_reboot, daemon=True).start()

    def _get_fastboot_path(self):
        """Get fastboot executable path (same directory as adb)"""
        adb_path = self.adb.adb_path
        fastboot = os.path.join(os.path.dirname(adb_path), 'fastboot.exe')
        return fastboot if os.path.exists(fastboot) else 'fastboot'

    def _run_fastboot(self, args: list) -> dict:
        """Run a fastboot command with the current device serial"""
        import subprocess
        fastboot = self._get_fastboot_path()
        cmd_parts = [fastboot]
        if self.current_device:
            cmd_parts += ['-s', self.current_device]
        cmd_parts += args
        try:
            result = subprocess.run(cmd_parts, capture_output=True, text=True, timeout=30)
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout.strip(),
                'stderr': result.stderr.strip(),
                'cmd': ' '.join(cmd_parts),
            }
        except Exception as e:
            return {'success': False, 'stdout': '', 'stderr': str(e), 'cmd': ' '.join(cmd_parts)}

    def fastboot_oem_unlock(self):
        """Execute: fastboot oem at-unlock-vboot"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        reply = QMessageBox.question(
            self, "OEM Unlock",
            "This will execute:\n  fastboot oem at-unlock-vboot\n\nAre you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.log("Running fastboot oem at-unlock-vboot...")
        self.update_status("Running OEM unlock...")

        def do_unlock():
            result = self._run_fastboot(['oem', 'at-unlock-vboot'])
            output = result['stdout'] or result['stderr'] or '(no output)'
            if result['success']:
                QTimer.singleShot(0, lambda: self.log(f"OEM Unlock OK: {output}", "INFO"))
                QTimer.singleShot(0, lambda: self.update_status("OEM Unlock completed"))
            else:
                QTimer.singleShot(0, lambda: self.log(f"OEM Unlock failed: {output}", "ERROR"))
                QTimer.singleShot(0, lambda: self.update_status("OEM Unlock failed"))
            QTimer.singleShot(0, lambda: QMessageBox.information(self, "OEM Unlock", f"Result:\n{output}"))

        threading.Thread(target=do_unlock, daemon=True).start()

    def fastboot_reboot(self):
        """Execute: fastboot reboot"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        self.log("Running fastboot reboot...")
        self.update_status("Fastboot rebooting...")

        def do_reboot():
            result = self._run_fastboot(['reboot'])
            output = result['stdout'] or result['stderr'] or '(no output)'
            if result['success']:
                QTimer.singleShot(0, lambda: self.log("Fastboot reboot OK", "INFO"))
                QTimer.singleShot(0, lambda: self.update_status("Fastboot reboot completed"))
            else:
                QTimer.singleShot(0, lambda: self.log(f"Fastboot reboot failed: {output}", "ERROR"))
                QTimer.singleShot(0, lambda: self.update_status("Fastboot reboot failed"))

        threading.Thread(target=do_reboot, daemon=True).start()

    def reboot_loader(self):
        """Reboot to loader"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        self.log("Rebooting to loader...")
        self.update_status("Rebooting to loader...")
        
        def do_reboot():
            cmd = f"{self.get_device_flag()} reboot loader"
            result = self.adb.run_command(cmd)
            self.log_command(cmd, result, "Reboot to Loader")
            if result.get('success'):
                self.log("Device rebooting to loader...", "INFO")
                self.update_status("Device rebooting to loader...")
            else:
                error_msg = result.get('stderr') or result.get('stdout') or 'Unknown error'
                self.log(f"Error: {error_msg}", "ERROR")
                self.update_status("Failed to reboot")
        
        threading.Thread(target=do_reboot, daemon=True).start()
    
    def adb_root_remount(self):
        """Execute adb root and adb remount"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        self.log("Button clicked: ADB Root & Remount", "INFO")
        self.log("Executing adb root...")
        self.update_status("Executing adb root...")
        
        def do_root_remount():
            # Execute adb root
            cmd1 = f"{self.get_device_flag()} root"
            result1 = self.adb.run_command(cmd1, timeout=60)
            self.log_command(cmd1, result1, "ADB Root & Remount")
            if result1.get('success'):
                self.log("adb root executed, waiting for device...")
                import time
                time.sleep(2)
                
                # Execute adb remount with longer timeout (may take time to disable verity)
                cmd2 = f"{self.get_device_flag()} remount"
                self.log("Executing adb remount (this may take a while)...")
                result2 = self.adb.run_command(cmd2, timeout=120)  # 120 seconds for remount
                self.log_command(cmd2, result2, "ADB Root & Remount")
                if result2.get('success'):
                    stdout = result2.get('stdout', '').strip()
                    if stdout:
                        # Log each line of the output
                        for line in stdout.split('\n'):
                            if line.strip():
                                self.log(f"  {line.strip()}", "INFO")
                    self.log("ADB remount completed!", "INFO")
                    self.update_status("ADB remount completed")
                else:
                    error_msg = result2.get('stderr') or result2.get('stdout') or 'Unknown error'
                    self.log(f"adb remount failed: {error_msg}", "ERROR")
                    self.update_status("adb remount failed")
            else:
                error_msg = result1.get('stderr') or result1.get('stdout') or 'Unknown error'
                self.log(f"adb root failed: {error_msg}", "ERROR")
                self.update_status("adb root failed")
        
        threading.Thread(target=do_root_remount, daemon=True).start()
    
    def run_shell_command(self):
        """Run shell command"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        command = self.shell_entry.toPlainText().strip()
        if not command:
            return
        
        # Strip "adb" and "shell" prefixes if user included them
        # This allows users to paste full adb commands or just shell commands
        command = command.strip()
        if command.startswith('adb '):
            command = command[4:].strip()
        if command.startswith('shell '):
            command = command[6:].strip()
        
        if not command:
            QMessageBox.warning(self, "Invalid Command", "Please enter a shell command to run on the device.")
            return
        
        # Warn if user tries to use Windows commands
        # Note: These commands run ON THE ANDROID DEVICE (Linux), not on Windows
        windows_commands = {
            'findstr': 'grep',
            'dir': 'ls',
            'type': 'cat',
            'copy': 'cp',
            'del': 'rm',
            'move': 'mv',
            'cd': 'cd',  # Same on both, but included for completeness
        }
        command_lower = command.lower()
        for win_cmd, linux_cmd in windows_commands.items():
            # Check if Windows command is used (as a separate word)
            if (f' {win_cmd} ' in command_lower or 
                command_lower.startswith(win_cmd + ' ') or 
                command_lower.endswith(' ' + win_cmd) or
                command_lower == win_cmd):
                if win_cmd != linux_cmd:  # Only warn if they're different
                    QMessageBox.warning(
                        self,
                        "Windows Command Detected",
                        f"⚠️ '{win_cmd}' is a Windows command and won't work on your Android device.\n\n"
                        f"These commands run ON YOUR ANDROID DEVICE (which uses Linux), not on Windows.\n\n"
                        f"Use '{linux_cmd}' instead of '{win_cmd}'.\n\n"
                        f"Example: Replace '{win_cmd}' with '{linux_cmd}' in your command."
                    )
                    return
        
        self.log(f"Running shell command: {command}")
        self.update_status("Running command...")
        
        def do_command():
            result = self.adb.run_command(f"{self.get_device_flag()} shell {command}")
            if result['success']:
                output = result['stdout'] if result['stdout'] else result['stderr']
                if output:
                    self.log(f"Output:\n{output}")
                else:
                    self.log("Command completed (no output)")
                self.update_status("Command completed")
            else:
                error_msg = result.get('stderr', 'Unknown error')
                self.log(f"Error: {error_msg}", "ERROR")
                self.update_status("Command failed")
        
        threading.Thread(target=do_command, daemon=True).start()
    
    def toggle_logcat(self):
        """Start/stop logcat"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        if self.log_running:
            self.log_running = False
            self.log_button.setText("▶️ Start Logcat")
            self.log("Logcat stopped")
            self.update_status("Logcat stopped")
            # Close log file
            if self.log_file:
                try:
                    self.log_file.close()
                except:
                    pass
                self.log_file = None
                self.log_file_label.setText("")
        else:
            self.log_running = True
            self.log_button.setText("⏹️ Stop Logcat")
            
            # Create log file if auto-save is enabled
            if self.auto_save_cb.isChecked():
                prefix = self.log_file_prefix.text() or "adb_logcat"
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{prefix}_{timestamp}.log"
                log_dir = os.path.join(self.project_dir, "logs")
                os.makedirs(log_dir, exist_ok=True)
                log_path = os.path.join(log_dir, filename)
                try:
                    self.log_file = open(log_path, 'w', encoding='utf-8')
                    self.log_file_label.setText(filename)
                except Exception as e:
                    self.log_file = None
                    self.log_file_label.setText("文件创建失败")
            
            self.log("Starting logcat...")
            self.update_status("Logcat running...")
            
            def run_logcat():
                try:
                    # Store device ID and ADB path for thread safety
                    device_id = self.current_device
                    adb_path = self.adb.adb_path
                    
                    # Debug: log the values
                    QTimer.singleShot(0, lambda: self.log(f"[DEBUG] device_id={device_id}, adb_path={adb_path}", "DEBUG"))
                    
                    # Convert to absolute path if needed
                    if adb_path and not os.path.isabs(adb_path):
                        adb_path = os.path.join(self.project_dir, adb_path)
                        QTimer.singleShot(0, lambda: self.log(f"[DEBUG] converted adb_path={adb_path}", "DEBUG"))
                    
                    # Check if adb_path exists
                    if not os.path.exists(adb_path):
                        QTimer.singleShot(0, lambda: self.log(f"[ERROR] ADB not found: {adb_path}", "ERROR"))
                        self.log_running = False
                        QTimer.singleShot(0, lambda: self.log_button.setText("▶️ Start Logcat"))
                        return
                    
                    process = subprocess.Popen(
                        [adb_path, '-s', device_id, 'logcat', '-v', 'threadtime'],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                        bufsize=1,
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                    )
                    
                    # Check if process started successfully
                    if process.poll() is not None:
                        # Process already terminated
                        stderr_output = process.stderr.read()
                        error_msg = f"Logcat process failed to start: {stderr_output}"
                        QTimer.singleShot(0, lambda: self.log(error_msg, "ERROR"))
                        self.log_running = False
                        QTimer.singleShot(0, lambda: self.log_button.setText("▶️ Start Logcat"))
                        return
                    
                    # Log that logcat started successfully
                    QTimer.singleShot(0, lambda: self.log(f"Logcat started with PID: {process.pid}", "INFO"))
                    
                    import time
                    read_count = 0
                    # Read output line by line
                    while self.log_running:
                        line = process.stdout.readline()
                        if line:
                            read_count += 1
                            # Use a closure to capture the line value properly
                            line_text = line.strip()
                            if line_text:  # Only log non-empty lines
                                QTimer.singleShot(0, lambda l=line_text: self.log(l, "LOGCAT"))
                        elif process.poll() is not None:
                            # Process ended - read any remaining stderr
                            stderr_output = process.stderr.read()
                            QTimer.singleShot(0, lambda: self.log(f"Logcat ended. Read {read_count} lines. stderr: {stderr_output}", "DEBUG"))
                            break
                        else:
                            time.sleep(0.1)  # Small delay to prevent CPU spin
                    
                    # Clean up
                    if process.poll() is None:
                        process.terminate()
                        try:
                            process.wait(timeout=2)
                        except subprocess.TimeoutExpired:
                            process.kill()
                    
                    if self.log_running:
                        # Process ended unexpectedly
                        stderr_output = process.stderr.read()
                        if stderr_output:
                            QTimer.singleShot(0, lambda: self.log(f"Logcat process ended: {stderr_output}", "ERROR"))
                        else:
                            QTimer.singleShot(0, lambda: self.log("Logcat process ended unexpectedly", "WARNING"))
                        self.log_running = False
                        QTimer.singleShot(0, lambda: self.log_button.setText("▶️ Start Logcat"))
                        
                except Exception as e:
                    error_msg = f"Logcat error: {str(e)}"
                    QTimer.singleShot(0, lambda: self.log(error_msg, "ERROR"))
                    QTimer.singleShot(0, lambda: QMessageBox.critical(self, "Logcat Error", error_msg))
                    self.log_running = False
                    QTimer.singleShot(0, lambda: self.log_button.setText("▶️ Start Logcat"))
                    import traceback
                    QTimer.singleShot(0, lambda: self.log(f"Traceback: {traceback.format_exc()}", "ERROR"))
            
            self.current_device = self.current_device  # Store for logcat thread
            threading.Thread(target=self.poll_logcat, daemon=True).start()
    
    def poll_logcat(self):
        """Poll logcat in a separate thread"""
        import time
        device_id = self.current_device
        adb_path = self.adb.adb_path
        
        # Convert to absolute path if needed
        if adb_path and not os.path.isabs(adb_path):
            adb_path = os.path.join(self.project_dir, adb_path)
        
        last_size = 0
        
        while self.log_running:
            try:
                result = subprocess.run(
                    [adb_path, '-s', device_id, 'logcat', '-d', '-v', 'threadtime'],
                    capture_output=True, text=True, timeout=10,
                    encoding='utf-8', errors='replace',
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                )
                
                if result.returncode == 0 and result.stdout:
                    lines = result.stdout.split('\n')
                    if last_size < len(lines):
                        new_lines = lines[last_size:]
                        last_size = len(lines)
                        for line in new_lines:
                            line = line.strip()
                            if line:
                                QTimer.singleShot(0, lambda l=line: self.log(l, "LOGCAT"))
            except:
                pass
            
            time.sleep(0.5)
    
    def get_absolute_path(self, relative_path):
        """Convert relative path to absolute path"""
        if not relative_path or relative_path.strip() == '':
            return None
        
        # If already absolute, return as is
        if os.path.isabs(relative_path):
            return relative_path
        
        # Convert relative path to absolute
        return os.path.normpath(os.path.join(self.project_dir, relative_path))
    
    def load_degoogle_state(self):
        """Load DeGoogle state from file"""
        if os.path.exists(self.degoogle_state_file):
            try:
                with open(self.degoogle_state_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_degoogle_state(self):
        """Save DeGoogle state to file"""
        try:
            with open(self.degoogle_state_file, 'w') as f:
                json.dump(self.degoogle_state, f, indent=2)
        except Exception as e:
            self.log(f"Error saving DeGoogle state: {e}", "ERROR")
    
    def apply_theme(self):
        """Apply light or dark theme"""
        if self.dark_mode:
            self.colors = self.dark_colors.copy()
        else:
            self.colors = self.light_colors.copy()
        
        # Apply stylesheet
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {self.colors['bg']};
                color: {self.colors['fg']};
            }}
            QWidget {{
                background-color: {self.colors['bg']};
                color: {self.colors['fg']};
            }}
            QPushButton {{
                background-color: {self.colors['card_bg']};
                color: {self.colors['fg']};
                border: 1px solid {self.colors['border']};
                border-radius: 4px;
                padding: 8px;
                font-family: 'Segoe UI';
                font-size: 9pt;
            }}
            QPushButton:hover {{
                background-color: {'#3e3e42' if self.dark_mode else '#f0f0f0'};
            }}
            QPushButton:pressed {{
                background-color: {'#2d2d30' if self.dark_mode else '#e0e0e0'};
            }}
            QPushButton[accent="true"] {{
                background-color: {self.colors['accent']};
                color: white;
            }}
            QPushButton[accent="true"]:hover {{
                background-color: {self.colors['accent_hover']};
            }}
            QGroupBox {{
                border: 1px solid {self.colors['border']};
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: {self.colors['card_bg']};
                color: {self.colors['fg']};
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: {self.colors['fg']};
            }}
            QLineEdit, QComboBox {{
                border: 1px solid {self.colors['border']};
                border-radius: 4px;
                padding: 5px;
                background-color: {self.colors['card_bg']};
                color: {self.colors['fg']};
            }}
            QTextEdit {{
                border: 1px solid {self.colors['border']};
                border-radius: 4px;
                background-color: {'#1e1e1e' if self.dark_mode else '#1e1e1e'};
                color: {'#d4d4d4' if self.dark_mode else '#d4d4d4'};
                font-family: 'Consolas';
                font-size: 9pt;
            }}
            QLabel {{
                color: {self.colors['fg']};
            }}
            QListWidget {{
                background-color: {self.colors['card_bg']};
                color: {self.colors['fg']};
                border: 1px solid {self.colors['border']};
            }}
            QCheckBox {{
                color: {self.colors['fg']};
            }}
            QRadioButton {{
                color: {self.colors['fg']};
            }}
            QTabWidget::pane {{
                border: 1px solid {self.colors['border']};
                background-color: {self.colors['card_bg']};
            }}
            QTabBar::tab {{
                background-color: {self.colors['bg']};
                color: {self.colors['fg']};
                border: 1px solid {self.colors['border']};
                padding: 8px;
            }}
            QTabBar::tab:selected {{
                background-color: {self.colors['card_bg']};
            }}
            QScrollArea {{
                background-color: {self.colors['card_bg']};
                border: 1px solid {self.colors['border']};
            }}
            QDialog {{
                background-color: {self.colors['bg']};
                color: {self.colors['fg']};
            }}
        """)
        
        # Update existing UI elements if they exist
        if hasattr(self, 'device_info_label'):
            self.device_info_label.setStyleSheet(f"color: {self.colors['text_secondary']};")
        if hasattr(self, 'adb_path_label'):
            self.adb_path_label.setStyleSheet(f"color: {self.colors['text_tertiary']};")
    
    def toggle_edit_mode(self):
        """Toggle edit mode for button layout"""
        self.edit_mode = not self.edit_mode
        
        if self.edit_mode:
            self.edit_mode_btn.setText("✅ Done")
            self.edit_mode_btn.setStyleSheet("background-color: #4CAF50; color: white;")
            self.log("Edit mode enabled - drag buttons or use Ctrl+C/V", "INFO")
            # 高亮所有按钮
            self._set_buttons_edit_style(True)
            # 设置快捷键
            self._setup_edit_shortcuts()
        else:
            self.edit_mode_btn.setText("✏️ Edit")
            self.edit_mode_btn.setStyleSheet("")
            self.log("Edit mode disabled", "INFO")
            # 恢复按钮样式
            self._set_buttons_edit_style(False)
            # 清除剪贴板
            self._button_clipboard = None
    
    def _setup_edit_shortcuts(self):
        """设置编辑模式快捷键"""
        if not hasattr(self, '_copy_shortcut'):
            self._copy_shortcut = QShortcut(QKeySequence("Ctrl+C"), self)
            self._copy_shortcut.activated.connect(self._copy_selected_button)
        
        if not hasattr(self, '_paste_shortcut'):
            self._paste_shortcut = QShortcut(QKeySequence("Ctrl+V"), self)
            self._paste_shortcut.activated.connect(self._paste_selected_button)
        
        # 初始化剪贴板
        if not hasattr(self, '_button_clipboard'):
            self._button_clipboard = None
        
        # 记录当前选中的按钮
        self._selected_button_id = None
    
    def _copy_selected_button(self):
        """复制当前选中的按钮"""
        if not self.edit_mode:
            return
        
        # 获取焦点控件
        focus_widget = QApplication.focusWidget()
        if isinstance(focus_widget, DraggableButton):
            btn_id = focus_widget.property('button_id')
            if btn_id and hasattr(self, 'button_configs'):
                import copy
                self._button_clipboard = copy.deepcopy(self.button_configs.get(btn_id))
                self._button_clipboard_source_group = focus_widget.property('group_id')
                self.log(f"Button copied: {btn_id}", "INFO")
            return
        
        self.log("No button selected for copy", "WARNING")
    
    def _paste_selected_button(self):
        """粘贴按钮到目标组"""
        if not self.edit_mode or not self._button_clipboard:
            self.log("No button in clipboard", "WARNING")
            return
        
        # 获取焦点控件
        focus_widget = QApplication.focusWidget()
        if isinstance(focus_widget, DraggableButton):
            target_group_id = focus_widget.property('group_id')
            if target_group_id:
                # 生成新ID
                import copy
                new_btn_config = copy.deepcopy(self._button_clipboard)
                new_btn_config['id'] = f"{self._button_clipboard.get('id', 'btn')}_copy_{len(self.button_widgets)}"
                
                # 添加到目标组
                for group in self.buttons_config.get('groups', []):
                    if group.get('id') == target_group_id:
                        group.setdefault('buttons', []).append(new_btn_config)
                        break
                
                self._save_buttons_config()
                self._rebuild_buttons_ui()
                self.log(f"Button pasted to {target_group_id}", "INFO")
                return
        
        self.log("Click a button first to select target group", "WARNING")
    
    def _on_button_reorder_requested(self, source_btn_id, target_btn_id, target_group_id):
        """处理按钮拖拽排序请求"""
        if not self.edit_mode or not hasattr(self, 'buttons_config'):
            return
        
        # 找到源按钮配置和位置
        source_btn_config = None
        source_group_id = None
        source_btn_idx = -1
        
        for group in self.buttons_config.get('groups', []):
            for b_idx, btn in enumerate(group.get('buttons', [])):
                if btn.get('id') == source_btn_id:
                    source_btn_config = btn
                    source_group_id = group.get('id')
                    source_btn_idx = b_idx
                    break
            if source_btn_config:
                break
        
        if not source_btn_config:
            return
        
        # 找到目标按钮位置
        target_btn_idx = -1
        for group in self.buttons_config.get('groups', []):
            if group.get('id') == target_group_id:
                for b_idx, btn in enumerate(group.get('buttons', [])):
                    if btn.get('id') == target_btn_id:
                        target_btn_idx = b_idx
                        break
                break
        
        # 从源位置移除
        for group in self.buttons_config.get('groups', []):
            if group.get('id') == source_group_id:
                group['buttons'].pop(source_btn_idx)
                break
        
        # 如果跨组，需要调整目标索引
        if source_group_id != target_group_id:
            # 跨组移动
            for group in self.buttons_config.get('groups', []):
                if group.get('id') == target_group_id:
                    if target_btn_idx >= 0:
                        # 插入到目标按钮后面
                        group['buttons'].insert(target_btn_idx, source_btn_config)
                    else:
                        # 添加到末尾
                        group['buttons'].append(source_btn_config)
                    break
            self.log(f"Button {source_btn_id} moved to group {target_group_id}", "INFO")
        else:
            # 同组移动
            for group in self.buttons_config.get('groups', []):
                if group.get('id') == target_group_id:
                    if target_btn_idx >= 0:
                        # 调整插入位置（因为已经删除了源位置）
                        if target_btn_idx >= source_btn_idx:
                            # 向下移动，插入到目标后面
                            group['buttons'].insert(target_btn_idx, source_btn_config)
                            self.log(f"Button {source_btn_id} moved down", "INFO")
                        else:
                            # 向上移动，插入到目标位置
                            group['buttons'].insert(target_btn_idx, source_btn_config)
                            self.log(f"Button {source_btn_id} moved up", "INFO")
                    else:
                        group['buttons'].append(source_btn_config)
                    break
        
        self._save_buttons_config()
        self._rebuild_buttons_ui()
    
    def _on_group_reordered(self, source_group_id, target_group_id):
        """处理组拖拽排序"""
        if not self.edit_mode or not hasattr(self, 'buttons_config'):
            return
        
        # 硬编码组不支持交换
        hardcoded_groups = ('screen_mirror', 'shell_commands')
        if source_group_id in hardcoded_groups or target_group_id in hardcoded_groups:
            self.log(f"Cannot swap hardcoded groups (screen_mirror, shell_commands)", "WARNING")
            return
        
        # 找到源组和目标组的位置
        source_idx = -1
        target_idx = -1
        
        for idx, group in enumerate(self.buttons_config.get('groups', [])):
            if group.get('id') == source_group_id:
                source_idx = idx
            if group.get('id') == target_group_id:
                target_idx = idx
        
        if source_idx < 0 or target_idx < 0:
            return
        
        # 交换位置
        groups = self.buttons_config['groups']
        groups[source_idx], groups[target_idx] = groups[target_idx], groups[source_idx]
        
        # 更新order字段
        for idx, group in enumerate(groups):
            group['order'] = idx + 1
        
        self._save_buttons_config()
        self._rebuild_buttons_ui()
        self.log(f"Group {source_group_id} swapped with {target_group_id}", "INFO")
    
    def _on_button_dropped_to_group(self, button_id, target_group_id):
        """处理按钮拖放到组标题栏"""
        if not self.edit_mode or not hasattr(self, 'buttons_config'):
            return
        
        # 找到源按钮配置
        source_btn_config = None
        source_group_id = None
        
        for group in self.buttons_config.get('groups', []):
            for btn in group.get('buttons', []):
                if btn.get('id') == button_id:
                    source_btn_config = btn
                    source_group_id = group.get('id')
                    break
            if source_btn_config:
                break
        
        if not source_btn_config:
            return
        
        # 从源组移除
        for group in self.buttons_config.get('groups', []):
            if group.get('id') == source_group_id:
                for i, btn in enumerate(group.get('buttons', [])):
                    if btn.get('id') == button_id:
                        group['buttons'].pop(i)
                        break
                break
        
        # 添加到目标组
        for group in self.buttons_config.get('groups', []):
            if group.get('id') == target_group_id:
                group.setdefault('buttons', []).append(source_btn_config)
                break
        
        self._save_buttons_config()
        self._rebuild_buttons_ui()
        self.log(f"Button {button_id} moved to group {target_group_id}", "INFO")
    
    def _set_buttons_edit_style(self, enabled):
        """Set edit mode style for all buttons"""
        if not hasattr(self, 'button_widgets'):
            return
        
        for btn_id, btn in self.button_widgets.items():
            if enabled:
                btn.setStyleSheet("border: 2px dashed #0078d4; background-color: rgba(0,120,212,0.1);")
            else:
                btn.setStyleSheet("")
    
    def _show_button_context_menu(self, btn, pos):
        """Show context menu for button in edit mode"""
        if not self.edit_mode:
            return
        
        from PySide6.QtWidgets import QMenu
        
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {self.colors['card_bg']};
                color: {self.colors['fg']};
                border: 1px solid {self.colors['border']};
            }}
            QMenu::item:selected {{
                background-color: {self.colors['accent']};
                color: white;
            }}
        """)
        
        # 获取按钮信息
        btn_id = btn.property('button_id')
        current_group_id = btn.property('group_id')
        
        # 上移/下移
        move_up = menu.addAction("⬆️ 上移 / Move Up")
        move_down = menu.addAction("⬇️ 下移 / Move Down")
        menu.addSeparator()
        
        # 移动到其他组
        move_to_menu = menu.addMenu("📁 移动到 / Move to")
        for group_id, group_widget in self.group_widgets.items():
            if group_id != current_group_id:
                group_name = group_widget.title()
                action = move_to_menu.addAction(group_name)
                action.triggered.connect(lambda checked, bid=btn_id, gid=group_id: self._move_button_to_group(bid, gid))
        
        # 复制到其他组
        copy_to_menu = menu.addMenu("📋 复制到 / Copy to")
        for group_id, group_widget in self.group_widgets.items():
            if group_id != current_group_id:
                group_name = group_widget.title()
                action = copy_to_menu.addAction(group_name)
                action.triggered.connect(lambda checked, bid=btn_id, gid=group_id: self._copy_button_to_group(bid, gid))
        
        menu.addSeparator()
        
        # 删除按钮
        delete_action = menu.addAction("🗑️ 删除 / Delete")
        delete_action.triggered.connect(lambda: self._delete_button(btn_id))
        
        # 连接上移/下移
        move_up.triggered.connect(lambda: self._move_button_up(btn_id))
        move_down.triggered.connect(lambda: self._move_button_down(btn_id))
        
        menu.exec(btn.mapToGlobal(pos))
    
    def _move_button_up(self, btn_id):
        """Move button up in its group"""
        if not hasattr(self, 'buttons_config'):
            return
        
        for group in self.buttons_config.get('groups', []):
            buttons = group.get('buttons', [])
            for i, btn in enumerate(buttons):
                if btn.get('id') == btn_id and i > 0:
                    # 交换位置
                    buttons[i], buttons[i-1] = buttons[i-1], buttons[i]
                    self._save_buttons_config()
                    self._rebuild_buttons_ui()
                    self.log(f"Button {btn_id} moved up", "INFO")
                    return
    
    def _move_button_down(self, btn_id):
        """Move button down in its group"""
        if not hasattr(self, 'buttons_config'):
            return
        
        for group in self.buttons_config.get('groups', []):
            buttons = group.get('buttons', [])
            for i, btn in enumerate(buttons):
                if btn.get('id') == btn_id and i < len(buttons) - 1:
                    # 交换位置
                    buttons[i], buttons[i+1] = buttons[i+1], buttons[i]
                    self._save_buttons_config()
                    self._rebuild_buttons_ui()
                    self.log(f"Button {btn_id} moved down", "INFO")
                    return
    
    def _move_button_to_group(self, btn_id, target_group_id):
        """Move button to another group"""
        if not hasattr(self, 'buttons_config'):
            return
        
        btn_config = None
        source_group_id = None
        
        # 找到按钮并从原组移除
        for group in self.buttons_config.get('groups', []):
            buttons = group.get('buttons', [])
            for i, btn in enumerate(buttons):
                if btn.get('id') == btn_id:
                    btn_config = buttons.pop(i)
                    source_group_id = group.get('id')
                    break
            if btn_config:
                break
        
        if not btn_config:
            return
        
        # 添加到目标组
        for group in self.buttons_config.get('groups', []):
            if group.get('id') == target_group_id:
                group.setdefault('buttons', []).append(btn_config)
                break
        
        self._save_buttons_config()
        self._rebuild_buttons_ui()
        self.log(f"Button {btn_id} moved to {target_group_id}", "INFO")
    
    def _copy_button_to_group(self, btn_id, target_group_id):
        """Copy button to another group"""
        if not hasattr(self, 'buttons_config'):
            return
        
        btn_config = None
        
        # 找到按钮配置
        for group in self.buttons_config.get('groups', []):
            for btn in group.get('buttons', []):
                if btn.get('id') == btn_id:
                    btn_config = btn.copy()
                    break
            if btn_config:
                break
        
        if not btn_config:
            return
        
        # 生成新ID
        import copy
        new_btn_config = copy.deepcopy(btn_config)
        new_btn_config['id'] = f"{btn_id}_copy_{len(self.button_widgets)}"
        
        # 添加到目标组
        for group in self.buttons_config.get('groups', []):
            if group.get('id') == target_group_id:
                group.setdefault('buttons', []).append(new_btn_config)
                break
        
        self._save_buttons_config()
        self._rebuild_buttons_ui()
        self.log(f"Button {btn_id} copied to {target_group_id}", "INFO")
    
    def _delete_button(self, btn_id):
        """Delete button from configuration"""
        if not hasattr(self, 'buttons_config'):
            return
        
        reply = QMessageBox.question(self, "Confirm Delete", 
                                      f"Delete button '{btn_id}'?",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        for group in self.buttons_config.get('groups', []):
            buttons = group.get('buttons', [])
            for i, btn in enumerate(buttons):
                if btn.get('id') == btn_id:
                    buttons.pop(i)
                    self._save_buttons_config()
                    self._rebuild_buttons_ui()
                    self.log(f"Button {btn_id} deleted", "INFO")
                    return
    
    def _save_buttons_config(self):
        """Save buttons configuration to JSON file"""
        config_path = os.path.join(self.project_dir, 'buttons_cmd.json')
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.buttons_config, f, indent=2, ensure_ascii=False)
            self.log("Buttons configuration saved", "INFO")
        except Exception as e:
            self.log(f"Failed to save buttons config: {e}", "ERROR")
    
    def _rebuild_buttons_ui(self):
        """Rebuild buttons UI after configuration change"""
        if not hasattr(self, 'ops_layout'):
            return
        
        # 获取硬编码组引用
        screen_mirror_widget = self.group_widgets.get('screen_mirror')
        shell_commands_widget = self.group_widgets.get('shell_commands')
        
        # 清除旧按钮（保留硬编码组）
        for group_id, group_widget in list(self.group_widgets.items()):
            if group_id not in ('screen_mirror', 'shell_commands'):
                if group_widget is not None:
                    self.ops_layout.removeWidget(group_widget)
                    group_widget.deleteLater()
        
        # 清除非硬编码组的引用
        self.group_widgets = {k: v for k, v in self.group_widgets.items() if k in ('screen_mirror', 'shell_commands')}
        self.button_widgets.clear()
        self.button_configs.clear()
        
        # 记录shell_commands在布局中的位置
        shell_index = -1
        if shell_commands_widget is not None:
            shell_index = self.ops_layout.indexOf(shell_commands_widget)
            # 临时移除shell_commands
            self.ops_layout.removeWidget(shell_commands_widget)
        
        # 创建配置按钮（会追加到末尾）
        self.create_buttons_from_config(self.ops_layout)
        
        # 在原位置重新插入shell_commands
        if shell_commands_widget is not None:
            if shell_index >= 0:
                self.ops_layout.insertWidget(shell_index, shell_commands_widget)
            else:
                self.ops_layout.addWidget(shell_commands_widget)
        
        # 保持编辑模式
        if self.edit_mode:
            self._set_buttons_edit_style(True)
    
    def toggle_dark_mode(self):
        """Toggle dark mode on/off"""
        self.dark_mode = not self.dark_mode
        self.config.set('app.dark_mode', self.dark_mode)
        self.apply_theme()
        
        # Update all UI elements that have custom styles
        self.update_widget_styles()
        
        # Update dark mode button text
        if hasattr(self, 'dark_mode_btn'):
            self.dark_mode_btn.setText("🌙 Dark Mode" if not self.dark_mode else "☀️ Light Mode")
    
    def show_opensource_components(self):
        """Show open source components dialog with Markdown rendering"""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTextBrowser, QPushButton, QLabel
        from PySide6.QtGui import QFont
        from PySide6.QtCore import QFileSystemWatcher
        
        # 组件清单文件路径
        components_file = os.path.join(self.project_dir, 'docs', 'OPENSOURCE_COMPONENTS.md')
        print(f"DEBUG: project_dir = {self.project_dir}")
        print(f"DEBUG: components_file = {components_file}")
        print(f"DEBUG: exists = {os.path.exists(components_file)}")
        
        dialog = QDialog(self)
        dialog.setWindowTitle("📜 开源组件清单 / Open Source Components")
        dialog.setMinimumSize(800, 600)
        
        layout = QVBoxLayout(dialog)
        
        # 标题
        title = QLabel("📜 开源组件清单")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Markdown显示区域
        text_browser = QTextBrowser()
        text_browser.setOpenExternalLinks(True)
        
        # 加载并渲染Markdown
        def load_content():
            if os.path.exists(components_file):
                try:
                    with open(components_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    html = self._markdown_to_html(content)
                    text_browser.setHtml(html)
                except Exception as e:
                    text_browser.setPlainText(f"Error loading file: {e}")
            else:
                text_browser.setPlainText("组件清单文件未找到: OPENSOURCE_COMPONENTS.md")
        
        load_content()
        
        # 文件监控 - 修改后自动刷新
        watcher = QFileSystemWatcher(dialog)
        if os.path.exists(components_file):
            watcher.addPath(components_file)
            watcher.fileChanged.connect(lambda: (watcher.addPath(components_file), load_content()))
        
        layout.addWidget(text_browser)
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_edit = QPushButton("📝 编辑清单")
        btn_edit.clicked.connect(lambda: os.startfile(components_file) if os.path.exists(components_file) else None)
        btn_layout.addWidget(btn_edit)
        
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(dialog.close)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)
        
        # 应用主题
        if self.dark_mode:
            dialog.setStyleSheet("""
                QDialog { background-color: #1e1e1e; color: #ffffff; }
                QPushButton {
                    background-color: #0e639c;
                    color: white;
                    border: none;
                    padding: 8px 15px;
                    border-radius: 3px;
                }
                QPushButton:hover { background-color: #1177bb; }
                QTextBrowser {
                    background-color: #2d2d2d;
                    border: 1px solid #3c3c3c;
                    border-radius: 5px;
                }
            """)
        
        dialog.exec()
    
    def update_widget_styles(self):
        """Update all widgets with custom stylesheets when theme changes"""
        # Header labels
        if hasattr(self, 'title_label'):
            self.title_label.setStyleSheet(f"color: {self.colors['fg']};")
        if hasattr(self, 'subtitle_label'):
            self.subtitle_label.setStyleSheet(f"color: {self.colors['text_secondary']};")
        
        # Device info labels (only update if not in special state)
        if hasattr(self, 'device_info_label'):
            current_style = self.device_info_label.styleSheet()
            if 'error' not in current_style.lower() and 'warning' not in current_style.lower() and 'success' not in current_style.lower():
                self.device_info_label.setStyleSheet(f"color: {self.colors['text_secondary']};")
        if hasattr(self, 'adb_path_label'):
            current_style = self.adb_path_label.styleSheet()
            if 'error' not in current_style.lower() and 'success' not in current_style.lower():
                self.adb_path_label.setStyleSheet(f"color: {self.colors['text_tertiary']};")
        
        # Separator
        if hasattr(self, 'separator'):
            self.separator.setStyleSheet(f"color: {self.colors['border']};")
        
        # Status bar
        if hasattr(self, 'status_bar'):
            self.status_bar.setStyleSheet(f"""
                background-color: {self.colors['card_bg']};
                border: 1px solid {self.colors['border']};
                padding: 8px 15px;
                color: {self.colors['text_secondary']};
            """)
        
        # Force refresh of all widgets to apply new stylesheet
        # This ensures the global stylesheet is reapplied to all widgets
        self.style().unpolish(self)
        self.style().polish(self)
        
        # Update all child widgets
        for widget in self.findChildren(QWidget):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
        
        # Update shell help label if it exists
        if hasattr(self, 'shell_help_label'):
            self.shell_help_label.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 8pt;")
    
    def degoogle_device(self):
        """DeGoogle the device - disable/uninstall Google apps"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        # Safe Google apps to disable (won't break functionality)
        # LIST 1 — SAFE TO REMOVE
        # A. Google Apps (Safe to Remove)
        safe_google_apps = [
            'com.google.android.youtube',
            'com.google.android.apps.youtube.music',
            'com.google.android.videos',
            'com.google.android.music',
            'com.google.android.apps.books',
            'com.google.android.apps.podcasts',
            'com.google.android.apps.tachyon',  # Duo / Meet
            'com.google.android.apps.chromecast.app',  # Google Home
            'com.google.android.apps.maps',  # Google Maps
            'com.google.android.apps.docs',  # Google Drive
            'com.google.android.gm',  # Gmail
            'com.google.android.calendar',
            'com.google.android.contacts',  # Only if using an alternative app
            # B. Google Assistant / Search / AI
            'com.google.android.googlequicksearchbox',  # Google App (search + feed)
            'com.google.android.apps.googleassistant',
            'com.android.hotwordenrollment.okgoogle',
            'com.android.hotwordenrollment.xgoogle',
            'com.google.android.apps.scribe',  # Recorder transcription AI
            'com.google.android.as',  # Pixel AI suggestions
            'com.google.android.apps.aiwallpapers',
            # C. Google Media Processing & AR
            'com.google.ar.core',
            'com.google.android.apps.photos',
            'com.google.android.apps.lens',
            'com.google.android.apps.photos.scanner',
            # D. Pixel Optional Features
            'com.google.android.apps.pixelmigrate',
            'com.google.android.apps.pixel.setupwizard',
            'com.google.android.apps.pixel.typeapps',
            'com.google.android.apps.pixel.extras',
            'com.google.android.onetimeinitializer',
            # E. Cloud / Backup / Sync (Non-essential)
            'com.google.android.apps.restore',
            'com.google.android.backuptransport',
            'com.google.android.syncadapters.contacts',
            'com.google.android.syncadapters.calendar',
            'com.google.android.partnersetup',
            # F. Vehicle / Cast / Wearable
            'com.google.android.projection.gearhead',  # Android Auto
            'com.google.android.gms.car',
            'com.google.android.apps.wearables',
            # G. Logging / Analytics / Feedback
            'com.google.android.feedback',
            'com.google.mainline.telemetry',
            'com.google.android.gms.advertisingid',
            'com.google.android.gms.location.history',
        ]
        
        # LIST 2 — UNSAFE / DO NOT REMOVE UNDER ANY CIRCUMSTANCES
        # These WILL break your Pixel instantly (bootloop, no camera, no network, no launcher, 
        # failed OTA, broken notifications, etc.)
        unsafe_google_packages = [
            # A. Pixel Launcher + UI
            'com.google.android.pixel.launcher',
            'com.google.android.apps.wallpaper',
            'com.google.android.systemui',
            'com.android.systemui',
            # B. Camera / Image Pipeline
            # Removing ANY Pixel camera component breaks HDR+, Night Sight, or makes camera fail entirely.
            'com.google.pixel.camera.services',
            'com.google.android.camera',
            'com.google.android.camera.provider',
            'com.google.android.camera.experimental2018',
            # C. Google Play Core Components
            # Removing any of these breaks apps, notifications, SafetyNet/Play Integrity, and OTA updates.
            'com.google.android.gms',  # Google Play Services
            'com.google.android.gsf',  # Google Services Framework
            'com.google.android.gms.location',
            'com.google.android.gms.policy_sidecar',
            # D. Phone, Messaging, Carrier
            # If you remove any of these → No calls, no SMS, no mobile data.
            'com.android.phone',
            'com.android.providers.telephony',
            'com.android.providers.telephony.overlay',
            'com.android.carrierconfig',
            'com.google.android.ims',  # VoLTE / VoWiFi
            # E. Core Android Infrastructure
            'com.android.providers.downloads',  # Breaks Play Store + OTA updates
            'com.android.providers.downloads.ui',
            'com.android.vending',  # Play Store (optional but not recommended to remove)
            'com.android.packageinstaller',
            # F. OTA Update Critical
            'com.google.android.gms.update',
            'com.google.android.gms.policy_sidecar',
            'com.google.android.gms.setup',
            'com.google.android.gms.unstable',
        ]
        
        # Risky Google services (might break functionality)
        # Note: syncadapters are already in safe_google_apps list E, but listed here as risky
        risky_google_services = [
            'com.google.android.gsf.login',  # Google Login Service
            'com.google.android.providers.gsf',  # Google Services Provider
            'com.google.android.syncadapters.calendar',  # Calendar sync
            'com.google.android.syncadapters.contacts',  # Contacts sync
        ]
        
        # Show mode selection dialog
        mode_dialog = QDialog(self)
        mode_dialog.setWindowTitle("DeGoogle Device - Choose Mode")
        mode_dialog.setMinimumSize(500, 400)
        mode_dialog.setModal(True)
        
        mode_layout = QVBoxLayout(mode_dialog)
        mode_layout.setSpacing(15)
        mode_layout.setContentsMargins(20, 20, 20, 20)
        
        # Warning label
        warning_label = QLabel("⚠️ IMPORTANT WARNING ⚠️\n\n"
                              "This will remove Chrome browser!\n\n"
                              "Before proceeding, install an alternative browser\n"
                              "(Chromium, Brave, Firefox, or DuckDuckGo).")
        warning_label.setStyleSheet("color: red; font-weight: bold;")
        warning_label.setWordWrap(True)
        warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mode_layout.addWidget(warning_label)
        
        # Mode selection
        mode_label = QLabel("Choose mode:")
        mode_label.setFont(QFont('Segoe UI', 10, QFont.Weight.Bold))
        mode_layout.addWidget(mode_label)
        
        mode_group = QButtonGroup(mode_dialog)
        simple_radio = QRadioButton("Simple Mode - Remove all safe apps")
        simple_radio.setChecked(True)
        mode_group.addButton(simple_radio, 0)
        mode_layout.addWidget(simple_radio)
        
        custom_radio = QRadioButton("Custom Mode - Select individual apps")
        mode_group.addButton(custom_radio, 1)
        mode_layout.addWidget(custom_radio)
        
        mode_layout.addStretch()
        
        # Buttons
        mode_button_frame = QHBoxLayout()
        mode_button_frame.addStretch()
        
        cancel_mode_btn = QPushButton("Cancel")
        cancel_mode_btn.clicked.connect(mode_dialog.reject)
        mode_button_frame.addWidget(cancel_mode_btn)
        
        continue_btn = QPushButton("Continue")
        mode_button_frame.addWidget(continue_btn)
        
        mode_layout.addLayout(mode_button_frame)
        
        mode_selected = {'mode': None}
        
        def on_continue():
            if simple_radio.isChecked():
                mode_selected['mode'] = 'simple'
            else:
                mode_selected['mode'] = 'custom'
            mode_dialog.accept()
        
        continue_btn.clicked.connect(on_continue)
        
        # Show mode selection dialog
        if mode_dialog.exec() != QDialog.DialogCode.Accepted:
            return
        
        # After mode dialog closes, proceed with selected mode
        if mode_selected['mode'] == 'simple':
            # Simple Mode
            self.show_simple_degoogle_dialog(safe_google_apps, risky_google_services, unsafe_google_packages)
        elif mode_selected['mode'] == 'custom':
            # Custom Mode - check installed packages and show selection dialog
            self.log("Checking installed packages for Custom Mode...")
            self.update_status("Checking installed packages...")
            
            # Store packages for use in callback
            packages_data = {'safe': safe_google_apps, 'risky': risky_google_services, 'unsafe': unsafe_google_packages}
            
            def check_installed_and_show():
                try:
                    # Get all installed packages
                    result = self.adb.run_command(f"{self.get_device_flag()} shell pm list packages", timeout=60)
                    installed_packages = set()
                    if result['success']:
                        packages = result['stdout'].strip().split('\n')
                        installed_packages = {pkg.replace('package:', '').strip() for pkg in packages if pkg.strip()}
                    
                    # Categorize installed packages
                    installed_safe = [pkg for pkg in packages_data['safe'] if pkg in installed_packages]
                    installed_risky = [pkg for pkg in packages_data['risky'] if pkg in installed_packages]
                    installed_unsafe = [pkg for pkg in packages_data['unsafe'] if pkg in installed_packages]
                    
                    self.log(f"Found {len(installed_safe)} safe, {len(installed_risky)} risky, {len(installed_unsafe)} unsafe packages")
                    self.update_status("Ready")
                    
                    # Store results for main thread
                    packages_data['installed_safe'] = installed_safe
                    packages_data['installed_risky'] = installed_risky
                    packages_data['installed_unsafe'] = installed_unsafe
                    packages_data['ready'] = True
                    
                    # Emit signal to show custom selection dialog (thread-safe)
                    self.custom_dialog_ready.emit(packages_data)
                except Exception as e:
                    self.log(f"Error checking installed packages: {e}", "ERROR")
                    self.update_status("Error checking packages")
                    import traceback
                    self.log(f"Traceback: {traceback.format_exc()}", "ERROR")
                    # Store error in packages_data and emit signal
                    packages_data['error'] = str(e)
                    packages_data['ready'] = True
                    self.custom_dialog_ready.emit(packages_data)
            
            packages_data['ready'] = False
            threading.Thread(target=check_installed_and_show, daemon=True).start()
    
    def show_simple_degoogle_dialog(self, safe_google_apps, risky_google_services, unsafe_google_packages):
        """Show simple DeGoogle dialog with checkbox for risky services"""
        dialog = QDialog(self)
        dialog.setWindowTitle("DeGoogle Device - Simple Mode")
        dialog.setMinimumSize(500, 600)
        dialog.setModal(True)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Title
        title_label = QLabel("DeGoogle Device - Simple Mode")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Critical warning about unsafe packages
        unsafe_warning_text = "🚨 CRITICAL: Unsafe packages are PROTECTED and will NOT be removed!\n"
        unsafe_warning_text += "These include: Pixel Launcher, Camera, System UI, Phone, Play Services, etc.\n"
        unsafe_warning_text += "Removing them WILL break your device (bootloop, no camera, no network, etc.)"
        unsafe_warning_label = QLabel(unsafe_warning_text)
        unsafe_warning_label.setStyleSheet("color: red; font-weight: bold;")
        unsafe_warning_label.setWordWrap(True)
        unsafe_warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(unsafe_warning_label)
        
        info_text = "This will disable/uninstall Google apps and services.\n\n"
        info_text += "Safe apps (won't break functionality):\n"
        info_text += "• Chrome, Google Photos, YouTube, Maps, Gmail, etc.\n\n"
        info_text += "Risky services (may break functionality):\n"
        info_text += "• Google Login Service\n"
        info_text += "• Google Services Provider\n"
        info_text += "• Calendar/Contacts sync adapters\n\n"
        info_text += "Warning: Disabling risky services may cause:\n"
        info_text += "• Apps to crash\n"
        info_text += "• Loss of sync functionality\n"
        info_text += "• Inability to use Google services\n"
        
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(info_label)
        
        # Checkbox for risky operations
        risky_checkbox = QCheckBox("Also disable/uninstall risky Google services (may break functionality)")
        layout.addWidget(risky_checkbox)
        
        # Action selection
        action_label = QLabel("Action:")
        layout.addWidget(action_label)
        
        action_group = QButtonGroup(dialog)
        action_frame = QHBoxLayout()
        
        disable_radio = QRadioButton("Disable (can be re-enabled)")
        disable_radio.setChecked(True)
        action_group.addButton(disable_radio, 0)
        action_frame.addWidget(disable_radio)
        
        uninstall_radio = QRadioButton("Uninstall for user (can be restored)")
        action_group.addButton(uninstall_radio, 1)
        action_frame.addWidget(uninstall_radio)
        
        action_frame.addStretch()
        layout.addLayout(action_frame)
        
        layout.addStretch()
        
        def do_degoogle():
            action = "disable" if disable_radio.isChecked() else "uninstall"
            include_risky = risky_checkbox.isChecked()
            
            # Close dialog first
            dialog.accept()
            
            # Show preview of what will be removed
            def show_preview_and_confirm():
                # Check which packages are installed
                result = self.adb.run_command(f"{self.get_device_flag()} shell pm list packages")
                installed_packages = set()
                if result['success']:
                    packages = result['stdout'].strip().split('\n')
                    installed_packages = {pkg.replace('package:', '').strip() for pkg in packages if pkg.strip()}
                
                all_packages = safe_google_apps.copy()
                if include_risky:
                    for risky in risky_google_services:
                        if risky not in all_packages:
                            all_packages.append(risky)
                
                # Filter to only installed packages, EXCLUDING unsafe packages
                packages_to_process = [pkg for pkg in all_packages if pkg in installed_packages and pkg not in unsafe_google_packages]
                unsafe_filtered = [pkg for pkg in all_packages if pkg in installed_packages and pkg in unsafe_google_packages]
                
                preview_text = f"This will {action} {len(packages_to_process)} Google package(s):\n\n"
                if packages_to_process:
                    preview_text += "Packages to be removed:\n"
                    for pkg in sorted(packages_to_process):
                        preview_text += f"• {pkg}\n"
                
                if unsafe_filtered:
                    preview_text += f"\n\n🚨 PROTECTED (will NOT be removed):\n"
                    preview_text += f"{len(unsafe_filtered)} unsafe package(s) detected and excluded:\n"
                    for pkg in sorted(unsafe_filtered):
                        preview_text += f"• {pkg} [PROTECTED]\n"
                
                preview_text += f"\n\nInclude risky services: {include_risky}\n"
                preview_text += f"Action: {action}\n\n"
                preview_text += "Continue?"
                
                reply = QMessageBox.question(self, "Preview - Confirm DeGoogle", preview_text,
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                return reply == QMessageBox.StandardButton.Yes
            
            if not show_preview_and_confirm():
                return
            
            self.log("Starting DeGoogle process...")
            self.update_status("DeGoogling device...")
            
            def process_degoogle():
                disabled_packages = []
                uninstalled_packages = []
                failed_packages = []
                
                all_packages = safe_google_apps.copy()
                if include_risky:
                    # Add risky services, but avoid duplicates
                    for risky in risky_google_services:
                        if risky not in all_packages:
                            all_packages.append(risky)
                
                # First, check which packages are installed
                result = self.adb.run_command(f"{self.get_device_flag()} shell pm list packages")
                installed_packages = set()
                if result['success']:
                    packages = result['stdout'].strip().split('\n')
                    installed_packages = {pkg.replace('package:', '').strip() for pkg in packages if pkg.strip()}
                
                # Filter to only installed packages, EXCLUDING unsafe packages
                packages_to_process = [pkg for pkg in all_packages if pkg in installed_packages and pkg not in unsafe_google_packages]
                
                # Check if any unsafe packages were filtered out
                unsafe_filtered = [pkg for pkg in all_packages if pkg in installed_packages and pkg in unsafe_google_packages]
                if unsafe_filtered:
                    self.log(f"WARNING: {len(unsafe_filtered)} unsafe packages excluded from removal: {', '.join(unsafe_filtered[:5])}", "WARNING")
                
                self.log(f"Found {len(packages_to_process)} Google packages to process")
                
                for i, package in enumerate(packages_to_process):
                    self.log(f"Processing {i+1}/{len(packages_to_process)}: {package}")
                    
                    if action == "disable":
                        # Try to disable
                        result = self.adb.run_command(f"{self.get_device_flag()} shell pm disable-user {package}")
                        if result['success']:
                            disabled_packages.append(package)
                            self.log(f"Disabled: {package}")
                        else:
                            failed_packages.append((package, result.get('stderr', 'Unknown error')))
                            self.log(f"Failed to disable {package}: {result.get('stderr', 'Unknown error')}", "ERROR")
                    else:  # uninstall
                        # Try to uninstall for user
                        result = self.adb.run_command(f"{self.get_device_flag()} shell pm uninstall --user 0 {package}")
                        if result['success']:
                            output = result['stdout'].strip() if result['stdout'] else ''
                            if 'Success' in output or 'success' in output.lower() or output == '':
                                uninstalled_packages.append(package)
                                self.log(f"Uninstalled for user: {package}")
                            else:
                                failed_packages.append((package, output))
                                self.log(f"Failed to uninstall {package}: {output}", "ERROR")
                        else:
                            failed_packages.append((package, result.get('stderr', 'Unknown error')))
                            self.log(f"Failed to uninstall {package}: {result.get('stderr', 'Unknown error')}", "ERROR")
                
                # Save state - accumulate packages instead of overwriting
                device_id = self.current_device
                if device_id not in self.degoogle_state:
                    self.degoogle_state[device_id] = {}
                
                if action == "disable":
                    # Merge with existing disabled packages
                    existing_disabled = set(self.degoogle_state[device_id].get('disabled', []))
                    existing_disabled.update(disabled_packages)
                    self.degoogle_state[device_id]['disabled'] = list(existing_disabled)
                    self.degoogle_state[device_id]['disabled_risky'] = include_risky
                else:
                    # Merge with existing uninstalled packages
                    existing_uninstalled = set(self.degoogle_state[device_id].get('uninstalled', []))
                    existing_uninstalled.update(uninstalled_packages)
                    self.degoogle_state[device_id]['uninstalled'] = list(existing_uninstalled)
                    self.degoogle_state[device_id]['uninstalled_risky'] = include_risky
                
                self.degoogle_state[device_id]['action'] = action
                self.degoogle_state[device_id]['timestamp'] = datetime.now().isoformat()
                
                self.save_degoogle_state()
                
                # Show results
                result_msg = f"DeGoogle completed!\n\n"
                if action == "disable":
                    result_msg += f"Disabled: {len(disabled_packages)} packages\n"
                else:
                    result_msg += f"Uninstalled: {len(uninstalled_packages)} packages\n"
                
                if failed_packages:
                    result_msg += f"Failed: {len(failed_packages)} packages\n"
                
                if failed_packages:
                    result_msg += f"\nFailed packages:\n"
                    for pkg, error in failed_packages[:5]:  # Show first 5
                        result_msg += f"• {pkg}\n"
                    if len(failed_packages) > 5:
                        result_msg += f"... and {len(failed_packages) - 5} more\n"
                
                self.update_status("DeGoogle completed")
                # Thread-safe messagebox - use QTimer to call from main thread
                QTimer.singleShot(0, lambda: QMessageBox.information(self, "DeGoogle Complete", result_msg))
            
            threading.Thread(target=process_degoogle, daemon=True).start()
        
        # Buttons
        button_frame = QHBoxLayout()
        button_frame.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        button_frame.addWidget(cancel_btn)
        
        degoogle_btn = QPushButton("DeGoogle")
        degoogle_btn.clicked.connect(do_degoogle)
        button_frame.addWidget(degoogle_btn)
        
        layout.addLayout(button_frame)
        
        # Show dialog
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
    
    def _show_custom_dialog(self, packages_data):
        """Helper method to show custom dialog from main thread (called via signal)"""
        try:
            # Check for error first
            if 'error' in packages_data:
                QMessageBox.critical(self, "Error", f"Failed to check installed packages: {packages_data['error']}")
                return
            
            if not packages_data.get('ready', False):
                QMessageBox.warning(self, "Error", "Package data not ready yet. Please try again.")
                return
            
            self.show_degoogle_selection_dialog(
                packages_data['installed_safe'],
                packages_data['installed_risky'],
                packages_data['installed_unsafe'],
                packages_data['safe'],
                packages_data['risky'],
                packages_data['unsafe']
            )
        except Exception as e:
            self.log(f"Error in _show_custom_dialog: {e}", "ERROR")
            import traceback
            self.log(f"Traceback: {traceback.format_exc()}", "ERROR")
            QMessageBox.critical(self, "Error", f"Failed to show selection dialog: {e}")
    
    def show_degoogle_selection_dialog(self, installed_safe, installed_risky, installed_unsafe, all_safe_apps, all_risky_services, unsafe_google_packages):
        """Show dialog with checkboxes for selecting apps to remove"""
        try:
            self.log(f"show_degoogle_selection_dialog called: {len(installed_safe)} safe, {len(installed_risky)} risky, {len(installed_unsafe)} unsafe")
            self.update_status("Opening custom selection dialog...")
            dialog = QDialog(self)
            dialog.setWindowTitle("DeGoogle Device - Select Apps")
            dialog.setMinimumSize(600, 800)
            dialog.setModal(True)
            
            layout = QVBoxLayout(dialog)
            layout.setSpacing(10)
            layout.setContentsMargins(15, 15, 15, 15)
            
            # Critical unsafe packages warning
            unsafe_warning_text = "🚨 CRITICAL WARNING 🚨\n"
            unsafe_warning_text += "Unsafe packages CAN break your device!\n"
            unsafe_warning_text += "Removing them may cause: bootloop, no camera, no network, no launcher, failed OTA, broken notifications, etc.\n"
            unsafe_warning_text += "Only select unsafe packages if you know what you're doing!"
            unsafe_warning_label = QLabel(unsafe_warning_text)
            unsafe_warning_label.setStyleSheet("color: red; font-weight: bold;")
            unsafe_warning_label.setWordWrap(True)
            unsafe_warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(unsafe_warning_label)
            
            # Create tab widget
            tab_widget = QTabWidget()
            layout.addWidget(tab_widget)
            
            # Dictionary to store checkboxes
            safe_checkboxes = {}
            risky_checkboxes = {}
            unsafe_checkboxes = {}
            
            # Safe packages tab
            if installed_safe:
                safe_widget = QWidget()
                safe_layout = QVBoxLayout(safe_widget)
                safe_layout.setContentsMargins(5, 5, 5, 5)
                
                safe_scroll = QScrollArea()
                safe_scroll.setWidgetResizable(True)
                safe_scroll_widget = QWidget()
                safe_scroll_layout = QVBoxLayout(safe_scroll_widget)
                
                for package in sorted(installed_safe):
                    checkbox = QCheckBox(package)
                    checkbox.setChecked(True)
                    safe_checkboxes[package] = checkbox
                    safe_scroll_layout.addWidget(checkbox)
                
                safe_scroll_layout.addStretch()
                safe_scroll.setWidget(safe_scroll_widget)
                safe_layout.addWidget(safe_scroll)
                
                tab_widget.addTab(safe_widget, f"Safe Packages ({len(installed_safe)})")
            
            # Risky packages tab
            if installed_risky:
                risky_widget = QWidget()
                risky_layout = QVBoxLayout(risky_widget)
                risky_layout.setContentsMargins(5, 5, 5, 5)
                
                risky_scroll = QScrollArea()
                risky_scroll.setWidgetResizable(True)
                risky_scroll_widget = QWidget()
                risky_scroll_layout = QVBoxLayout(risky_scroll_widget)
                
                for package in sorted(installed_risky):
                    checkbox = QCheckBox(package)
                    risky_checkboxes[package] = checkbox
                    risky_scroll_layout.addWidget(checkbox)
                
                risky_scroll_layout.addStretch()
                risky_scroll.setWidget(risky_scroll_widget)
                risky_layout.addWidget(risky_scroll)
                
                tab_widget.addTab(risky_widget, f"Risky Packages ({len(installed_risky)})")
            
            # Unsafe packages tab (selectable with warning)
            if installed_unsafe:
                unsafe_widget = QWidget()
                unsafe_layout = QVBoxLayout(unsafe_widget)
                unsafe_layout.setContentsMargins(5, 5, 5, 5)
                
                unsafe_info = QLabel("⚠️ WARNING: These packages are UNSAFE to remove!\n"
                                    "Removing them WILL break your device (bootloop, no camera, no network, etc.)\n"
                                    "Only select if you understand the risks and have a backup/recovery plan.")
                unsafe_info.setStyleSheet("color: red; font-weight: bold;")
                unsafe_info.setWordWrap(True)
                unsafe_layout.addWidget(unsafe_info)
                
                unsafe_scroll = QScrollArea()
                unsafe_scroll.setWidgetResizable(True)
                unsafe_scroll_widget = QWidget()
                unsafe_scroll_layout = QVBoxLayout(unsafe_scroll_widget)
                
                for package in sorted(installed_unsafe):
                    checkbox = QCheckBox(f"🔒 {package} [UNSAFE]")
                    checkbox.setStyleSheet("QCheckBox { color: #cc0000; font-weight: bold; }")
                    unsafe_checkboxes[package] = checkbox
                    unsafe_scroll_layout.addWidget(checkbox)
                
                unsafe_scroll_layout.addStretch()
                unsafe_scroll.setWidget(unsafe_scroll_widget)
                unsafe_layout.addWidget(unsafe_scroll)
                
                tab_widget.addTab(unsafe_widget, f"Unsafe Packages ({len(installed_unsafe)})")
            
            # Action selection
            action_label = QLabel("Action:")
            layout.addWidget(action_label)
            
            action_group = QButtonGroup(dialog)
            action_frame = QHBoxLayout()
            
            disable_radio = QRadioButton("Disable (can be re-enabled)")
            disable_radio.setChecked(True)
            action_group.addButton(disable_radio, 0)
            action_frame.addWidget(disable_radio)
            
            uninstall_radio = QRadioButton("Uninstall for user (can be restored)")
            action_group.addButton(uninstall_radio, 1)
            action_frame.addWidget(uninstall_radio)
            
            action_frame.addStretch()
            layout.addLayout(action_frame)
            
            def do_degoogle():
                action = "disable" if disable_radio.isChecked() else "uninstall"
                
                # Get selected packages
                selected_safe = [pkg for pkg, cb in safe_checkboxes.items() if cb.isChecked()]
                selected_risky = [pkg for pkg, cb in risky_checkboxes.items() if cb.isChecked()]
                selected_unsafe = [pkg for pkg, cb in unsafe_checkboxes.items() if cb.isChecked()]
                selected_packages = selected_safe + selected_risky + selected_unsafe
                
                if not selected_packages:
                    QMessageBox.warning(dialog, "No Selection", "Please select at least one package to remove.")
                    return
                
                # Warn if unsafe packages are selected
                if selected_unsafe:
                    warning_msg = f"⚠️ CRITICAL WARNING ⚠️\n\n"
                    warning_msg += f"You have selected {len(selected_unsafe)} UNSAFE package(s):\n\n"
                    for pkg in selected_unsafe[:5]:  # Show first 5
                        warning_msg += f"• {pkg}\n"
                    if len(selected_unsafe) > 5:
                        warning_msg += f"... and {len(selected_unsafe) - 5} more\n"
                    warning_msg += f"\nRemoving these WILL break your device!\n"
                    warning_msg += f"Possible consequences:\n"
                    warning_msg += f"• Bootloop (device won't start)\n"
                    warning_msg += f"• No camera functionality\n"
                    warning_msg += f"• No network/mobile data\n"
                    warning_msg += f"• No launcher (black screen)\n"
                    warning_msg += f"• Failed OTA updates\n"
                    warning_msg += f"• Broken notifications\n\n"
                    warning_msg += f"Are you absolutely sure you want to proceed?"
                    
                    reply = QMessageBox.critical(dialog, "⚠️ DANGER - Unsafe Packages Selected", warning_msg,
                                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                                QMessageBox.StandardButton.No)
                    if reply != QMessageBox.StandardButton.Yes:
                        return
                
                dialog.accept()
                
                # Process the selected packages
                self.log(f"Starting DeGoogle process for {len(selected_packages)} packages...")
                self.update_status("DeGoogling device...")
                
                def process_degoogle():
                    disabled_packages = []
                    uninstalled_packages = []
                    failed_packages = []
                    
                    for i, package in enumerate(selected_packages):
                        self.log(f"Processing {i+1}/{len(selected_packages)}: {package}")
                        
                        if action == "disable":
                            result = self.adb.run_command(f"{self.get_device_flag()} shell pm disable-user {package}")
                            if result['success']:
                                disabled_packages.append(package)
                                self.log(f"Disabled: {package}")
                            else:
                                failed_packages.append((package, result.get('stderr', 'Unknown error')))
                                self.log(f"Failed to disable {package}: {result.get('stderr', 'Unknown error')}", "ERROR")
                        else:  # uninstall
                            result = self.adb.run_command(f"{self.get_device_flag()} shell pm uninstall --user 0 {package}")
                            if result['success']:
                                output = result['stdout'].strip() if result['stdout'] else ''
                                if 'Success' in output or 'success' in output.lower() or output == '':
                                    uninstalled_packages.append(package)
                                    self.log(f"Uninstalled for user: {package}")
                                else:
                                    failed_packages.append((package, output))
                                    self.log(f"Failed to uninstall {package}: {output}", "ERROR")
                            else:
                                failed_packages.append((package, result.get('stderr', 'Unknown error')))
                                self.log(f"Failed to uninstall {package}: {result.get('stderr', 'Unknown error')}", "ERROR")
                    
                    # Save state
                    device_id = self.current_device
                    if device_id not in self.degoogle_state:
                        self.degoogle_state[device_id] = {}
                    
                    if action == "disable":
                        existing_disabled = set(self.degoogle_state[device_id].get('disabled', []))
                        existing_disabled.update(disabled_packages)
                        self.degoogle_state[device_id]['disabled'] = list(existing_disabled)
                    else:
                        existing_uninstalled = set(self.degoogle_state[device_id].get('uninstalled', []))
                        existing_uninstalled.update(uninstalled_packages)
                        self.degoogle_state[device_id]['uninstalled'] = list(existing_uninstalled)
                    
                    self.degoogle_state[device_id]['action'] = action
                    self.degoogle_state[device_id]['timestamp'] = datetime.now().isoformat()
                    self.save_degoogle_state()
                    
                    # Show results
                    result_msg = f"DeGoogle completed!\n\n"
                    if action == "disable":
                        result_msg += f"Disabled: {len(disabled_packages)} packages\n"
                    else:
                        result_msg += f"Uninstalled: {len(uninstalled_packages)} packages\n"
                    
                    # Check if any unsafe packages were processed
                    processed_unsafe = [pkg for pkg in (disabled_packages + uninstalled_packages) if pkg in selected_unsafe]
                    if processed_unsafe:
                        result_msg += f"\n⚠️ WARNING: {len(processed_unsafe)} unsafe package(s) were processed!\n"
                        result_msg += f"Monitor your device for issues. If problems occur, use 'Undo DeGoogle' to restore.\n"
                    
                    if failed_packages:
                        result_msg += f"\nFailed: {len(failed_packages)} packages\n"
                        result_msg += f"\nFailed packages:\n"
                        for pkg, error in failed_packages[:5]:
                            result_msg += f"• {pkg}\n"
                        if len(failed_packages) > 5:
                            result_msg += f"... and {len(failed_packages) - 5} more\n"
                    
                    self.update_status("DeGoogle completed")
                    QTimer.singleShot(0, lambda: QMessageBox.information(self, "DeGoogle Complete", result_msg))
                
                threading.Thread(target=process_degoogle, daemon=True).start()
            
            # Buttons
            button_frame = QHBoxLayout()
            button_frame.addStretch()
            
            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(dialog.reject)
            button_frame.addWidget(cancel_btn)
            
            degoogle_btn = QPushButton("DeGoogle")
            degoogle_btn.clicked.connect(do_degoogle)
            button_frame.addWidget(degoogle_btn)
            
            layout.addLayout(button_frame)
            
            # If no packages found, show a message in the dialog
            if not installed_safe and not installed_risky and not installed_unsafe:
                no_packages_label = QLabel("No Google packages found on your device.\n\n"
                                          "Either they are already removed, or your device doesn't have them installed.")
                no_packages_label.setWordWrap(True)
                no_packages_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                no_packages_label.setStyleSheet("color: #666666; font-size: 12px; padding: 20px;")
                layout.insertWidget(1, no_packages_label)  # Insert after warning, before tabs
                # Disable the DeGoogle button since there's nothing to do
                degoogle_btn.setEnabled(False)
            
            # Show dialog (raise and activate to ensure it's visible)
            self.log("About to show custom selection dialog...")
            # Make sure dialog is on top and visible
            dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint)
            result = dialog.exec()
            self.log(f"Custom selection dialog closed with result: {result}")
            
        except Exception as e:
            self.log(f"Error showing degoogle selection dialog: {e}", "ERROR")
            import traceback
            self.log(f"Traceback: {traceback.format_exc()}", "ERROR")
            QMessageBox.critical(self, "Error", f"Failed to show dialog: {e}")
    
    def undo_degoogle(self):
        """Undo DeGoogle - restore disabled/uninstalled Google apps with selection"""
        if not self.current_device:
            QMessageBox.warning(self, "No Device", "Please select a device first")
            return
        
        device_id = self.current_device
        
        # LIST 1 — SAFE TO REMOVE (for restore purposes, includes all safe packages)
        google_packages = [
            # A. Google Apps (Safe to Remove)
            'com.google.android.youtube',
            'com.google.android.apps.youtube.music',
            'com.google.android.videos',
            'com.google.android.music',
            'com.google.android.apps.books',
            'com.google.android.apps.podcasts',
            'com.google.android.apps.tachyon',  # Duo / Meet
            'com.google.android.apps.chromecast.app',  # Google Home
            'com.google.android.apps.maps',  # Google Maps
            'com.google.android.apps.docs',  # Google Drive
            'com.google.android.gm',  # Gmail
            'com.google.android.calendar',
            'com.google.android.contacts',  # Only if using an alternative app
            # B. Google Assistant / Search / AI
            'com.google.android.googlequicksearchbox',  # Google App (search + feed)
            'com.google.android.apps.googleassistant',
            'com.android.hotwordenrollment.okgoogle',
            'com.android.hotwordenrollment.xgoogle',
            'com.google.android.apps.scribe',  # Recorder transcription AI
            'com.google.android.as',  # Pixel AI suggestions
            'com.google.android.apps.aiwallpapers',
            # C. Google Media Processing & AR
            'com.google.ar.core',
            'com.google.android.apps.photos',
            'com.google.android.apps.lens',
            'com.google.android.apps.photos.scanner',
            # D. Pixel Optional Features
            'com.google.android.apps.pixelmigrate',
            'com.google.android.apps.pixel.setupwizard',
            'com.google.android.apps.pixel.typeapps',
            'com.google.android.apps.pixel.extras',
            'com.google.android.onetimeinitializer',
            # E. Cloud / Backup / Sync (Non-essential)
            'com.google.android.apps.restore',
            'com.google.android.backuptransport',
            'com.google.android.syncadapters.contacts',
            'com.google.android.syncadapters.calendar',
            'com.google.android.partnersetup',
            # F. Vehicle / Cast / Wearable
            'com.google.android.projection.gearhead',  # Android Auto
            'com.google.android.gms.car',
            'com.google.android.apps.wearables',
            # G. Logging / Analytics / Feedback
            'com.google.android.feedback',
            'com.google.mainline.telemetry',
            'com.google.android.gms.advertisingid',
            'com.google.android.gms.location.history',
            # LIST 2 — UNSAFE (can be restored if accidentally removed)
            # A. Pixel Launcher + UI
            'com.google.android.pixel.launcher',
            'com.google.android.apps.wallpaper',
            'com.google.android.systemui',
            'com.android.systemui',
            # B. Camera / Image Pipeline
            'com.google.pixel.camera.services',
            'com.google.android.camera',
            'com.google.android.camera.provider',
            'com.google.android.camera.experimental2018',
            # C. Google Play Core Components
            'com.google.android.gms',  # Google Play Services
            'com.google.android.gsf',  # Google Services Framework
            'com.google.android.gms.location',
            'com.google.android.gms.policy_sidecar',
            # D. Phone, Messaging, Carrier
            'com.android.phone',
            'com.android.providers.telephony',
            'com.android.providers.telephony.overlay',
            'com.android.carrierconfig',
            'com.google.android.ims',  # VoLTE / VoWiFi
            # E. Core Android Infrastructure
            'com.android.providers.downloads',  # Breaks Play Store + OTA updates
            'com.android.providers.downloads.ui',
            'com.android.vending',  # Play Store
            'com.android.packageinstaller',
            # F. OTA Update Critical
            'com.google.android.gms.update',
            'com.google.android.gms.policy_sidecar',
            'com.google.android.gms.setup',
            'com.google.android.gms.unstable',
        ]
        
        # Get packages from saved state and filter to only show specified packages
        state = self.degoogle_state.get(device_id, {})
        saved_disabled = [pkg for pkg in state.get('disabled', []) if pkg in google_packages]
        saved_uninstalled = [pkg for pkg in state.get('uninstalled', []) if pkg in google_packages]
        
        # Show dialog with saved state only (no device scanning)
        if saved_disabled or saved_uninstalled:
            self.show_restore_dialog(device_id, saved_disabled, saved_uninstalled)
        else:
            QMessageBox.information(self, "Nothing to Restore", "No disabled or uninstalled Google packages found in saved state.")
    
    def show_restore_dialog(self, device_id, disabled_packages, uninstalled_packages):
        """Show the restore selection dialog"""
        if not disabled_packages and not uninstalled_packages:
            QMessageBox.information(self, "Nothing to Restore", "No disabled or uninstalled Google packages found on device or in saved state.")
            return
        
        # Show selection dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Restore DeGoogled Packages")
        dialog.setMinimumSize(600, 700)
        dialog.setModal(True)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Title
        title_label = QLabel("Select packages to restore")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        info_text = "Select which packages you want to restore.\n"
        info_text += "Disabled packages can be re-enabled.\n"
        info_text += "Uninstalled packages will be reinstalled for your user account.\n"
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(info_label)
        
        # Create tab widget
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)
        
        disabled_checkboxes = {}
        uninstalled_checkboxes = {}
        
        # Disabled packages tab
        if disabled_packages:
            disabled_widget = QWidget()
            disabled_layout = QVBoxLayout(disabled_widget)
            disabled_layout.setContentsMargins(5, 5, 5, 5)
            
            disabled_scroll = QScrollArea()
            disabled_scroll.setWidgetResizable(True)
            disabled_scroll_widget = QWidget()
            disabled_scroll_layout = QVBoxLayout(disabled_scroll_widget)
            
            for package in sorted(disabled_packages):
                checkbox = QCheckBox(package)
                checkbox.setChecked(True)
                disabled_checkboxes[package] = checkbox
                disabled_scroll_layout.addWidget(checkbox)
            
            disabled_scroll_layout.addStretch()
            disabled_scroll.setWidget(disabled_scroll_widget)
            disabled_layout.addWidget(disabled_scroll)
            
            tab_widget.addTab(disabled_widget, f"Disabled ({len(disabled_packages)})")
        
        # Uninstalled packages tab
        if uninstalled_packages:
            uninstalled_widget = QWidget()
            uninstalled_layout = QVBoxLayout(uninstalled_widget)
            uninstalled_layout.setContentsMargins(5, 5, 5, 5)
            
            uninstalled_scroll = QScrollArea()
            uninstalled_scroll.setWidgetResizable(True)
            uninstalled_scroll_widget = QWidget()
            uninstalled_scroll_layout = QVBoxLayout(uninstalled_scroll_widget)
            
            for package in sorted(uninstalled_packages):
                checkbox = QCheckBox(package)
                checkbox.setChecked(True)
                uninstalled_checkboxes[package] = checkbox
                uninstalled_scroll_layout.addWidget(checkbox)
            
            uninstalled_scroll_layout.addStretch()
            uninstalled_scroll.setWidget(uninstalled_scroll_widget)
            uninstalled_layout.addWidget(uninstalled_scroll)
            
            tab_widget.addTab(uninstalled_widget, f"Uninstalled ({len(uninstalled_packages)})")
        
        # Select all / Deselect all buttons
        if disabled_packages or uninstalled_packages:
            button_frame_top = QHBoxLayout()
            
            def select_all_disabled():
                for cb in disabled_checkboxes.values():
                    cb.setChecked(True)
            
            def deselect_all_disabled():
                for cb in disabled_checkboxes.values():
                    cb.setChecked(False)
            
            def select_all_uninstalled():
                for cb in uninstalled_checkboxes.values():
                    cb.setChecked(True)
            
            def deselect_all_uninstalled():
                for cb in uninstalled_checkboxes.values():
                    cb.setChecked(False)
            
            if disabled_packages:
                select_all_disabled_btn = QPushButton("Select All Disabled")
                select_all_disabled_btn.clicked.connect(select_all_disabled)
                button_frame_top.addWidget(select_all_disabled_btn)
                
                deselect_all_disabled_btn = QPushButton("Deselect All Disabled")
                deselect_all_disabled_btn.clicked.connect(deselect_all_disabled)
                button_frame_top.addWidget(deselect_all_disabled_btn)
            
            if uninstalled_packages:
                select_all_uninstalled_btn = QPushButton("Select All Uninstalled")
                select_all_uninstalled_btn.clicked.connect(select_all_uninstalled)
                button_frame_top.addWidget(select_all_uninstalled_btn)
                
                deselect_all_uninstalled_btn = QPushButton("Deselect All Uninstalled")
                deselect_all_uninstalled_btn.clicked.connect(deselect_all_uninstalled)
                button_frame_top.addWidget(deselect_all_uninstalled_btn)
            
            button_frame_top.addStretch()
            layout.addLayout(button_frame_top)
        
        def do_restore():
            # Get selected packages
            selected_disabled = [pkg for pkg, cb in disabled_checkboxes.items() if cb.isChecked()]
            selected_uninstalled = [pkg for pkg, cb in uninstalled_checkboxes.items() if cb.isChecked()]
            
            if not selected_disabled and not selected_uninstalled:
                QMessageBox.warning(dialog, "No Selection", "Please select at least one package to restore.")
                return
            
            dialog.accept()
            
            total = len(selected_disabled) + len(selected_uninstalled)
            reply = QMessageBox.question(self, "Confirm Restore", f"Restore {total} package(s)?\n\n"
                                                          f"Disabled: {len(selected_disabled)}\n"
                                                          f"Uninstalled: {len(selected_uninstalled)}\n\n"
                                                                  f"Uninstalled packages will be reinstalled for your user account.",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            self.log(f"Restoring {total} packages...")
            self.update_status("Restoring packages...")
            
            def do_restore_work():
                restored_packages = []
                failed = []
                
                # Combine all selected packages and try both methods for each
                all_packages = selected_disabled + selected_uninstalled
                
                for i, package in enumerate(all_packages):
                    self.log(f"Restoring {i+1}/{len(all_packages)}: {package}")
                    restored = False
                    errors = []
                    
                    # Try install-existing first (for uninstalled packages)
                    result1 = self.adb.run_command(f"{self.get_device_flag()} shell pm install-existing {package}")
                    if result1['success']:
                        # Command succeeded, mark as restored
                        restored_packages.append(package)
                        output = result1['stdout'].strip() if result1['stdout'] else ''
                        self.log(f"Reinstalled: {package} (output: {output})")
                        restored = True
                    else:
                        errors.append(f"install-existing: {result1.get('stderr', result1.get('stdout', 'Unknown error'))}")
                    
                    # Also try enable (for disabled packages) - try this regardless
                    if not restored:
                        result2 = self.adb.run_command(f"{self.get_device_flag()} shell pm enable {package}")
                        if result2['success']:
                            restored_packages.append(package)
                            self.log(f"Enabled: {package}")
                            restored = True
                        else:
                            errors.append(f"enable: {result2.get('stderr', result2.get('stdout', 'Unknown error'))}")
                    
                    if not restored:
                        error_msg = " | ".join(errors) if errors else 'Unknown error'
                        failed.append((package, error_msg))
                        self.log(f"Failed to restore {package}: {error_msg}", "ERROR")
                
                # Update state - remove only restored packages
                if restored_packages:
                    # Remove from disabled list
                    remaining_disabled = [pkg for pkg in self.degoogle_state[device_id].get('disabled', []) if pkg not in restored_packages]
                    if remaining_disabled:
                        self.degoogle_state[device_id]['disabled'] = remaining_disabled
                    else:
                        if 'disabled' in self.degoogle_state[device_id]:
                            del self.degoogle_state[device_id]['disabled']
                    
                    # Remove from uninstalled list
                    remaining_uninstalled = [pkg for pkg in self.degoogle_state[device_id].get('uninstalled', []) if pkg not in restored_packages]
                    if remaining_uninstalled:
                        self.degoogle_state[device_id]['uninstalled'] = remaining_uninstalled
                    else:
                        if 'uninstalled' in self.degoogle_state[device_id]:
                            del self.degoogle_state[device_id]['uninstalled']
                
                # Clean up empty state
                if not self.degoogle_state[device_id].get('disabled') and not self.degoogle_state[device_id].get('uninstalled'):
                    # Only remove if no other state exists
                    if len(self.degoogle_state[device_id]) <= 2:  # Only timestamp and action left
                        del self.degoogle_state[device_id]
                
                self.save_degoogle_state()
                
                result_msg = f"Restore completed!\n\n"
                result_msg += f"Restored: {len(restored_packages)} packages\n"
                if failed:
                    result_msg += f"Failed: {len(failed)} packages\n"
                
                self.update_status("Restore completed")
                # Thread-safe messagebox - use QTimer to call from main thread
                QTimer.singleShot(0, lambda: QMessageBox.information(self, "Restore Complete", result_msg))
            
            threading.Thread(target=do_restore_work, daemon=True).start()
        
        # Buttons
        button_frame = QHBoxLayout()
        button_frame.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        button_frame.addWidget(cancel_btn)
        
        restore_btn = QPushButton("Restore Selected")
        restore_btn.clicked.connect(do_restore)
        button_frame.addWidget(restore_btn)
        
        layout.addLayout(button_frame)
        
        # Show dialog
        dialog.exec()


def main():
    app = QApplication(sys.argv)
    window = ADBGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
