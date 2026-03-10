# -*- coding: utf-8 -*-
"""
Config Manager - Handle config.ini and settings.json
"""
import os
import json
import configparser


class ConfigManager:
    """Manages application configuration"""
    
    def __init__(self, project_dir):
        self.project_dir = project_dir
        self.config_file = os.path.join(project_dir, 'config.ini')
        self.settings_file = os.path.join(project_dir, 'settings.json')
        
        self.config = self._load_config()
        self.settings = self._load_settings()
    
    def _load_config(self):
        """Load config.ini file"""
        config = configparser.ConfigParser()
        if os.path.exists(self.config_file):
            try:
                config.read(self.config_file, encoding='utf-8')
            except:
                pass
        return config
    
    def _load_settings(self):
        """Load settings.json file"""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def save_settings(self):
        """Save settings to JSON file"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except:
            pass
    
    def get(self, section, key, fallback=None):
        """Get config value"""
        return self.config.get(section, key, fallback=fallback)
    
    def getboolean(self, section, key, fallback=False):
        """Get boolean config value"""
        return self.config.getboolean(section, key, fallback=fallback)
    
    def get_absolute_path(self, relative_path):
        """Convert relative path to absolute path"""
        if not relative_path:
            return ''
        if os.path.isabs(relative_path):
            return relative_path
        return os.path.normpath(os.path.join(self.project_dir, relative_path))
