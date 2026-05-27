# -*- coding: utf-8 -*-
"""
打包脚本 - 将 ADB GUI Tool 打包为可执行文件
每次打包自动递增构建号
"""
import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

# 导入版本管理
from version import get_version_manager


class Builder:
    """打包构建器"""
    
    def __init__(self):
        self.project_dir = Path(__file__).parent.parent
        self.dist_dir = self.project_dir / "dist"
        self.build_dir = self.project_dir / "build"
        self.version_manager = get_version_manager()
        
    def check_pyinstaller(self):
        """检查 PyInstaller 是否安装"""
        try:
            import PyInstaller
            return True
        except ImportError:
            return False
    
    def install_pyinstaller(self):
        """安装 PyInstaller"""
        print("[信息] 正在安装 PyInstaller...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "pyinstaller", "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"[错误] 安装 PyInstaller 失败: {result.stderr}")
            return False
        print("[成功] PyInstaller 安装完成")
        return True
    
    def clean_build(self):
        """清理之前的构建文件"""
        print("[信息] 清理构建文件...")
        
        # 清理 build 目录
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
            print(f"  - 已删除: {self.build_dir}")
        
        # 清理旧的 dist（可选，保留以允许用户选择）
        # if self.dist_dir.exists():
        #     shutil.rmtree(self.dist_dir)
        #     print(f"  - 已删除: {self.dist_dir}")
        
        # 清理 __pycache__
        for pycache in self.project_dir.rglob("__pycache__"):
            shutil.rmtree(pycache)
            print(f"  - 已删除: {pycache}")
        
        print("[成功] 清理完成")
    
    def bump_build_number(self):
        """递增构建号"""
        old_build = self.version_manager.build_number
        new_build = self.version_manager.bump_build()
        print(f"[信息] 构建号: {old_build} -> {new_build}")
        return new_build
    
    def get_version_info(self):
        """获取版本信息"""
        version = self.version_manager.version
        build = self.version_manager.build_number
        full_version = f"{version}.{build}"
        return version, build, full_version
    
    def build(self, onefile=False, console=False, icon=None):
        """
        执行打包
        :param onefile: 是否打包为单文件
        :param console: 是否显示控制台窗口
        :param icon: 图标文件路径
        """
        print("=" * 50)
        print("ADB GUI Tool - 打包构建")
        print("=" * 50)
        
        # 检查 PyInstaller
        if not self.check_pyinstaller():
            if not self.install_pyinstaller():
                print("[错误] 无法安装 PyInstaller，打包失败")
                return False
        
        # 递增构建号
        self.bump_build_number()
        version, build, full_version = self.get_version_info()
        
        print(f"\n[信息] 版本: {version}")
        print(f"[信息] 构建号: {build}")
        print(f"[信息] 完整版本: {full_version}")
        print(f"[信息] 打包模式: {'单文件' if onefile else '目录'}")
        print(f"[信息] 控制台: {'显示' if console else '隐藏'}")
        print()
        
        # 清理
        self.clean_build()
        
        # 构建 PyInstaller 命令
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--name", f"ADB_GUI_Tool_v{full_version}",
            "--noconfirm",
        ]
        
        if onefile:
            cmd.append("--onefile")
        else:
            cmd.append("--onedir")
        
        if not console:
            cmd.append("--windowed")
        
        if icon and Path(icon).exists():
            cmd.extend(["--icon", icon])
        
        # 添加数据文件
        # extensions 目录
        cmd.extend(["--add-data", f"extensions{os.pathsep}extensions"])
        # plugins 目录
        cmd.extend(["--add-data", f"plugins{os.pathsep}plugins"])
        # apks 目录（空目录）
        cmd.extend(["--add-data", f"apks{os.pathsep}apks"])
        # screenshots 目录（空目录）
        cmd.extend(["--add-data", f"screenshots{os.pathsep}screenshots"])
        # logs 目录（空目录）
        cmd.extend(["--add-data", f"logs{os.pathsep}logs"])
        # config.json
        cmd.extend(["--add-data", f"config.json{os.pathsep}."])
        # buttons_cmd.json
        cmd.extend(["--add-data", f"buttons_cmd.json{os.pathsep}."])
        # device_groups.json
        if Path("device_groups.json").exists():
            cmd.extend(["--add-data", f"device_groups.json{os.pathsep}."])
        # docs 目录
        if Path("docs").exists():
            cmd.extend(["--add-data", f"docs{os.pathsep}docs"])
        
        # 排除 PyQt6（避免与 PySide6 冲突）
        cmd.extend(["--exclude-module", "PyQt6"])
        cmd.extend(["--exclude-module", "PyQt6.sip"])

        # 隐藏导入
        hidden_imports = [
            "qfluentwidgets",
            "websocket",
            "loguru",
            "requests",
            "curl_cffi",
        ]
        for imp in hidden_imports:
            cmd.extend(["--hidden-import", imp])
        
        # 主脚本
        cmd.append("adb_gui.py")
        
        print("[信息] 执行命令:")
        print(" ".join(cmd))
        print()
        
        # 执行打包
        result = subprocess.run(cmd, cwd=self.project_dir)
        
        if result.returncode != 0:
            print("\n[错误] 打包失败！")
            return False
        
        print("\n[成功] 打包完成！")
        
        # 显示输出路径
        output_dir = self.dist_dir / f"ADB_GUI_Tool_v{full_version}"
        if onefile:
            output_exe = self.dist_dir / f"ADB_GUI_Tool_v{full_version}.exe"
            print(f"[信息] 输出文件: {output_exe}")
        else:
            output_exe = output_dir / f"ADB_GUI_Tool_v{full_version}.exe"
            print(f"[信息] 输出目录: {output_dir}")
            print(f"[信息] 可执行文件: {output_exe}")
        
        # 保存构建信息
        build_info = {
            "version": version,
            "build_number": build,
            "full_version": full_version,
            "build_time": datetime.now().isoformat(),
            "onefile": onefile,
            "console": console,
            "output_path": str(output_exe),
        }
        
        build_info_file = self.project_dir / "build_info.json"
        with open(build_info_file, 'w', encoding='utf-8') as f:
            json.dump(build_info, f, indent=2, ensure_ascii=False)
        
        print(f"\n[信息] 构建信息已保存: {build_info_file}")
        return True


