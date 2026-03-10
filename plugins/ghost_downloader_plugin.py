# -*- coding: utf-8 -*-
"""
Ghost Downloader 插件包装器
将 Ghost-Downloader-3 集成到 ADB GUI 工具中
"""
import os
import sys
import subprocess
from typing import Dict, Any, List
from pathlib import Path

from framework.plugin.plugin_interface import UIPluginInterface, PluginMetadata, PluginStatus
from framework.event.event_bus import EventBus


class GhostDownloaderPlugin(UIPluginInterface):
    """Ghost Downloader 插件 - 提供下载管理功能"""
    
    def __init__(self):
        self._metadata = PluginMetadata(
            id="ghost_downloader",
            name="Ghost Downloader",
            version="3.6.1",
            author="XiaoYouChR",
            description="多线程下载器，支持断点续传、浏览器扩展集成",
            dependencies=[],
            enabled=True
        )
        self._api = None
        self._event_bus = None
        self._process = None
        self._extension_path = None
        
    def get_metadata(self) -> PluginMetadata:
        """获取插件元数据"""
        return self._metadata
    
    def on_load(self, api, event_bus: EventBus) -> bool:
        """插件加载"""
        self._api = api
        self._event_bus = event_bus
        
        # 查找 Ghost-Downloader-3 路径
        self._extension_path = self._find_ghost_downloader_path()
        
        if self._extension_path:
            self._api.log_info(f"Ghost Downloader found at: {self._extension_path}", self._metadata.id)
            return True
        else:
            self._api.log_warning("Ghost Downloader not found in extensions directory", self._metadata.id)
            return True  # 仍然加载成功，只是路径未找到
    
    def on_unload(self) -> bool:
        """插件卸载"""
        # 关闭下载器进程
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
        
        self._api = None
        self._event_bus = None
        return True
    
    def on_enable(self) -> bool:
        """插件启用"""
        return True
    
    def on_disable(self) -> bool:
        """插件禁用"""
        return True
    
    def _find_ghost_downloader_path(self) -> str:
        """查找 Ghost-Downloader-3 路径"""
        # 从当前插件目录向上查找 extensions 目录
        base_dir = Path(__file__).parent.parent
        extensions_dir = base_dir / "extensions" / "Ghost-Downloader-3"
        
        if extensions_dir.exists():
            main_script = extensions_dir / "Ghost-Downloader-3.py"
            if main_script.exists():
                return str(extensions_dir)
        
        # 备用：检查相对于工作目录
        cwd = Path.cwd()
        extensions_dir = cwd / "extensions" / "Ghost-Downloader-3"
        if extensions_dir.exists():
            return str(extensions_dir)
        
        return None
    
    def launch_downloader(self, url: str = None, silence: bool = False) -> Dict[str, Any]:
        """
        启动 Ghost Downloader
        
        Args:
            url: 可选的下载链接
            silence: 是否静默启动
            
        Returns:
            启动结果
        """
        if not self._extension_path:
            return {
                'success': False,
                'error': 'Ghost Downloader 路径未找到'
            }
        
        try:
            main_script = os.path.join(self._extension_path, "Ghost-Downloader-3.py")
            
            # 构建命令
            cmd = [sys.executable, main_script]
            
            if silence:
                cmd.append("--silence")
            
            # 设置工作目录
            cwd = self._extension_path
            
            # 启动进程
            if sys.platform == "win32":
                # Windows 下使用 CREATE_NO_WINDOW 避免弹出控制台窗口
                self._process = subprocess.Popen(
                    cmd,
                    cwd=cwd,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                self._process = subprocess.Popen(cmd, cwd=cwd)
            
            self._api.log_info(f"Ghost Downloader started (PID: {self._process.pid})", self._metadata.id)
            
            return {
                'success': True,
                'pid': self._process.pid
            }
            
        except Exception as e:
            self._api.log_error(f"Failed to start Ghost Downloader: {e}", self._metadata.id)
            return {
                'success': False,
                'error': str(e)
            }
    
    def add_download_task(self, url: str, file_name: str = None, 
                          file_path: str = None) -> Dict[str, Any]:
        """
        添加下载任务
        通过 Socket 通信与运行中的 Ghost Downloader 交互
        
        Args:
            url: 下载链接
            file_name: 文件名（可选）
            file_path: 保存路径（可选）
            
        Returns:
            操作结果
        """
        # Ghost Downloader 支持 Socket 通信接收下载任务
        # 需要在设置中启用浏览器扩展功能
        
        if not self._extension_path:
            return {
                'success': False,
                'error': 'Ghost Downloader 路径未找到'
            }
        
        # 如果下载器未运行，先启动它
        if not self._process or self._process.poll() is not None:
            result = self.launch_downloader(silence=True)
            if not result.get('success'):
                return result
        
        # 通过 Socket 发送下载任务
        try:
            import socket
            import json
            
            # Ghost Downloader 默认监听端口
            HOST = '127.0.0.1'
            PORT = 9527  # 默认端口
            
            task_data = {
                'url': url,
                'fileName': file_name,
                'filePath': file_path
            }
            
            message = json.dumps(task_data)
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((HOST, PORT))
                s.sendall(message.encode('utf-8'))
            
            return {
                'success': True,
                'message': '下载任务已发送'
            }
            
        except ConnectionRefusedError:
            # Socket 连接失败，尝试直接启动并传入 URL
            self._api.log_warning("Socket connection failed, launching with URL", self._metadata.id)
            return {
                'success': False,
                'error': '无法连接到 Ghost Downloader，请确保已启用浏览器扩展功能'
            }
        except Exception as e:
            self._api.log_error(f"Failed to add download task: {e}", self._metadata.id)
            return {
                'success': False,
                'error': str(e)
            }
    
    def is_running(self) -> bool:
        """检查下载器是否正在运行"""
        return self._process is not None and self._process.poll() is None
    
    def get_process_info(self) -> Dict[str, Any]:
        """获取进程信息"""
        if self._process:
            return {
                'pid': self._process.pid,
                'running': self._process.poll() is None,
                'return_code': self._process.poll()
            }
        return {
            'pid': None,
            'running': False,
            'return_code': None
        }
    
    # === UI 接口 ===
    
    def create_ui(self, parent_window) -> Any:
        """创建插件 UI（可选）"""
        # 目前不创建嵌入 UI，通过菜单启动独立窗口
        return None
    
    def get_menu_items(self) -> List[Dict[str, Any]]:
        """获取菜单项"""
        return [
            {
                'menu': 'Tools',
                'label': 'Ghost Downloader',
                'callback': self._launch_gui,
                'icon': '📥'
            },
            {
                'menu': 'Tools',
                'label': 'Ghost Downloader (静默)',
                'callback': self._launch_silent,
                'icon': '📥'
            }
        ]
    
    def get_toolbar_actions(self) -> List[Dict[str, Any]]:
        """获取工具栏动作"""
        return [
            {
                'text': '下载器',
                'icon': '📥',
                'callback': self._launch_gui,
                'tooltip': '打开 Ghost Downloader 下载管理器'
            }
        ]
    
    def _launch_gui(self):
        """启动下载器 GUI"""
        result = self.launch_downloader()
        if result.get('success'):
            if self._event_bus:
                self._event_bus.publish(
                    'ui.show_message',
                    {'message': f'Ghost Downloader 已启动 (PID: {result["pid"]})', 'type': 'info'}
                )
        else:
            if self._event_bus:
                self._event_bus.publish(
                    'ui.show_message',
                    {'message': f'启动失败: {result.get("error", "未知错误")}', 'type': 'error'}
                )
    
    def _launch_silent(self):
        """静默启动下载器"""
        result = self.launch_downloader(silence=True)
        if result.get('success'):
            if self._event_bus:
                self._event_bus.publish(
                    'ui.show_message',
                    {'message': f'Ghost Downloader 已在后台启动', 'type': 'info'}
                )
        else:
            if self._event_bus:
                self._event_bus.publish(
                    'ui.show_message',
                    {'message': f'启动失败: {result.get("error", "未知错误")}', 'type': 'error'}
                )
