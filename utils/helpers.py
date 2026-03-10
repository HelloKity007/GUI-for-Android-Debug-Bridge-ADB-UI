# -*- coding: utf-8 -*-
"""
Helper functions
"""
import os
import sys


def get_project_dir():
    """Get project directory path"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_absolute_path(project_dir, relative_path):
    """Convert relative path to absolute path"""
    if not relative_path:
        return ''
    if os.path.isabs(relative_path):
        return relative_path
    return os.path.normpath(os.path.join(project_dir, relative_path))
