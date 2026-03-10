"""
MVP架构 - Presenter层
负责协调Model和View之间的交互
"""
from typing import Optional, Callable, Any, Dict, List
from abc import ABC, abstractmethod

from framework.event.event_bus import EventBus, EventTypes
from .models import DeviceModel, ADBModel, AppModel, FileModel


class MainViewInterface(ABC):
    """主视图接口 - View层需要实现"""
    
    @abstractmethod
    def show_devices(self, devices: List[Dict[str, Any]]) -> None:
        """显示设备列表"""
        pass
    
    @abstractmethod
    def show_current_device(self, device: Optional[Dict[str, Any]]) -> None:
        """显示当前设备"""
        pass
    
    @abstractmethod
    def show_message(self, message: str, msg_type: str = 'info') -> None:
        """显示消息"""
        pass
    
    @abstractmethod
    def set_refreshing(self, refreshing: bool) -> None:
        """设置刷新状态"""
        pass
    
    @abstractmethod
    def update_adb_path_display(self, path: str) -> None:
        """更新ADB路径显示"""
        pass


class MainPresenter:
    """主Presenter - 协调主窗口的业务逻辑"""
    
    def __init__(
        self,
        view: MainViewInterface,
        event_bus: EventBus,
        device_model: DeviceModel,
        adb_model: ADBModel,
        app_model: AppModel,
        file_model: FileModel
    ):
        self._view = view
        self._event_bus = event_bus
        self._device_model = device_model
        self._adb_model = adb_model
        self._app_model = app_model
        self._file_model = file_model
        
        self._setup_event_handlers()
    
    def _setup_event_handlers(self) -> None:
        """设置事件处理器"""
        # 设备相关事件
        self._event_bus.subscribe(
            EventTypes.DEVICE_LIST_UPDATED,
            self._on_device_list_updated
        )
        self._event_bus.subscribe(
            EventTypes.DEVICE_SELECTED,
            self._on_device_selected
        )
        self._event_bus.subscribe(
            EventTypes.DEVICE_DISCONNECTED,
            self._on_device_disconnected
        )
        
        # ADB相关事件
        self._event_bus.subscribe(
            'adb.path_changed',
            self._on_adb_path_changed
        )
        self._event_bus.subscribe(
            'adb.command_error',
            self._on_adb_error
        )
        
        # 设备刷新事件
        self._event_bus.subscribe(
            'device.refreshing',
            self._on_refreshing_changed
        )
    
    def _on_device_list_updated(self, event) -> None:
        """设备列表更新处理"""
        devices = event.data.get('devices', [])
        self._view.show_devices(devices)
    
    def _on_device_selected(self, event) -> None:
        """设备选择处理"""
        device = event.data.get('device')
        self._view.show_current_device(device)
        
        # 同步更新其他模型
        if device:
            device_id = device.get('id')
            self._app_model.set_device(device_id)
            self._file_model.set_device(device_id)
    
    def _on_device_disconnected(self, event) -> None:
        """设备断开处理"""
        self._view.show_current_device(None)
        self._app_model.set_device(None)
        self._file_model.set_device(None)
    
    def _on_adb_path_changed(self, event) -> None:
        """ADB路径变更处理"""
        path = event.data.get('path', '')
        self._view.update_adb_path_display(path)
    
    def _on_adb_error(self, event) -> None:
        """ADB错误处理"""
        error = event.data.get('error', 'Unknown error')
        command = event.data.get('command', '')
        self._view.show_message(f'ADB Error: {error}', 'error')
    
    def _on_refreshing_changed(self, event) -> None:
        """刷新状态变更处理"""
        refreshing = event.data.get('refreshing', False)
        self._view.set_refreshing(refreshing)
    
    # === 公开方法供View调用 ===
    
    def refresh_devices(self) -> None:
        """刷新设备列表"""
        self._device_model.set_refreshing(True)
        
        try:
            devices = self._adb_model.get_devices()
            self._device_model.set_devices(devices)
            
            # 检查当前设备是否还在列表中
            current = self._device_model.current_device
            if current:
                device_id = current.get('id')
                if not any(d.get('id') == device_id for d in devices):
                    # 当前设备已断开
                    self._device_model.set_current_device(None)
        finally:
            self._device_model.set_refreshing(False)
    
    def select_device(self, device_id: str) -> None:
        """选择设备"""
        device = self._device_model.get_device_by_id(device_id)
        if device:
            self._device_model.set_current_device(device)
        else:
            self._view.show_message(f'Device {device_id} not found', 'error')
    
    def set_adb_path(self, path: str) -> None:
        """设置ADB路径"""
        self._adb_model.set_adb_path(path)
        # 保存到配置
        self._event_bus.publish(
            'config.set',
            {'key': 'paths.adb_path', 'value': path},
            source='MainPresenter'
        )
    
    def execute_shell_command(self, command: str) -> Dict[str, Any]:
        """执行Shell命令"""
        device = self._device_model.current_device
        if not device:
            self._view.show_message('No device selected', 'error')
            return {'success': False, 'error': 'No device selected'}
        
        # 自动添加shell前缀（如果没有）
        if not command.startswith('shell '):
            command = f'shell {command}'
        
        return self._adb_model.execute_command(command, device.get('id'))
    
    def install_apk(self, apk_path: str) -> bool:
        """安装APK"""
        result = self._app_model.install_app(apk_path)
        if result['success']:
            self._view.show_message('App installed successfully', 'success')
        else:
            error = result.get('error', 'Unknown error')
            self._view.show_message(f'Install failed: {error}', 'error')
        return result['success']
    
    def uninstall_app(self, package_name: str) -> bool:
        """卸载应用"""
        result = self._app_model.uninstall_app(package_name)
        if result['success']:
            self._view.show_message('App uninstalled successfully', 'success')
        else:
            error = result.get('error', 'Unknown error')
            self._view.show_message(f'Uninstall failed: {error}', 'error')
        return result['success']
    
    def get_device_info(self) -> Optional[Dict[str, str]]:
        """获取当前设备信息"""
        device = self._device_model.current_device
        if not device:
            return None
        
        return self._adb_model.get_device_info(device.get('id'))
    
    def list_files(self, path: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出文件"""
        return self._file_model.list_directory(path)
    
    def navigate_file_path(self, path: str) -> None:
        """导航文件路径"""
        self._file_model.set_path(path)
    
    def push_file(self, local_path: str, remote_name: str) -> bool:
        """推送文件"""
        result = self._file_model.push_file(local_path, remote_name)
        if result['success']:
            self._view.show_message('File pushed successfully', 'success')
        else:
            error = result.get('error', 'Unknown error')
            self._view.show_message(f'Push failed: {error}', 'error')
        return result['success']
    
    def pull_file(self, remote_name: str, local_path: str) -> bool:
        """拉取文件"""
        result = self._file_model.pull_file(remote_name, local_path)
        if result['success']:
            self._view.show_message('File pulled successfully', 'success')
        else:
            error = result.get('error', 'Unknown error')
            self._view.show_message(f'Pull failed: {error}', 'error')
        return result['success']
    
    def initialize(self) -> None:
        """初始化Presenter"""
        # 加载配置
        self._event_bus.publish(
            'config.get',
            {'key': 'paths.adb_path'},
            source='MainPresenter'
        )
        
        # 刷新设备列表
        self.refresh_devices()
