# -*- coding: utf-8 -*-
"""
GPIO Control Dialog - GPIO CMD 专项
支持Eywa/Middleware接口，SOC/MCU平台，GPIO电平控制和计算器
"""
import re
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QMessageBox, QGroupBox, QLineEdit, QComboBox,
    QWidget, QFrame, QApplication
)
from PySide6.QtCore import Qt, Signal

# PyQt6 兼容别名
pyqtSignal = Signal


class GPIOCalculator:
    """GPIO编号计算器 - 支持多SOC平台和MCU平台"""

    # SOC GPIO bank偏移量 (通用)
    SOC_BANK_OFFSET = {
        'A': 0, 'B': 8, 'C': 16, 'D': 24
    }

    # 支持的SOC平台列表
    SUPPORTED_SOC_PLATFORMS = {
        "rk35xx": "Rockchip RK35xx (RK3566/RK3568/RK3588等)",
        "rk33xx": "Rockchip RK33xx (RK3326/RK3328/RK3399等)",
        "rk31xx": "Rockchip RK31xx (RK3126/RK3128等)",
        "rk30xx": "Rockchip RK30xx (RK3066等)",
    }

    # MCU GPIO基数: MCU_GRP_PIN(group, pin) = ((group + 1) << 16) + pin
    # PAx = (0+1)<<16 + x = 0x10000 + x = 65536 + x
    # PBx = (1+1)<<16 + x = 0x20000 + x = 131072 + x
    MCU_GROUP_BASE = 0  # MCUA_GROUP_BASE for GD32F310
    MCU_PIN_PER_GROUP = 32  # 每端口32个pin (0-31)

    @staticmethod
    def mcu_grp_pin(group, pin):
        """MCU GPIO编号计算: ((group + 1) << 16) + pin"""
        return ((group + 1) << 16) + pin

    @classmethod
    def mcu_name_to_number(cls, port_letter, pin):
        """MCU GPIO名称转编号: PAx -> number"""
        group = ord(port_letter) - ord('A') + cls.MCU_GROUP_BASE
        return cls.mcu_grp_pin(group, pin)

    @classmethod
    def mcu_number_to_parts(cls, number):
        """MCU GPIO编号转 (port_letter, pin) 或 None"""
        if not isinstance(number, int) or number < 0x10000:
            return None
        group_plus_1 = number >> 16
        pin = number & 0xFFFF
        if pin >= cls.MCU_PIN_PER_GROUP:
            return None
        group_index = group_plus_1 - 1 - cls.MCU_GROUP_BASE
        if 0 <= group_index < 26:
            return (chr(ord('A') + group_index), pin)
        return None

    @staticmethod
    def parse_gpio_name(name, platform_hint=None):
        """
        解析GPIO名称，返回(number, platform)
        支持格式：PA0, PB15, GPIO0_B0, GPIO3_D2, 或纯数字
        platform_hint: "soc" 或 "mcu"，用于区分PA0等歧义名称
        """
        name = name.strip().upper()

        # 纯数字
        if name.isdigit():
            return int(name), "unknown"

        # SOC格式: GPIO{bank}_{port}{pin}
        soc_match = re.match(r'GPIO(\d+)_([A-D])(\d+)', name)
        if soc_match:
            bank = int(soc_match.group(1))
            port = soc_match.group(2)
            pin = int(soc_match.group(3))
            if pin <= 7:
                offset = GPIOCalculator.SOC_BANK_OFFSET.get(port, 0)
                return bank * 32 + offset + pin, "soc"

        # MCU格式: PA0, PB15, PC3, PD5, ..., PF31
        short_match = re.match(r'P([A-Z])(\d+)', name)
        if short_match:
            port = short_match.group(1)
            pin = int(short_match.group(2))
            if pin < GPIOCalculator.MCU_PIN_PER_GROUP:
                number = GPIOCalculator.mcu_name_to_number(port, pin)
                return number, "mcu"

        return None, None

    @staticmethod
    def number_to_name(number, platform):
        """
        将GPIO编号转换为名称
        platform: "soc" 或 "mcu"
        """
        if not isinstance(number, int) or number < 0:
            return None

        if platform == "mcu":
            parts = GPIOCalculator.mcu_number_to_parts(number)
            if parts:
                return f"P{parts[0]}{parts[1]}"
            return None
        elif platform == "soc":
            bank = number // 32
            remainder = number % 32
            if remainder < 8:
                port = 'A'
                pin = remainder
            elif remainder < 16:
                port = 'B'
                pin = remainder - 8
            elif remainder < 24:
                port = 'C'
                pin = remainder - 16
            else:
                port = 'D'
                pin = remainder - 24
            return f"GPIO{bank}_{port}{pin}"

        return None

    @staticmethod
    def convert(input_value, from_type, platform):
        """
        转换GPIO
        from_type: "name" 或 "number"
        platform: "soc" 或 "mcu"
        """
        if from_type == "name":
            number, detected_platform = GPIOCalculator.parse_gpio_name(input_value, platform)
            if number is None:
                return None, None, "无法解析GPIO名称"
            return number, detected_platform or platform, None
        elif from_type == "number":
            try:
                number = int(input_value)
                name = GPIOCalculator.number_to_name(number, platform)
                if name is None:
                    return None, None, "无法转换为GPIO名称"
                return name, platform, None
            except ValueError:
                return None, None, "请输入有效的数字"


