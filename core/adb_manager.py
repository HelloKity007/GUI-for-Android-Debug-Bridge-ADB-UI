# -*- coding: utf-8 -*-
"""
ADB Manager for Android Debug Bridge operations
"""
import os
import sys
import subprocess
import shlex


class ADBManager:
    """Manages ADB operations"""
    
    def __init__(self, adb_path=None):
        if adb_path:
            self.adb_path = adb_path
        else:
            self.adb_path = self.find_adb()
        self.log_callback = None
        
    def find_adb(self):
        """Try to find ADB executable (fallback only - should use saved path from settings)"""
        # Try to find in PATH first (most reliable if installed system-wide)
        try:
            result = subprocess.run(['where', 'adb'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                path = result.stdout.strip().split('\n')[0]
                if os.path.exists(path):
                    return path
        except:
            pass
        
        # Check common locations as fallback
        common_paths = [
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Android', 'Sdk', 'platform-tools', 'adb.exe'),
            os.path.join(os.environ.get('ProgramFiles', ''), 'Android', 'android-sdk', 'platform-tools', 'adb.exe'),
            os.path.join(os.path.expanduser('~'), 'Downloads', 'platform-tools-latest-windows', 'platform-tools', 'adb.exe'),
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        return 'adb'  # Fallback to assuming it's in PATH
    
    def set_adb_path(self, path):
        """Set custom ADB path"""
        if os.path.exists(path):
            self.adb_path = path
            return True
        elif os.path.exists(os.path.join(path, 'adb.exe')):
            self.adb_path = os.path.join(path, 'adb.exe')
            return True
        return False
    
    def run_command(self, command, timeout=30):
        """Run ADB command and return result"""
        try:
            # On Windows, use posix=True to properly handle quoted arguments
            # This will strip quotes from the arguments
            if sys.platform == 'win32':
                command_parts = shlex.split(command, posix=True) if command else []
            else:
                command_parts = shlex.split(command, posix=False) if command else []
            full_command = [self.adb_path] + command_parts
            
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'stdout': '',
                'stderr': 'Command timed out',
                'returncode': -1
            }
        except Exception as e:
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'returncode': -1
            }
    
    def get_devices(self, silent=False, full_info=True):
        """Get list of connected devices with model information

        Args:
            silent:    If True, don't log debug output (for auto-refresh)
            full_info: If False, skip extra getprop calls (xbh_model/serial/android).
                       Used by silent auto-refresh to keep it fast (only 'adb devices -l').
        """
        result = self.run_command('devices -l')
        
        # Log the raw output for debugging (only if not silent)
        if not silent and hasattr(self, 'log_callback') and self.log_callback:
            # Only log stderr if it's not empty
            stderr_part = f"\nstderr: {result['stderr']}" if result.get('stderr', '').strip() else "\nstderr: (empty)"
            self.log_callback(f"ADB devices command output:\nstdout: {result['stdout']}{stderr_part}\nsuccess: {result['success']}", "DEBUG")
        
        if not result['success']:
            if hasattr(self, 'log_callback') and self.log_callback:
                self.log_callback(f"ADB command failed: {result['stderr']}", "ERROR")
            return []
        
        devices = []
        output = result['stdout'].strip()
        if not output:
            return []
        
        lines = output.split('\n')
        # Skip header line (usually "List of devices attached")
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
            
            # Handle both tab and space separated formats
            if '\t' in line:
                parts = line.split('\t', 1)
            elif ' ' in line:
                parts = line.split(' ', 1)
            else:
                # Just device ID, no status
                devices.append({'id': line, 'status': 'unknown', 'model': None, 'product': None})
                continue
            
            device_id = parts[0].strip()
            if device_id:
                rest = parts[1].strip() if len(parts) > 1 else ''
                status = rest.split()[0] if rest else 'unknown'
                
                # Parse model and product from -l output (e.g., "device product:mustang model:Pixel_10_Pro_XL")
                model = None
                product = None
                if 'model:' in rest:
                    try:
                        model_part = rest.split('model:')[1].split()[0]
                        model = model_part.replace('_', ' ')
                    except:
                        pass
                if 'product:' in rest:
                    try:
                        product_part = rest.split('product:')[1].split()[0]
                        product = product_part.replace('_', ' ')
                    except:
                        pass
                
                devices.append({
                    'id': device_id, 
                    'status': status,
                    'model': model,
                    'product': product
                })
        
        # For devices without model info from -l, try to get it via getprop
        for device in devices:
            if not device.get('model') and device['status'] == 'device':
                # Try to get model name
                model_result = self.run_command(f"-s {device['id']} shell getprop ro.product.model")
                if model_result['success'] and model_result['stdout'].strip():
                   device['model'] = model_result['stdout'].strip()
                
                # Also get manufacturer if model is available
                if device.get('model'):
                    mfr_result = self.run_command(f"-s {device['id']} shell getprop ro.product.manufacturer")
                    if mfr_result['success'] and mfr_result['stdout'].strip():
                       device['manufacturer'] = mfr_result['stdout'].strip()
            
            # Get XbhModel, Serial, Android version (only when full_info requested)
            if full_info and device['status'] == 'device':
                xbh_result = self.run_command(f"-s {device['id']} shell getprop ro.product.xbh.customer.model")
                if xbh_result['success'] and xbh_result['stdout'].strip():
                   device['xbh_model'] = xbh_result['stdout'].strip()

                serial_result = self.run_command(f"-s {device['id']} shell getprop ro.serialno")
                if serial_result['success'] and serial_result['stdout'].strip():
                   device['serial'] = serial_result['stdout'].strip()

                android_result = self.run_command(f"-s {device['id']} shell getprop ro.build.version.release")
                if android_result['success'] and android_result['stdout'].strip():
                   device['android_version'] = android_result['stdout'].strip()

        return devices
    
    def get_device_info(self, device_id):
        """Get device information"""
        info = {}
        commands = {
            'Model': 'shell getprop ro.product.model',
            'Manufacturer': 'shell getprop ro.product.manufacturer',
            'Android Version': 'shell getprop ro.build.version.release',
            'SDK Version': 'shell getprop ro.build.version.sdk',
            'Serial': 'shell getprop ro.serialno',
            'XbhModel': 'shell getprop ro.product.xbh.customer.model',
        }
        
        for key, cmd in commands.items():
            result = self.run_command(f'-s {device_id} {cmd}')
            if result['success']:
                info[key] = result['stdout'].strip()
            else:
                info[key] = 'N/A'
        
        return info
