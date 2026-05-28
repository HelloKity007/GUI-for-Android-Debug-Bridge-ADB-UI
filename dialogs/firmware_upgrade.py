# -*- coding: utf-8 -*-
"""
Firmware Upgrade Dialog - 固件升级工具
集成 lg_task_download 下载 和 upgrade_tool 烧录
支持独立窗口、设备同步、配置持久化
"""
import json
import logging
import os
import re
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("firmware_upgrade")
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QMessageBox, QGroupBox, QLineEdit, QComboBox,
    QWidget, QFrame, QApplication, QCheckBox, QFileDialog,
    QGridLayout, QProgressBar
)
from PySide6.QtCore import Qt, Signal, QThread, QObject

# PyQt6 兼容别名
pyqtSignal = Signal


# ==================== 配置管理 ====================

DEFAULT_CONFIG = {
    "download": {
        "output_dir": "E:/debug_local/log/firmware",
        "server": "auto",
        "threads": 8
    },
    "upgrade_tool_path": "extensions/upgrade_tool_v2.56_for_window/upgrade_tool.exe",
    "partitions": [
        {"enabled": True, "name": "Full Image", "image": "update.img", "is_full_image": True},
        {"enabled": False, "name": "uboot", "image": "uboot.img", "is_full_image": False},
        {"enabled": False, "name": "boot", "image": "boot.img", "is_full_image": False},
        {"enabled": False, "name": "loader", "image": "rk3576_spl_loader_v1.08.105.bin", "is_full_image": False},
        {"enabled": False, "name": "", "image": "", "is_full_image": False},
        {"enabled": False, "name": "", "image": "", "is_full_image": False}
    ]
}


def load_config():
    """加载配置文件"""
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'config', 'firmware_upgrade.json'
    )
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config):
    """保存配置文件"""
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'config', 'firmware_upgrade.json'
    )
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception:
        return False


# ==================== 下载工作线程 ====================

class DownloadWorker(QObject):
    """下载工作线程 - 使用subprocess调用download.py脚本"""
    progress = pyqtSignal(str)       # 进度消息
    finished = pyqtSignal(bool, str)  # (成功, 消息)

    def __init__(self, task_ids, output_dir, server="auto", threads=8):
        super().__init__()
        self.task_ids = task_ids
        self.output_dir = output_dir
        self.server = server
        self.threads = threads
        self._cancelled = False
        # 下载脚本路径 - 使用项目内的脚本
        self.download_script = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'extensions', 'lg_task_download', 'download.py'
        )

    def cancel(self):
        """取消下载"""
        self._cancelled = True

    def run(self):
        """执行下载 - 逐个调用download.py脚本"""
        if not os.path.exists(self.download_script):
            self.finished.emit(False, f"下载脚本不存在: {self.download_script}")
            return

        try:
            for task_id in self.task_ids:
                if self._cancelled:
                    self.finished.emit(False, "下载已取消")
                    return
                task_id = task_id.strip()
                if not task_id:
                    continue
                self.progress.emit(f"开始下载任务: {task_id}")
                success = self._download_task(task_id)
                if self._cancelled:
                    self.finished.emit(False, "下载已取消")
                    return
                if not success:
                    self.finished.emit(False, f"任务 {task_id} 下载失败")
                    return
                self.progress.emit(f"任务 {task_id} 下载完成")

            self.finished.emit(True, "所有任务下载完成")

        except Exception as e:
            tb = traceback.format_exc()
            self.progress.emit(f"[异常详情] {tb}")
            self.finished.emit(False, f"下载异常: {str(e)}")

    def _download_task(self, task_id):
        """下载单个任务 - 调用download.py脚本"""
        try:
            # 构建命令: python download.py <task_id> -o <output_dir> -s <server> -t <threads>
            cmd = [
                sys.executable,  # python
                self.download_script,
                task_id,
                '-o', self.output_dir,
                '-s', self.server,
                '-t', str(self.threads)
            ]

            self.progress.emit(f"执行: python download.py {task_id}")

            # 使用subprocess运行，禁用Python输出缓冲
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'

            # 使用 communicate() 一次性获取所有输出
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env
            )

            stdout, _ = process.communicate()

            # 解析输出，按行处理
            output = stdout.decode('utf-8', errors='replace')
            for line in output.split('\n'):
                if self._cancelled:
                    return False
                line = line.strip()
                if line:
                    self.progress.emit(line)

            if process.returncode == 0:
                return True
            else:
                self.progress.emit(f"下载脚本返回错误码: {process.returncode}")
                return False

        except Exception as e:
            self.progress.emit(f"下载异常: {str(e)}")
            return False


# ==================== 烧录工作线程 ====================

