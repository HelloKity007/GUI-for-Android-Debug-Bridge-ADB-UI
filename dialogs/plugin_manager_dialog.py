# -*- coding: utf-8 -*-
"""
Plugin Manager Dialog - 插件管理对话框
提供插件的查看、启用/禁用、配置功能
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QMessageBox, QHeaderView, QWidget, QTextEdit,
    QSplitter, QGroupBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

# PyQt6 兼容别名
pyqtSignal = Signal
from typing import Optional


class PluginManagerDialog(QDialog):
    """插件管理对话框"""
    
    # 信号
    plugin_enabled = pyqtSignal(str)      # 插件ID
    plugin_disabled = pyqtSignal(str)     # 插件ID
    plugin_reloaded = pyqtSignal(str)     # 插件ID
    
    def __init__(self, plugin_manager, parent=None):
        super().__init__(parent)
        self.plugin_manager = plugin_manager
        
        self.setWindowTitle("🔌 插件管理器")
        self.setMinimumSize(900, 600)
        self.setModal(False)
        
        self.setup_ui()
        self.load_plugins()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("插件管理")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        layout.addWidget(title_label)
        
        # 分割器：左侧插件列表，右侧详情
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：插件列表
        left_widget = self.create_plugin_list_widget()
        splitter.addWidget(left_widget)
        
        # 右侧：插件详情
        right_widget = self.create_plugin_detail_widget()
        splitter.addWidget(right_widget)
        
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        
        # Ghost Downloader 快捷按钮
        self.ghost_downloader_btn = QPushButton("📥 Ghost Downloader")
        self.ghost_downloader_btn.setToolTip("启动 Ghost Downloader 下载管理器")
        self.ghost_downloader_btn.clicked.connect(self.launch_ghost_downloader)
        button_layout.addWidget(self.ghost_downloader_btn)
        
        button_layout.addStretch()
        
        self.refresh_btn = QPushButton("🔄 刷新")
        self.refresh_btn.clicked.connect(self.load_plugins)
        button_layout.addWidget(self.refresh_btn)
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.close)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def create_plugin_list_widget(self) -> QWidget:
        """创建插件列表组件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 统计信息
        self.stats_label = QLabel("共 0 个插件")
        self.stats_label.setStyleSheet("color: #666; padding: 5px;")
        layout.addWidget(self.stats_label)
        
        # 插件表格
        self.plugin_table = QTableWidget()
        self.plugin_table.setColumnCount(5)
        self.plugin_table.setHorizontalHeaderLabels(["名称", "版本", "作者", "状态", "操作"])
        
        # 设置列宽
        header = self.plugin_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        # 选择模式
        self.plugin_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.plugin_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        
        # 连接选择信号
        self.plugin_table.itemSelectionChanged.connect(self.on_plugin_selected)
        
        layout.addWidget(self.plugin_table)
        
        return widget
    
    def create_plugin_detail_widget(self) -> QWidget:
        """创建插件详情组件"""
        widget = QGroupBox("插件详情")
        layout = QVBoxLayout(widget)
        
        # 基本信息
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setMaximumHeight(200)
        layout.addWidget(self.detail_text)
        
        # 操作按钮
        button_layout = QVBoxLayout()
        
        self.enable_btn = QPushButton("✅ 启用插件")
        self.enable_btn.clicked.connect(self.enable_current_plugin)
        self.enable_btn.setEnabled(False)
        button_layout.addWidget(self.enable_btn)
        
        self.disable_btn = QPushButton("❌ 禁用插件")
        self.disable_btn.clicked.connect(self.disable_current_plugin)
        self.disable_btn.setEnabled(False)
        button_layout.addWidget(self.disable_btn)
        
        self.reload_btn = QPushButton("🔄 重新加载")
        self.reload_btn.clicked.connect(self.reload_current_plugin)
        self.reload_btn.setEnabled(False)
        button_layout.addWidget(self.reload_btn)
        
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        return widget
    
    def load_plugins(self):
        """加载插件列表"""
        plugins = self.plugin_manager.get_plugin_list()
        
        self.plugin_table.setRowCount(0)
        self.stats_label.setText(f"共 {len(plugins)} 个插件")
        
        for plugin_info in plugins:
            row = self.plugin_table.rowCount()
            self.plugin_table.insertRow(row)
            
            # 名称
            name_item = QTableWidgetItem(plugin_info['name'])
            name_item.setData(Qt.ItemDataRole.UserRole, plugin_info['id'])
            self.plugin_table.setItem(row, 0, name_item)
            
            # 版本
            version_item = QTableWidgetItem(plugin_info['version'])
            self.plugin_table.setItem(row, 1, version_item)
            
            # 作者
            author_item = QTableWidgetItem(plugin_info['author'])
            self.plugin_table.setItem(row, 2, author_item)
            
            # 状态
            status_item = QTableWidgetItem(plugin_info['status'])
            if plugin_info['enabled']:
                status_item.setForeground(QColor("green"))
                status_item.setText("✅ 已启用")
            else:
                status_item.setForeground(QColor("gray"))
                status_item.setText("⚪ 已禁用")
            self.plugin_table.setItem(row, 3, status_item)
            
            # 操作按钮
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(2, 2, 2, 2)
            
            toggle_btn = QPushButton("切换")
            toggle_btn.setMaximumWidth(60)
            toggle_btn.clicked.connect(lambda checked, pid=plugin_info['id']: self.toggle_plugin(pid))
            action_layout.addWidget(toggle_btn)
            
            self.plugin_table.setCellWidget(row, 4, action_widget)
    
    def on_plugin_selected(self):
        """插件选中事件"""
        selected_rows = self.plugin_table.selectedItems()
        if not selected_rows:
            self.detail_text.clear()
            self.enable_btn.setEnabled(False)
            self.disable_btn.setEnabled(False)
            self.reload_btn.setEnabled(False)
            return
        
        # 获取插件ID
        plugin_id = self.plugin_table.item(selected_rows[0].row(), 0).data(Qt.ItemDataRole.UserRole)
        plugin = self.plugin_manager.get_plugin(plugin_id)
        
        if plugin:
            metadata = plugin.get_metadata()
            
            # 显示详情
            detail_html = f"""
            <h3>{metadata.name}</h3>
            <p><b>ID:</b> {metadata.id}</p>
            <p><b>版本:</b> {metadata.version}</p>
            <p><b>作者:</b> {metadata.author}</p>
            <p><b>状态:</b> {plugin.status.value}</p>
            <p><b>描述:</b> {metadata.description}</p>
            <p><b>依赖:</b> {', '.join(metadata.dependencies) if metadata.dependencies else '无'}</p>
            """
            
            self.detail_text.setHtml(detail_html)
            
            # 更新按钮状态
            from framework.plugin import PluginStatus
            is_running = plugin.status == PluginStatus.RUNNING
            
            self.enable_btn.setEnabled(not is_running)
            self.disable_btn.setEnabled(is_running)
            self.reload_btn.setEnabled(True)
            
            # 保存当前选中的插件ID
            self.current_plugin_id = plugin_id
    
    def toggle_plugin(self, plugin_id: str):
        """切换插件启用/禁用状态"""
        plugin = self.plugin_manager.get_plugin(plugin_id)
        if not plugin:
            return
        
        from framework.plugin import PluginStatus
        
        if plugin.status == PluginStatus.RUNNING:
            self.plugin_manager.disable_plugin(plugin_id)
            self.plugin_disabled.emit(plugin_id)
        else:
            self.plugin_manager.enable_plugin(plugin_id)
            self.plugin_enabled.emit(plugin_id)
        
        self.load_plugins()
    
    def enable_current_plugin(self):
        """启用当前选中的插件"""
        if hasattr(self, 'current_plugin_id'):
            self.plugin_manager.enable_plugin(self.current_plugin_id)
            self.plugin_enabled.emit(self.current_plugin_id)
            self.load_plugins()
            self.on_plugin_selected()
    
    def disable_current_plugin(self):
        """禁用当前选中的插件"""
        if hasattr(self, 'current_plugin_id'):
            self.plugin_manager.disable_plugin(self.current_plugin_id)
            self.plugin_disabled.emit(self.current_plugin_id)
            self.load_plugins()
            self.on_plugin_selected()
    
    def reload_current_plugin(self):
        """重新加载当前选中的插件"""
        if hasattr(self, 'current_plugin_id'):
            reply = QMessageBox.question(
                self,
                "确认重载",
                f"确定要重新加载插件吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 卸载并重新加载
                # TODO: 实现插件重载逻辑
                self.plugin_reloaded.emit(self.current_plugin_id)
                QMessageBox.information(self, "提示", "插件重载功能开发中...")
    
    def launch_ghost_downloader(self):
        """启动 Ghost Downloader"""
        import os
        import sys
        import subprocess
        from pathlib import Path
        
        # 查找 Ghost-Downloader-3 路径
        base_dir = Path(__file__).parent.parent
        extensions_dir = base_dir / "extensions" / "Ghost-Downloader-3"
        
        if not extensions_dir.exists():
            QMessageBox.warning(self, "错误", "未找到 Ghost Downloader\n路径: " + str(extensions_dir))
            return
        
        main_script = extensions_dir / "Ghost-Downloader-3.py"
        if not main_script.exists():
            QMessageBox.warning(self, "错误", "未找到主程序文件\n文件: " + str(main_script))
            return
        
        try:
            cmd = [sys.executable, str(main_script)]
            cwd = str(extensions_dir)
            
            if sys.platform == "win32":
                subprocess.Popen(cmd, cwd=cwd, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                subprocess.Popen(cmd, cwd=cwd)
            
            # 启动成功，不显示弹窗
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动失败: {e}")