def print_usage():
    """打印使用说明"""
    print("""
用法: python build.py [选项]

选项:
  --onefile     打包为单文件（默认：目录模式）
  --console     显示控制台窗口（默认：隐藏）
  --icon PATH   指定图标文件路径
  --clean       仅清理构建文件
  --version     显示当前版本信息
  --bump TYPE   递增版本号 (major/minor/patch)
  -h, --help    显示此帮助信息

示例:
  python build.py                    # 默认打包（目录模式，隐藏控制台）
  python build.py --onefile          # 打包为单文件
  python build.py --console          # 显示控制台（调试用）
  python build.py --bump patch       # 递增补丁版本号后打包
  python build.py --version          # 查看版本信息
""")


def main():
    """主函数"""
    args = sys.argv[1:]
    
    if "-h" in args or "--help" in args:
        print_usage()
        return
    
    if "--version" in args:
        vm = get_version_manager()
        print(f"当前版本: {vm.version}")
        print(f"构建号: {vm.build_number}")
        print(f"完整版本: {vm.full_version}")
        return
    
    if "--bump" in args:
        idx = args.index("--bump")
        if idx + 1 < len(args):
            bump_type = args[idx + 1]
            vm = get_version_manager()
            new_version = vm.bump_version(bump_type)
            print(f"[成功] 版本号已更新: {new_version}")
            # 移除 --bump 参数，继续打包
            args.pop(idx + 1)
            args.pop(idx)
        else:
            print("[错误] --bump 需要指定类型 (major/minor/patch)")
            return
    if "--clean" in args:
        builder = Builder()
        builder.clean_build()
        return
    
    # 解析参数
    onefile = "--onefile" in args
    console = "--console" in args
    
    icon = None
    if "--icon" in args:
        idx = args.index("--icon")
        if idx + 1 < len(args):
            icon = args[idx + 1]
    
    # 执行打包
    builder = Builder()
    success = builder.build(onefile=onefile, console=console, icon=icon)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

