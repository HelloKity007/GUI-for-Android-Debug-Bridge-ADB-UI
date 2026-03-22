"""
JADX Decompiler Extension for ADB GUI
基于 jadx-gui-ai 的反编译工具集成
https://github.com/cncsnet1/jadx-gui-ai

功能:
- 单独启动JADX-GUI-AI反编译工具
- 从App列表拉取APK并自动反编译
- 管理反编译项目
"""

import os
import sys
import subprocess
import threading
import shutil
import json
from datetime import datetime

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QListWidget, QListWidgetItem, QFileDialog,
    QMessageBox, QGroupBox, QProgressBar, QComboBox, QTabWidget, QWidget,
    QTreeWidget, QTreeWidgetItem, QSplitter, QFrame, QCheckBox, QMenu
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer
from PySide6.QtGui import QFont, QColor, QAction

# PyQt6 兼容别名
pyqtSignal = Signal


class JadxWorker(QThread):
    """后台JADX操作工作线程"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, jadx_path, apk_path, output_dir, use_gui=False):
        super().__init__()
        self.jadx_path = jadx_path
        self.apk_path = apk_path
        self.output_dir = output_dir
        self.use_gui = use_gui
        self.process = None
    
    def run(self):
        try:
            if self.use_gui:
                # 启动JADX GUI
                self.progress.emit(f"启动 JADX-GUI-AI: {self.apk_path}")
                
                # 如果是exe直接启动
                if self.jadx_path.endswith('.exe'):
                    cmd = [self.jadx_path, self.apk_path]
                elif sys.platform == 'win32':
                    # 查找可用的GUI启动方式
                    jadx_dir = os.path.dirname(self.jadx_path)
                    gui_exe = os.path.join(jadx_dir, 'jadx-gui-dev.exe')
                    gui_bat = os.path.join(jadx_dir, 'jadx-gui.bat')
                    
                    if os.path.exists(gui_exe):
                        cmd = [gui_exe, self.apk_path]
                    elif os.path.exists(gui_bat):
                        cmd = [gui_bat, self.apk_path]
                    else:
                        cmd = [self.jadx_path, self.apk_path]
                else:
                    cmd = [self.jadx_path.replace('jadx', 'jadx-gui'), self.apk_path]
                
                subprocess.Popen(cmd)
                self.finished.emit(True, "JADX-GUI 已启动")
            else:
                # 命令行反编译
                self.progress.emit(f"开始反编译: {self.apk_path}")
                self.progress.emit(f"输出目录: {self.output_dir}")
                
                cmd = [self.jadx_path, '-d', self.output_dir, self.apk_path]
                
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                )
                
                for line in self.process.stdout:
                    self.progress.emit(line.strip())
                
                self.process.wait()
                
                if self.process.returncode == 0:
                    self.finished.emit(True, f"反编译完成: {self.output_dir}")
                else:
                    self.finished.emit(False, f"反编译失败,返回码: {self.process.returncode}")
                    
        except Exception as e:
            self.finished.emit(False, f"错误: {str(e)}")
    
    def stop(self):
        if self.process:
            self.process.terminate()


class ApkPullWorker(QThread):
    """APK拉取工作线程"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, adb_path, device_id, package_name, output_path):
        super().__init__()
        self.adb_path = adb_path
        self.device_id = device_id
        self.package_name = package_name
        self.output_path = output_path
    
    def run(self):
        try:
            # 获取APK路径
            self.progress.emit(f"获取 {self.package_name} 的APK路径...")
            
            cmd = [self.adb_path]
            if self.device_id:
                cmd.extend(['-s', self.device_id])
            cmd.extend(['shell', 'pm', 'path', self.package_name])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0 or not result.stdout.strip():
                self.finished.emit(False, f"无法获取APK路径: {result.stderr}")
                return
            
            # 解析APK路径 (格式: package:/path/to/app.apk)
            apk_paths = []
            for line in result.stdout.strip().split('\n'):
                if line.startswith('package:'):
                    apk_paths.append(line.replace('package:', '').strip())
            
            if not apk_paths:
                self.finished.emit(False, "未找到APK路径")
                return
            
            # 拉取主APK
            main_apk = apk_paths[0]
            self.progress.emit(f"拉取APK: {main_apk}")
            
            cmd = [self.adb_path]
            if self.device_id:
                cmd.extend(['-s', self.device_id])
            cmd.extend(['pull', main_apk, self.output_path])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                self.progress.emit(f"APK已保存到: {self.output_path}")
                
                # 如果有split APKs,也拉取
                if len(apk_paths) > 1:
                    split_dir = os.path.join(os.path.dirname(self.output_path), 'splits')
                    os.makedirs(split_dir, exist_ok=True)
                    
                    for i, split_apk in enumerate(apk_paths[1:], 1):
                        self.progress.emit(f"拉取Split APK {i}: {split_apk}")
                        split_name = f"split_{i}.apk"
                        split_output = os.path.join(split_dir, split_name)
                        
                        cmd = [self.adb_path]
                        if self.device_id:
                            cmd.extend(['-s', self.device_id])
                        cmd.extend(['pull', split_apk, split_output])
                        subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                
                self.finished.emit(True, self.output_path)
            else:
                self.finished.emit(False, f"拉取失败: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            self.finished.emit(False, "操作超时")
        except Exception as e:
            self.finished.emit(False, f"错误: {str(e)}")


class JadxDecompilerDialog(QDialog):
    """JADX反编译工具对话框"""
    
    def __init__(self, parent=None, adb_path='adb', device_id=None, 
                 package_name=None, dark_mode=False, colors=None):
        super().__init__(parent)
        self.adb_path = adb_path
        self.device_id = device_id
        self.package_name = package_name
        self.dark_mode = dark_mode
        self.colors = colors or {}
        
        # 路径配置
        self.project_dir = os.path.dirname(os.path.abspath(__file__))
        self.jadx_dir = os.path.join(self.project_dir, 'extension', 'jadx_decompiler')
        self.apk_cache_dir = os.path.join(self.jadx_dir, 'apk_cache')
        self.decompiled_dir = os.path.join(self.jadx_dir, 'decompiled')
        self.projects_file = os.path.join(self.jadx_dir, 'projects.json')
        
        # 确保目录存在
        os.makedirs(self.apk_cache_dir, exist_ok=True)
        os.makedirs(self.decompiled_dir, exist_ok=True)
        
        # JADX路径
        self.jadx_path = self._find_jadx()
        
        # 项目列表
        self.projects = self._load_projects()
        
        # 工作线程
        self.worker = None
        self.pull_worker = None
        
        self.init_ui()
        self.apply_theme()
        
        # 如果指定了包名,自动开始处理
        if self.package_name:
            QTimer.singleShot(100, self._auto_decompile_package)
    
    def _find_jadx(self):
        """查找JADX可执行文件"""
        # 检查extension目录下的jadx - 优先exe
        jadx_locations = [
            os.path.join(self.jadx_dir, 'jadx-gui-dev.exe'),  # jadx-gui-ai exe
            os.path.join(self.jadx_dir, 'jadx-gui.exe'),
            os.path.join(self.jadx_dir, 'bin', 'jadx-gui.bat'),
            os.path.join(self.jadx_dir, 'bin', 'jadx.bat'),
            os.path.join(self.jadx_dir, 'bin', 'jadx'),
            os.path.join(self.jadx_dir, 'jadx.bat'),
            os.path.join(self.jadx_dir, 'jadx'),
        ]
        
        for path in jadx_locations:
            if os.path.exists(path):
                return path
        
        # 检查系统PATH
        try:
            if sys.platform == 'win32':
                result = subprocess.run(['where', 'jadx'], capture_output=True, text=True, timeout=5)
            else:
                result = subprocess.run(['which', 'jadx'], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().split('\n')[0]
        except:
            pass
        
        return None
    
    def _load_projects(self):
        """加载项目列表"""
        if os.path.exists(self.projects_file):
            try:
                with open(self.projects_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return []
    
    def _save_projects(self):
        """保存项目列表"""
        try:
            with open(self.projects_file, 'w', encoding='utf-8') as f:
                json.dump(self.projects, f, indent=2, ensure_ascii=False)
        except:
            pass
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("🔍 JADX 反编译工具")
        self.setMinimumSize(900, 700)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # 标题
        title = QLabel("🔍 JADX-GUI-AI 反编译工具")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # JADX状态
        status_layout = QHBoxLayout()
        self.jadx_status = QLabel()
        self._update_jadx_status()
        status_layout.addWidget(self.jadx_status)
        status_layout.addStretch()
        
        btn_config_jadx = QPushButton("⚙️ 配置JADX路径")
        btn_config_jadx.clicked.connect(self.configure_jadx_path)
        status_layout.addWidget(btn_config_jadx)
        
        btn_download = QPushButton("📥 下载JADX-GUI-AI")
        btn_download.clicked.connect(self.open_download_page)
        status_layout.addWidget(btn_download)
        
        layout.addLayout(status_layout)
        
        # 主选项卡
        tabs = QTabWidget()
        
        # Tab 1: 快速反编译
        quick_tab = self._create_quick_tab()
        tabs.addTab(quick_tab, "🚀 快速反编译")
        
        # Tab 2: 项目管理
        projects_tab = self._create_projects_tab()
        tabs.addTab(projects_tab, "📁 项目管理")
        
        # Tab 3: 从设备拉取
        device_tab = self._create_device_tab()
        tabs.addTab(device_tab, "📱 从设备拉取")
        
        layout.addWidget(tabs)
        
        # 日志输出
        log_group = QGroupBox("📝 操作日志")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        log_layout.addWidget(self.progress_bar)
        
        layout.addWidget(log_group)
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_launch_gui = QPushButton("🚀 启动 JADX-GUI-AI")
        btn_launch_gui.clicked.connect(self.launch_jadx_gui)
        btn_layout.addWidget(btn_launch_gui)
        
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.close)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)
    
    def _create_quick_tab(self):
        """创建快速反编译选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # APK文件选择
        file_group = QGroupBox("选择APK文件")
        file_layout = QGridLayout(file_group)
        
        file_layout.addWidget(QLabel("APK文件:"), 0, 0)
        self.apk_path_edit = QLineEdit()
        self.apk_path_edit.setPlaceholderText("选择或拖放APK文件...")
        file_layout.addWidget(self.apk_path_edit, 0, 1)
        
        btn_browse = QPushButton("浏览...")
        btn_browse.clicked.connect(self.browse_apk)
        file_layout.addWidget(btn_browse, 0, 2)
        
        file_layout.addWidget(QLabel("输出目录:"), 1, 0)
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setText(self.decompiled_dir)
        file_layout.addWidget(self.output_dir_edit, 1, 1)
        
        btn_browse_output = QPushButton("浏览...")
        btn_browse_output.clicked.connect(self.browse_output_dir)
        file_layout.addWidget(btn_browse_output, 1, 2)
        
        layout.addWidget(file_group)
        
        # 反编译选项
        options_group = QGroupBox("反编译选项")
        options_layout = QVBoxLayout(options_group)
        
        self.cb_use_gui = QCheckBox("使用GUI界面打开 (推荐)")
        self.cb_use_gui.setChecked(True)
        options_layout.addWidget(self.cb_use_gui)
        
        self.cb_save_project = QCheckBox("保存到项目列表")
        self.cb_save_project.setChecked(True)
        options_layout.addWidget(self.cb_save_project)
        
        layout.addWidget(options_group)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_decompile = QPushButton("🔧 开始反编译")
        self.btn_decompile.clicked.connect(self.start_decompile)
        btn_layout.addWidget(self.btn_decompile)
        
        layout.addLayout(btn_layout)
        layout.addStretch()
        
        return tab
    
    def _create_projects_tab(self):
        """创建项目管理选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 项目列表
        self.projects_list = QListWidget()
        self.projects_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.projects_list.customContextMenuRequested.connect(self._show_project_context_menu)
        self.projects_list.itemDoubleClicked.connect(self._open_project)
        self._refresh_projects_list()
        layout.addWidget(self.projects_list)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        
        btn_refresh = QPushButton("🔄 刷新")
        btn_refresh.clicked.connect(self._refresh_projects_list)
        btn_layout.addWidget(btn_refresh)
        
        btn_open = QPushButton("📂 打开选中项目")
        btn_open.clicked.connect(lambda: self._open_project(self.projects_list.currentItem()))
        btn_layout.addWidget(btn_open)
        
        btn_open_folder = QPushButton("📁 打开目录")
        btn_open_folder.clicked.connect(self._open_project_folder)
        btn_layout.addWidget(btn_open_folder)
        
        btn_delete = QPushButton("🗑️ 删除项目")
        btn_delete.clicked.connect(self._delete_project)
        btn_layout.addWidget(btn_delete)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        return tab
    
    def _create_device_tab(self):
        """创建从设备拉取选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 设备信息
        device_group = QGroupBox("设备信息")
        device_layout = QGridLayout(device_group)
        
        device_layout.addWidget(QLabel("设备ID:"), 0, 0)
        self.device_id_label = QLabel(self.device_id or "未连接")
        device_layout.addWidget(self.device_id_label, 0, 1)
        
        layout.addWidget(device_group)
        
        # 应用选择
        app_group = QGroupBox("选择应用")
        app_layout = QVBoxLayout(app_group)
        
        search_layout = QHBoxLayout()
        self.app_search = QLineEdit()
        self.app_search.setPlaceholderText("搜索应用包名...")
        self.app_search.textChanged.connect(self._filter_apps)
        search_layout.addWidget(self.app_search)
        
        btn_refresh_apps = QPushButton("🔄 刷新应用列表")
        btn_refresh_apps.clicked.connect(self._load_device_apps)
        search_layout.addWidget(btn_refresh_apps)
        
        app_layout.addLayout(search_layout)
        
        # 应用列表
        self.apps_list = QListWidget()
        self.apps_list.itemDoubleClicked.connect(self._pull_and_decompile_app)
        app_layout.addWidget(self.apps_list)
        
        # 只显示第三方应用
        self.cb_third_party = QCheckBox("只显示第三方应用")
        self.cb_third_party.setChecked(True)
        self.cb_third_party.stateChanged.connect(self._load_device_apps)
        app_layout.addWidget(self.cb_third_party)
        
        layout.addWidget(app_group)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_pull = QPushButton("📥 拉取并反编译")
        btn_pull.clicked.connect(lambda: self._pull_and_decompile_app(self.apps_list.currentItem()))
        btn_layout.addWidget(btn_pull)
        
        layout.addLayout(btn_layout)
        
        # 自动加载应用列表
        if self.device_id:
            QTimer.singleShot(500, self._load_device_apps)
        
        return tab
    
    def _update_jadx_status(self):
        """更新JADX状态显示"""
        if self.jadx_path and os.path.exists(self.jadx_path):
            self.jadx_status.setText(f"✅ JADX已配置: {self.jadx_path}")
            self.jadx_status.setStyleSheet("color: green;")
        else:
            self.jadx_status.setText("❌ JADX未配置 - 请下载并配置JADX-GUI-AI")
            self.jadx_status.setStyleSheet("color: red;")
    
    def configure_jadx_path(self):
        """配置JADX路径"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择JADX可执行文件",
            self.jadx_dir,
            "可执行文件 (jadx.bat jadx jadx-gui.bat jadx-gui);;所有文件 (*.*)"
        )
        
        if path:
            self.jadx_path = path
            self._update_jadx_status()
            self.log(f"JADX路径已设置: {path}")
    
    def open_download_page(self):
        """打开下载页面"""
        import webbrowser
        webbrowser.open("https://github.com/cncsnet1/jadx-gui-ai/releases")
        self.log("已打开JADX-GUI-AI下载页面")
        self.log(f"请下载后解压到: {self.jadx_dir}")
    
    def browse_apk(self):
        """浏览选择APK文件"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择APK文件",
            self.apk_cache_dir,
            "APK文件 (*.apk);;所有文件 (*.*)"
        )
        
        if path:
            self.apk_path_edit.setText(path)
            
            # 自动设置输出目录
            apk_name = os.path.splitext(os.path.basename(path))[0]
            output_dir = os.path.join(self.decompiled_dir, apk_name)
            self.output_dir_edit.setText(output_dir)
    
    def browse_output_dir(self):
        """浏览选择输出目录"""
        path = QFileDialog.getExistingDirectory(
            self, "选择输出目录",
            self.decompiled_dir
        )
        
        if path:
            self.output_dir_edit.setText(path)
    
    def start_decompile(self):
        """开始反编译"""
        apk_path = self.apk_path_edit.text().strip()
        output_dir = self.output_dir_edit.text().strip()
        
        if not apk_path:
            QMessageBox.warning(self, "警告", "请选择APK文件")
            return
        
        if not os.path.exists(apk_path):
            QMessageBox.warning(self, "警告", f"APK文件不存在: {apk_path}")
            return
        
        if not self.jadx_path or not os.path.exists(self.jadx_path):
            QMessageBox.warning(self, "警告", "请先配置JADX路径")
            return
        
        use_gui = self.cb_use_gui.isChecked()
        
        # 保存项目信息
        if self.cb_save_project.isChecked():
            project_info = {
                'name': os.path.splitext(os.path.basename(apk_path))[0],
                'apk_path': apk_path,
                'output_dir': output_dir,
                'created_at': datetime.now().isoformat(),
                'package_name': ''
            }
            self.projects.append(project_info)
            self._save_projects()
            self._refresh_projects_list()
        
        # 启动反编译
        self.btn_decompile.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 无限进度
        
        self.worker = JadxWorker(self.jadx_path, apk_path, output_dir, use_gui)
        self.worker.progress.connect(self.log)
        self.worker.finished.connect(self._on_decompile_finished)
        self.worker.start()
    
    def _on_decompile_finished(self, success, message):
        """反编译完成回调"""
        self.btn_decompile.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if success:
            self.log(f"✅ {message}")
            self._refresh_projects_list()
        else:
            self.log(f"❌ {message}")
            QMessageBox.warning(self, "反编译失败", message)
    
    def launch_jadx_gui(self):
        """启动JADX GUI (无文件)"""
        if not self.jadx_path:
            QMessageBox.warning(self, "警告", "请先配置JADX路径")
            return
        
        try:
            # 如果jadx_path本身就是exe，直接使用
            if self.jadx_path.endswith('.exe'):
                subprocess.Popen([self.jadx_path])
                self.log("✅ JADX-GUI-AI 已启动")
                return
            
            # 查找GUI启动脚本
            jadx_dir = os.path.dirname(self.jadx_path)
            
            if sys.platform == 'win32':
                gui_candidates = [
                    os.path.join(jadx_dir, 'jadx-gui-dev.exe'),
                    os.path.join(jadx_dir, 'jadx-gui.exe'),
                    os.path.join(jadx_dir, 'jadx-gui.bat'),
                    os.path.join(jadx_dir, 'jadx-gui-ai.bat'),
                ]
            else:
                gui_candidates = [
                    os.path.join(jadx_dir, 'jadx-gui'),
                    os.path.join(jadx_dir, 'jadx-gui-ai'),
                ]
            
            gui_path = None
            for candidate in gui_candidates:
                if os.path.exists(candidate):
                    gui_path = candidate
                    break
            
            if gui_path:
                subprocess.Popen([gui_path])
                self.log("✅ JADX-GUI-AI 已启动")
            else:
                self.log("❌ 未找到JADX-GUI启动脚本")
                QMessageBox.warning(self, "警告", "未找到JADX-GUI启动脚本")
                
        except Exception as e:
            self.log(f"❌ 启动失败: {str(e)}")
    
    def _refresh_projects_list(self):
        """刷新项目列表"""
        self.projects_list.clear()
        self.projects = self._load_projects()
        
        for project in self.projects:
            item = QListWidgetItem()
            item.setText(f"📦 {project['name']} - {project.get('created_at', 'Unknown')[:10]}")
            item.setData(Qt.ItemDataRole.UserRole, project)
            self.projects_list.addItem(item)
    
    def _show_project_context_menu(self, pos):
        """显示项目右键菜单"""
        item = self.projects_list.itemAt(pos)
        if not item:
            return
        
        menu = QMenu(self)
        
        action_open_gui = menu.addAction("🔍 用JADX-GUI打开")
        action_open_gui.triggered.connect(lambda: self._open_project(item))
        
        action_open_folder = menu.addAction("📁 打开目录")
        action_open_folder.triggered.connect(self._open_project_folder)
        
        menu.addSeparator()
        
        action_delete = menu.addAction("🗑️ 删除项目")
        action_delete.triggered.connect(self._delete_project)
        
        menu.exec(self.projects_list.mapToGlobal(pos))
    
    def _open_project(self, item):
        """打开项目"""
        if not item:
            return
        
        project = item.data(Qt.ItemDataRole.UserRole)
        apk_path = project.get('apk_path', '')
        
        if not apk_path or not os.path.exists(apk_path):
            QMessageBox.warning(self, "警告", f"APK文件不存在: {apk_path}")
            return
        
        if not self.jadx_path:
            QMessageBox.warning(self, "警告", "请先配置JADX路径")
            return
        
        # 启动JADX GUI打开APK
        self.worker = JadxWorker(self.jadx_path, apk_path, '', use_gui=True)
        self.worker.progress.connect(self.log)
        self.worker.finished.connect(lambda s, m: self.log(f"{'✅' if s else '❌'} {m}"))
        self.worker.start()
    
    def _open_project_folder(self):
        """打开项目目录"""
        item = self.projects_list.currentItem()
        if not item:
            return
        
        project = item.data(Qt.ItemDataRole.UserRole)
        output_dir = project.get('output_dir', '')
        
        if output_dir and os.path.exists(output_dir):
            if sys.platform == 'win32':
                os.startfile(output_dir)
            else:
                subprocess.run(['xdg-open', output_dir])
        else:
            # 打开APK所在目录
            apk_path = project.get('apk_path', '')
            if apk_path and os.path.exists(os.path.dirname(apk_path)):
                if sys.platform == 'win32':
                    os.startfile(os.path.dirname(apk_path))
    
    def _delete_project(self):
        """删除项目"""
        item = self.projects_list.currentItem()
        if not item:
            return
        
        project = item.data(Qt.ItemDataRole.UserRole)
        
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除项目 '{project['name']}' 吗?\n\n(APK和反编译文件不会被删除)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.projects = [p for p in self.projects if p != project]
            self._save_projects()
            self._refresh_projects_list()
            self.log(f"项目已删除: {project['name']}")
    
    def _load_device_apps(self):
        """加载设备应用列表"""
        if not self.device_id:
            self.log("未连接设备")
            return
        
        self.apps_list.clear()
        self.log("正在加载应用列表...")
        
        try:
            cmd = [self.adb_path, '-s', self.device_id, 'shell', 'pm', 'list', 'packages']
            
            if self.cb_third_party.isChecked():
                cmd.append('-3')
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                packages = []
                for line in result.stdout.strip().split('\n'):
                    if line.startswith('package:'):
                        packages.append(line.replace('package:', '').strip())
                
                packages.sort()
                self.all_packages = packages
                
                for pkg in packages:
                    self.apps_list.addItem(pkg)
                
                self.log(f"已加载 {len(packages)} 个应用")
            else:
                self.log(f"加载失败: {result.stderr}")
                
        except Exception as e:
            self.log(f"错误: {str(e)}")
    
    def _filter_apps(self, text):
        """过滤应用列表"""
        if not hasattr(self, 'all_packages'):
            return
        
        self.apps_list.clear()
        
        for pkg in self.all_packages:
            if text.lower() in pkg.lower():
                self.apps_list.addItem(pkg)
    
    def _pull_and_decompile_app(self, item):
        """拉取并反编译应用"""
        if not item:
            return
        
        package_name = item.text()
        
        if not self.device_id:
            QMessageBox.warning(self, "警告", "未连接设备")
            return
        
        # 设置APK保存路径
        apk_filename = f"{package_name}.apk"
        apk_path = os.path.join(self.apk_cache_dir, apk_filename)
        
        self.log(f"开始拉取: {package_name}")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        # 保存当前要处理的包名
        self._pending_package = package_name
        self._pending_apk_path = apk_path
        
        # 启动拉取工作线程
        self.pull_worker = ApkPullWorker(
            self.adb_path, self.device_id, package_name, apk_path
        )
        self.pull_worker.progress.connect(self.log)
        self.pull_worker.finished.connect(self._on_pull_finished)
        self.pull_worker.start()
    
    def _on_pull_finished(self, success, result):
        """APK拉取完成回调"""
        if success:
            self.log(f"✅ APK拉取成功: {result}")
            
            # 自动用JADX-GUI打开
            if self.jadx_path:
                self.worker = JadxWorker(self.jadx_path, result, '', use_gui=True)
                self.worker.progress.connect(self.log)
                self.worker.finished.connect(self._on_gui_launch_finished)
                self.worker.start()
                
                # 保存到项目列表
                project_info = {
                    'name': self._pending_package,
                    'apk_path': result,
                    'output_dir': os.path.join(self.decompiled_dir, self._pending_package),
                    'created_at': datetime.now().isoformat(),
                    'package_name': self._pending_package
                }
                self.projects.append(project_info)
                self._save_projects()
                self._refresh_projects_list()
            else:
                self.progress_bar.setVisible(False)
                QMessageBox.information(self, "完成", 
                    f"APK已拉取到: {result}\n\n请配置JADX路径后打开")
        else:
            self.progress_bar.setVisible(False)
            self.log(f"❌ {result}")
            QMessageBox.warning(self, "拉取失败", result)
    
    def _on_gui_launch_finished(self, success, message):
        """GUI启动完成回调"""
        self.progress_bar.setVisible(False)
        self.log(f"{'✅' if success else '❌'} {message}")
    
    def _auto_decompile_package(self):
        """自动反编译指定的包"""
        if not self.package_name:
            return
        
        # 填充搜索框并选中
        self.app_search.setText(self.package_name)
        
        # 查找并选中应用
        for i in range(self.apps_list.count()):
            if self.apps_list.item(i).text() == self.package_name:
                self.apps_list.setCurrentRow(i)
                # 自动开始拉取
                QTimer.singleShot(500, lambda: self._pull_and_decompile_app(self.apps_list.currentItem()))
                break
    
    def log(self, message):
        """输出日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        
        # 滚动到底部
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def apply_theme(self):
        """应用主题"""
        if self.dark_mode:
            self.setStyleSheet("""
                QDialog { background-color: #1e1e1e; color: #ffffff; }
                QGroupBox { 
                    border: 1px solid #3c3c3c; 
                    border-radius: 5px; 
                    margin-top: 10px; 
                    padding-top: 10px;
                    color: #ffffff;
                }
                QGroupBox::title { 
                    subcontrol-origin: margin; 
                    left: 10px; 
                    padding: 0 5px;
                }
                QLineEdit, QTextEdit, QListWidget, QTreeWidget {
                    background-color: #2d2d2d;
                    border: 1px solid #3c3c3c;
                    border-radius: 3px;
                    color: #ffffff;
                    padding: 5px;
                }
                QPushButton {
                    background-color: #0e639c;
                    color: white;
                    border: none;
                    padding: 8px 15px;
                    border-radius: 3px;
                }
                QPushButton:hover { background-color: #1177bb; }
                QPushButton:disabled { background-color: #3c3c3c; color: #808080; }
                QTabWidget::pane { border: 1px solid #3c3c3c; }
                QTabBar::tab {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    padding: 8px 15px;
                    border: 1px solid #3c3c3c;
                }
                QTabBar::tab:selected { background-color: #0e639c; }
                QProgressBar {
                    border: 1px solid #3c3c3c;
                    border-radius: 3px;
                    text-align: center;
                }
                QProgressBar::chunk { background-color: #0e639c; }
            """)
        else:
            self.setStyleSheet("""
                QGroupBox { 
                    border: 1px solid #cccccc; 
                    border-radius: 5px; 
                    margin-top: 10px; 
                    padding-top: 10px;
                }
                QGroupBox::title { 
                    subcontrol-origin: margin; 
                    left: 10px; 
                    padding: 0 5px;
                }
                QPushButton {
                    background-color: #0078d4;
                    color: white;
                    border: none;
                    padding: 8px 15px;
                    border-radius: 3px;
                }
                QPushButton:hover { background-color: #106ebe; }
                QPushButton:disabled { background-color: #cccccc; color: #666666; }
            """)
    
    def closeEvent(self, event):
        """关闭事件"""
        # 停止工作线程
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        
        if self.pull_worker and self.pull_worker.isRunning():
            self.pull_worker.wait()
        
        event.accept()


# 用于独立运行
if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    dialog = JadxDecompilerDialog()
    dialog.show()
    sys.exit(app.exec())

