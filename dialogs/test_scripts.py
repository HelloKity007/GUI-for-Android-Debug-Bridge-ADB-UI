# -*- coding: utf-8 -*-
"""
Android Test Scripts Automation Extension
Based on: https://github.com/gb112211/AndroidTestScripts
"""
import os
import threading
import time
import csv
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QMessageBox, QFileDialog, QGroupBox, QLineEdit,
    QComboBox, QSpinBox, QCheckBox, QTabWidget, QWidget,
    QTableWidget, QTableWidgetItem, QProgressBar
)
from PySide6.QtCore import Qt, QTimer, Signal

# PyQt6 兼容别名
pyqtSignal = Signal


class TestScriptsDialog(QDialog):
    """Android automation test scripts extension"""
    
    log_signal = pyqtSignal(str)
    test_complete = pyqtSignal(str, bool)
    
    def __init__(self, parent, adb, device_id, colors, project_dir):
        super().__init__(parent)
        self.adb = adb
        self.device_id = device_id
        self.colors = colors
        self.project_dir = project_dir
        
        # Test data storage
        self.test_data_dir = os.path.join(project_dir, 'test_data')
        os.makedirs(self.test_data_dir, exist_ok=True)
        
        # Performance monitoring flags
        self.monitoring_active = False
        self.monitor_thread = None
        
        self.setWindowTitle("🧪 Android Test Scripts")
        self.setMinimumSize(900, 700)
        self.setup_ui()
        
        # Connect signals
        self.log_signal.connect(self.append_log)
        self.test_complete.connect(self.on_test_complete)
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Main tabs
        tabs = QTabWidget()
        
        # Tab 1: Batch Operations
        batch_tab = self.create_batch_tab()
        tabs.addTab(batch_tab, "📦 Batch Operations")
        
        # Tab 2: Performance Testing
        perf_tab = self.create_performance_tab()
        tabs.addTab(perf_tab, "⚡ Performance")
        
        # Tab 3: App Info
        info_tab = self.create_app_info_tab()
        tabs.addTab(info_tab, "ℹ️ App Info")
        
        # Tab 4: Media Capture
        media_tab = self.create_media_tab()
        tabs.addTab(media_tab, "📸 Media")
        
        # Tab 5: Log Collection
        log_tab = self.create_log_tab()
        tabs.addTab(log_tab, "📋 Logs")
        
        layout.addWidget(tabs)
        
        # Output console
        console_group = QGroupBox("📊 Console Output")
        console_layout = QVBoxLayout(console_group)
        
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setMaximumHeight(150)
        console_layout.addWidget(self.console)
        
        clear_console_btn = QPushButton("🗑️ Clear Console")
        clear_console_btn.clicked.connect(self.console.clear)
        console_layout.addWidget(clear_console_btn)
        
        layout.addWidget(console_group)
        
        # Bottom buttons
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        
        open_folder_btn = QPushButton("📂 Open Test Data Folder")
        open_folder_btn.clicked.connect(self.open_test_data_folder)
        bottom_layout.addWidget(open_folder_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        bottom_layout.addWidget(close_btn)
        
        layout.addLayout(bottom_layout)
    
    def create_batch_tab(self):
        """Create batch operations tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Batch install group
        install_group = QGroupBox("📦 Batch Install APKs")
        install_layout = QVBoxLayout(install_group)
        
        install_layout.addWidget(QLabel("Select multiple APK files to install"))
        
        install_btn_layout = QHBoxLayout()
        self.batch_install_btn = QPushButton("➕ Select APKs")
        self.batch_install_btn.clicked.connect(self.batch_install_apks)
        install_btn_layout.addWidget(self.batch_install_btn)
        
        self.install_folder_btn = QPushButton("📁 Select Folder")
        self.install_folder_btn.clicked.connect(self.batch_install_from_folder)
        install_btn_layout.addWidget(self.install_folder_btn)
        
        install_layout.addLayout(install_btn_layout)
        layout.addWidget(install_group)
        
        # Batch uninstall group
        uninstall_group = QGroupBox("🗑️ Batch Uninstall Apps")
        uninstall_layout = QVBoxLayout(uninstall_group)
        
        uninstall_layout.addWidget(QLabel("Enter package names (one per line):"))
        
        self.uninstall_text = QTextEdit()
        self.uninstall_text.setPlaceholderText("com.example.app1\ncom.example.app2\n...")
        self.uninstall_text.setMaximumHeight(100)
        uninstall_layout.addWidget(self.uninstall_text)
        
        uninstall_btn = QPushButton("🗑️ Batch Uninstall")
        uninstall_btn.clicked.connect(self.batch_uninstall_apps)
        uninstall_layout.addWidget(uninstall_btn)
        
        layout.addWidget(uninstall_group)
        
        # Backup apps group
        backup_group = QGroupBox("💾 Backup Third-party Apps")
        backup_layout = QVBoxLayout(backup_group)
        
        backup_layout.addWidget(QLabel("Backup all third-party app APKs to local folder"))
        
        backup_btn = QPushButton("💾 Start Backup")
        backup_btn.clicked.connect(self.backup_third_party_apps)
        backup_layout.addWidget(backup_btn)
        
        layout.addWidget(backup_group)
        
        layout.addStretch()
        return tab
    
    def create_performance_tab(self):
        """Create performance testing tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # FPS test group
        fps_group = QGroupBox("📊 FPS & Jankiness Test")
        fps_layout = QVBoxLayout(fps_group)
        
        fps_input_layout = QHBoxLayout()
        fps_input_layout.addWidget(QLabel("Package Name:"))
        self.fps_package_edit = QLineEdit()
        self.fps_package_edit.setPlaceholderText("com.example.app")
        fps_input_layout.addWidget(self.fps_package_edit)
        fps_layout.addLayout(fps_input_layout)
        
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Test Duration (seconds):"))
        self.fps_duration_spin = QSpinBox()
        self.fps_duration_spin.setRange(10, 300)
        self.fps_duration_spin.setValue(60)
        duration_layout.addWidget(self.fps_duration_spin)
        duration_layout.addStretch()
        fps_layout.addLayout(duration_layout)
        
        fps_layout.addWidget(QLabel("Instructions: Start test, then operate the app interface"))
        
        fps_btn = QPushButton("▶️ Start FPS Test")
        fps_btn.clicked.connect(self.start_fps_test)
        fps_layout.addWidget(fps_btn)
        
        layout.addWidget(fps_group)
        
        # CPU/Memory monitoring group
        monitor_group = QGroupBox("🧠 CPU & Memory Monitor")
        monitor_layout = QVBoxLayout(monitor_group)
        
        monitor_input_layout = QHBoxLayout()
        monitor_input_layout.addWidget(QLabel("Package Name:"))
        self.monitor_package_edit = QLineEdit()
        self.monitor_package_edit.setPlaceholderText("com.example.app")
        monitor_input_layout.addWidget(self.monitor_package_edit)
        monitor_layout.addLayout(monitor_input_layout)
        
        samples_layout = QHBoxLayout()
        samples_layout.addWidget(QLabel("Sample Count:"))
        self.monitor_samples_spin = QSpinBox()
        self.monitor_samples_spin.setRange(5, 100)
        self.monitor_samples_spin.setValue(20)
        samples_layout.addWidget(self.monitor_samples_spin)
        samples_layout.addStretch()
        monitor_layout.addLayout(samples_layout)
        
        monitor_btn_layout = QHBoxLayout()
        self.start_monitor_btn = QPushButton("▶️ Start Monitoring")
        self.start_monitor_btn.clicked.connect(self.start_cpu_memory_monitor)
        monitor_btn_layout.addWidget(self.start_monitor_btn)
        
        self.stop_monitor_btn = QPushButton("⏹️ Stop Monitoring")
        self.stop_monitor_btn.clicked.connect(self.stop_cpu_memory_monitor)
        self.stop_monitor_btn.setEnabled(False)
        monitor_btn_layout.addWidget(self.stop_monitor_btn)
        
        monitor_layout.addLayout(monitor_btn_layout)
        
        # Monitor progress
        self.monitor_progress = QProgressBar()
        monitor_layout.addWidget(self.monitor_progress)
        
        layout.addWidget(monitor_group)
        
        layout.addStretch()
        return tab
    
    def create_app_info_tab(self):
        """Create app info tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Current app info group
        current_group = QGroupBox("📱 Current App Info")
        current_layout = QVBoxLayout(current_group)
        
        current_layout.addWidget(QLabel("Get information about the current foreground app"))
        
        current_btn_layout = QHBoxLayout()
        
        package_btn = QPushButton("📦 Get Package Name")
        package_btn.clicked.connect(self.get_current_package)
        current_btn_layout.addWidget(package_btn)
        
        activity_btn = QPushButton("🔲 Get Activity Name")
        activity_btn.clicked.connect(self.get_current_activity)
        current_btn_layout.addWidget(activity_btn)
        
        current_layout.addLayout(current_btn_layout)
        
        apk_btn = QPushButton("📥 Pull Current App APK")
        apk_btn.clicked.connect(self.pull_current_apk)
        current_layout.addWidget(apk_btn)
        
        layout.addWidget(current_group)
        
        # App permissions group
        permission_group = QGroupBox("🔐 App Permissions")
        permission_layout = QVBoxLayout(permission_group)
        
        perm_input_layout = QHBoxLayout()
        perm_input_layout.addWidget(QLabel("Package Name:"))
        self.permission_package_edit = QLineEdit()
        self.permission_package_edit.setPlaceholderText("com.example.app")
        perm_input_layout.addWidget(self.permission_package_edit)
        permission_layout.addLayout(perm_input_layout)
        
        perm_btn = QPushButton("🔍 Get Permissions")
        perm_btn.clicked.connect(self.get_app_permissions)
        permission_layout.addWidget(perm_btn)
        
        layout.addWidget(permission_group)
        
        layout.addStretch()
        return tab
    
    def create_media_tab(self):
        """Create media capture tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Screenshot group
        screenshot_group = QGroupBox("📸 Screenshot")
        screenshot_layout = QVBoxLayout(screenshot_group)
        
        screenshot_layout.addWidget(QLabel("Capture multiple screenshots with custom interval"))
        
        screenshot_settings = QHBoxLayout()
        screenshot_settings.addWidget(QLabel("Count:"))
        self.screenshot_count_spin = QSpinBox()
        self.screenshot_count_spin.setRange(1, 50)
        self.screenshot_count_spin.setValue(1)
        screenshot_settings.addWidget(self.screenshot_count_spin)
        
        screenshot_settings.addWidget(QLabel("Interval (seconds):"))
        self.screenshot_interval_spin = QSpinBox()
        self.screenshot_interval_spin.setRange(1, 60)
        self.screenshot_interval_spin.setValue(5)
        screenshot_settings.addWidget(self.screenshot_interval_spin)
        screenshot_settings.addStretch()
        
        screenshot_layout.addLayout(screenshot_settings)
        
        screenshot_btn = QPushButton("📸 Capture Screenshots")
        screenshot_btn.clicked.connect(self.batch_screenshot)
        screenshot_layout.addWidget(screenshot_btn)
        
        layout.addWidget(screenshot_group)
        
        # Screen recording group
        record_group = QGroupBox("🎥 Screen Recording")
        record_layout = QVBoxLayout(record_group)
        
        record_layout.addWidget(QLabel("Record device screen with custom duration"))
        
        record_settings = QHBoxLayout()
        record_settings.addWidget(QLabel("Duration (seconds):"))
        self.record_duration_spin = QSpinBox()
        self.record_duration_spin.setRange(5, 180)
        self.record_duration_spin.setValue(30)
        record_settings.addWidget(self.record_duration_spin)
        record_settings.addStretch()
        
        record_layout.addLayout(record_settings)
        
        record_btn = QPushButton("🎥 Start Recording")
        record_btn.clicked.connect(self.screen_record)
        record_layout.addWidget(record_btn)
        
        layout.addWidget(record_group)
        
        layout.addStretch()
        return tab
    
    def create_log_tab(self):
        """Create log collection tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Crash log group
        crash_group = QGroupBox("💥 Crash Log Collection")
        crash_layout = QVBoxLayout(crash_group)
        
        crash_layout.addWidget(QLabel("Extract crash logs from device"))
        
        crash_btn = QPushButton("📥 Get Crash Logs")
        crash_btn.clicked.connect(self.get_crash_logs)
        crash_layout.addWidget(crash_btn)
        
        layout.addWidget(crash_group)
        
        # Logcat with filter
        logcat_group = QGroupBox("📋 Filtered Logcat")
        logcat_layout = QVBoxLayout(logcat_group)
        
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter Tag:"))
        self.logcat_tag_edit = QLineEdit()
        self.logcat_tag_edit.setPlaceholderText("e.g., ActivityManager")
        filter_layout.addWidget(self.logcat_tag_edit)
        logcat_layout.addLayout(filter_layout)
        
        level_layout = QHBoxLayout()
        level_layout.addWidget(QLabel("Log Level:"))
        self.logcat_level_combo = QComboBox()
        self.logcat_level_combo.addItems(["V", "D", "I", "W", "E", "F"])
        self.logcat_level_combo.setCurrentText("I")
        level_layout.addWidget(self.logcat_level_combo)
        level_layout.addStretch()
        logcat_layout.addLayout(level_layout)
        
        logcat_btn = QPushButton("📥 Dump Logcat")
        logcat_btn.clicked.connect(self.dump_filtered_logcat)
        logcat_layout.addWidget(logcat_btn)
        
        layout.addWidget(logcat_group)
        
        layout.addStretch()
        return tab
    
    def append_log(self, message):
        """Append message to console (thread-safe)"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.console.append(f"[{timestamp}] {message}")
    
    def on_test_complete(self, message, success):
        """Handle test completion"""
        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.warning(self, "Error", message)
    
    # Batch Operations
    def batch_install_apks(self):
        """Batch install APKs"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select APK files", "", "APK Files (*.apk)"
        )
        
        if not files:
            return
        
        self.log_signal.emit(f"Starting batch install: {len(files)} APKs")
        
        def do_install():
            success_count = 0
            for apk_file in files:
                filename = os.path.basename(apk_file)
                self.log_signal.emit(f"Installing: {filename}")
                
                result = self.adb.run_command(f'-s {self.device_id} install -r "{apk_file}"')
                
                if result['success'] or 'Success' in result['stdout']:
                    success_count += 1
                    self.log_signal.emit(f"✓ Installed: {filename}")
                else:
                    self.log_signal.emit(f"✗ Failed: {filename}")
            
            self.test_complete.emit(
                f"Batch install complete: {success_count}/{len(files)} successful",
                True
            )
        
        threading.Thread(target=do_install, daemon=True).start()
    
    def batch_install_from_folder(self):
        """Batch install APKs from folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select folder containing APKs")
        
        if not folder:
            return
        
        apk_files = [
            os.path.join(folder, f) for f in os.listdir(folder)
            if f.lower().endswith('.apk')
        ]
        
        if not apk_files:
            QMessageBox.warning(self, "No APKs", "No APK files found in selected folder")
            return
        
        self.log_signal.emit(f"Found {len(apk_files)} APKs in folder")
        
        def do_install():
            success_count = 0
            for apk_file in apk_files:
                filename = os.path.basename(apk_file)
                self.log_signal.emit(f"Installing: {filename}")
                
                result = self.adb.run_command(f'-s {self.device_id} install -r "{apk_file}"')
                
                if result['success'] or 'Success' in result['stdout']:
                    success_count += 1
                    self.log_signal.emit(f"✓ Installed: {filename}")
                else:
                    self.log_signal.emit(f"✗ Failed: {filename}")
            
            self.test_complete.emit(
                f"Batch install complete: {success_count}/{len(apk_files)} successful",
                True
            )
        
        threading.Thread(target=do_install, daemon=True).start()
    
    def batch_uninstall_apps(self):
        """Batch uninstall apps"""
        packages = self.uninstall_text.toPlainText().strip().split('\n')
        packages = [p.strip() for p in packages if p.strip()]
        
        if not packages:
            QMessageBox.warning(self, "No Packages", "Please enter package names")
            return
        
        reply = QMessageBox.question(
            self, "Confirm",
            f"Uninstall {len(packages)} app(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return
        
        self.log_signal.emit(f"Starting batch uninstall: {len(packages)} apps")
        
        def do_uninstall():
            success_count = 0
            for package in packages:
                self.log_signal.emit(f"Uninstalling: {package}")
                
                result = self.adb.run_command(f'-s {self.device_id} uninstall {package}')
                
                if result['success'] or 'Success' in result['stdout']:
                    success_count += 1
                    self.log_signal.emit(f"✓ Uninstalled: {package}")
                else:
                    self.log_signal.emit(f"✗ Failed: {package}")
            
            self.test_complete.emit(
                f"Batch uninstall complete: {success_count}/{len(packages)} successful",
                True
            )
        
        threading.Thread(target=do_uninstall, daemon=True).start()
    
    def backup_third_party_apps(self):
        """Backup third-party apps"""
        self.log_signal.emit("Starting backup of third-party apps...")
        
        backup_dir = os.path.join(self.test_data_dir, 'app_backup', 
                                  datetime.now().strftime("%Y%m%d_%H%M%S"))
        os.makedirs(backup_dir, exist_ok=True)
        
        def do_backup():
            # Get third-party packages
            result = self.adb.run_command(f'-s {self.device_id} shell pm list packages -3')
            
            if not result['success']:
                self.test_complete.emit("Failed to list packages", False)
                return
            
            packages = [line.replace('package:', '').strip() 
                       for line in result['stdout'].split('\n') if line.strip()]
            
            self.log_signal.emit(f"Found {len(packages)} third-party apps")
            
            success_count = 0
            for package in packages:
                # Get APK path
                path_result = self.adb.run_command(
                    f'-s {self.device_id} shell pm path {package}'
                )
                
                if path_result['success']:
                    apk_path = path_result['stdout'].strip().replace('package:', '')
                    local_path = os.path.join(backup_dir, f"{package}.apk")
                    
                    self.log_signal.emit(f"Backing up: {package}")
                    
                    # Pull APK
                    pull_result = self.adb.run_command(
                        f'-s {self.device_id} pull "{apk_path}" "{local_path}"'
                    )
                    
                    if pull_result['success']:
                        success_count += 1
                        self.log_signal.emit(f"✓ Backed up: {package}")
            
            self.test_complete.emit(
                f"Backup complete: {success_count}/{len(packages)} apps backed up to:\n{backup_dir}",
                True
            )
        
        threading.Thread(target=do_backup, daemon=True).start()
    
    # Performance Testing
    def start_fps_test(self):
        """Start FPS test"""
        package = self.fps_package_edit.text().strip()
        duration = self.fps_duration_spin.value()
        
        if not package:
            QMessageBox.warning(self, "Missing Info", "Please enter package name")
            return
        
        self.log_signal.emit(f"Starting FPS test for {package} ({duration}s)")
        self.log_signal.emit("Please operate the app interface now...")
        
        def do_fps_test():
            fps_data = []
            start_time = time.time()
            
            while time.time() - start_time < duration:
                result = self.adb.run_command(
                    f'-s {self.device_id} shell dumpsys gfxinfo {package}'
                )
                
                if result['success']:
                    # Parse FPS data (simplified)
                    output = result['stdout']
                    if 'Total frames rendered' in output:
                        for line in output.split('\n'):
                            if 'Janky frames:' in line:
                                parts = line.split(':')
                                if len(parts) >= 2:
                                    janky = parts[1].strip().split()[0]
                                    fps_data.append({
                                        'timestamp': datetime.now().isoformat(),
                                        'janky_frames': janky
                                    })
                
                time.sleep(1)
            
            # Save data
            csv_file = os.path.join(
                self.test_data_dir, 
                f'fps_test_{package}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            )
            
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                if fps_data:
                    writer = csv.DictWriter(f, fieldnames=fps_data[0].keys())
                    writer.writeheader()
                    writer.writerows(fps_data)
            
            self.test_complete.emit(
                f"FPS test complete. Data saved to:\n{csv_file}",
                True
            )
        
        threading.Thread(target=do_fps_test, daemon=True).start()
    
    def start_cpu_memory_monitor(self):
        """Start CPU/Memory monitoring"""
        package = self.monitor_package_edit.text().strip()
        samples = self.monitor_samples_spin.value()
        
        if not package:
            QMessageBox.warning(self, "Missing Info", "Please enter package name")
            return
        
        self.monitoring_active = True
        self.start_monitor_btn.setEnabled(False)
        self.stop_monitor_btn.setEnabled(True)
        self.monitor_progress.setMaximum(samples)
        self.monitor_progress.setValue(0)
        
        self.log_signal.emit(f"Starting CPU/Memory monitor for {package}")
        
        def do_monitor():
            monitor_data = []
            
            for i in range(samples):
                if not self.monitoring_active:
                    break
                
                # Get CPU info
                cpu_result = self.adb.run_command(
                    f'-s {self.device_id} shell top -n 1 | grep {package}'
                )
                
                # Get memory info
                mem_result = self.adb.run_command(
                    f'-s {self.device_id} shell dumpsys meminfo {package}'
                )
                
                if cpu_result['success'] and mem_result['success']:
                    cpu_line = cpu_result['stdout'].strip().split('\n')[0] if cpu_result['stdout'] else ''
                    mem_output = mem_result['stdout']
                    
                    # Parse memory (simplified)
                    total_pss = '0'
                    for line in mem_output.split('\n'):
                        if 'TOTAL' in line and 'PSS' in mem_output:
                            parts = line.split()
                            if len(parts) > 1:
                                total_pss = parts[1]
                                break
                    
                    monitor_data.append({
                        'timestamp': datetime.now().isoformat(),
                        'sample': i + 1,
                        'cpu_line': cpu_line,
                        'memory_pss_kb': total_pss
                    })
                    
                    QTimer.singleShot(0, lambda v=i+1: self.monitor_progress.setValue(v))
                
                time.sleep(2)
            
            # Save data
            csv_file = os.path.join(
                self.test_data_dir,
                f'monitor_{package}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            )
            
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                if monitor_data:
                    writer = csv.DictWriter(f, fieldnames=monitor_data[0].keys())
                    writer.writeheader()
                    writer.writerows(monitor_data)
            
            QTimer.singleShot(0, self.reset_monitor_ui)
            
            self.test_complete.emit(
                f"Monitoring complete. Data saved to:\n{csv_file}",
                True
            )
        
        self.monitor_thread = threading.Thread(target=do_monitor, daemon=True)
        self.monitor_thread.start()
    
    def stop_cpu_memory_monitor(self):
        """Stop CPU/Memory monitoring"""
        self.monitoring_active = False
        self.log_signal.emit("Stopping monitor...")
    
    def reset_monitor_ui(self):
        """Reset monitor UI (thread-safe)"""
        self.start_monitor_btn.setEnabled(True)
        self.stop_monitor_btn.setEnabled(False)
        self.monitor_progress.setValue(0)
    
    # App Info
    def get_current_package(self):
        """Get current app package name"""
        self.log_signal.emit("Getting current package name...")
        
        def do_get():
            result = self.adb.run_command(
                f'-s {self.device_id} shell dumpsys window | grep mCurrentFocus'
            )
            
            if result['success']:
                output = result['stdout'].strip()
                # Parse package name from output
                import re
                match = re.search(r'([a-zA-Z0-9_.]+)/([a-zA-Z0-9_.]+)', output)
                if match:
                    package = match.group(1)
                    self.log_signal.emit(f"Current package: {package}")
                    self.test_complete.emit(f"Package: {package}", True)
                else:
                    self.test_complete.emit("Failed to parse package name", False)
            else:
                self.test_complete.emit("Failed to get package name", False)
        
        threading.Thread(target=do_get, daemon=True).start()
    
    def get_current_activity(self):
        """Get current activity name"""
        self.log_signal.emit("Getting current activity name...")
        
        def do_get():
            result = self.adb.run_command(
                f'-s {self.device_id} shell dumpsys window | grep mCurrentFocus'
            )
            
            if result['success']:
                output = result['stdout'].strip()
                self.log_signal.emit(f"Current focus: {output}")
                self.test_complete.emit(f"Activity info:\n{output}", True)
            else:
                self.test_complete.emit("Failed to get activity info", False)
        
        threading.Thread(target=do_get, daemon=True).start()
    
    def pull_current_apk(self):
        """Pull current app APK"""
        self.log_signal.emit("Pulling current app APK...")
        
        def do_pull():
            # Get current package
            focus_result = self.adb.run_command(
                f'-s {self.device_id} shell dumpsys window | grep mCurrentFocus'
            )
            
            if not focus_result['success']:
                self.test_complete.emit("Failed to get current package", False)
                return
            
            import re
            match = re.search(r'([a-zA-Z0-9_.]+)/([a-zA-Z0-9_.]+)', focus_result['stdout'])
            if not match:
                self.test_complete.emit("Failed to parse package name", False)
                return
            
            package = match.group(1)
            self.log_signal.emit(f"Current package: {package}")
            
            # Get APK path
            path_result = self.adb.run_command(
                f'-s {self.device_id} shell pm path {package}'
            )
            
            if not path_result['success']:
                self.test_complete.emit("Failed to get APK path", False)
                return
            
            apk_path = path_result['stdout'].strip().replace('package:', '')
            
            # Pull APK
            save_dir = os.path.join(self.test_data_dir, 'pulled_apks')
            os.makedirs(save_dir, exist_ok=True)
            
            local_path = os.path.join(save_dir, f"{package}.apk")
            
            self.log_signal.emit(f"Pulling APK to: {local_path}")
            
            pull_result = self.adb.run_command(
                f'-s {self.device_id} pull "{apk_path}" "{local_path}"'
            )
            
            if pull_result['success']:
                self.test_complete.emit(f"APK saved to:\n{local_path}", True)
            else:
                self.test_complete.emit("Failed to pull APK", False)
        
        threading.Thread(target=do_pull, daemon=True).start()
    
    def get_app_permissions(self):
        """Get app permissions"""
        package = self.permission_package_edit.text().strip()
        
        if not package:
            QMessageBox.warning(self, "Missing Info", "Please enter package name")
            return
        
        self.log_signal.emit(f"Getting permissions for {package}...")
        
        def do_get():
            result = self.adb.run_command(
                f'-s {self.device_id} shell dumpsys package {package}'
            )
            
            if result['success']:
                output = result['stdout']
                
                # Extract permissions
                permissions = []
                in_permissions = False
                for line in output.split('\n'):
                    if 'requested permissions:' in line.lower():
                        in_permissions = True
                        continue
                    if in_permissions:
                        if line.strip().startswith('android.permission.'):
                            permissions.append(line.strip())
                        elif not line.strip() or 'install permissions' in line.lower():
                            break
                
                if permissions:
                    perm_text = '\n'.join(permissions)
                    self.log_signal.emit(f"Found {len(permissions)} permissions")
                    
                    # Save to file
                    perm_file = os.path.join(
                        self.test_data_dir,
                        f'permissions_{package}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
                    )
                    
                    with open(perm_file, 'w', encoding='utf-8') as f:
                        f.write(f"Permissions for {package}:\n\n")
                        f.write(perm_text)
                    
                    self.test_complete.emit(
                        f"Found {len(permissions)} permissions\nSaved to:\n{perm_file}",
                        True
                    )
                else:
                    self.test_complete.emit("No permissions found", False)
            else:
                self.test_complete.emit("Failed to get permissions", False)
        
        threading.Thread(target=do_get, daemon=True).start()
    
    # Media Capture
    def batch_screenshot(self):
        """Batch screenshot"""
        count = self.screenshot_count_spin.value()
        interval = self.screenshot_interval_spin.value()
        
        self.log_signal.emit(f"Starting batch screenshot: {count} images")
        
        def do_screenshot():
            save_dir = os.path.join(self.test_data_dir, 'screenshots',
                                   datetime.now().strftime("%Y%m%d_%H%M%S"))
            os.makedirs(save_dir, exist_ok=True)
            
            for i in range(count):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                remote_path = f"/sdcard/screenshot_{timestamp}.png"
                local_path = os.path.join(save_dir, f"screenshot_{i+1:03d}.png")
                
                self.log_signal.emit(f"Capturing screenshot {i+1}/{count}")
                
                # Take screenshot
                self.adb.run_command(
                    f'-s {self.device_id} shell screencap -p {remote_path}'
                )
                
                # Pull screenshot
                self.adb.run_command(
                    f'-s {self.device_id} pull {remote_path} "{local_path}"'
                )
                
                # Delete from device
                self.adb.run_command(
                    f'-s {self.device_id} shell rm {remote_path}'
                )
                
                if i < count - 1:
                    time.sleep(interval)
            
            self.test_complete.emit(
                f"Screenshots saved to:\n{save_dir}",
                True
            )
        
        threading.Thread(target=do_screenshot, daemon=True).start()
    
    def screen_record(self):
        """Screen record"""
        duration = self.record_duration_spin.value()
        
        self.log_signal.emit(f"Starting screen recording ({duration}s)...")
        
        def do_record():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            remote_path = f"/sdcard/screenrecord_{timestamp}.mp4"
            
            save_dir = os.path.join(self.test_data_dir, 'recordings')
            os.makedirs(save_dir, exist_ok=True)
            local_path = os.path.join(save_dir, f"recording_{timestamp}.mp4")
            
            # Record
            self.adb.run_command(
                f'-s {self.device_id} shell screenrecord --time-limit {duration} {remote_path}'
            )
            
            self.log_signal.emit("Recording complete, downloading...")
            
            # Pull recording
            pull_result = self.adb.run_command(
                f'-s {self.device_id} pull {remote_path} "{local_path}"'
            )
            
            # Delete from device
            self.adb.run_command(
                f'-s {self.device_id} shell rm {remote_path}'
            )
            
            if pull_result['success']:
                self.test_complete.emit(
                    f"Recording saved to:\n{local_path}",
                    True
                )
            else:
                self.test_complete.emit("Failed to download recording", False)
        
        threading.Thread(target=do_record, daemon=True).start()
    
    # Log Collection
    def get_crash_logs(self):
        """Get crash logs"""
        self.log_signal.emit("Collecting crash logs...")
        
        def do_get():
            result = self.adb.run_command(
                f'-s {self.device_id} shell ls /data/tombstones/'
            )
            
            if result['success'] and result['stdout'].strip():
                log_file = os.path.join(
                    self.test_data_dir,
                    f'crash_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
                )
                
                with open(log_file, 'w', encoding='utf-8') as f:
                    f.write("Tombstones found:\n\n")
                    f.write(result['stdout'])
                
                self.test_complete.emit(
                    f"Crash logs saved to:\n{log_file}",
                    True
                )
            else:
                self.test_complete.emit("No crash logs found", False)
        
        threading.Thread(target=do_get, daemon=True).start()
    
    def dump_filtered_logcat(self):
        """Dump filtered logcat"""
        tag = self.logcat_tag_edit.text().strip()
        level = self.logcat_level_combo.currentText()
        
        self.log_signal.emit("Dumping logcat...")
        
        def do_dump():
            cmd_parts = [f'-s {self.device_id} logcat -d']
            
            if tag:
                cmd_parts.append(f'{tag}:{level}')
            else:
                cmd_parts.append(f'*:{level}')
            
            result = self.adb.run_command(' '.join(cmd_parts))
            
            if result['success']:
                log_file = os.path.join(
                    self.test_data_dir,
                    f'logcat_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
                )
                
                with open(log_file, 'w', encoding='utf-8') as f:
                    f.write(result['stdout'])
                
                self.test_complete.emit(
                    f"Logcat saved to:\n{log_file}",
                    True
                )
            else:
                self.test_complete.emit("Failed to dump logcat", False)
        
        threading.Thread(target=do_dump, daemon=True).start()
    
    def open_test_data_folder(self):
        """Open test data folder"""
        import subprocess
        import sys
        
        if sys.platform == 'win32':
            os.startfile(self.test_data_dir)
        elif sys.platform == 'darwin':
            subprocess.run(['open', self.test_data_dir])
        else:
            subprocess.run(['xdg-open', self.test_data_dir])
