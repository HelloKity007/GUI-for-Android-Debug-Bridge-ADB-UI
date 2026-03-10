# -*- coding: utf-8 -*-

import argparse
import re
import shutil
from pathlib import Path

"""
核心转换逻辑 (按执行顺序):
1.  底层绑定转换:
    - `sip` -> `sip`
    - `wrapinstance` -> `wrapinstance`
2.  核心API转换:
    - `pyqtSignal` -> `pyqtSignal`
    - `pyqtSlot` -> `pyqtSlot`
    - `pyqtProperty` -> `pyqtProperty`
3.  枚举 (Enum) 语法转换 (最关键部分):
    - `QClassName.EnumType.Value` -> `QClassName.Value` (例如: QFileDialog.FileMode.ExistingFiles -> QFileDialog.ExistingFiles)
    - `Qt.EnumType.Value` -> `Qt.Value` (例如: Qt.AlignmentFlag.AlignCenter -> Qt.AlignCenter)
4.  全局模块名转换:
    - `PyQt6` -> `PyQt5`
"""

# 定义替换规则. 顺序至关重要, 从最具体到最通用, 确保不会错误替换.
REPLACEMENT_RULES = [
    # 规则 1: 转换底层绑定 (sip -> sip).
    # PyQt5使用sip, PySide6使用shiboken6. wrapInstance函数名也需小写.
    (re.compile(r'\bshiboken6\b'), 'sip'),
    (re.compile(r'\bwrapInstance\b'), 'wrapinstance'),

    # 规则 2: 转换 pyqtSignal, pyqtSlot 和 pyqtProperty.
    # 使用负向前瞻 `(?!pyqt)` 避免重复替换, 例如将 `pyqtSignal` 错误地再次处理.
    (re.compile(r'\b(?!pyqt)pyqtSignal\b'), 'pyqtSignal'),
    (re.compile(r'\b(?!pyqt)pyqtSlot\b'), 'pyqtSlot'),
    (re.compile(r'\b(?!pyqt)pyqtProperty\b'), 'pyqtProperty'),

    # 规则 3: 转换 PyQt6 风格的枚举 (Enum). 这是确保运行正确的关键.
    # 规则 3a: 处理 QClassName 内的枚举, 例如 `QFileDialog.FileMode.ExistingFiles`.
    # 模式匹配: (QClassName).(EnumTypeName).(EnumValue) -> \1.\3 (即 QClassName.EnumValue).
    (re.compile(r'\b(Q[A-Z][a-zA-Z0-9_]+)\.([A-Z][a-zA-Z]+)\.([a-zA-Z0-9_]+)\b'), r'\1.\3'),
    
    # 规则 3b: 处理 Qt 命名空间内的枚举, 例如 `Qt.AlignmentFlag.AlignCenter`.
    # 负向前瞻 `(?!emit|...|)` 避免错误替换 Qt 的方法名.
    (re.compile(r'\bQt\.([A-Z][a-zA-Z]+)\.(?!emit|connect|disconnect|sender)([a-zA-Z0-9_]+)\b'), r'Qt.\2'),
    
    # 规则 4: 全局替换模块名. 必须在所有规则之后执行.
    (re.compile(r'PyQt6'), 'PyQt5'),
]

def convert_file_content(content: str) -> str:
    """对单个文件的内容应用所有替换规则."""
    for pattern, replacement in REPLACEMENT_RULES:
        content = pattern.sub(replacement, content)
    return content

def process_directory(source_dir: Path, output_dir: Path):
    """处理整个目录, 转换 .py 文件并复制其他文件."""
    if not source_dir.is_dir():
        print(f"❌ 错误: 源路径 '{source_dir}' 不是一个有效的目录.")
        return

    print(f"🚀 开始转换项目...")
    print(f"   源目录: {source_dir}")
    print(f"   目标目录: {output_dir}")
    print("-" * 40)

    file_converted_count = 0
    file_copied_count = 0

    for item in source_dir.rglob('*'):
        relative_path = item.relative_to(source_dir)
        dest_path = output_dir / relative_path

        if item.is_dir():
            dest_path.mkdir(parents=True, exist_ok=True)
            continue
            
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        if item.suffix == '.py':
            try:
                # 增强的容错性: 尝试以 utf-8 读取
                with open(item, 'r', encoding='utf-8') as f_in:
                    original_content = f_in.read()
                
                converted_content = convert_file_content(original_content)
                
                with open(dest_path, 'w', encoding='utf-8') as f_out:
                    f_out.write(converted_content)
                print(f"🔧 正在转换: {relative_path}")
                file_converted_count += 1

            except UnicodeDecodeError:
                print(f"⚠️ 警告: 文件 '{relative_path}' 不是 UTF-8 编码, 无法转换. 将直接复制.")
                shutil.copy2(item, dest_path)
                file_copied_count += 1
            except Exception as e:
                print(f"❌ 处理文件 '{item}' 时发生意外错误: {e}")
                print(f"   -> 将作为副本复制原始文件以确保安全.")
                shutil.copy2(item, dest_path)
                file_copied_count += 1
        else:
            print(f"📋 正在复制: {relative_path}")
            shutil.copy2(item, dest_path)
            file_copied_count += 1
    
    print("-" * 40)
    print("✅ 转换完成!")
    print(f"   - {file_converted_count} 个 Python 文件已转换.")
    print(f"   - {file_copied_count} 个其他文件已复制.")
    print(f"   - 转换后的项目已保存到: {output_dir}")

def main():
    parser = argparse.ArgumentParser(
        description="自动将 PyQt6 Python 项目转换为 PyQt5 项目.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("source_dir", type=str, help="包含 PyQt6 项目的源目录.")
    parser.add_argument(
        "-o", "--output_dir", type=str,
        help="用于保存转换后的 PyQt5 项目的目标目录.\n如果未提供, 将自动创建 '源目录名_pyqt5'."
    )
    
    args = parser.parse_args()
    
    source_path = Path(args.source_dir).resolve()
    
    if args.output_dir:
        output_path = Path(args.output_dir).resolve()
    else:
        output_path = source_path.parent / f"{source_path.name}_pyqt5"
        
    process_directory(source_path, output_path)

if __name__ == "__main__":
    main()