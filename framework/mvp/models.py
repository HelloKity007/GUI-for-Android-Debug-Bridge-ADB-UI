"""
MVP架构 - Model层
负责数据管理和业务逻辑
"""
import subprocess
import re
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

from framework.event.event_bus import EventBus, EventTypes, Event


@dataclass
class DeviceInfo:
    """设备信息数据类"""
    id: str
    status: str
    name: str = ""
    model: str = ""
    brand: str = ""
    android_version: str = ""
    sdk_version: str = ""


class DeviceModel:
    """设备模型 - 管理设备列表和当前设备"""
    
    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus
        self._devices: List[Dict[str, Any]] = []
        self._current_device: Optional[Dict[str, Any]] = None
        self._is_refreshing: bool = False
    
    @property
    def devices(self) -> List[Dict[str, Any]]:
        """获取设备列表"""
        return self._devices.copy()
    
    @property
    def current_device(self) -> Optional[Dict[str, Any]]:
        """获取当前设备"""
        return self._current_device
    
    @property
    def is_refreshing(self) -> bool:
        """是否正在刷新"""
        return self._is_refreshing
    
    def set_devices(self, devices: List[Dict[str, Any]]) -> None:
        """设置设备列表"""
        self._devices = devices
        self._event_bus.publish(
            EventTypes.DEVICE_LIST_UPDATED,
            {'devices': devices, 'count': len(devices)},
            source='DeviceModel'
        )
    
    def set_current_device(self, device: Optional[Dict[str, Any]]) -> None:
        """设置当前设备"""
        self._current_device = device
        if device:
            self._event_bus.publish(
                EventTypes.DEVICE_SELECTED,
                {'device': device, 'device_id': device.get('id')},
                source='DeviceModel'
            )
        else:
            self._event_bus.publish(
                EventTypes.DEVICE_DISCONNECTED,
                {'device': None},
                source='DeviceModel'
            )
    
    def clear_devices(self) -> None:
        """清除设备列表"""
        self._devices = []
        self._current_device = None
        self._event_bus.publish(
            EventTypes.DEVICE_LIST_UPDATED,
            {'devices': [], 'count': 0},
            source='DeviceModel'
        )
    
    def get_device_by_id(self, device_id: str) -> Optional[Dict[str, Any]]:
        """通过ID获取设备"""
        for device in self._devices:
            if device.get('id') == device_id:
                return device
        return None
    
    def set_refreshing(self, refreshing: bool) -> None:
        """设置刷新状态"""
        self._is_refreshing = refreshing
        self._event_bus.publish(
            'device.refreshing',
            {'refreshing': refreshing},
            source='DeviceModel'
        )


