# -*- coding: utf-8 -*-
"""
Advanced File Manager for ADB GUI (Based on ADB-Explorer concept)
"""
import os
import threading
import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QLineEdit, QMessageBox, QMenu, QFileDialog,
    QListWidget, QListWidgetItem, QSplitter, QProgressBar, QTableWidget,
    QTableWidgetItem, QHeaderView, QComboBox, QTextEdit, QGroupBox,
    QCheckBox, QTabWidget, QWidget
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QMimeData
from PyQt6.QtGui import QFont, QDrag, QCursor


class FileManagerDialog(QDialog):
    """Advanced file manager with Drive View, Recycle Bin, and Operation Queue"""
    
    file_list_ready = pyqtSignal(list)
    storage_info_ready = pyqtSignal(dict)
    operation_complete = pyqtSignal(str, bool)
    
    def __init__(self, parent, adb, device_id, colors, project_dir):
        super().__init__(parent)
        self.adb = adb
        self.device_id = device_id
        self.colors = colors
        self.project_dir = project_dir
        self.current_path = "/sdcard"
        
        # Clipboard for cut/copy operations
        self.clipboard = []
        self.clipboard_mode = None  # 'copy' or 'cut'
        
        # Recycle bin
        self.recycle_bin_enabled = True
        self.recycle_bin_path = os.path.join(project_dir, 'recycle_bin')
        os.makedirs(self.recycle_bin_path, exist_ok=True)
        self.recycle_bin_data = self.load_recycle_bin()
        
        # Operation queue
        self.operation_queue = []
        
        # Favorites
        self.favorites = self.load_favorites()
        
        self.setWindowTitle("📂 Advanced File Manager")
        self.setMinimumSize(1100, 700)
        self.setup_ui()
        
        # Connect signals
        self.file_list_ready.connect(self.update_file_list)
        self.storage_info_ready.connect(self.update_storage_info)
        self.operation_complete.connect(self.on_operation_complete)
        
        # Load initial data
        self.refresh_storage_info()
        self.refresh_files()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Top toolbar
        toolbar = QHBoxLayout()
        
        back_btn = QPushButton("⬅️ Back")
        back_btn.clicked.connect(self.go_back)
        toolbar.addWidget(back_btn)
        
        forward_btn = QPushButton("➡️ Forward")
        forward_btn.clicked.connect(self.go_forward)
        toolbar.addWidget(forward_btn)
        
        up_btn = QPushButton("⬆️ Up")
        up_btn.clicked.connect(self.go_up)
        toolbar.addWidget(up_btn)
        
        home_btn = QPushButton("🏠 Home")
        home_btn.clicked.connect(lambda: self.navigate_to("/sdcard"))
        toolbar.addWidget(home_btn)
        
        root_btn = QPushButton("📁 Root")
        root_btn.clicked.connect(lambda: self.navigate_to("/"))
        toolbar.addWidget(root_btn)
        
        self.path_edit = QLineEdit()
        self.path_edit.setText(self.current_path)
        self.path_edit.returnPressed.connect(self.navigate_to_input)
        toolbar.addWidget(self.path_edit)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_files)
        toolbar.addWidget(refresh_btn)
        
        layout.addLayout(toolbar)
        
        # Main content area with tabs
        self.main_tabs = QTabWidget()
        
        # Tab 1: File Explorer
        explorer_tab = QWidget()
        explorer_layout = QVBoxLayout(explorer_tab)
        
        # Drive view
        self.storage_label = QLabel("Loading storage info...")
        self.storage_label.setStyleSheet("font-weight: bold; padding: 5px;")
        explorer_layout.addWidget(self.storage_label)
        
        self.storage_progress = QProgressBar()
        self.storage_progress.setMaximumHeight(20)
        explorer_layout.addWidget(self.storage_progress)
        
        # Splitter for favorites and file list
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left: Favorites and Quick Access
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        left_layout.addWidget(QLabel("⭐ Favorites"))
        self.favorites_list = QListWidget()
        self.favorites_list.setMaximumWidth(200)
        self.favorites_list.itemDoubleClicked.connect(self.on_favorite_clicked)
        left_layout.addWidget(self.favorites_list)
        
        add_fav_btn = QPushButton("➕ Add")
        add_fav_btn.clicked.connect(self.add_to_favorites)
        left_layout.addWidget(add_fav_btn)
        
        splitter.addWidget(left_panel)
        
        # Right: File list
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(4)
        self.file_table.setHorizontalHeaderLabels(["Name", "Size", "Date", "Permissions"])
        self.file_table.horizontalHeader().setStretchLastSection(False)
        self.file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.file_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.file_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.file_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.file_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_table.customContextMenuRequested.connect(self.show_context_menu)
        self.file_table.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.file_table.setDragEnabled(True)
        splitter.addWidget(self.file_table)
        
        splitter.setStretchFactor(1, 1)
        explorer_layout.addWidget(splitter)
        
        self.main_tabs.addTab(explorer_tab, "📁 Explorer")
        
        # Tab 2: Operation Queue
        queue_tab = QWidget()
        queue_layout = QVBoxLayout(queue_tab)
        
        queue_layout.addWidget(QLabel("📋 Operation Queue"))
        self.queue_table = QTableWidget()
        self.queue_table.setColumnCount(4)
        self.queue_table.setHorizontalHeaderLabels(["Operation", "File", "Progress", "Status"])
        queue_layout.addWidget(self.queue_table)
        
        clear_queue_btn = QPushButton("🗑️ Clear Completed")
        clear_queue_btn.clicked.connect(self.clear_completed_operations)
        queue_layout.addWidget(clear_queue_btn)
        
        self.main_tabs.addTab(queue_tab, "📋 Queue (0)")
        
        # Tab 3: Recycle Bin
        recycle_tab = QWidget()
        recycle_layout = QVBoxLayout(recycle_tab)
        
        recycle_controls = QHBoxLayout()
        self.recycle_enabled_cb = QCheckBox("Enable Recycle Bin")
        self.recycle_enabled_cb.setChecked(self.recycle_bin_enabled)
        self.recycle_enabled_cb.stateChanged.connect(self.toggle_recycle_bin)
        recycle_controls.addWidget(self.recycle_enabled_cb)
        recycle_controls.addStretch()
        
        restore_btn = QPushButton("↩️ Restore Selected")
        restore_btn.clicked.connect(self.restore_from_recycle_bin)
        recycle_controls.addWidget(restore_btn)
        
        empty_btn = QPushButton("🗑️ Empty Recycle Bin")
        empty_btn.clicked.connect(self.empty_recycle_bin)
        recycle_controls.addWidget(empty_btn)
        
        recycle_layout.addLayout(recycle_controls)
        
        self.recycle_table = QTableWidget()
        self.recycle_table.setColumnCount(3)
        self.recycle_table.setHorizontalHeaderLabels(["Original Path", "Deleted Date", "Size"])
        recycle_layout.addWidget(self.recycle_table)
        
        self.main_tabs.addTab(recycle_tab, "🗑️ Recycle Bin")
        
        layout.addWidget(self.main_tabs)
        
        # Bottom action buttons
        actions = QHBoxLayout()
        
        copy_btn = QPushButton("📋 Copy")
        copy_btn.clicked.connect(self.copy_selected)
        actions.addWidget(copy_btn)
        
        cut_btn = QPushButton("✂️ Cut")
        cut_btn.clicked.connect(self.cut_selected)
        actions.addWidget(cut_btn)
        
        paste_btn = QPushButton("📌 Paste")
        paste_btn.clicked.connect(self.paste_files)
        actions.addWidget(paste_btn)
        
        upload_btn = QPushButton("⬆️ Upload")
        upload_btn.clicked.connect(self.upload_files)
        actions.addWidget(upload_btn)
        
        download_btn = QPushButton("⬇️ Download")
        download_btn.clicked.connect(self.download_selected)
        actions.addWidget(download_btn)
        
        delete_btn = QPushButton("🗑️ Delete")
        delete_btn.clicked.connect(self.delete_selected)
        actions.addWidget(delete_btn)
        
        actions.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        actions.addWidget(close_btn)
        
        layout.addLayout(actions)
        
        # Load favorites
        self.update_favorites_list()
        self.update_recycle_bin_table()
    
    def load_favorites(self):
        """Load favorites from file"""
        fav_file = os.path.join(self.project_dir, 'file_manager_favorites.json')
        if os.path.exists(fav_file):
            try:
                with open(fav_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return ["/sdcard", "/sdcard/DCIM", "/sdcard/Download", "/data/local/tmp"]
    
    def save_favorites(self):
        """Save favorites to file"""
        fav_file = os.path.join(self.project_dir, 'file_manager_favorites.json')
        try:
            with open(fav_file, 'w', encoding='utf-8') as f:
                json.dump(self.favorites, f, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save favorites: {e}")
    
    def load_recycle_bin(self):
        """Load recycle bin metadata"""
        meta_file = os.path.join(self.recycle_bin_path, 'metadata.json')
        if os.path.exists(meta_file):
            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return []
    
    def save_recycle_bin(self):
        """Save recycle bin metadata"""
        meta_file = os.path.join(self.recycle_bin_path, 'metadata.json')
        try:
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump(self.recycle_bin_data, f, indent=2)
        except Exception as e:
            print(f"Failed to save recycle bin metadata: {e}")
    
    def update_favorites_list(self):
        """Update favorites list widget"""
        self.favorites_list.clear()
        for fav in self.favorites:
            self.favorites_list.addItem(fav)
    
    def add_to_favorites(self):
        """Add current path to favorites"""
        if self.current_path not in self.favorites:
            self.favorites.append(self.current_path)
            self.save_favorites()
            self.update_favorites_list()
            QMessageBox.information(self, "Success", f"Added to favorites:\n{self.current_path}")
    
    def on_favorite_clicked(self, item):
        """Navigate to favorite path"""
        self.navigate_to(item.text())
    
    def navigate_to(self, path):
        """Navigate to specified path"""
        self.current_path = path
        self.path_edit.setText(path)
        self.refresh_files()
        self.refresh_storage_info()
    
    def navigate_to_input(self):
        """Navigate to path from input"""
        path = self.path_edit.text().strip()
        if path:
            self.navigate_to(path)
    
    def go_back(self):
        """Go back in history (placeholder)"""
        self.go_up()
    
    def go_forward(self):
        """Go forward in history (placeholder)"""
        pass
    
    def go_up(self):
        """Go to parent directory"""
        parent = os.path.dirname(self.current_path.rstrip('/'))
        if not parent:
            parent = '/'
        self.navigate_to(parent)
    
    def refresh_storage_info(self):
        """Refresh storage information"""
        def do_storage():
            result = self.adb.run_command(f"-s {self.device_id} shell df -h '{self.current_path}'")
            
            if result['success'] and result['stdout'].strip():
                lines = result['stdout'].strip().split('\n')
                if len(lines) >= 2:
                    parts = lines[1].split()
                    if len(parts) >= 5:
                        storage_info = {
                            'total': parts[1],
                            'used': parts[2],
                            'available': parts[3],
                            'use_percent': parts[4].rstrip('%')
                        }
                        self.storage_info_ready.emit(storage_info)
        
        threading.Thread(target=do_storage, daemon=True).start()
    
    def update_storage_info(self, info):
        """Update storage info display (thread-safe)"""
        try:
            use_percent = int(info['use_percent'])
            self.storage_label.setText(
                f"💾 Storage: {info['used']} / {info['total']} used ({info['use_percent']}% full) - {info['available']} available"
            )
            self.storage_progress.setValue(use_percent)
            
            # Color code based on usage
            if use_percent >= 90:
                self.storage_progress.setStyleSheet("QProgressBar::chunk { background-color: #f44336; }")
            elif use_percent >= 70:
                self.storage_progress.setStyleSheet("QProgressBar::chunk { background-color: #ff9800; }")
            else:
                self.storage_progress.setStyleSheet("QProgressBar::chunk { background-color: #4caf50; }")
        except:
            self.storage_label.setText("💾 Storage info unavailable")
    
    def refresh_files(self):
        """Refresh file list"""
        self.file_table.setRowCount(0)
        
        def do_list():
            result = self.adb.run_command(f"-s {self.device_id} shell ls -lAh '{self.current_path}'")
            
            if result['success']:
                files = []
                for line in result['stdout'].strip().split('\n'):
                    if not line.strip() or line.startswith('total'):
                        continue
                    
                    parts = line.split()
                    if len(parts) < 7:
                        continue
                    
                    perms = parts[0]
                    size = parts[4] if len(parts) > 4 else '0'
                    date_time = ' '.join(parts[5:7]) if len(parts) > 6 else ''
                    name = ' '.join(parts[7:]) if len(parts) > 7 else parts[-1]
                    
                    is_dir = perms.startswith('d')
                    
                    files.append({
                        'name': name,
                        'size': size if not is_dir else '',
                        'date': date_time,
                        'perms': perms,
                        'is_dir': is_dir
                    })
                
                self.file_list_ready.emit(files)
            else:
                QTimer.singleShot(0, lambda: QMessageBox.warning(
                    self, "Error", f"Failed to list directory:\n{result.get('stderr', 'Unknown error')}"
                ))
        
        threading.Thread(target=do_list, daemon=True).start()
    
    def update_file_list(self, files):
        """Update file table (thread-safe)"""
        self.file_table.setRowCount(0)
        
        # Sort: directories first, then files
        files.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
        
        for file_info in files:
            row = self.file_table.rowCount()
            self.file_table.insertRow(row)
            
            icon = "📁" if file_info['is_dir'] else "📄"
            name_item = QTableWidgetItem(f"{icon} {file_info['name']}")
            name_item.setData(Qt.ItemDataRole.UserRole, file_info)
            
            self.file_table.setItem(row, 0, name_item)
            self.file_table.setItem(row, 1, QTableWidgetItem(file_info['size']))
            self.file_table.setItem(row, 2, QTableWidgetItem(file_info['date']))
            self.file_table.setItem(row, 3, QTableWidgetItem(file_info['perms']))
    
    def on_item_double_clicked(self, item):
        """Handle double click on item"""
        row = item.row()
        name_item = self.file_table.item(row, 0)
        file_info = name_item.data(Qt.ItemDataRole.UserRole)
        
        if file_info['is_dir']:
            # Navigate into directory
            new_path = os.path.join(self.current_path, file_info['name']).replace('\\', '/')
            self.navigate_to(new_path)
    
    def show_context_menu(self, position):
        """Show context menu for file operations"""
        menu = QMenu()
        
        copy_action = menu.addAction("📋 Copy")
        cut_action = menu.addAction("✂️ Cut")
        paste_action = menu.addAction("📌 Paste")
        menu.addSeparator()
        download_action = menu.addAction("⬇️ Download")
        delete_action = menu.addAction("🗑️ Delete")
        menu.addSeparator()
        rename_action = menu.addAction("✏️ Rename")
        properties_action = menu.addAction("ℹ️ Properties")
        
        action = menu.exec(self.file_table.viewport().mapToGlobal(position))
        
        if action == copy_action:
            self.copy_selected()
        elif action == cut_action:
            self.cut_selected()
        elif action == paste_action:
            self.paste_files()
        elif action == download_action:
            self.download_selected()
        elif action == delete_action:
            self.delete_selected()
        elif action == rename_action:
            self.rename_selected()
        elif action == properties_action:
            self.show_properties()
    
    def copy_selected(self):
        """Copy selected files to clipboard"""
        selected = self.file_table.selectedItems()
        if not selected:
            return
        
        self.clipboard = []
        rows = set()
        for item in selected:
            rows.add(item.row())
        
        for row in rows:
            name_item = self.file_table.item(row, 0)
            file_info = name_item.data(Qt.ItemDataRole.UserRole)
            file_path = os.path.join(self.current_path, file_info['name']).replace('\\', '/')
            self.clipboard.append(file_path)
        
        self.clipboard_mode = 'copy'
        QMessageBox.information(self, "Copied", f"Copied {len(self.clipboard)} item(s)")
    
    def cut_selected(self):
        """Cut selected files to clipboard"""
        self.copy_selected()
        self.clipboard_mode = 'cut'
    
    def paste_files(self):
        """Paste files from clipboard"""
        if not self.clipboard:
            QMessageBox.information(self, "Info", "Clipboard is empty")
            return
        
        def do_paste():
            for src_path in self.clipboard:
                filename = os.path.basename(src_path)
                dest_path = os.path.join(self.current_path, filename).replace('\\', '/')
                
                if self.clipboard_mode == 'copy':
                    # Copy file
                    self.adb.run_command(f'-s {self.device_id} shell cp -r "{src_path}" "{dest_path}"')
                else:
                    # Move file
                    self.adb.run_command(f'-s {self.device_id} shell mv "{src_path}" "{dest_path}"')
            
            self.operation_complete.emit(f"Pasted {len(self.clipboard)} item(s)", True)
            
            if self.clipboard_mode == 'cut':
                self.clipboard = []
        
        threading.Thread(target=do_paste, daemon=True).start()
    
    def upload_files(self):
        """Upload files to current directory"""
        files, _ = QFileDialog.getOpenFileNames(self, "Select files to upload")
        if not files:
            return
        
        def do_upload():
            for file_path in files:
                filename = os.path.basename(file_path)
                remote_path = os.path.join(self.current_path, filename).replace('\\', '/')
                
                result = self.adb.run_command(f'-s {self.device_id} push "{file_path}" "{remote_path}"')
                
                if not result['success']:
                    QTimer.singleShot(0, lambda: QMessageBox.warning(
                        self, "Error", f"Failed to upload {filename}"
                    ))
            
            self.operation_complete.emit(f"Uploaded {len(files)} file(s)", True)
        
        threading.Thread(target=do_upload, daemon=True).start()
    
    def download_selected(self):
        """Download selected files"""
        selected = self.file_table.selectedItems()
        if not selected:
            return
        
        save_dir = QFileDialog.getExistingDirectory(self, "Select save location")
        if not save_dir:
            return
        
        rows = set(item.row() for item in selected)
        
        def do_download():
            for row in rows:
                name_item = self.file_table.item(row, 0)
                file_info = name_item.data(Qt.ItemDataRole.UserRole)
                remote_path = os.path.join(self.current_path, file_info['name']).replace('\\', '/')
                local_path = os.path.join(save_dir, file_info['name'])
                
                result = self.adb.run_command(f'-s {self.device_id} pull "{remote_path}" "{local_path}"')
                
                if not result['success']:
                    QTimer.singleShot(0, lambda: QMessageBox.warning(
                        self, "Error", f"Failed to download {file_info['name']}"
                    ))
            
            self.operation_complete.emit(f"Downloaded {len(rows)} file(s)", True)
        
        threading.Thread(target=do_download, daemon=True).start()
    
    def delete_selected(self):
        """Delete selected files"""
        selected = self.file_table.selectedItems()
        if not selected:
            return
        
        rows = set(item.row() for item in selected)
        
        if self.recycle_bin_enabled:
            action = "move to recycle bin"
        else:
            action = "permanently delete"
        
        reply = QMessageBox.question(
            self, "Confirm", 
            f"{action.capitalize()} {len(rows)} item(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            def do_delete():
                for row in rows:
                    name_item = self.file_table.item(row, 0)
                    file_info = name_item.data(Qt.ItemDataRole.UserRole)
                    remote_path = os.path.join(self.current_path, file_info['name']).replace('\\', '/')
                    
                    if self.recycle_bin_enabled:
                        # Download to recycle bin first
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        local_name = f"{timestamp}_{file_info['name']}"
                        local_path = os.path.join(self.recycle_bin_path, local_name)
                        
                        result = self.adb.run_command(f'-s {self.device_id} pull "{remote_path}" "{local_path}"')
                        
                        if result['success']:
                            # Save metadata
                            self.recycle_bin_data.append({
                                'original_path': remote_path,
                                'local_name': local_name,
                                'deleted_date': datetime.now().isoformat(),
                                'size': file_info['size']
                            })
                            self.save_recycle_bin()
                    
                    # Delete from device
                    self.adb.run_command(f'-s {self.device_id} shell rm -rf "{remote_path}"')
                
                self.operation_complete.emit(f"Deleted {len(rows)} item(s)", True)
                QTimer.singleShot(0, self.update_recycle_bin_table)
            
            threading.Thread(target=do_delete, daemon=True).start()
    
    def rename_selected(self):
        """Rename selected file"""
        selected = self.file_table.selectedItems()
        if not selected:
            return
        
        row = selected[0].row()
        name_item = self.file_table.item(row, 0)
        file_info = name_item.data(Qt.ItemDataRole.UserRole)
        old_name = file_info['name']
        
        from PyQt6.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(self, "Rename", "New name:", text=old_name)
        
        if ok and new_name:
            old_path = os.path.join(self.current_path, old_name).replace('\\', '/')
            new_path = os.path.join(self.current_path, new_name).replace('\\', '/')
            
            def do_rename():
                result = self.adb.run_command(f'-s {self.device_id} shell mv "{old_path}" "{new_path}"')
                self.operation_complete.emit("Renamed file", result['success'])
            
            threading.Thread(target=do_rename, daemon=True).start()
    
    def show_properties(self):
        """Show file properties"""
        selected = self.file_table.selectedItems()
        if not selected:
            return
        
        row = selected[0].row()
        name_item = self.file_table.item(row, 0)
        file_info = name_item.data(Qt.ItemDataRole.UserRole)
        
        info_text = f"Name: {file_info['name']}\n"
        info_text += f"Size: {file_info['size']}\n"
        info_text += f"Date: {file_info['date']}\n"
        info_text += f"Permissions: {file_info['perms']}\n"
        info_text += f"Path: {os.path.join(self.current_path, file_info['name'])}"
        
        QMessageBox.information(self, "Properties", info_text)
    
    def toggle_recycle_bin(self, state):
        """Toggle recycle bin feature"""
        self.recycle_bin_enabled = bool(state)
    
    def update_recycle_bin_table(self):
        """Update recycle bin table"""
        self.recycle_table.setRowCount(0)
        
        for item in self.recycle_bin_data:
            row = self.recycle_table.rowCount()
            self.recycle_table.insertRow(row)
            
            self.recycle_table.setItem(row, 0, QTableWidgetItem(item['original_path']))
            self.recycle_table.setItem(row, 1, QTableWidgetItem(item['deleted_date']))
            self.recycle_table.setItem(row, 2, QTableWidgetItem(item.get('size', 'N/A')))
        
        # Update tab title
        count = len(self.recycle_bin_data)
        self.main_tabs.setTabText(2, f"🗑️ Recycle Bin ({count})")
    
    def restore_from_recycle_bin(self):
        """Restore selected items from recycle bin"""
        selected = self.recycle_table.selectedItems()
        if not selected:
            return
        
        rows = set(item.row() for item in selected)
        
        def do_restore():
            for row in sorted(rows, reverse=True):
                item = self.recycle_bin_data[row]
                local_path = os.path.join(self.recycle_bin_path, item['local_name'])
                remote_path = item['original_path']
                
                if os.path.exists(local_path):
                    result = self.adb.run_command(f'-s {self.device_id} push "{local_path}" "{remote_path}"')
                    
                    if result['success']:
                        os.remove(local_path)
                        self.recycle_bin_data.pop(row)
                
            self.save_recycle_bin()
            self.operation_complete.emit(f"Restored {len(rows)} item(s)", True)
            QTimer.singleShot(0, self.update_recycle_bin_table)
        
        threading.Thread(target=do_restore, daemon=True).start()
    
    def empty_recycle_bin(self):
        """Empty recycle bin"""
        if not self.recycle_bin_data:
            QMessageBox.information(self, "Info", "Recycle bin is empty")
            return
        
        reply = QMessageBox.question(
            self, "Confirm", 
            "Permanently delete all items in recycle bin?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            for item in self.recycle_bin_data:
                local_path = os.path.join(self.recycle_bin_path, item['local_name'])
                if os.path.exists(local_path):
                    try:
                        os.remove(local_path)
                    except:
                        pass
            
            self.recycle_bin_data = []
            self.save_recycle_bin()
            self.update_recycle_bin_table()
            QMessageBox.information(self, "Success", "Recycle bin emptied")
    
    def clear_completed_operations(self):
        """Clear completed operations from queue"""
        # Placeholder for operation queue management
        pass
    
    def on_operation_complete(self, message, success):
        """Handle operation completion (thread-safe)"""
        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.warning(self, "Error", message)
        
        self.refresh_files()
