# -*- coding: utf-8 -*-
"""
Scrcpy Manager for screen mirroring operations
"""
import os
import sys
import subprocess


class ScrcpyManager:
    """Manages Scrcpy operations for screen mirroring and control"""
    
    def __init__(self, scrcpy_path=None):
        self.scrcpy_path = scrcpy_path or self.find_scrcpy()
        self.process = None
        
    def find_scrcpy(self):
        """Try to find scrcpy executable"""
        try:
            result = subprocess.run(['where', 'scrcpy'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                path = result.stdout.strip().split('\n')[0]
                if os.path.exists(path):
                    return path
        except:
            pass
        
        # Check common locations
        common_paths = [
            os.path.join(os.environ.get('ProgramFiles', ''), 'scrcpy', 'scrcpy.exe'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'scrcpy', 'scrcpy.exe'),
            os.path.join(os.path.expanduser('~'), 'scrcpy', 'scrcpy.exe'),
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        return 'scrcpy'  # Fallback to PATH
    
    def set_scrcpy_path(self, path):
        """Set custom scrcpy path"""
        if os.path.exists(path):
            self.scrcpy_path = path
            return True
        elif os.path.exists(os.path.join(path, 'scrcpy.exe')):
            self.scrcpy_path = os.path.join(path, 'scrcpy.exe')
            return True
        return False
    
    def is_available(self):
        """Check if scrcpy is available"""
        try:
            result = subprocess.run([self.scrcpy_path, '--version'], 
                                   capture_output=True, text=True, timeout=5,
                                   creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
            return result.returncode == 0
        except:
            return False