class GPIOCommandBuilder:
    """GPIO命令构建器"""

    @staticmethod
    def build_cmd(prefix, interface, number, action):
        """
        构建GPIO命令
        prefix: "xbhfunc" 或 "xbhfunc_new"
        interface: "eywa" 或 "middleware"
        action: "high", "low", "read_output", "read_input"
        """
        if interface == "eywa":
            if action == "high":
                return f"{prefix} XbhApi_setGpioOutputValue {number} 1"
            elif action == "low":
                return f"{prefix} XbhApi_setGpioOutputValue {number} 0"
            elif action == "read_output":
                return f"{prefix} XbhApi_getGpioOutputValue {number}"
            elif action == "read_input":
                return f"{prefix} XbhApi_getGpioInputValue {number}"
        elif interface == "middleware":
            if action == "high":
                return f"{prefix} setGpioOutputValue {number} true"
            elif action == "low":
                return f"{prefix} setGpioOutputValue {number} false"
            elif action == "read_output":
                return f"{prefix} getGpioOutputValue {number}"
            elif action == "read_input":
                return f"{prefix} getGpioInputValue {number}"
        return None


class GPIOControlDialog(QDialog):
    """GPIO控制对话框 - GPIO CMD 专项"""

    log_signal = pyqtSignal(str)

    def __init__(self, parent, adb, device_id, colors):
        super().__init__(parent)
        self.adb = adb
        self.device_id = device_id
        self.colors = colors

        self.setWindowTitle("🔧 Gpio Control")
        self.setMinimumSize(700, 650)

        self.setup_ui()
        self.log_signal.connect(self.append_log)

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # ==================== GPIO 配置 ====================
        config_group = QGroupBox("⚙️ GPIO 配置")
        config_layout = QVBoxLayout(config_group)

        # 第一行：接口类型和命令前缀
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("接口类型:"))
        self.interface_combo = QComboBox()
        self.interface_combo.addItems(["eywa", "middleware"])
        row1.addWidget(self.interface_combo)

        row1.addWidget(QLabel("命令前缀:"))
        self.prefix_combo = QComboBox()
        self.prefix_combo.addItems(["xbhfunc_new", "xbhfunc"])
        row1.addWidget(self.prefix_combo)
        row1.addStretch()
        config_layout.addLayout(row1)

        # 第二行：平台类型和SOC型号
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("平台类型:"))
        self.platform_combo = QComboBox()
        self.platform_combo.addItems(["SOC", "MCU"])
        self.platform_combo.currentTextChanged.connect(self.on_platform_changed)
        row2.addWidget(self.platform_combo)

        self.soc_label = QLabel("SOC型号:")
        row2.addWidget(self.soc_label)
        self.soc_combo = QComboBox()
        for key, desc in GPIOCalculator.SUPPORTED_SOC_PLATFORMS.items():
            self.soc_combo.addItem(f"{key} - {desc}", key)
        row2.addWidget(self.soc_combo)
        row2.addStretch()
        config_layout.addLayout(row2)

        layout.addWidget(config_group)

        # ==================== GPIO 输入 ====================
        gpio_group = QGroupBox("📌 GPIO 输入")
        gpio_layout = QVBoxLayout(gpio_group)

        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("GPIO:"))
        self.gpio_input = QLineEdit()
        self.gpio_input.setPlaceholderText("输入编号或名称 (如: 8, PA0, GPIO0_B0, PCA_IO0_0)")
        self.gpio_input.textChanged.connect(self.update_preview)
        input_layout.addWidget(self.gpio_input)

        validate_btn = QPushButton("✅ Validate")
        validate_btn.clicked.connect(self.validate_gpio)
        input_layout.addWidget(validate_btn)
        gpio_layout.addLayout(input_layout)

        self.gpio_info = QLabel("GPIO Info: -")
        self.gpio_info.setStyleSheet("font-weight: bold; color: #4CAF50;")
        gpio_layout.addWidget(self.gpio_info)

        layout.addWidget(gpio_group)

        # ==================== 电平控制 ====================
        control_group = QGroupBox("🎛️ 电平控制")
        control_layout = QVBoxLayout(control_group)

        output_layout = QHBoxLayout()
        high_btn = QPushButton("⬆️ HIGH 拉高")
        high_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px;")
        high_btn.clicked.connect(lambda: self.execute_gpio_cmd("high"))
        output_layout.addWidget(high_btn)

        low_btn = QPushButton("⬇️ LOW 拉低")
        low_btn.setStyleSheet("background-color: #f44336; color: white; padding: 8px;")
        low_btn.clicked.connect(lambda: self.execute_gpio_cmd("low"))
        output_layout.addWidget(low_btn)
        control_layout.addLayout(output_layout)

        read_layout = QHBoxLayout()
        read_output_btn = QPushButton("📤 读输出电平")
        read_output_btn.setStyleSheet("padding: 8px;")
        read_output_btn.clicked.connect(lambda: self.execute_gpio_cmd("read_output"))
        read_layout.addWidget(read_output_btn)

        read_input_btn = QPushButton("📥 读输入电平")
        read_input_btn.setStyleSheet("padding: 8px;")
        read_input_btn.clicked.connect(lambda: self.execute_gpio_cmd("read_input"))
        read_layout.addWidget(read_input_btn)
        control_layout.addLayout(read_layout)

        layout.addWidget(control_group)

        # ==================== 命令预览 ====================
        preview_group = QGroupBox("👁️ 命令预览")
        preview_layout = QVBoxLayout(preview_group)

        preview_row = QHBoxLayout()
        self.preview_label = QLabel("-")
        self.preview_label.setStyleSheet(
            "font-family: monospace; color: #00ff00; background-color: #1e1e1e; padding: 10px; border-radius: 4px; border: 1px solid #333333;"
        )
        self.preview_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        preview_row.addWidget(self.preview_label)

        copy_btn = QPushButton("📋 复制")
        copy_btn.setFixedWidth(60)
        copy_btn.clicked.connect(self.copy_preview_command)
        preview_row.addWidget(copy_btn)

        preview_layout.addLayout(preview_row)

        layout.addWidget(preview_group)

        # ==================== GPIO 计算器 ====================
        calc_group = QGroupBox("🔢 GPIO 计算器")
        calc_layout = QVBoxLayout(calc_group)

        # 名称→编号
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("名称→编号:"))
        self.calc_name_input = QLineEdit()
        self.calc_name_input.setPlaceholderText("如: PB7, GPIO7_B4, PCA_IO0_0")
        name_row.addWidget(self.calc_name_input)
        name_to_num_btn = QPushButton("转换")
        name_to_num_btn.clicked.connect(self.convert_name_to_number)
        name_row.addWidget(name_to_num_btn)
        self.calc_name_result = QLabel("→ -")
        self.calc_name_result.setStyleSheet("font-weight: bold; min-width: 80px;")
        name_row.addWidget(self.calc_name_result)
        calc_layout.addLayout(name_row)

        # 编号→名称
        num_row = QHBoxLayout()
        num_row.addWidget(QLabel("编号→名称:"))
        self.calc_num_input = QLineEdit()
        self.calc_num_input.setPlaceholderText("如: 236, 8, 394")
        num_row.addWidget(self.calc_num_input)
        num_to_name_btn = QPushButton("转换")
        num_to_name_btn.clicked.connect(self.convert_number_to_name)
        num_row.addWidget(num_to_name_btn)
        self.calc_num_result = QLabel("→ -")
        self.calc_num_result.setStyleSheet("font-weight: bold; min-width: 80px;")
        num_row.addWidget(self.calc_num_result)
        calc_layout.addLayout(num_row)

        layout.addWidget(calc_group)

        # ==================== 输出控制台 ====================
        console_group = QGroupBox("📊 输出控制台")
        console_layout = QVBoxLayout(console_group)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setMaximumHeight(120)
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

    def on_platform_changed(self, platform):
        """平台类型切换"""
        is_soc = (platform == "SOC")
        self.soc_label.setVisible(is_soc)
        self.soc_combo.setVisible(is_soc)

    def get_platform_hint(self):
        """获取当前平台类型"""
        return "soc" if self.platform_combo.currentIndex() == 0 else "mcu"

    def validate_gpio(self):
        """验证GPIO输入"""
        text = self.gpio_input.text().strip()
        if not text:
            self.gpio_info.setText("GPIO Info: 请输入GPIO编号或名称")
            return

        platform_hint = self.get_platform_hint()
        number, platform = GPIOCalculator.parse_gpio_name(text, platform_hint)

        if number is not None:
            name = GPIOCalculator.number_to_name(number, platform or platform_hint)
            self.gpio_info.setText(f"GPIO Info: Number={number}, Name={name}, Platform={platform}")
        else:
            self.gpio_info.setText("GPIO Info: ❌ 无法解析GPIO，请检查格式")

    def update_preview(self):
        """更新命令预览"""
        text = self.gpio_input.text().strip()
        if not text:
            self.preview_label.setText("-")
            return

        platform_hint = self.get_platform_hint()
        number, _ = GPIOCalculator.parse_gpio_name(text, platform_hint)
        if number is None:
            self.preview_label.setText("Invalid GPIO input")
            return

        prefix = self.prefix_combo.currentText()
        interface = self.interface_combo.currentText()
        cmd = GPIOCommandBuilder.build_cmd(prefix, interface, number, "high")
        self.preview_label.setText(cmd if cmd else "-")

    def execute_gpio_cmd(self, action):
        """执行GPIO命令"""
        text = self.gpio_input.text().strip()
        if not text:
            QMessageBox.warning(self, "警告", "请输入GPIO编号或名称")
            return

        # 检查设备连接
        if not self.device_id:
            QMessageBox.warning(self, "警告", "未连接设备，请先连接设备后再执行命令\n\nGPIO计算器功能可正常使用")
            return

        platform_hint = self.get_platform_hint()
        number, platform = GPIOCalculator.parse_gpio_name(text, platform_hint)
        if number is None:
            QMessageBox.warning(self, "警告", "无法解析GPIO，请检查格式")
            return

        prefix = self.prefix_combo.currentText()
        interface = self.interface_combo.currentText()

        cmd = GPIOCommandBuilder.build_cmd(prefix, interface, number, action)
        if not cmd:
            QMessageBox.warning(self, "错误", "无法构建命令")
            return

        self.log_signal.emit(f"Executing: {cmd}")

        result = self.adb.run_command(f'-s {self.device_id} shell "{cmd}"')

        if result['success']:
            output = result['stdout'].strip()
            self.log_signal.emit(f"Result: {output if output else 'success'}")
        else:
            error = result.get('stderr', result.get('stdout', 'Unknown error'))
            self.log_signal.emit(f"Error: {error}")

    def convert_name_to_number(self):
        """名称转编号"""
        name = self.calc_name_input.text().strip()
        if not name:
            self.calc_name_result.setText("→ 请输入名称")
            return

        platform = self.get_platform_hint()
        number, detected_platform, error = GPIOCalculator.convert(name, "name", platform)

        if error:
            self.calc_name_result.setText(f"→ {error}")
        else:
            self.calc_name_result.setText(f"→ {number}")

    def convert_number_to_name(self):
        """编号转名称"""
        num_str = self.calc_num_input.text().strip()
        if not num_str:
            self.calc_num_result.setText("→ 请输入编号")
            return

        platform = self.get_platform_hint()
        name, _, error = GPIOCalculator.convert(num_str, "number", platform)

        if error:
            self.calc_num_result.setText(f"→ {error}")
        else:
            self.calc_num_result.setText(f"→ {name}")

    def copy_preview_command(self):
        """复制命令预览内容到剪贴板"""
        command = self.preview_label.text()
        if command and command != "-":
            clipboard = QApplication.clipboard()
            clipboard.setText(command)
            self.log_signal.emit(f"Copied: {command}")
        else:
            self.log_signal.emit("No command to copy")

    def update_device(self, device_id):
        """更新设备ID（由主界面调用同步设备信息）"""
        self.device_id = device_id
        if device_id:
            self.log_signal.emit(f"Device updated: {device_id}")
        else:
            self.log_signal.emit("Device disconnected")

    def append_log(self, message):
        """追加日志到控制台"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.console.append(f"[{timestamp}] {message}")
