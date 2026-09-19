# -*- mode: python ; coding: utf-8 -*-
"""
AutoKeyboard Pro — PyInstaller Spec File
Produces a one-directory bundle with a single launcher EXE.
"""

import sys
import os

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('assets', 'assets'),
        ('config', 'config'),
    ],
    hiddenimports=[
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'pynput',
        'pynput.keyboard',
        'pynput._util',
        'pynput._util.win32',
        'keyboard',
        'win32gui',
        'win32con',
        'win32api',
        'winreg',
        'core.text_parser',
        'core.timing_engine',
        'core.keyboard_controller',
        'core.typing_engine',
        'core.hotkeys',
        'core.safety',
        'config.settings',
        'ui.main_window',
        'ui.settings_dialog',
        'ui.permission_dialog',
        'ui.widgets',
        'ui.theme',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AutoKeyboardPro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,       # No console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,           # Replace with: icon='assets/icon.ico'
    version_file=None,
    uac_admin=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AutoKeyboardPro',
)
