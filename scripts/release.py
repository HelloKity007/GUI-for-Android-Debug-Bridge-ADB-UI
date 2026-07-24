# -*- coding: utf-8 -*-
"""
正式发布管理脚本
自动化版本发布流程：打包 -> 复制到 release 目录 -> 生成发布说明
"""
import os
import sys
import json
import shutil
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Optional

# 导入版本管理和构建模块
from version import get_version_manager
from build import Builder


class ReleaseManager:
    """正式发布管理器"""

    def __init__(self):
        self.project_dir = Path(__file__).parent.parent
        self.release_dir = self.project_dir / "release"
        self.dist_dir = self.project_dir / "dist"
        self.version_manager = get_version_manager()

        # 确保 release 目录存在
        self.release_dir.mkdir(exist_ok=True)

    def get_version_info(self) -> dict:
        """获取版本信息"""
        version = self.version_manager.version
        build = self.version_manager.build_number
        full_version = f"{version}.{build}"
        return {
            'version': version,
            'build': build,
            'full_version': full_version,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'datetime': datetime.now().isoformat()
        }

    def build_package(self, onefile: bool = False, console: bool = False) -> bool:
        """
        执行打包
        :param onefile: 是否打包为单文件
        :param console: 是否显示控制台
        :return: 是否成功
        """
        print("\n" + "=" * 60)
        print("第 1 步: 执行打包")
        print("=" * 60)

        builder = Builder()
        success = builder.build(onefile=onefile, console=console)

        if not success:
            print("[错误] 打包失败！")
            return False

        print("[成功] 打包完成")
        return True

    def copy_to_release(self, version_info: dict, onefile: bool = False) -> Optional[Path]:
        """
        将打包文件复制到 release 目录
        :param version_info: 版本信息
        :param onefile: 是否为单文件模式
        :return: release 目录路径
        """
        print("\n" + "=" * 60)
        print("第 2 步: 复制到 Release 目录")
        print("=" * 60)

        full_version = version_info['full_version']
        version = version_info['version']
        date = version_info['date']

        # 源文件路径
        if onefile:
            source = self.dist_dir / f"ADB_GUI_Tool_v{full_version}.exe"
            if not source.exists():
                print(f"[错误] 找不到打包文件: {source}")
                return None
        else:
            source = self.dist_dir / f"ADB_GUI_Tool_v{full_version}"
            if not source.exists() or not source.is_dir():
                print(f"[错误] 找不到打包目录: {source}")
                return None

        # 目标目录: release/v{version}_{date}
        release_name = f"v{version}_{date}"
        target_dir = self.release_dir / release_name

        # 如果目录已存在，添加序号
        counter = 1
        while target_dir.exists():
            release_name = f"v{version}_{date}_{counter}"
            target_dir = self.release_dir / release_name
            counter += 1

        target_dir.mkdir(parents=True)
        print(f"[信息] 创建发布目录: {target_dir}")

        # 复制文件
        if onefile:
            target_exe = target_dir / f"ADB_GUI_Tool_v{version}.exe"
            shutil.copy2(source, target_exe)
            print(f"[成功] 已复制: {target_exe.name}")
        else:
            target_subdir = target_dir / f"ADB_GUI_Tool_v{version}"
            shutil.copytree(source, target_subdir)
            print(f"[成功] 已复制目录: {target_subdir.name}")

        return target_dir

    def create_zip_archive(self, release_dir: Path, version_info: dict) -> Optional[Path]:
        """
        创建 ZIP 压缩包
        :param release_dir: release 目录路径
        :param version_info: 版本信息
        :return: ZIP 文件路径
        """
        print("\n" + "=" * 60)
        print("第 3 步: 创建 ZIP 压缩包")
        print("=" * 60)

        version = version_info['version']
        zip_name = f"ADB_GUI_Tool_v{version}.zip"
        zip_path = release_dir / zip_name

        # 获取要压缩的内容
        contents = list(release_dir.iterdir())
        if not contents:
            print("[错误] Release 目录为空")
            return None

        print(f"[信息] 创建压缩包: {zip_name}")

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for item in contents:
                if item == zip_path:  # 跳过压缩包自身
                    continue

                if item.is_file():
                    zipf.write(item, item.name)
                    print(f"  - 添加文件: {item.name}")
                elif item.is_dir():
                    for root, dirs, files in os.walk(item):
                        for file in files:
                            file_path = Path(root) / file
                            arcname = file_path.relative_to(release_dir)
                            zipf.write(file_path, arcname)
                    print(f"  - 添加目录: {item.name}")

        print(f"[成功] 压缩包已创建: {zip_path}")
        return zip_path

    def generate_release_notes(self, release_dir: Path, version_info: dict, zip_path: Optional[Path]) -> Path:
        """
        生成发布说明
        :param release_dir: release 目录路径
        :param version_info: 版本信息
        :param zip_path: ZIP 文件路径
        :return: 发布说明文件路径
        """
        print("\n" + "=" * 60)
        print("第 4 步: 生成发布说明")
        print("=" * 60)

        version = version_info['version']
        full_version = version_info['full_version']
        date = version_info['date']

        # 从 CHANGELOG.md 提取当前版本的变更内容
        changelog_file = self.project_dir / "CHANGELOG.md"
        changelog_content = ""

        if changelog_file.exists():
            with open(changelog_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                in_version_section = False
                for line in lines:
                    # 匹配版本标题
                    if f"## [{version}]" in line or f"## [Unreleased]" in line:
                        in_version_section = True
                        continue
                    # 遇到下一个版本标题，停止
                    if in_version_section and line.startswith("## ["):
                        break
                    if in_version_section:
                        changelog_content += line

        # 生成发布说明内容
        notes_content = f"""# ADB GUI Tool v{version} 发布说明

**发布日期**: {date}
**完整版本**: {full_version}
**发布类型**: 正式版 (Release)

---

## 📦 下载

"""

        if zip_path:
            notes_content += f"- **压缩包**: [{zip_path.name}](./{zip_path.name})\n"

        # 列出可执行文件
        exe_files = list(release_dir.glob("**/*.exe"))
        if exe_files:
            notes_content += f"\n**可执行文件**:\n"
            for exe in exe_files:
                rel_path = exe.relative_to(release_dir)
                notes_content += f"- `{rel_path}`\n"

        notes_content += f"""
---

## 📋 更新内容

{changelog_content.strip() if changelog_content else '详见 CHANGELOG.md'}

---

## 💻 系统要求

- **操作系统**: Windows 10/11 (64位)
- **Android 设备**: 需启用 USB 调试
- **ADB**: 内置 Android Platform Tools

---

## 🚀 使用方法

1. 下载并解压缩包
2. 运行 `ADB_GUI_Tool_v{version}.exe`
3. 首次使用会提示选择 ADB 路径（已内置，直接确认即可）
4. 连接 Android 设备，开始使用

---

## 📖 文档

- [README.md](../README.md) - 完整使用文档
- [CHANGELOG.md](../CHANGELOG.md) - 完整更新日志

---

## 🐛 问题反馈

如遇到问题，请在 GitHub Issues 提交反馈。

---

**构建时间**: {version_info['datetime']}
**构建号**: {version_info['build']}
"""

        # 保存发布说明
        notes_file = release_dir / "RELEASE_NOTES.md"
        with open(notes_file, 'w', encoding='utf-8') as f:
            f.write(notes_content)

        print(f"[成功] 发布说明已生成: {notes_file.name}")
        return notes_file

    def create_release_manifest(self, release_dir: Path, version_info: dict) -> Path:
        """
        创建 release 清单文件
        :param release_dir: release 目录路径
        :param version_info: 版本信息
        :return: 清单文件路径
        """
        manifest = {
            "version": version_info['version'],
            "full_version": version_info['full_version'],
            "build_number": version_info['build'],
            "release_date": version_info['date'],
            "build_datetime": version_info['datetime'],
            "files": []
        }

        # 收集文件信息
        for item in release_dir.iterdir():
            if item.is_file() and item.suffix != '.json':
                file_info = {
                    "name": item.name,
                    "size": item.stat().st_size,
                    "type": "executable" if item.suffix == '.exe' else "archive" if item.suffix == '.zip' else "document"
                }
                manifest["files"].append(file_info)

        # 保存清单
        manifest_file = release_dir / "manifest.json"
        with open(manifest_file, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        print(f"[信息] 清单文件已生成: {manifest_file.name}")
        return manifest_file

    def update_release_index(self, release_dir: Path, version_info: dict):
        """
        更新 release 索引文件
        :param release_dir: release 目录路径
        :param version_info: 版本信息
        """
        index_file = self.release_dir / "index.json"

        # 读取现有索引
        if index_file.exists():
            with open(index_file, 'r', encoding='utf-8') as f:
                index = json.load(f)
        else:
            index = {
                "releases": []
            }

        # 添加新版本
        release_entry = {
            "version": version_info['version'],
            "full_version": version_info['full_version'],
            "date": version_info['date'],
            "path": release_dir.name,
            "latest": True
        }

        # 将之前的版本标记为非最新
        for release in index["releases"]:
            release["latest"] = False

        # 插入到最前面
        index["releases"].insert(0, release_entry)

        # 保存索引
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

        print(f"[信息] Release 索引已更新")

    def _update_version_info_py(self, version_info: dict):
        """
        更新 version_info.py 文件（应用启动时读取）
        :param version_info: 版本信息
        """
        version_info_file = self.project_dir / "version_info.py"

        content = f'''# -*- coding: utf-8 -*-
"""
版本信息文件 - 统一管理应用版本号
"""
# 主版本号.次版本号.修订号.构建号
VERSION = "{version_info['version']}"
BUILD_NUMBER = {version_info['build']}
FULL_VERSION = f"{{VERSION}}.{{BUILD_NUMBER}}"
'''

        try:
            with open(version_info_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[信息] version_info.py 已更新: v{version_info['full_version']}")
        except Exception as e:
            print(f"[警告] 更新 version_info.py 失败: {e}")

    def release(self, onefile: bool = False, console: bool = False, skip_build: bool = False, create_zip: bool = True) -> bool:
        """
        执行完整的发布流程
        :param onefile: 是否打包为单文件
        :param console: 是否显示控制台
        :param skip_build: 是否跳过打包步骤
        :param create_zip: 是否创建 ZIP 压缩包
        :return: 是否成功
        """
        print("\n" + "=" * 60)
        print("ADB GUI Tool - 正式发布")
        print("=" * 60)

        # 获取版本信息
        version_info = self.get_version_info()
        print(f"\n[信息] 版本: {version_info['version']}")
        print(f"[信息] 完整版本: {version_info['full_version']}")
        print(f"[信息] 发布日期: {version_info['date']}")

        # 步骤 1: 打包
        if not skip_build:
            if not self.build_package(onefile=onefile, console=console):
                return False
        else:
            print("\n[信息] 跳过打包步骤")

        # 步骤 2: 复制到 release 目录
        release_dir = self.copy_to_release(version_info, onefile=onefile)
        if not release_dir:
            return False

        # 步骤 3: 创建 ZIP 压缩包
        zip_path = None
        if create_zip:
            zip_path = self.create_zip_archive(release_dir, version_info)

        # 步骤 4: 生成发布说明
        self.generate_release_notes(release_dir, version_info, zip_path)

        # 步骤 5: 创建清单
        self.create_release_manifest(release_dir, version_info)

        # 步骤 6: 更新索引
        self.update_release_index(release_dir, version_info)

        # 步骤 7: 更新 version_info.py（应用启动时读取）
        self._update_version_info_py(version_info)

        print("\n" + "=" * 60)
        print("✅ 发布完成！")
        print("=" * 60)
        print(f"\n发布目录: {release_dir}")
        print(f"版本: v{version_info['version']}")

        if zip_path:
            print(f"\n📦 压缩包: {zip_path.name}")

        print(f"\n发布说明: {release_dir / 'RELEASE_NOTES.md'}")

        return True


def print_usage():
    """打印使用说明"""
    print("""
用法: python release.py [选项]

选项:
  --onefile         打包为单文件（默认：目录模式）
  --console         显示控制台窗口（默认：隐藏）
  --skip-build      跳过打包步骤（使用已有的构建）
  --no-zip          不创建 ZIP 压缩包
  --bump TYPE       发布前递增版本号 (major/minor/patch)
  -h, --help        显示此帮助信息

示例:
  python release.py                        # 标准发布流程
  python release.py --onefile              # 单文件模式发布
  python release.py --bump patch           # 递增补丁版本号后发布
  python release.py --skip-build --no-zip  # 仅打包现有构建，不创建 ZIP
""")


def main():
    """主函数"""
    args = sys.argv[1:]

    if "-h" in args or "--help" in args:
        print_usage()
        return

    # 解析参数
    onefile = "--onefile" in args
    console = "--console" in args
    skip_build = "--skip-build" in args
    create_zip = "--no-zip" not in args

    # 版本号递增
    if "--bump" in args:
        idx = args.index("--bump")
        if idx + 1 < len(args):
            bump_type = args[idx + 1]
            from version import get_version_manager
            vm = get_version_manager()
            new_version = vm.bump_version(bump_type)
            print(f"[成功] 版本号已更新: {new_version}")
        else:
            print("[错误] --bump 需要指定类型 (major/minor/patch)")
            return

    # 执行发布
    manager = ReleaseManager()
    success = manager.release(
        onefile=onefile,
        console=console,
        skip_build=skip_build,
        create_zip=create_zip
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
