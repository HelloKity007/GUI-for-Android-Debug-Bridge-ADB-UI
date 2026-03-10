# -*- coding: utf-8 -*-
"""
App Manager Dialog for ADB GUI
"""
import os
import threading
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QLineEdit, QMessageBox, QMenu, QCheckBox,
    QProgressDialog
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont


class AppManagerDialog(QDialog):
    """App list manager with advanced features"""
    
    app_list_ready = pyqtSignal(list)
    
    def __init__(self, parent, adb, device_id, colors):
        super().__init__(parent)
        self.adb = adb
        self.device_id = device_id
        self.colors = colors
        self.parent_window = parent
        
        self.setWindowTitle("📱 App List Manager")
        self.setMinimumSize(900, 700)
        self.setup_ui()
        self.refresh_apps()
        
        # Connect signal
        self.app_list_ready.connect(self.update_app_list)
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Top bar with filter and options
        top_layout = QHBoxLayout()
        
        self.show_system_cb = QCheckBox("Show System Apps")
        self.show_system_cb.stateChanged.connect(self.refresh_apps)
        top_layout.addWidget(self.show_system_cb)
        
        top_layout.addWidget(QLabel("🔍 Filter:"))
        
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Search by package name...")
        self.filter_edit.textChanged.connect(self.apply_filter)
        top_layout.addWidget(self.filter_edit)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_apps)
        top_layout.addWidget(refresh_btn)
        
        layout.addLayout(top_layout)
        
        # App list tree
        self.app_tree = QTreeWidget()
        self.app_tree.setHeaderLabels(["Package Name", "Status"])
        self.app_tree.setColumnWidth(0, 500)
        self.app_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.app_tree.customContextMenuRequested.connect(self.show_context_menu)
        self.app_tree.itemDoubleClicked.connect(self.show_app_info)
        layout.addWidget(self.app_tree)
        
        # Status label
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
        # Bottom buttons
        bottom_layout = QHBoxLayout()
        
        info_btn = QPushButton("ℹ️ App Info")
        info_btn.clicked.connect(lambda: self.show_app_info(self.app_tree.currentItem()))
        bottom_layout.addWidget(info_btn)
        
        extract_btn = QPushButton("📦 Extract APK")
        extract_btn.clicked.connect(lambda: self.extract_apk(self.app_tree.currentItem()))
        bottom_layout.addWidget(extract_btn)
        
        run_btn = QPushButton("▶️ Run App")
        run_btn.clicked.connect(lambda: self.run_app(self.app_tree.currentItem()))
        bottom_layout.addWidget(run_btn)
        
        clear_btn = QPushButton("🗑️ Clear Data")
        clear_btn.clicked.connect(lambda: self.clear_app_data(self.app_tree.currentItem()))
        bottom_layout.addWidget(clear_btn)
        
        bottom_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        bottom_layout.addWidget(close_btn)
        
        layout.addLayout(bottom_layout)
    
    def refresh_apps(self):
        """Refresh app list"""
        self.app_tree.clear()
        self.status_label.setText("Loading apps...")
        
        show_system = self.show_system_cb.isChecked()
        
        def do_list():
            # Get app list
            flag = "-s" if show_system else "-3"
            result = self.adb.run_command(f"-s {self.device_id} shell pm list packages {flag}")
            
            if result['success']:
                apps = []
                for line in result['stdout'].strip().split('\n'):
                    if line.strip().startswith('package:'):
                        package = line.strip().replace('package:', '')
                        apps.append(package)
                
                self.app_list_ready.emit(sorted(apps))
            else:
                QTimer.singleShot(0, lambda: QMessageBox.warning(
                    self, "Error", f"Failed to list apps:\n{result.get('stderr', 'Unknown error')}"
                ))
                QTimer.singleShot(0, lambda: self.status_label.setText("Error loading apps"))
        
        threading.Thread(target=do_list, daemon=True).start()
    
    def update_app_list(self, apps):
        """Update app tree (thread-safe)"""
        self.app_tree.clear()
        
        for package in apps:
            item = QTreeWidgetItem([package, ""])
            self.app_tree.addTopLevelItem(item)
        
        self.status_label.setText(f"Loaded {len(apps)} apps")
        self.apply_filter()
    
    def apply_filter(self):
        """Apply search filter"""
        filter_text = self.filter_edit.text().lower()
        
        visible_count = 0
        for i in range(self.app_tree.topLevelItemCount()):
            item = self.app_tree.topLevelItem(i)
            package = item.text(0).lower()
            
            if filter_text in package:
                item.setHidden(False)
                visible_count += 1
            else:
                item.setHidden(True)
        
        if filter_text:
            self.status_label.setText(f"Showing {visible_count} apps (filtered)")
    
    def show_context_menu(self, position):
        """Show context menu"""
        item = self.app_tree.itemAt(position)
        if not item:
            return
        
        menu = QMenu()
        
        info_action = menu.addAction("ℹ️ App Info")
        path_action = menu.addAction("📂 Show APK Path")
        extract_action = menu.addAction("📦 Extract APK")
        decompile_action = menu.addAction("🔍 Decompile with JADX")
        menu.addSeparator()
        run_action = menu.addAction("▶️ Run App")
        stop_action = menu.addAction("⏹️ Force Stop")
        clear_action = menu.addAction("🗑️ Clear Data")
        uninstall_action = menu.addAction("❌ Uninstall")
        
        action = menu.exec(self.app_tree.mapToGlobal(position))
        
        if action == info_action:
            self.show_app_info(item)
        elif action == path_action:
            self.show_apk_path(item)
        elif action == extract_action:
            self.extract_apk(item)
        elif action == decompile_action:
            self.decompile_app(item)
        elif action == run_action:
            self.run_app(item)
        elif action == stop_action:
            self.force_stop(item)
        elif action == clear_action:
            self.clear_app_data(item)
        elif action == uninstall_action:
            self.uninstall_app(item)
    
    def show_app_info(self, item):
        """Show detailed app information"""
        if not item:
            return
        
        package = item.text(0)
        
        def do_info():
            result = self.adb.run_command(f"-s {self.device_id} shell dumpsys package {package}")
            
            if result['success']:
                info = result['stdout']
                
                # Extract key information
                version_name = ""
                version_code = ""
                install_time = ""
                
                for line in info.split('\n'):
                    if 'versionName=' in line:
                        version_name = line.split('versionName=')[1].split()[0] if 'versionName=' in line else ""
                    elif 'versionCode=' in line:
                        version_code = line.split('versionCode=')[1].split()[0] if 'versionCode=' in line else ""
                    elif 'firstInstallTime=' in line:
                        install_time = line.split('firstInstallTime=')[1].strip() if 'firstInstallTime=' in line else ""
                
                info_text = f"Package: {package}\n\n"
                if version_name:
                    info_text += f"Version Name: {version_name}\n"
                if version_code:
                    info_text += f"Version Code: {version_code}\n"
                if install_time:
                    info_text += f"Install Time: {install_time}\n"
                
                QTimer.singleShot(0, lambda: QMessageBox.information(
                    self, "App Info", info_text
                ))
            else:
                QTimer.singleShot(0, lambda: QMessageBox.warning(
                    self, "Error", f"Failed to get app info:\n{result.get('stderr', 'Unknown error')}"
                ))
        
        threading.Thread(target=do_info, daemon=True).start()
    
    def show_apk_path(self, item):
        """Show APK file path"""
        if not item:
            return
        
        package = item.text(0)
        
        def do_path():
            result = self.adb.run_command(f"-s {self.device_id} shell pm path {package}")
            
            if result['success']:
                path = result['stdout'].strip().replace('package:', '')
                QTimer.singleShot(0, lambda: QMessageBox.information(
                    self, "APK Path", f"Package: {package}\n\nPath: {path}"
                ))
            else:
                QTimer.singleShot(0, lambda: QMessageBox.warning(
                    self, "Error", f"Failed to get APK path:\n{result.get('stderr', 'Unknown error')}"
                ))
        
        threading.Thread(target=do_path, daemon=True).start()
    
    def extract_apk(self, item):
        """Extract APK file to computer"""
        if not item:
            return
        
        package = item.text(0)
        
        def do_extract():
            # Get APK path
            result = self.adb.run_command(f"-s {self.device_id} shell pm path {package}")
            if not result['success']:
                QTimer.singleShot(0, lambda: QMessageBox.warning(
                    self, "Error", "Failed to get APK path"
                ))
                return
            
            apk_path = result['stdout'].strip().replace('package:', '')
            
            # Pull APK
            project_dir = getattr(self.parent_window, 'project_dir', os.getcwd())
            apks_dir = os.path.join(project_dir, 'apks')
            os.makedirs(apks_dir, exist_ok=True)
            
            local_path = os.path.join(apks_dir, f"{package}.apk")
            
            result = self.adb.run_command(f'-s {self.device_id} pull "{apk_path}" "{local_path}"')
            
            if result['success']:
                QTimer.singleShot(0, lambda: QMessageBox.information(
                    self, "Success", f"APK extracted to:\n{local_path}"
                ))
            else:
                QTimer.singleShot(0, lambda: QMessageBox.warning(
                    self, "Error", f"Failed to extract APK:\n{result.get('stderr', 'Unknown error')}"
                ))
        
        threading.Thread(target=do_extract, daemon=True).start()
    
    def run_app(self, item):
        """Run/Launch app"""
        if not item:
            return
        
        package = item.text(0)
        
        def do_run():
            result = self.adb.run_command(
                f"-s {self.device_id} shell monkey -p {package} -c android.intent.category.LAUNCHER 1"
            )
            
            if result['success']:
                QTimer.singleShot(0, lambda: self.status_label.setText(f"Launched: {package}"))
            else:
                QTimer.singleShot(0, lambda: QMessageBox.warning(
                    self, "Error", f"Failed to launch app:\n{result.get('stderr', 'Unknown error')}"
                ))
        
        threading.Thread(target=do_run, daemon=True).start()
    
    def force_stop(self, item):
        """Force stop app"""
        if not item:
            return
        
        package = item.text(0)
        
        def do_stop():
            result = self.adb.run_command(f"-s {self.device_id} shell am force-stop {package}")
            
            if result['success']:
                QTimer.singleShot(0, lambda: self.status_label.setText(f"Stopped: {package}"))
            else:
                QTimer.singleShot(0, lambda: QMessageBox.warning(
                    self, "Error", f"Failed to stop app:\n{result.get('stderr', 'Unknown error')}"
                ))
        
        threading.Thread(target=do_stop, daemon=True).start()
    
    def clear_app_data(self, item):
        """Clear app data and cache"""
        if not item:
            return
        
        package = item.text(0)
        
        reply = QMessageBox.question(
            self, "Confirm", f"Clear data for {package}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            def do_clear():
                result = self.adb.run_command(f"-s {self.device_id} shell pm clear {package}")
                
                if result['success']:
                    QTimer.singleShot(0, lambda: QMessageBox.information(
                        self, "Success", f"Cleared data for:\n{package}"
                    ))
                else:
                    QTimer.singleShot(0, lambda: QMessageBox.warning(
                        self, "Error", f"Failed to clear data:\n{result.get('stderr', 'Unknown error')}"
                    ))
            
            threading.Thread(target=do_clear, daemon=True).start()
    
    def uninstall_app(self, item):
        """Uninstall app"""
        if not item:
            return
        
        package = item.text(0)
        
        reply = QMessageBox.question(
            self, "Confirm", f"Uninstall {package}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            def do_uninstall():
                result = self.adb.run_command(f"-s {self.device_id} uninstall {package}")
                
                if result['success']:
                    QTimer.singleShot(0, lambda: QMessageBox.information(
                        self, "Success", f"Uninstalled: {package}"
                    ))
                    QTimer.singleShot(100, self.refresh_apps)
                else:
                    QTimer.singleShot(0, lambda: QMessageBox.warning(
                        self, "Error", f"Failed to uninstall:\n{result.get('stderr', 'Unknown error')}"
                    ))
            
            threading.Thread(target=do_uninstall, daemon=True).start()
    
    def decompile_app(self, item):
        """Open JADX decompiler for the selected app"""
        if not item:
            return
        
        package = item.text(0)
        
        # Call parent's show_jadx_decompiler with package name
        if hasattr(self.parent_window, 'show_jadx_decompiler'):
            self.close()  # Close app manager first
            self.parent_window.show_jadx_decompiler(package_name=package)
        else:
            # Fallback: directly open JADX dialog
            try:
                from jadx_decompiler_extension import JadxDecompilerDialog
                dialog = JadxDecompilerDialog(
                    self,
                    adb_path=self.adb.adb_path,
                    device_id=self.device_id,
                    package_name=package,
                    dark_mode=getattr(self.parent_window, 'dark_mode', False),
                    colors=self.colors
                )
                dialog.exec()
            except ImportError:
                QMessageBox.warning(self, "Error", "JADX Decompiler extension not available")
