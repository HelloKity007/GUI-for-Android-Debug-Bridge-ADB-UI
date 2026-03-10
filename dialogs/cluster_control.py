# -*- coding: utf-8 -*-
"""
Device Cluster Control Extension
Based on: https://github.com/imharryzhu/AndroidControl
Multi-device synchronized control and management
"""
import os
import threading
import time
import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QMessageBox, QGroupBox, QLineEdit, QListWidget,
    QListWidgetItem, QCheckBox, QComboBox, QSplitter, QWidget,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QScrollArea, QGridLayout
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal


class ClusterControlDialog(QDialog):
    """Device cluster control extension"""
    
    log_signal = pyqtSignal(str)
    device_refresh_signal = pyqtSignal(list)
    
    def __init__(self, parent, adb, device_id, colors, project_dir):
        super().__init__(parent)
        self.adb = adb
        self.current_device = device_id
        self.colors = colors
        self.project_dir = project_dir
        self.parent_window = parent
        
        # Device groups
        self.groups_file = os.path.join(project_dir, 'device_groups.json')
        self.device_groups = self.load_groups()
        
        # Script recording
        self.recording = False
        self.recorded_commands = []
        self.scripts_dir = os.path.join(project_dir, 'cluster_scripts')
        os.makedirs(self.scripts_dir, exist_ok=True)
        
        # Selected devices for batch operations
        self.selected_devices = []
        
        self.setWindowTitle("🎛️ Device Cluster Control")
        self.setMinimumSize(1000, 700)
        self.setup_ui()
        
        # Connect signals
        self.log_signal.connect(self.append_log)
        self.device_refresh_signal.connect(self.update_device_list)
        
        # Refresh devices
        self.refresh_all_devices()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Main splitter: device list | control panel
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel: Device list and groups
        left_panel = self.create_device_panel()
        main_splitter.addWidget(left_panel)
        
        # Right panel: Control tabs
        right_panel = self.create_control_panel()
        main_splitter.addWidget(right_panel)
        
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 2)
        
        layout.addWidget(main_splitter)
        
        # Bottom console
        console_group = QGroupBox("📊 Console Output")
        console_layout = QVBoxLayout(console_group)
        
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setMaximumHeight(120)
        console_layout.addWidget(self.console)
        
        console_btn_layout = QHBoxLayout()
        clear_btn = QPushButton("🗑️ Clear")
        clear_btn.clicked.connect(self.console.clear)
        console_btn_layout.addWidget(clear_btn)
        console_btn_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        console_btn_layout.addWidget(close_btn)
        
        console_layout.addLayout(console_btn_layout)
        layout.addWidget(console_group)
    
    def create_device_panel(self):
        """Create device list panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Device list header
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("📱 Connected Devices"))
        
        refresh_btn = QPushButton("🔄")
        refresh_btn.setMaximumWidth(40)
        refresh_btn.clicked.connect(self.refresh_all_devices)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Device selection options
        select_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("☑️ All")
        select_all_btn.clicked.connect(self.select_all_devices)
        select_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("☐ None")
        deselect_all_btn.clicked.connect(self.deselect_all_devices)
        select_layout.addWidget(deselect_all_btn)
        
        layout.addLayout(select_layout)
        
        # Device list
        self.device_list = QListWidget()
        self.device_list.itemChanged.connect(self.on_device_selection_changed)
        layout.addWidget(self.device_list)
        
        # Selected count
        self.selected_count_label = QLabel("Selected: 0 devices")
        self.selected_count_label.setStyleSheet("font-weight: bold; padding: 5px;")
        layout.addWidget(self.selected_count_label)
        
        # Device groups
        groups_group = QGroupBox("👥 Device Groups")
        groups_layout = QVBoxLayout(groups_group)
        
        self.groups_list = QListWidget()
        self.groups_list.itemClicked.connect(self.on_group_selected)
        groups_layout.addWidget(self.groups_list)
        
        groups_btn_layout = QHBoxLayout()
        
        add_group_btn = QPushButton("➕ New Group")
        add_group_btn.clicked.connect(self.create_new_group)
        groups_btn_layout.addWidget(add_group_btn)
        
        del_group_btn = QPushButton("🗑️ Delete")
        del_group_btn.clicked.connect(self.delete_group)
        groups_btn_layout.addWidget(del_group_btn)
        
        groups_layout.addLayout(groups_btn_layout)
        layout.addWidget(groups_group)
        
        self.update_groups_list()
        
        return panel
    
    def create_control_panel(self):
        """Create control panel with tabs"""
        tabs = QTabWidget()
        
        # Tab 1: Batch Commands
        batch_tab = self.create_batch_commands_tab()
        tabs.addTab(batch_tab, "📋 Batch Commands")
        
        # Tab 2: Script Control
        script_tab = self.create_script_tab()
        tabs.addTab(script_tab, "🎬 Script Control")
        
        # Tab 3: Synchronized Actions
        sync_tab = self.create_sync_actions_tab()
        tabs.addTab(sync_tab, "🔄 Sync Actions")
        
        # Tab 4: Quick Actions
        quick_tab = self.create_quick_actions_tab()
        tabs.addTab(quick_tab, "⚡ Quick Actions")
        
        return tabs
    
    def create_batch_commands_tab(self):
        """Create batch commands tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Command templates
        templates_group = QGroupBox("📝 Command Templates")
        templates_layout = QVBoxLayout(templates_group)
        
        self.template_combo = QComboBox()
        self.template_combo.addItems([
            "Custom Command",
            "Install APK",
            "Uninstall Package",
            "Clear App Data",
            "Force Stop App",
            "Take Screenshot",
            "Reboot Device",
            "Enable/Disable WiFi",
            "Set System Property"
        ])
        self.template_combo.currentTextChanged.connect(self.on_template_changed)
        templates_layout.addWidget(self.template_combo)
        
        layout.addWidget(templates_group)
        
        # Command input
        command_group = QGroupBox("💻 Command Input")
        command_layout = QVBoxLayout(command_group)
        
        self.batch_command_edit = QTextEdit()
        self.batch_command_edit.setPlaceholderText("Enter ADB command here (without 'adb -s device_id')\nExample: shell input keyevent 3")
        self.batch_command_edit.setMaximumHeight(100)
        command_layout.addWidget(self.batch_command_edit)
        
        layout.addWidget(command_group)
        
        # Execution options
        options_group = QGroupBox("⚙️ Execution Options")
        options_layout = QVBoxLayout(options_group)
        
        self.parallel_exec_cb = QCheckBox("Parallel execution (faster but may overwhelm devices)")
        self.parallel_exec_cb.setChecked(False)
        options_layout.addWidget(self.parallel_exec_cb)
        
        self.stop_on_error_cb = QCheckBox("Stop on first error")
        self.stop_on_error_cb.setChecked(False)
        options_layout.addWidget(self.stop_on_error_cb)
        
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("Delay between devices (ms):"))
        self.delay_spin = QLineEdit("100")
        self.delay_spin.setMaximumWidth(80)
        delay_layout.addWidget(self.delay_spin)
        delay_layout.addStretch()
        options_layout.addLayout(delay_layout)
        
        layout.addWidget(options_group)
        
        # Execute button
        execute_btn = QPushButton("▶️ Execute on Selected Devices")
        execute_btn.clicked.connect(self.execute_batch_command)
        execute_btn.setStyleSheet(f"background-color: {self.colors.get('accent', '#0078d4')}; color: white; font-weight: bold; padding: 10px;")
        layout.addWidget(execute_btn)
        
        layout.addStretch()
        return tab
    
    def create_script_tab(self):
        """Create script recording and playback tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Script recording
        record_group = QGroupBox("🎙️ Script Recording")
        record_layout = QVBoxLayout(record_group)
        
        record_info = QLabel("Record commands to create reusable scripts")
        record_layout.addWidget(record_info)
        
        record_btn_layout = QHBoxLayout()
        
        self.record_btn = QPushButton("⏺️ Start Recording")
        self.record_btn.clicked.connect(self.toggle_recording)
        record_btn_layout.addWidget(self.record_btn)
        
        self.save_script_btn = QPushButton("💾 Save Script")
        self.save_script_btn.clicked.connect(self.save_recorded_script)
        self.save_script_btn.setEnabled(False)
        record_btn_layout.addWidget(self.save_script_btn)
        
        record_layout.addLayout(record_btn_layout)
        
        self.recorded_commands_text = QTextEdit()
        self.recorded_commands_text.setReadOnly(True)
        self.recorded_commands_text.setPlaceholderText("Recorded commands will appear here...")
        self.recorded_commands_text.setMaximumHeight(100)
        record_layout.addWidget(self.recorded_commands_text)
        
        layout.addWidget(record_group)
        
        # Saved scripts
        scripts_group = QGroupBox("📚 Saved Scripts")
        scripts_layout = QVBoxLayout(scripts_group)
        
        self.scripts_list = QListWidget()
        self.scripts_list.itemDoubleClicked.connect(self.preview_script)
        scripts_layout.addWidget(self.scripts_list)
        
        scripts_btn_layout = QHBoxLayout()
        
        refresh_scripts_btn = QPushButton("🔄 Refresh")
        refresh_scripts_btn.clicked.connect(self.refresh_scripts_list)
        scripts_btn_layout.addWidget(refresh_scripts_btn)
        
        run_script_btn = QPushButton("▶️ Run Script")
        run_script_btn.clicked.connect(self.run_selected_script)
        scripts_btn_layout.addWidget(run_script_btn)
        
        delete_script_btn = QPushButton("🗑️ Delete")
        delete_script_btn.clicked.connect(self.delete_selected_script)
        scripts_btn_layout.addWidget(delete_script_btn)
        
        scripts_layout.addLayout(scripts_btn_layout)
        layout.addWidget(scripts_group)
        
        self.refresh_scripts_list()
        
        layout.addStretch()
        return tab
    
    def create_sync_actions_tab(self):
        """Create synchronized actions tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        layout.addWidget(QLabel("Execute synchronized actions on all selected devices"))
        
        # Input simulation
        input_group = QGroupBox("⌨️ Input Simulation")
        input_layout = QVBoxLayout(input_group)
        
        text_layout = QHBoxLayout()
        text_layout.addWidget(QLabel("Text to input:"))
        self.sync_text_input = QLineEdit()
        text_layout.addWidget(self.sync_text_input)
        input_layout.addLayout(text_layout)
        
        input_btn = QPushButton("📝 Send Text to All Devices")
        input_btn.clicked.connect(self.sync_input_text)
        input_layout.addWidget(input_btn)
        
        layout.addWidget(input_group)
        
        # Key events
        key_group = QGroupBox("🎮 Key Events")
        key_layout = QGridLayout(key_group)
        
        keys = [
            ("Home", "3"), ("Back", "4"), ("Menu", "82"),
            ("Power", "26"), ("Volume Up", "24"), ("Volume Down", "25"),
            ("Enter", "66"), ("Delete", "67"), ("Tab", "61")
        ]
        
        row, col = 0, 0
        for key_name, key_code in keys:
            btn = QPushButton(key_name)
            btn.clicked.connect(lambda checked, kc=key_code: self.sync_key_event(kc))
            key_layout.addWidget(btn, row, col)
            col += 1
            if col >= 3:
                col = 0
                row += 1
        
        layout.addWidget(key_group)
        
        # Tap/Swipe
        gesture_group = QGroupBox("👆 Gestures")
        gesture_layout = QVBoxLayout(gesture_group)
        
        tap_layout = QHBoxLayout()
        tap_layout.addWidget(QLabel("Tap at X:"))
        self.tap_x = QLineEdit("500")
        self.tap_x.setMaximumWidth(80)
        tap_layout.addWidget(self.tap_x)
        
        tap_layout.addWidget(QLabel("Y:"))
        self.tap_y = QLineEdit("500")
        self.tap_y.setMaximumWidth(80)
        tap_layout.addWidget(self.tap_y)
        
        tap_btn = QPushButton("👆 Tap")
        tap_btn.clicked.connect(self.sync_tap)
        tap_layout.addWidget(tap_btn)
        
        gesture_layout.addLayout(tap_layout)
        
        swipe_layout = QHBoxLayout()
        swipe_layout.addWidget(QLabel("Swipe from X1:"))
        self.swipe_x1 = QLineEdit("500")
        self.swipe_x1.setMaximumWidth(60)
        swipe_layout.addWidget(self.swipe_x1)
        
        swipe_layout.addWidget(QLabel("Y1:"))
        self.swipe_y1 = QLineEdit("1000")
        self.swipe_y1.setMaximumWidth(60)
        swipe_layout.addWidget(self.swipe_y1)
        
        swipe_layout.addWidget(QLabel("to X2:"))
        self.swipe_x2 = QLineEdit("500")
        self.swipe_x2.setMaximumWidth(60)
        swipe_layout.addWidget(self.swipe_x2)
        
        swipe_layout.addWidget(QLabel("Y2:"))
        self.swipe_y2 = QLineEdit("200")
        self.swipe_y2.setMaximumWidth(60)
        swipe_layout.addWidget(self.swipe_y2)
        
        swipe_btn = QPushButton("👆 Swipe")
        swipe_btn.clicked.connect(self.sync_swipe)
        swipe_layout.addWidget(swipe_btn)
        
        gesture_layout.addLayout(swipe_layout)
        layout.addWidget(gesture_group)
        
        layout.addStretch()
        return tab
    
    def create_quick_actions_tab(self):
        """Create quick actions tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Common quick actions
        actions = [
            ("📸 Take Screenshots", self.quick_screenshot_all),
            ("🔄 Reboot All", self.quick_reboot_all),
            ("✈️ Toggle Airplane Mode", self.quick_toggle_airplane),
            ("📶 Toggle WiFi", self.quick_toggle_wifi),
            ("🔊 Set Volume to Max", self.quick_max_volume),
            ("🔇 Mute All", self.quick_mute_all),
            ("🌙 Toggle Dark Mode", self.quick_toggle_dark_mode),
            ("🔋 Show Battery Status", self.quick_battery_status),
            ("📊 Collect Device Info", self.quick_collect_info),
            ("🗑️ Clear All App Caches", self.quick_clear_caches)
        ]
        
        for action_name, action_func in actions:
            btn = QPushButton(action_name)
            btn.clicked.connect(action_func)
            layout.addWidget(btn)
        
        layout.addStretch()
        return tab
    
    # Device management
    def refresh_all_devices(self):
        """Refresh connected devices list"""
        def do_refresh():
            result = self.adb.run_command("devices -l")
            
            if result['success']:
                devices = []
                for line in result['stdout'].strip().split('\n')[1:]:  # Skip first line
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 2:
                            device_id = parts[0]
                            status = parts[1]
                            
                            # Extract model name if available
                            model = "Unknown"
                            for part in parts[2:]:
                                if part.startswith('model:'):
                                    model = part.split(':')[1]
                                    break
                            
                            devices.append({
                                'id': device_id,
                                'status': status,
                                'model': model
                            })
                
                self.device_refresh_signal.emit(devices)
        
        threading.Thread(target=do_refresh, daemon=True).start()
    
    def update_device_list(self, devices):
        """Update device list widget (thread-safe)"""
        self.device_list.clear()
        
        for device in devices:
            if device['status'] == 'device':
                item = QListWidgetItem(f"📱 {device['model']} ({device['id']})")
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                item.setData(Qt.ItemDataRole.UserRole, device['id'])
                self.device_list.addItem(item)
        
        self.log_signal.emit(f"Found {len(devices)} connected devices")
    
    def on_device_selection_changed(self, item):
        """Handle device selection change"""
        self.selected_devices = []
        
        for i in range(self.device_list.count()):
            item = self.device_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                device_id = item.data(Qt.ItemDataRole.UserRole)
                self.selected_devices.append(device_id)
        
        self.selected_count_label.setText(f"Selected: {len(self.selected_devices)} devices")
    
    def select_all_devices(self):
        """Select all devices"""
        for i in range(self.device_list.count()):
            item = self.device_list.item(i)
            item.setCheckState(Qt.CheckState.Checked)
        self.on_device_selection_changed(None)
    
    def deselect_all_devices(self):
        """Deselect all devices"""
        for i in range(self.device_list.count()):
            item = self.device_list.item(i)
            item.setCheckState(Qt.CheckState.Unchecked)
        self.on_device_selection_changed(None)
    
    # Group management
    def load_groups(self):
        """Load device groups from file"""
        if os.path.exists(self.groups_file):
            try:
                with open(self.groups_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def save_groups(self):
        """Save device groups to file"""
        try:
            with open(self.groups_file, 'w', encoding='utf-8') as f:
                json.dump(self.device_groups, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.log_signal.emit(f"Failed to save groups: {e}")
    
    def update_groups_list(self):
        """Update groups list widget"""
        self.groups_list.clear()
        
        for group_name, device_ids in self.device_groups.items():
            item = QListWidgetItem(f"👥 {group_name} ({len(device_ids)} devices)")
            item.setData(Qt.ItemDataRole.UserRole, group_name)
            self.groups_list.addItem(item)
    
    def create_new_group(self):
        """Create new device group"""
        if not self.selected_devices:
            QMessageBox.warning(self, "No Selection", "Please select devices first")
            return
        
        from PyQt6.QtWidgets import QInputDialog
        group_name, ok = QInputDialog.getText(self, "New Group", "Group name:")
        
        if ok and group_name:
            self.device_groups[group_name] = self.selected_devices.copy()
            self.save_groups()
            self.update_groups_list()
            self.log_signal.emit(f"Created group: {group_name} with {len(self.selected_devices)} devices")
    
    def delete_group(self):
        """Delete selected group"""
        current_item = self.groups_list.currentItem()
        if not current_item:
            return
        
        group_name = current_item.data(Qt.ItemDataRole.UserRole)
        
        reply = QMessageBox.question(
            self, "Confirm",
            f"Delete group '{group_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            del self.device_groups[group_name]
            self.save_groups()
            self.update_groups_list()
            self.log_signal.emit(f"Deleted group: {group_name}")
    
    def on_group_selected(self, item):
        """Select devices in group"""
        group_name = item.data(Qt.ItemDataRole.UserRole)
        device_ids = self.device_groups.get(group_name, [])
        
        # Check devices in group
        for i in range(self.device_list.count()):
            list_item = self.device_list.item(i)
            device_id = list_item.data(Qt.ItemDataRole.UserRole)
            
            if device_id in device_ids:
                list_item.setCheckState(Qt.CheckState.Checked)
            else:
                list_item.setCheckState(Qt.CheckState.Unchecked)
        
        self.on_device_selection_changed(None)
        self.log_signal.emit(f"Selected group: {group_name}")
    
    # Batch command execution
    def on_template_changed(self, template):
        """Handle template selection"""
        templates = {
            "Install APK": "install -r /path/to/app.apk",
            "Uninstall Package": "uninstall com.example.package",
            "Clear App Data": "shell pm clear com.example.package",
            "Force Stop App": "shell am force-stop com.example.package",
            "Take Screenshot": "shell screencap -p /sdcard/screenshot.png",
            "Reboot Device": "reboot",
            "Enable/Disable WiFi": "shell svc wifi enable",
            "Set System Property": "shell setprop key value"
        }
        
        if template in templates:
            self.batch_command_edit.setPlainText(templates[template])
    
    def execute_batch_command(self):
        """Execute command on all selected devices"""
        if not self.selected_devices:
            QMessageBox.warning(self, "No Selection", "Please select devices first")
            return
        
        command = self.batch_command_edit.toPlainText().strip()
        if not command:
            QMessageBox.warning(self, "No Command", "Please enter a command")
            return
        
        parallel = self.parallel_exec_cb.isChecked()
        stop_on_error = self.stop_on_error_cb.isChecked()
        
        try:
            delay = int(self.delay_spin.text())
        except:
            delay = 100
        
        self.log_signal.emit(f"Executing on {len(self.selected_devices)} devices: {command}")
        
        # Record if recording
        if self.recording:
            self.record_command(command)
        
        def execute_on_device(device_id):
            self.log_signal.emit(f"[{device_id}] Executing...")
            result = self.adb.run_command(f"-s {device_id} {command}")
            
            if result['success']:
                self.log_signal.emit(f"[{device_id}] ✓ Success")
                return True
            else:
                self.log_signal.emit(f"[{device_id}] ✗ Failed: {result.get('stderr', 'Unknown error')}")
                return False
        
        def do_batch():
            if parallel:
                # Parallel execution
                threads = []
                for device_id in self.selected_devices:
                    t = threading.Thread(target=execute_on_device, args=(device_id,))
                    t.start()
                    threads.append(t)
                
                for t in threads:
                    t.join()
            else:
                # Sequential execution
                for device_id in self.selected_devices:
                    success = execute_on_device(device_id)
                    
                    if not success and stop_on_error:
                        self.log_signal.emit("Stopped due to error")
                        break
                    
                    if delay > 0:
                        time.sleep(delay / 1000.0)
            
            self.log_signal.emit("Batch execution complete")
        
        threading.Thread(target=do_batch, daemon=True).start()
    
    # Script recording and playback
    def toggle_recording(self):
        """Toggle script recording"""
        self.recording = not self.recording
        
        if self.recording:
            self.recorded_commands = []
            self.recorded_commands_text.clear()
            self.record_btn.setText("⏹️ Stop Recording")
            self.save_script_btn.setEnabled(False)
            self.log_signal.emit("Script recording started")
        else:
            self.record_btn.setText("⏺️ Start Recording")
            self.save_script_btn.setEnabled(True)
            self.log_signal.emit(f"Recording stopped. {len(self.recorded_commands)} commands recorded")
    
    def record_command(self, command):
        """Record a command"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.recorded_commands.append({
            'timestamp': timestamp,
            'command': command
        })
        
        self.recorded_commands_text.append(f"[{timestamp}] {command}")
    
    def save_recorded_script(self):
        """Save recorded script"""
        if not self.recorded_commands:
            QMessageBox.information(self, "No Commands", "No commands to save")
            return
        
        from PyQt6.QtWidgets import QInputDialog
        script_name, ok = QInputDialog.getText(self, "Save Script", "Script name:")
        
        if ok and script_name:
            script_file = os.path.join(self.scripts_dir, f"{script_name}.json")
            
            try:
                with open(script_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'name': script_name,
                        'created': datetime.now().isoformat(),
                        'commands': self.recorded_commands
                    }, f, indent=2, ensure_ascii=False)
                
                self.log_signal.emit(f"Script saved: {script_name}")
                self.refresh_scripts_list()
                
                # Clear recording
                self.recorded_commands = []
                self.recorded_commands_text.clear()
                self.save_script_btn.setEnabled(False)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to save script: {e}")
    
    def refresh_scripts_list(self):
        """Refresh scripts list"""
        self.scripts_list.clear()
        
        if os.path.exists(self.scripts_dir):
            for filename in os.listdir(self.scripts_dir):
                if filename.endswith('.json'):
                    script_name = filename[:-5]
                    item = QListWidgetItem(f"🎬 {script_name}")
                    item.setData(Qt.ItemDataRole.UserRole, filename)
                    self.scripts_list.addItem(item)
    
    def preview_script(self, item):
        """Preview script content"""
        filename = item.data(Qt.ItemDataRole.UserRole)
        script_file = os.path.join(self.scripts_dir, filename)
        
        try:
            with open(script_file, 'r', encoding='utf-8') as f:
                script_data = json.load(f)
            
            commands_text = '\n'.join([f"[{cmd['timestamp']}] {cmd['command']}" 
                                      for cmd in script_data.get('commands', [])])
            
            QMessageBox.information(self, f"Script: {script_data['name']}", commands_text)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load script: {e}")
    
    def run_selected_script(self):
        """Run selected script"""
        current_item = self.scripts_list.currentItem()
        if not current_item:
            return
        
        if not self.selected_devices:
            QMessageBox.warning(self, "No Selection", "Please select devices first")
            return
        
        filename = current_item.data(Qt.ItemDataRole.UserRole)
        script_file = os.path.join(self.scripts_dir, filename)
        
        try:
            with open(script_file, 'r', encoding='utf-8') as f:
                script_data = json.load(f)
            
            self.log_signal.emit(f"Running script: {script_data['name']}")
            
            def do_run():
                for device_id in self.selected_devices:
                    self.log_signal.emit(f"[{device_id}] Running script...")
                    
                    for cmd_data in script_data.get('commands', []):
                        command = cmd_data['command']
                        self.adb.run_command(f"-s {device_id} {command}")
                        time.sleep(0.5)  # Small delay between commands
                    
                    self.log_signal.emit(f"[{device_id}] ✓ Script complete")
                
                self.log_signal.emit("Script execution complete")
            
            threading.Thread(target=do_run, daemon=True).start()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to run script: {e}")
    
    def delete_selected_script(self):
        """Delete selected script"""
        current_item = self.scripts_list.currentItem()
        if not current_item:
            return
        
        filename = current_item.data(Qt.ItemDataRole.UserRole)
        script_file = os.path.join(self.scripts_dir, filename)
        
        reply = QMessageBox.question(
            self, "Confirm",
            f"Delete script '{filename[:-5]}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                os.remove(script_file)
                self.refresh_scripts_list()
                self.log_signal.emit(f"Script deleted: {filename[:-5]}")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to delete script: {e}")
    
    # Synchronized actions
    def sync_input_text(self):
        """Send text to all devices"""
        text = self.sync_text_input.text()
        if not text or not self.selected_devices:
            return
        
        # Escape special characters
        escaped_text = text.replace(' ', '%s').replace("'", "\\'")
        command = f"shell input text '{escaped_text}'"
        
        self.batch_command_edit.setPlainText(command)
        self.execute_batch_command()
    
    def sync_key_event(self, key_code):
        """Send key event to all devices"""
        if not self.selected_devices:
            return
        
        command = f"shell input keyevent {key_code}"
        self.batch_command_edit.setPlainText(command)
        self.execute_batch_command()
    
    def sync_tap(self):
        """Send tap gesture to all devices"""
        try:
            x = int(self.tap_x.text())
            y = int(self.tap_y.text())
        except:
            QMessageBox.warning(self, "Invalid Input", "Please enter valid coordinates")
            return
        
        command = f"shell input tap {x} {y}"
        self.batch_command_edit.setPlainText(command)
        self.execute_batch_command()
    
    def sync_swipe(self):
        """Send swipe gesture to all devices"""
        try:
            x1 = int(self.swipe_x1.text())
            y1 = int(self.swipe_y1.text())
            x2 = int(self.swipe_x2.text())
            y2 = int(self.swipe_y2.text())
        except:
            QMessageBox.warning(self, "Invalid Input", "Please enter valid coordinates")
            return
        
        command = f"shell input swipe {x1} {y1} {x2} {y2} 300"
        self.batch_command_edit.setPlainText(command)
        self.execute_batch_command()
    
    # Quick actions
    def quick_screenshot_all(self):
        """Take screenshots on all devices"""
        self.batch_command_edit.setPlainText("shell screencap -p /sdcard/screenshot.png")
        self.execute_batch_command()
    
    def quick_reboot_all(self):
        """Reboot all devices"""
        reply = QMessageBox.question(
            self, "Confirm",
            f"Reboot {len(self.selected_devices)} devices?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.batch_command_edit.setPlainText("reboot")
            self.execute_batch_command()
    
    def quick_toggle_airplane(self):
        """Toggle airplane mode"""
        self.batch_command_edit.setPlainText("shell settings put global airplane_mode_on 1")
        self.execute_batch_command()
    
    def quick_toggle_wifi(self):
        """Toggle WiFi"""
        self.batch_command_edit.setPlainText("shell svc wifi enable")
        self.execute_batch_command()
    
    def quick_max_volume(self):
        """Set volume to max"""
        self.batch_command_edit.setPlainText("shell media volume --set 15")
        self.execute_batch_command()
    
    def quick_mute_all(self):
        """Mute all devices"""
        self.batch_command_edit.setPlainText("shell media volume --set 0")
        self.execute_batch_command()
    
    def quick_toggle_dark_mode(self):
        """Toggle dark mode"""
        self.batch_command_edit.setPlainText("shell cmd uimode night yes")
        self.execute_batch_command()
    
    def quick_battery_status(self):
        """Show battery status"""
        self.batch_command_edit.setPlainText("shell dumpsys battery")
        self.execute_batch_command()
    
    def quick_collect_info(self):
        """Collect device info"""
        self.batch_command_edit.setPlainText("shell getprop ro.product.model")
        self.execute_batch_command()
    
    def quick_clear_caches(self):
        """Clear all app caches"""
        self.batch_command_edit.setPlainText("shell pm trim-caches 999G")
        self.execute_batch_command()
    
    def append_log(self, message):
        """Append log message (thread-safe)"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.console.append(f"[{timestamp}] {message}")