class ADBModel:
    """ADB模型 - 管理ADB命令执行"""
    
    def __init__(self, event_bus: EventBus, adb_path: str = 'adb'):
        self._event_bus = event_bus
        self._adb_path = adb_path
        self._is_connected = False
    
    @property
    def adb_path(self) -> str:
        """获取ADB路径"""
        return self._adb_path
    
    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._is_connected
    
    def set_adb_path(self, path: str) -> None:
        """设置ADB路径"""
        old_path = self._adb_path
        self._adb_path = path
        self._event_bus.publish(
            'adb.path_changed',
            {'path': path, 'old_path': old_path},
            source='ADBModel'
        )
    
    def execute_command(
        self, 
        command: str, 
        device_id: Optional[str] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """执行ADB命令"""
        try:
            # 构建命令
            if device_id:
                full_command = f'{self._adb_path} -s {device_id} {command}'
            else:
                full_command = f'{self._adb_path} {command}'
            
            # 发布命令执行前事件
            self._event_bus.publish(
                'adb.command_before',
                {'command': command, 'device_id': device_id},
                source='ADBModel'
            )
            
            # 执行命令
            result = subprocess.run(
                full_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            # 构建结果
            output = {
                'success': result.returncode == 0,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'command': command
            }
            
            # 发布命令执行后事件
            self._event_bus.publish(
                'adb.command_after',
                {
                    'command': command,
                    'device_id': device_id,
                    'result': output
                },
                source='ADBModel'
            )
            
            return output
            
        except subprocess.TimeoutExpired as e:
            error_result = {
                'success': False,
                'error': 'Command timeout',
                'stderr': str(e),
                'stdout': '',
                'command': command
            }
            self._event_bus.publish(
                'adb.command_error',
                {'command': command, 'error': 'timeout'},
                source='ADBModel'
            )
            return error_result
            
        except Exception as e:
            error_result = {
                'success': False,
                'error': str(e),
                'stderr': str(e),
                'stdout': '',
                'command': command
            }
            self._event_bus.publish(
                'adb.command_error',
                {'command': command, 'error': str(e)},
                source='ADBModel'
            )
            return error_result
    
    def get_devices(self) -> List[Dict[str, Any]]:
        """获取设备列表"""
        result = self.execute_command('devices')
        devices = []
        
        if result['success']:
            lines = result['stdout'].strip().split('\n')
            # 跳过第一行 (List of devices attached)
            for line in lines[1:]:
                line = line.strip()
                if not line:
                    continue
                    
                # 解析 device1\tdevice 格式
                parts = line.split('\t')
                if len(parts) >= 2:
                    device = {
                        'id': parts[0],
                        'status': parts[1]
                    }
                    devices.append(device)
        
        return devices
    
    def get_device_info(self, device_id: str) -> Dict[str, str]:
        """获取设备详细信息"""
        info = {}
        
        # 批量获取设备属性
        result = self.execute_command(
            'shell getprop ro.product.model; getprop ro.build.version.release',
            device_id
        )
        
        if result['success']:
            lines = result['stdout'].strip().split('\n')
            if len(lines) >= 1:
                info['model'] = lines[0].strip()
            if len(lines) >= 2:
                info['android_version'] = lines[1].strip()
        
        # 确保所有字段存在
        info.setdefault('model', '')
        info.setdefault('android_version', '')
        
        return info
    
    def check_connection(self) -> bool:
        """检查ADB连接状态"""
        result = self.execute_command('version')
        self._is_connected = result['success']
        return self._is_connected


class AppModel:
    """应用模型 - 管理应用安装/卸载/信息"""
    
    def __init__(self, event_bus: EventBus, adb_model: ADBModel):
        self._event_bus = event_bus
        self._adb_model = adb_model
        self._apps: List[Dict[str, Any]] = []
        self._current_device: Optional[str] = None
    
    @property
    def apps(self) -> List[Dict[str, Any]]:
        """获取应用列表"""
        return self._apps.copy()
    
    @property
    def current_device(self) -> Optional[str]:
        """获取当前设备"""
        return self._current_device
    
    def set_device(self, device_id: Optional[str]) -> None:
        """设置当前设备"""
        self._current_device = device_id
        self._apps = []  # 清空应用列表
    
    def load_apps(self) -> List[Dict[str, Any]]:
        """加载应用列表"""
        if not self._current_device:
            return []
        
        result = self._adb_model.execute_command(
            'shell pm list packages',
            self._current_device
        )
        
        apps = []
        if result['success']:
            lines = result['stdout'].strip().split('\n')
            for line in lines:
                # 解析 package:com.example.app
                if line.startswith('package:'):
                    package_name = line[8:]  # 去掉 'package:' 前缀
                    apps.append({
                        'package': package_name,
                        'name': package_name.split('.')[-1]  # 简化名称
                    })
        
        self._apps = apps
        self._event_bus.publish(
            'app.list_updated',
            {'apps': apps, 'count': len(apps)},
            source='AppModel'
        )
        
        return apps
    
    def install_app(self, apk_path: str) -> Dict[str, Any]:
        """安装应用"""
        if not self._current_device:
            return {'success': False, 'error': 'No device selected'}
        
        result = self._adb_model.execute_command(
            f'install "{apk_path}"',
            self._current_device
        )
        
        success = result['success'] and 'Success' in result['stdout']
        
        self._event_bus.publish(
            'app.installed',
            {
                'apk_path': apk_path,
                'success': success,
                'output': result['stdout']
            },
            source='AppModel'
        )
        
        return {
            'success': success,
            'output': result['stdout'],
            'error': result['stderr'] if not success else None
        }
    
    def uninstall_app(self, package_name: str) -> Dict[str, Any]:
        """卸载应用"""
        if not self._current_device:
            return {'success': False, 'error': 'No device selected'}
        
        result = self._adb_model.execute_command(
            f'uninstall {package_name}',
            self._current_device
        )
        
        success = result['success'] and 'Success' in result['stdout']
        
        self._event_bus.publish(
            'app.uninstalled',
            {
                'package': package_name,
                'success': success
            },
            source='AppModel'
        )
        
        return {
            'success': success,
            'output': result['stdout']
        }
    
    def disable_app(self, package_name: str) -> Dict[str, Any]:
        """禁用应用"""
        if not self._current_device:
            return {'success': False, 'error': 'No device selected', 'stderr': 'No device selected'}
        
        result = self._adb_model.execute_command(
            f'shell pm disable-user --user 0 {package_name}',
            self._current_device
        )
        
        return {
            'success': result['success'],
            'output': result.get('stdout', ''),
            'error': result.get('stderr', ''),
            'stderr': result.get('stderr', '')
        }
    
    def enable_app(self, package_name: str) -> Dict[str, Any]:
        """启用应用"""
        if not self._current_device:
            return {'success': False, 'error': 'No device selected', 'stderr': 'No device selected'}
        
        result = self._adb_model.execute_command(
            f'shell pm enable --user 0 {package_name}',
            self._current_device
        )
        
        return {
            'success': result['success'],
            'output': result.get('stdout', ''),
            'error': result.get('stderr', ''),
            'stderr': result.get('stderr', '')
        }
    
    def get_app_info(self, package_name: str) -> Dict[str, Any]:
        """获取应用信息"""
        if not self._current_device:
            return {}
        
        result = self._adb_model.execute_command(
            f'shell dumpsys package {package_name}',
            self._current_device
        )
        
        info = {'package': package_name}
        
        if result['success']:
            output = result['stdout']
            # 解析版本号
            version_match = re.search(r'versionName=([^\s]+)', output)
            if version_match:
                info['version'] = version_match.group(1)
            
            # 解析首次安装时间
            first_install_match = re.search(r'firstInstallTime=([^\n]+)', output)
            if first_install_match:
                info['first_install'] = first_install_match.group(1).strip()
        
        return info


class FileModel:
    """文件模型 - 管理文件操作"""
    
    def __init__(self, event_bus: EventBus, adb_model: ADBModel):
        self._event_bus = event_bus
        self._adb_model = adb_model
        self._current_path: str = '/sdcard'
        self._current_device: Optional[str] = None
    
    @property
    def current_path(self) -> str:
        """获取当前路径"""
        return self._current_path
    
    @property
    def current_device(self) -> Optional[str]:
        """获取当前设备"""
        return self._current_device
    
    def set_device(self, device_id: Optional[str]) -> None:
        """设置当前设备"""
        self._current_device = device_id
    
    def set_path(self, path: str) -> None:
        """设置当前路径"""
        self._current_path = path
        self._event_bus.publish(
            'file.path_changed',
            {'path': path},
            source='FileModel'
        )
    
    def list_directory(self, path: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出目录内容"""
        if not self._current_device:
            return []
        
        target_path = path or self._current_path
        
        result = self._adb_model.execute_command(
            f'shell ls -la "{target_path}"',
            self._current_device
        )
        
        files = []
        if result['success']:
            lines = result['stdout'].strip().split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # 解析 ls -la 输出
                # drwxrwx--- 2 root sdcard_rw 4096 2024-01-01 10:00 DCIM
                # 格式: permissions hardlinks owner group size date time name
                parts = line.split(None, 7)  # 最多分割7次，保留文件名完整
                if len(parts) >= 8:
                    name = parts[7]
                    if name in ('.', '..'):
                        continue
                    
                    files.append({
                        'name': name,
                        'permissions': parts[0],
                        'is_dir': parts[0].startswith('d'),
                        'owner': parts[2] if len(parts) > 2 else '',
                        'group': parts[3] if len(parts) > 3 else '',
                        'size': parts[4] if len(parts) > 4 else '',
                        'date': parts[5] if len(parts) > 5 else '',
                        'path': f"{target_path}/{name}".replace('//', '/')
                    })
                elif len(parts) == 1 and parts[0] not in ('.', '..'):
                    # 简化格式: 只有文件名
                    files.append({
                        'name': parts[0],
                        'permissions': '',
                        'is_dir': False,
                        'owner': '',
                        'group': '',
                        'size': '',
                        'date': '',
                        'path': f"{target_path}/{parts[0]}".replace('//', '/')
                    })
        
        return files
    
    def push_file(self, local_path: str, remote_name: str) -> Dict[str, Any]:
        """推送文件到设备"""
        if not self._current_device:
            return {'success': False, 'error': 'No device selected', 'stderr': 'No device selected'}
        
        remote_path = f"{self._current_path}/{remote_name}".replace('//', '/')
        
        result = self._adb_model.execute_command(
            f'push "{local_path}" "{remote_path}"',
            self._current_device
        )
        
        success = result['success']
        
        self._event_bus.publish(
            'file.pushed',
            {
                'local_path': local_path,
                'remote_path': remote_path,
                'success': success
            },
            source='FileModel'
        )
        
        return {
            'success': success,
            'output': result.get('stdout', ''),
            'error': result.get('stderr', ''),
            'stderr': result.get('stderr', '')
        }
    
    def pull_file(self, remote_name: str, local_path: str) -> Dict[str, Any]:
        """从设备拉取文件"""
        if not self._current_device:
            return {'success': False, 'error': 'No device selected', 'stderr': 'No device selected'}
        
        remote_path = f"{self._current_path}/{remote_name}".replace('//', '/')
        
        result = self._adb_model.execute_command(
            f'pull "{remote_path}" "{local_path}"',
            self._current_device
        )
        
        success = result['success']
        
        self._event_bus.publish(
            'file.pulled',
            {
                'remote_path': remote_path,
                'local_path': local_path,
                'success': success
            },
            source='FileModel'
        )
        
        return {
            'success': success,
            'output': result.get('stdout', ''),
            'error': result.get('stderr', ''),
            'stderr': result.get('stderr', '')
        }
    
    def delete_file(self, name: str) -> Dict[str, Any]:
        """删除文件/目录"""
        if not self._current_device:
            return {'success': False, 'error': 'No device selected', 'stderr': 'No device selected'}
        
        remote_path = f"{self._current_path}/{name}".replace('//', '/')
        
        result = self._adb_model.execute_command(
            f'shell rm -rf "{remote_path}"',
            self._current_device
        )
        
        return {
            'success': result['success'],
            'output': result.get('stdout', ''),
            'error': result.get('stderr', ''),
            'stderr': result.get('stderr', '')
        }
    
    def create_directory(self, name: str) -> Dict[str, Any]:
        """创建目录"""
        if not self._current_device:
            return {'success': False, 'error': 'No device selected'}
        
        remote_path = f"{self._current_path}/{name}".replace('//', '/')
        
        result = self._adb_model.execute_command(
            f'shell mkdir -p "{remote_path}"',
            self._current_device
        )
        
        return {
            'success': result['success'],
            'output': result['stdout'],
            'error': result['stderr']
        }
    
    def navigate_up(self) -> str:
        """向上导航"""
        if self._current_path == '/':
            return self._current_path
        
        parent = self._current_path.rsplit('/', 1)[0]
        if not parent:
            parent = '/'
        
        self.set_path(parent)
        return parent
    
    def navigate_to(self, name: str) -> str:
        """导航到子目录"""
        new_path = f"{self._current_path}/{name}".replace('//', '/')
        self.set_path(new_path)
        return new_path