class FlashWorker(QObject):
    """烧录工作线程"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    SHORT_NAMES = {
        'boot': '-b', 'kernel': '-k', 'recovery': '-r',
        'system': '-s', 'uboot': '-u', 'misc': '-m', 'trust': '-t'
    }

    def __init__(self, upgrade_tool_path, partitions, download_dir, device_location_id=None):
        super().__init__()
        self.upgrade_tool_path = upgrade_tool_path
        self.partitions = partitions
        self.download_dir = download_dir
        self.device_location_id = device_location_id
        self._cancelled = False

    def cancel(self):
        """取消烧录"""
        self._cancelled = True

    def run(self):
        """执行烧录"""
        try:
            logger.info("[FlashWorker] run 开始执行")
            # 等待设备就绪
            self.progress.emit("检查设备连接...")
            if not self._wait_for_device():
                self.finished.emit(False, "未检测到升级设备，请确认设备已进入Loader模式")
                return

            self.progress.emit("设备已就绪，开始烧录...")

            # 构建烧录命令
            enabled_partitions = [p for p in self.partitions if p['enabled'] and p['name']]
            if not enabled_partitions:
                self.finished.emit(False, "未选择任何分区")
                return

            # 检查是否包含 Full Image
            full_image = None
            partition_list = []
            for p in enabled_partitions:
                if p.get('is_full_image'):
                    full_image = p
                else:
                    partition_list.append(p)

            # 烧录 Full Image
            if full_image:
                image_path = self._resolve_image_path(full_image['image'])
                if not image_path:
                    self.finished.emit(False, f"找不到镜像文件: {full_image['image']}")
                    return
                self.progress.emit(f"烧录 Full Image: {image_path}")
                success, output = self._run_upgrade_cmd(['UF', image_path])
                if not success:
                    self.finished.emit(False, f"Full Image 烧录失败: {output}")
                    return
                self.progress.emit("Full Image 烧录成功，设备将自动重启")
                self.finished.emit(True, "烧录完成，设备已重启")
                return

            # 烧录分区镜像 - 多分区单命令烧录
            # 先解析所有镜像路径
            resolved = []
            for p in partition_list:
                image_path = self._resolve_image_path(p['image'])
                if not image_path:
                    self.finished.emit(False, f"找不到镜像文件: {p['image']}")
                    return
                resolved.append((p['name'], image_path))

            # 构建 di 命令: di -name1 img1 -name2 img2 ...
            cmd_args = ['DI']
            for name, image_path in resolved:
                self.progress.emit(f"分区 {name}: {image_path}")
                flag = self.SHORT_NAMES.get(name.lower(), f'-{name}')
                cmd_args.extend([flag, image_path])

            self.progress.emit(f"执行烧录命令: {' '.join(cmd_args)}")
            success, output = self._run_upgrade_cmd(cmd_args)
            if not success:
                self.finished.emit(False, f"分区烧录失败: {output}")
                return
            self.progress.emit("分区烧录成功")

            # 重启设备（不带参数 = 正常开机）
            self.progress.emit("烧录完成，重启设备...")
            self._run_upgrade_cmd(['RD'])
            self.finished.emit(True, "所有分区烧录完成，设备已重启")

        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"[FlashWorker] run 异常: {e}\n{tb}")
            self.progress.emit(f"[异常详情] {tb}")
            self.finished.emit(False, f"烧录异常: {str(e)}")

    def _resolve_image_path(self, image_name):
        """解析镜像文件路径"""
        if not image_name:
            return None
        # 绝对路径
        if os.path.isabs(image_name) and os.path.exists(image_name):
            return image_name
        # 相对于下载目录
        # 镜像可能在 download_dir/key/ 子目录下，搜索所有子目录
        for root, dirs, files in os.walk(self.download_dir):
            if image_name in files:
                return os.path.join(root, image_name)
        # 直接在下载目录下
        direct_path = os.path.join(self.download_dir, image_name)
        if os.path.exists(direct_path):
            return direct_path
        return None

    def _flash_partition(self, partition_name, image_path):
        """烧录单个分区"""
        # 已定义缩写的分区
        short_names = {
            'boot': '-b', 'kernel': '-k', 'recovery': '-r',
            'system': '-s', 'uboot': '-u', 'misc': '-m', 'trust': '-t'
        }

        if partition_name.lower() in short_names:
            flag = short_names[partition_name.lower()]
            return self._run_upgrade_cmd(['DI', flag, image_path])
        else:
            # 自定义分区名: DI -partition_name image.img
            return self._run_upgrade_cmd(['DI', f'-{partition_name}', image_path])

    def _wait_for_device(self):
        """等待设备就绪，最多等待30秒"""
        for i in range(30):
            if self._cancelled:
                return False
            success, output = self._run_upgrade_cmd(['LD'], capture=True)
            # 检查输出中是否包含设备信息（Loader 或 Maskrom）
            if output and ('Loader' in output or 'Maskrom' in output):
                # 解析 LocationID
                match = re.search(r'LocationID=(\w+)', output)
                if match:
                    self.device_location_id = match.group(1)
                    self.progress.emit(f"检测到设备: LocationID={self.device_location_id}, Mode={'Loader' if 'Loader' in output else 'Maskrom'}")
                    # 延时2秒再确认
                    time.sleep(2)
                    success2, output2 = self._run_upgrade_cmd(['LD'], capture=True)
                    if output2 and ('Loader' in output2 or 'Maskrom' in output2):
                        return True
            else:
                self.progress.emit(f"等待设备... ({i+1}/30)")
            time.sleep(1)
        return False

    def _run_upgrade_cmd(self, args, capture=False):
        """执行 upgrade_tool 命令"""
        cmd = [self.upgrade_tool_path] + args
        try:
            if self.device_location_id:
                cmd = [self.upgrade_tool_path, '-s', str(self.device_location_id)] + args

            logger.debug(f"[FlashWorker] 执行命令: {cmd}")

            if capture:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                output = result.stdout + result.stderr
                return result.returncode == 0, output.strip()
            else:
                # 日志中只显示文件名，不显示完整路径
                tool_name = os.path.basename(self.upgrade_tool_path)
                log_cmd = [tool_name] + cmd[1:]
                self.progress.emit(f"执行: {' '.join(log_cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                output = result.stdout + result.stderr
                if output.strip():
                    self.progress.emit(output.strip())
                return result.returncode == 0, output.strip()
        except subprocess.TimeoutExpired:
            logger.warning(f"[FlashWorker] 命令超时: {cmd}")
            return False, "命令执行超时"
        except FileNotFoundError:
            logger.error(f"[FlashWorker] 找不到升级工具: {self.upgrade_tool_path}")
            return False, f"找不到升级工具: {self.upgrade_tool_path}"
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"[FlashWorker] 命令异常: {e}\n{tb}")
            self.progress.emit(f"[异常详情] {tb}")
            return False, str(e)


# ==================== 设备检测工作线程 ====================

class DeviceChecker(QObject):
    """后台设备检测线程"""
    devices_found = pyqtSignal(list)  # 设备列表 [(location_id, description)]
    devices_changed = pyqtSignal(list)  # 仅设备变化时触发
    check_error = pyqtSignal(str)

    def __init__(self, upgrade_tool_path):
        super().__init__()
        self.upgrade_tool_path = upgrade_tool_path
        self._running = False
        self._last_device_ids = []  # 上次检测到的设备ID列表

    def start_checking(self):
        """开始循环检测"""
        self._running = True
        while self._running:
            self._check_devices()
            time.sleep(1)

    def stop(self):
        """停止检测"""
        self._running = False

    def _check_devices(self):
        """执行一次设备检查"""
        try:
            result = subprocess.run(
                [self.upgrade_tool_path, 'LD'],
                capture_output=True, text=True, timeout=5
            )
            output = (result.stdout + result.stderr).strip()

            if not output:
                self.devices_found.emit([])
                return

            devices = []
            for line in output.split('\n'):
                line = line.strip()
                if not line:
                    continue
                # 解析设备行，格式如: "DevNo=1    Vid=2207,Pid=350b,LocationID=1    Loader"
                match = re.search(r'LocationID=(\w+)', line)
                if match:
                    location_id = match.group(1)
                    devices.append((location_id, line))

            self.devices_found.emit(devices)

            # 检测设备变化，仅在设备数量或ID变化时触发
            current_ids = sorted([d[0] for d in devices])
            if current_ids != self._last_device_ids:
                self._last_device_ids = current_ids
                self.devices_changed.emit(devices)

        except subprocess.TimeoutExpired:
            pass  # 超时忽略，下次再检查
        except FileNotFoundError:
            self.check_error.emit(f"找不到升级工具: {self.upgrade_tool_path}")
        except Exception as e:
            logger.debug(f"[设备检测] 异常: {e}")


# ==================== 主对话框 ====================

class FirmwareUpgradeDialog(QDialog):
    """固件升级对话框 - 独立窗口"""

    log_signal = pyqtSignal(str)

    PARTITION_ROWS = 6  # 总行数（含 Full Image）
    SHORT_NAMES = {
        'boot': '-b', 'kernel': '-k', 'recovery': '-r',
        'system': '-s', 'uboot': '-u', 'misc': '-m', 'trust': '-t'
    }

    def __init__(self, parent, adb, device_id, colors):
        super().__init__(parent)
        self.adb = adb
        self.device_id = device_id
        self.colors = colors
        self.project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        self.config = load_config()
        self._download_worker = None
        self._download_thread = None
        self._flash_worker = None
        self._flash_thread = None
        self._device_checker = None
        self._device_check_thread = None
        self._device_checking = False

        self.setWindowTitle("🔧 RK Firmware Upgrade")
        self.setMinimumSize(750, 700)

        self.setup_ui()
        self._load_config_to_ui()
        self.log_signal.connect(self.append_log)

        # 不再自动启动设备检测，由用户手动启动
        # self._start_device_check()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # ==================== 下载配置 ====================
        dl_group = QGroupBox("📥 下载配置")
        dl_layout = QVBoxLayout(dl_group)

        # 下载路径
        path_row = QHBoxLayout()
        path_row.addWidget(QLabel("下载路径:"))
        self.download_path_input = QLineEdit()
        self.download_path_input.setPlaceholderText("选择固件下载目录")
        path_row.addWidget(self.download_path_input)
        browse_btn = QPushButton("浏览")
        browse_btn.setFixedWidth(60)
        browse_btn.clicked.connect(self._browse_download_path)
        path_row.addWidget(browse_btn)
        dl_layout.addLayout(path_row)

        # 服务器选择
        server_row = QHBoxLayout()
        server_row.addWidget(QLabel("服务器:"))
        self.server_combo = QComboBox()
        self.server_combo.addItems(["auto", "gz", "cs"])
        server_row.addWidget(self.server_combo)
        server_row.addWidget(QLabel("线程数:"))
        self.threads_combo = QComboBox()
        self.threads_combo.addItems(["4", "8", "16"])
        self.threads_combo.setCurrentText("8")
        server_row.addWidget(self.threads_combo)
        server_row.addStretch()
        dl_layout.addLayout(server_row)

        # 任务ID输入框（3个）
        id_row = QHBoxLayout()
        id_row.addWidget(QLabel("任务ID:"))
        self.task_id_inputs = []
        for i in range(3):
            inp = QLineEdit()
            inp.setPlaceholderText(f"任务ID {i+1}")
            self.task_id_inputs.append(inp)
            id_row.addWidget(inp)
        dl_layout.addLayout(id_row)

        layout.addWidget(dl_group)

        # ==================== 分区配置 ====================
        part_group = QGroupBox("💾 分区配置")
        part_layout = QVBoxLayout(part_group)

        # 表头
        header_row = QHBoxLayout()
        header_row.addWidget(QLabel("启用"), 0)
        header_row.addWidget(QLabel("分区名"), 1)
        header_row.addWidget(QLabel("镜像文件名"), 2)
        part_layout.addLayout(header_row)

        # 分区行
        self.partition_checks = []
        self.partition_name_inputs = []
        self.partition_image_inputs = []

        for i in range(self.PARTITION_ROWS):
            row = QHBoxLayout()
            cb = QCheckBox()
            cb.setFixedWidth(30)
            self.partition_checks.append(cb)
            row.addWidget(cb, 0)

            name_input = QLineEdit()
            name_input.setPlaceholderText("分区名")
            self.partition_name_inputs.append(name_input)
            row.addWidget(name_input, 1)

            image_input = QLineEdit()
            image_input.setPlaceholderText("镜像文件名")
            self.partition_image_inputs.append(image_input)
            row.addWidget(image_input, 2)

            part_layout.addLayout(row)

        # 保存配置按钮
        save_btn_row = QHBoxLayout()
        save_config_btn = QPushButton("💾 保存分区配置")
        save_config_btn.clicked.connect(self._save_partition_config)
        save_btn_row.addWidget(save_config_btn)
        save_btn_row.addStretch()
        part_layout.addLayout(save_btn_row)

        layout.addWidget(part_group)

        # ==================== 操作按钮 ====================
        action_group = QGroupBox("⚡ 操作")
        action_layout = QVBoxLayout(action_group)

        btn_row = QHBoxLayout()

        self.download_btn = QPushButton("📥 下载")
        self.download_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 10px; font-weight: bold;")
        self.download_btn.setToolTip("仅下载任务文件，多个ID同时下载")
        self.download_btn.clicked.connect(self._download_only)
        btn_row.addWidget(self.download_btn)

        self.flash_btn = QPushButton("🔥 烧录")
        self.flash_btn.setStyleSheet("background-color: #f44336; color: white; padding: 10px; font-weight: bold;")
        self.flash_btn.setToolTip("仅烧录已勾选的分区（设备需已进入Loader模式）")
        self.flash_btn.clicked.connect(self._flash_only)
        btn_row.addWidget(self.flash_btn)

        self.download_flash_btn = QPushButton("📥🔥 下载+烧录")
        self.download_flash_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px; font-weight: bold;")
        self.download_flash_btn.setToolTip("下载任务文件 → reboot loader → 等待设备 → 烧录 → 重启")
        self.download_flash_btn.clicked.connect(self._download_and_flash)
        btn_row.addWidget(self.download_flash_btn)

        self.cancel_btn = QPushButton("❌ 取消")
        self.cancel_btn.setStyleSheet("background-color: #9E9E9E; color: white; padding: 10px; font-weight: bold;")
        self.cancel_btn.setToolTip("取消当前下载或烧录操作")
        self.cancel_btn.clicked.connect(self._cancel_operation)
        self.cancel_btn.setEnabled(False)
        btn_row.addWidget(self.cancel_btn)

        action_layout.addLayout(btn_row)

        # 设备信息
        device_row = QHBoxLayout()
        device_row.addWidget(QLabel("ADB设备:"))
        self.device_label = QLabel("未连接")
        self.device_label.setStyleSheet("font-weight: bold; color: #FF9800;")
        device_row.addWidget(self.device_label)
        device_row.addStretch()
        action_layout.addLayout(device_row)

        layout.addWidget(action_group)

        # ==================== 升级设备检测 ====================
        detect_group = QGroupBox("🔍 升级设备检测 (Loader/Maskrom)")
        detect_layout = QVBoxLayout(detect_group)

        # 检测状态和控制
        detect_ctrl_row = QHBoxLayout()
        self.detect_status_label = QLabel("检测: 未启动")
        self.detect_status_label.setStyleSheet("color: #9E9E9E;")
        detect_ctrl_row.addWidget(self.detect_status_label)

        self.detect_btn = QPushButton("▶ 启动检测")
        self.detect_btn.setFixedWidth(100)
        self.detect_btn.clicked.connect(self._toggle_device_check)
        detect_ctrl_row.addWidget(self.detect_btn)
        detect_ctrl_row.addStretch()
        detect_layout.addLayout(detect_ctrl_row)

        # 设备列表
        self.device_list_widget = QTextEdit()
        self.device_list_widget.setReadOnly(True)
        self.device_list_widget.setMaximumHeight(80)
        self.device_list_widget.setStyleSheet("font-family: monospace; font-size: 12px;")
        detect_layout.addWidget(self.device_list_widget)

        # 选中设备
        select_row = QHBoxLayout()
        select_row.addWidget(QLabel("选中LocationID:"))
        self.selected_location_id_input = QLineEdit()
        self.selected_location_id_input.setPlaceholderText("点击设备列表中的设备自动填入，或手动输入")
        select_row.addWidget(self.selected_location_id_input)
        detect_layout.addLayout(select_row)

        layout.addWidget(detect_group)

        # ==================== 输出控制台 ====================
        console_group = QGroupBox("📊 输出控制台")
        console_layout = QVBoxLayout(console_group)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setMinimumHeight(200)
        console_layout.addWidget(self.console)

        clear_btn = QPushButton("🗑️ 清空控制台")
        clear_btn.clicked.connect(self.console.clear)
        console_layout.addWidget(clear_btn)

        layout.addWidget(console_group)

        # 底部
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        bottom_layout.addWidget(close_btn)
        layout.addLayout(bottom_layout)

    def _load_config_to_ui(self):
        """从配置加载到UI"""
        dl = self.config.get('download', {})
        self.download_path_input.setText(dl.get('output_dir', ''))
        server = dl.get('server', 'auto')
        idx = self.server_combo.findText(server)
        if idx >= 0:
            self.server_combo.setCurrentIndex(idx)
        threads = str(dl.get('threads', 8))
        idx = self.threads_combo.findText(threads)
        if idx >= 0:
            self.threads_combo.setCurrentIndex(idx)

        partitions = self.config.get('partitions', [])
        for i, p in enumerate(partitions):
            if i >= self.PARTITION_ROWS:
                break
            self.partition_checks[i].setChecked(p.get('enabled', False))
            self.partition_name_inputs[i].setText(p.get('name', ''))
            self.partition_image_inputs[i].setText(p.get('image', ''))

    def _save_partition_config(self):
        """保存分区配置"""
        self.config['download'] = {
            "output_dir": self.download_path_input.text().strip(),
            "server": self.server_combo.currentText(),
            "threads": int(self.threads_combo.currentText())
        }

        partitions = []
        for i in range(self.PARTITION_ROWS):
            partitions.append({
                "enabled": self.partition_checks[i].isChecked(),
                "name": self.partition_name_inputs[i].text().strip(),
                "image": self.partition_image_inputs[i].text().strip(),
                "is_full_image": (i == 0)
            })
        self.config['partitions'] = partitions

        if save_config(self.config):
            self.log_signal.emit("配置已保存")
        else:
            self.log_signal.emit("配置保存失败")

    def _browse_download_path(self):
        """浏览下载路径"""
        current = self.download_path_input.text().strip()
        directory = QFileDialog.getExistingDirectory(self, "选择下载目录", current)
        if directory:
            self.download_path_input.setText(directory)
            # 自动保存路径配置
            self.config.setdefault('download', {})['output_dir'] = directory
            save_config(self.config)
            self.log_signal.emit(f"下载路径已更新: {directory}")

    def _toggle_device_check(self):
        """切换设备检测状态"""
        if self._device_checking:
            self._stop_device_check()
        else:
            self._start_device_check()

    def _start_device_check(self):
        """启动后台设备检测"""
        upgrade_tool = os.path.join(self.project_dir, self.config.get('upgrade_tool_path', ''))
        if not os.path.exists(upgrade_tool):
            QMessageBox.critical(self, "错误", f"找不到升级工具: {upgrade_tool}")
            return

        self._device_checking = True
        self.detect_btn.setText("⏹ 停止检测")
        self.detect_status_label.setText("检测: 运行中...")
        self.detect_status_label.setStyleSheet("color: #4CAF50;")

        self._device_check_thread = QThread()
        self._device_checker = DeviceChecker(upgrade_tool)
        self._device_checker.moveToThread(self._device_check_thread)

        self._device_check_thread.started.connect(self._device_checker.start_checking)
        self._device_checker.devices_found.connect(self._on_devices_found)
        self._device_checker.devices_changed.connect(self._on_devices_changed)
        self._device_checker.check_error.connect(lambda msg: self.log_signal.emit(f"[检测] {msg}"))

        self._device_check_thread.start()

    def _stop_device_check(self):
        """停止后台设备检测"""
        self._device_checking = False
        if self._device_checker:
            self._device_checker.stop()
        if self._device_check_thread:
            self._device_check_thread.quit()
            self._device_check_thread.wait(2000)
        self.detect_btn.setText("▶ 启动检测")
        self.detect_status_label.setText("检测: 已停止")
        self.detect_status_label.setStyleSheet("color: #9E9E9E;")

    def _on_devices_found(self, devices):
        """设备列表更新回调（仅更新UI，不打印日志）"""
        self.device_list_widget.clear()
        if not devices:
            self.device_list_widget.setPlainText("未检测到升级设备")
            self.detect_status_label.setText("检测: 运行中... 未发现设备")
            self.detect_status_label.setStyleSheet("color: #FF9800;")
            return

        self.detect_status_label.setText(f"检测: 运行中... 发现 {len(devices)} 个设备")
        self.detect_status_label.setStyleSheet("color: #4CAF50;")

        # 显示设备列表
        for location_id, desc in devices:
            self.device_list_widget.append(f"📍 {desc}")

        # 自动选择逻辑
        if len(devices) == 1:
            self.selected_location_id_input.setText(devices[0][0])

    def _on_devices_changed(self, devices):
        """设备变化时打印日志（仅在数量或ID变化时触发）"""
        if not devices:
            self.log_signal.emit("[检测] 所有升级设备已断开")
            return

        self.log_signal.emit(f"[检测] 设备变化: 发现 {len(devices)} 个设备")
        for location_id, desc in devices:
            self.log_signal.emit(f"  📍 {desc}")

        if len(devices) == 1:
            self.selected_location_id_input.setText(devices[0][0])
            self.log_signal.emit(f"[检测] 自动选择设备: LocationID={devices[0][0]}")
        elif len(devices) > 1:
            current = self.selected_location_id_input.text().strip()
            if not current:
                self.log_signal.emit(f"[检测] 多个设备，请手动选择 LocationID")

    def _get_selected_location_id(self):
        """获取选中的设备 LocationID"""
        text = self.selected_location_id_input.text().strip()
        return text if text else None

    def _get_enabled_partitions(self):
        """获取已启用的分区列表"""
        partitions = []
        for i in range(self.PARTITION_ROWS):
            if self.partition_checks[i].isChecked():
                name = self.partition_name_inputs[i].text().strip()
                image = self.partition_image_inputs[i].text().strip()
                if name and image:
                    partitions.append({
                        'enabled': True,
                        'name': name,
                        'image': image,
                        'is_full_image': (i == 0)
                    })
        return partitions

    def _download_only(self):
        """仅下载"""
        task_ids = []
        for inp in self.task_id_inputs:
            text = inp.text().strip()
            if text:
                task_ids.append(text)

        if not task_ids:
            QMessageBox.warning(self, "警告", "请至少输入一个任务ID")
            return

        download_dir = self.download_path_input.text().strip()
        if not download_dir:
            QMessageBox.warning(self, "警告", "请设置下载路径")
            return

        server = self.server_combo.currentText()
        threads = int(self.threads_combo.currentText())

        self.log_signal.emit("=" * 40)
        self.log_signal.emit(f"开始下载 {len(task_ids)} 个任务...")

        self._start_download_thread(task_ids, download_dir, server, threads, None)

    def _flash_only(self):
        """仅烧录"""
        try:
            logger.info("[烧录] _flash_only 开始执行")
            partitions = self._get_enabled_partitions()
            if not partitions:
                QMessageBox.warning(self, "警告", "请至少勾选一个分区")
                return

            upgrade_tool = os.path.join(self.project_dir, self.config.get('upgrade_tool_path', ''))
            if not os.path.exists(upgrade_tool):
                QMessageBox.critical(self, "错误", f"找不到升级工具: {upgrade_tool}")
                return

            download_dir = self.download_path_input.text().strip()
            if not download_dir:
                QMessageBox.warning(self, "警告", "请设置下载路径")
                return

            location_id = self._get_selected_location_id()
            logger.info(f"[烧录] location_id={location_id}, device_id={self.device_id}")

            self.log_signal.emit("=" * 40)
            self.log_signal.emit("开始烧录...")
            self._set_operation_running(True)

            # 检查升级设备是否已存在，不存在则尝试 reboot loader
            if not location_id:
                if self.device_id:
                    self.log_signal.emit(f"未检测到升级设备，发送 reboot loader 到设备 {self.device_id}...")
                    # 异步执行 reboot loader
                    threading.Thread(target=self._reboot_loader_and_flash,
                                     args=(upgrade_tool, partitions, download_dir),
                                     daemon=True).start()
                    return
                else:
                    self.log_signal.emit("警告: 未连接ADB设备且未检测到升级设备")
            else:
                self.log_signal.emit(f"已检测到升级设备 LocationID={location_id}")

            self._start_flash_thread(upgrade_tool, partitions, download_dir, location_id)
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"[烧录] _flash_only 异常: {e}\n{tb}")
            self.log_signal.emit(f"[烧录] 异常: {str(e)}\n{tb}")
            self._set_operation_running(False)

    def _download_and_flash(self):
        """下载+烧录"""
        try:
            logger.info("[下载+烧录] _download_and_flash 开始执行")
            # 收集任务ID
            task_ids = []
            for inp in self.task_id_inputs:
                text = inp.text().strip()
                if text:
                    task_ids.append(text)

            if not task_ids:
                QMessageBox.warning(self, "警告", "请至少输入一个任务ID")
                return

            partitions = self._get_enabled_partitions()
            if not partitions:
                QMessageBox.warning(self, "警告", "请至少勾选一个分区")
                return

            upgrade_tool = os.path.join(self.project_dir, self.config.get('upgrade_tool_path', ''))
            if not os.path.exists(upgrade_tool):
                QMessageBox.critical(self, "错误", f"找不到升级工具: {upgrade_tool}")
                return

            download_dir = self.download_path_input.text().strip()
            if not download_dir:
                QMessageBox.warning(self, "警告", "请设置下载路径")
                return

            # 保存配置
            self._save_partition_config()

            self.log_signal.emit("=" * 40)
            self.log_signal.emit("开始下载+烧录流程...")
            self._set_operation_running(True)

            # 在主线程中获取UI值，避免跨线程访问Qt控件
            location_id = self._get_selected_location_id()
            device_id = self.device_id
            server = self.server_combo.currentText()
            threads = int(self.threads_combo.currentText())

            # 异步执行整个流程
            self.log_signal.emit("[调试] 准备启动后台线程...")
            try:
                t = threading.Thread(target=self._download_and_flash_worker,
                                     args=(task_ids, upgrade_tool, partitions, download_dir, location_id, device_id, server, threads),
                                     daemon=True)
                t.start()
                self.log_signal.emit(f"[调试] 后台线程已启动, tid={t.ident}")
            except Exception as e:
                self.log_signal.emit(f"[调试] 启动线程异常: {str(e)}")
                self._set_operation_running(False)
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"[下载+烧录] _download_and_flash 异常: {e}\n{tb}")
            self.log_signal.emit(f"[下载+烧录] 异常: {str(e)}\n{tb}")
            self._set_operation_running(False)

    def _reboot_loader_and_flash(self, upgrade_tool, partitions, download_dir):
        """异步执行 reboot loader 后烧录"""
        try:
            self.log_signal.emit(f"[异步] 发送 reboot loader 到设备 {self.device_id}...")
            result = self.adb.run_command(f'-s {self.device_id} reboot loader')
            if result.get('success'):
                self.log_signal.emit("[异步] reboot loader 命令已发送")
            else:
                self.log_signal.emit(f"[异步] reboot loader 失败: {result.get('stderr', 'unknown error')}")
        except Exception as e:
            tb = traceback.format_exc()
            self.log_signal.emit(f"[异步] reboot loader 异常: {str(e)}\n{tb}")

        # 启动烧录线程（会自动等待设备）
        self._start_flash_thread(upgrade_tool, partitions, download_dir, None)

    def _download_and_flash_worker(self, task_ids, upgrade_tool, partitions, download_dir, location_id, device_id, server, threads):
        """异步执行下载+烧录全流程"""
        try:
            self.log_signal.emit("[流程] 开始执行...")

            # 步骤1: 检查升级设备，不存在则 reboot loader
            self.log_signal.emit("[流程] 步骤1: 检查升级设备...")

            # 先用 upgrade_tool LD 验证 LocationID 是否真实存在
            real_location_id = None
            if location_id:
                self.log_signal.emit(f"[流程] 验证 LocationID={location_id} 是否存在...")
                try:
                    result = subprocess.run(
                        [upgrade_tool, 'LD'],
                        capture_output=True, text=True, timeout=5
                    )
                    output = (result.stdout + result.stderr).strip()
                    if location_id in output:
                        self.log_signal.emit(f"[流程] LocationID={location_id} 存在")
                        real_location_id = location_id
                    else:
                        self.log_signal.emit(f"[流程] LocationID={location_id} 已不存在，需要重新进入 loader")
                except Exception as e:
                    self.log_signal.emit(f"[流程] 验证设备异常: {str(e)}")

            if not real_location_id:
                if device_id:
                    self.log_signal.emit(f"[流程] 未检测到升级设备，发送 reboot loader 到设备 {device_id}...")
                    try:
                        result = self.adb.run_command(f'-s {device_id} reboot loader')
                        if result.get('success'):
                            self.log_signal.emit("[流程] reboot loader 命令已发送")
                        else:
                            self.log_signal.emit(f"[流程] reboot loader 失败: {result.get('stderr', 'unknown error')}")
                    except Exception as e:
                        self.log_signal.emit(f"[流程] reboot loader 异常: {str(e)}")
                else:
                    self.log_signal.emit("[流程] 警告: 未连接ADB设备且未检测到升级设备")
            else:
                self.log_signal.emit(f"[流程] 已验证升级设备 LocationID={real_location_id}")

            # 步骤2: 下载（同步等待完成）
            self.log_signal.emit("[流程] 步骤2: 开始下载...")
            download_success = self._download_tasks_sync(task_ids, download_dir, server, threads)

            if not download_success:
                self.log_signal.emit("[流程] 下载失败，中止流程")
                self._set_operation_running(False)
                return

            # 步骤3: 烧录
            self.log_signal.emit("[流程] 步骤3: 开始烧录...")
            self._start_flash_thread(upgrade_tool, partitions, download_dir, real_location_id)

        except Exception as e:
            tb = traceback.format_exc()
            self.log_signal.emit(f"[流程] 异常: {str(e)}\n{tb}")
            self._set_operation_running(False)

    def _download_tasks_sync(self, task_ids, output_dir, server, threads):
        """同步下载任务（在线程中调用）"""
        download_script = os.path.join(self.project_dir, 'extensions', 'lg_task_download', 'download.py')
        if not os.path.exists(download_script):
            self.log_signal.emit(f"[下载] 脚本不存在: {download_script}")
            return False

        for task_id in task_ids:
            task_id = task_id.strip()
            if not task_id:
                continue
            self.log_signal.emit(f"[下载] 开始下载任务: {task_id}")
            cmd = [sys.executable, download_script, task_id, '-o', output_dir, '-s', server, '-t', str(threads)]
            try:
                env = os.environ.copy()
                env['PYTHONUNBUFFERED'] = '1'
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
                stdout, _ = process.communicate()
                output = stdout.decode('utf-8', errors='replace')
                for line in output.split('\n'):
                    line = line.strip()
                    if line:
                        self.log_signal.emit(f"[下载] {line}")
                if process.returncode != 0:
                    self.log_signal.emit(f"[下载] 任务 {task_id} 失败，返回码: {process.returncode}")
                    return False
                self.log_signal.emit(f"[下载] 任务 {task_id} 完成")
            except Exception as e:
                self.log_signal.emit(f"[下载] 任务 {task_id} 异常: {str(e)}")
                return False
        return True

    def _start_download_thread(self, task_ids, output_dir, server, threads, on_complete_callback):
        """启动下载线程"""
        self._set_operation_running(True)
        self._download_thread = QThread()
        self._download_worker = DownloadWorker(task_ids, output_dir, server, threads)
        self._download_worker.moveToThread(self._download_thread)

        self._download_thread.started.connect(self._download_worker.run)
        self._download_worker.progress.connect(lambda msg: self.log_signal.emit(f"[下载] {msg}"))
        self._download_worker.finished.connect(lambda ok, msg: self._on_download_finished(ok, msg, on_complete_callback))

        self._download_worker.finished.connect(self._download_thread.quit)
        self._download_worker.finished.connect(self._download_worker.deleteLater)
        self._download_thread.finished.connect(self._download_thread.deleteLater)

        self._download_thread.start()

    def _on_download_finished(self, success, message, on_complete_callback):
        """下载完成回调"""
        self._set_operation_running(False)
        if success:
            self.log_signal.emit(f"[下载] ✅ {message}")
            if on_complete_callback:
                on_complete_callback()
        else:
            self.log_signal.emit(f"[下载] ❌ {message}")

    def _start_flash_thread(self, upgrade_tool, partitions, download_dir, location_id=None):
        """启动烧录线程"""
        try:
            logger.info(f"[烧录] _start_flash_thread 开始, location_id={location_id}")

            # 清理旧的烧录线程
            self._cleanup_flash_thread()

            self._flash_thread = QThread()
            self._flash_worker = FlashWorker(upgrade_tool, partitions, download_dir, location_id)
            self._flash_worker.moveToThread(self._flash_thread)

            self._flash_thread.started.connect(self._flash_worker.run)
            self._flash_worker.progress.connect(lambda msg: self.log_signal.emit(f"[烧录] {msg}"))
            self._flash_worker.finished.connect(self._on_flash_finished)

            self._flash_worker.finished.connect(self._flash_thread.quit)
            self._flash_worker.finished.connect(self._flash_worker.deleteLater)
            self._flash_thread.finished.connect(self._flash_thread.deleteLater)

            self._flash_thread.start()
            logger.info("[烧录] 烧录线程已启动")
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"[烧录] _start_flash_thread 异常: {e}\n{tb}")
            self.log_signal.emit(f"[烧录] 启动线程异常: {str(e)}\n{tb}")
            self._set_operation_running(False)

    def _cleanup_flash_thread(self):
        """清理旧的烧录线程"""
        try:
            if hasattr(self, '_flash_worker') and self._flash_worker:
                logger.info("[烧录] 清理旧的烧录 worker")
                self._flash_worker.cancel()
                self._flash_worker = None
            if hasattr(self, '_flash_thread') and self._flash_thread:
                if self._flash_thread.isRunning():
                    logger.info("[烧录] 停止旧的烧录线程")
                    self._flash_thread.quit()
                    self._flash_thread.wait(1000)
                self._flash_thread = None
        except Exception as e:
            logger.warning(f"[烧录] 清理线程异常: {e}")

    def _on_flash_finished(self, success, message):
        """烧录完成回调"""
        try:
            self._set_operation_running(False)
            if success:
                self.log_signal.emit(f"[烧录] ✅ {message}")
            else:
                self.log_signal.emit(f"[烧录] ❌ {message}")
        except Exception as e:
            tb = traceback.format_exc()
            self.log_signal.emit(f"[烧录] 回调异常: {str(e)}\n{tb}")

    def _cancel_operation(self):
        """取消当前操作"""
        if self._download_worker:
            self._download_worker.cancel()
            self.log_signal.emit("[操作] 正在取消下载...")
        if self._flash_worker:
            self._flash_worker.cancel()
            self.log_signal.emit("[操作] 正在取消烧录...")

    def _set_operation_running(self, running):
        """设置操作运行状态，控制按钮可用性"""
        self.download_btn.setEnabled(not running)
        self.flash_btn.setEnabled(not running)
        self.download_flash_btn.setEnabled(not running)
        self.cancel_btn.setEnabled(running)
        # 取消按钮样式：运行时黄色高亮，否则灰色
        if running:
            self.cancel_btn.setStyleSheet("background-color: #FF9800; color: white; padding: 10px; font-weight: bold;")
        else:
            self.cancel_btn.setStyleSheet("background-color: #9E9E9E; color: white; padding: 10px; font-weight: bold;")

    def update_device(self, device_id):
        """更新设备ID（由主界面调用同步设备信息）"""
        self.device_id = device_id
        if device_id:
            self.device_label.setText(device_id)
            self.device_label.setStyleSheet(f"font-weight: bold; color: {self.colors.get('success', '#4CAF50')};")
            self.log_signal.emit(f"设备已连接: {device_id}")
        else:
            self.device_label.setText("未连接")
            self.device_label.setStyleSheet("font-weight: bold; color: #FF9800;")
            self.log_signal.emit("设备已断开")

    def closeEvent(self, event):
        """关闭事件 - 停止后台线程"""
        try:
            self.log_signal.emit("窗口关闭，停止后台线程...")
            self._stop_device_check()
            self._cleanup_flash_thread()
            # 等待下载线程结束
            if hasattr(self, '_download_thread') and self._download_thread and self._download_thread.isRunning():
                self.log_signal.emit("等待下载线程结束...")
                if self._download_worker:
                    self._download_worker.cancel()
                self._download_thread.quit()
                self._download_thread.wait(3000)
        except Exception as e:
            tb = traceback.format_exc()
            self.log_signal.emit(f"关闭异常: {str(e)}\n{tb}")
        event.accept()

    def append_log(self, message):
        """追加日志到控制台"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.console.append(f"[{timestamp}] {message}")
