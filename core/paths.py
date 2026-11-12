"""Paths for both source development and a packaged desktop executable."""
import os
import sys
from pathlib import Path


def project_root():
    # PyInstaller extracts read-only UI assets into _MEIPASS.
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def ui_index():
    return project_root() / 'ui' / 'index.html'


def storage_root():
    configured = os.environ.get('COPYQ_STORAGE_DIR')
    if configured:
        return Path(configured)
    if getattr(sys, 'frozen', False):
        return Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'CopyQ' / 'storage'
    return project_root() / 'storage'
