"""
AutoKeyboard Pro — Application Entry Point

This application simulates keyboard input in Windows applications.
It does NOT record keystrokes, capture passwords, monitor clipboard,
or perform any surveillance activity.

Usage:
    python main.py
"""

from __future__ import annotations

import logging
import sys
import os

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMessageBox

from config.settings import AppSettings, get_app_data_dir
from core.hotkeys import HotkeyManager
from ui.theme import ThemeManager
from ui.main_window import MainWindow
from ui.permission_dialog import PermissionDialog


def setup_logging(log_file: str) -> None:
    """Configure application logging. Text content is NEVER logged."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logger = logging.getLogger(__name__)
    logger.info("Application started")


def main() -> int:
    # ── Qt application ─────────────────────────────────────────────────
    app = QApplication(sys.argv)
    app.setApplicationName("AutoKeyboard Pro")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("AutoKeyboardPro")

    # ── Load settings ──────────────────────────────────────────────────
    settings = AppSettings.load()
    setup_logging(settings.log_file)
    logger = logging.getLogger(__name__)

    # ── Apply theme ────────────────────────────────────────────────────
    theme_mgr = ThemeManager()
    theme = settings.theme
    # Follow system theme if requested (default to dark on Windows 11)
    if theme == "System":
        theme = _detect_system_theme()
    theme_mgr.apply(app, theme)

    # ── Font ───────────────────────────────────────────────────────────
    default_font = QFont("Segoe UI", 10)
    app.setFont(default_font)

    # ── Permission check ───────────────────────────────────────────────
    if not settings.permission_granted:
        dlg = PermissionDialog()
        result = dlg.exec()
        if not dlg.permission_granted:
            logger.info("User did not grant permission — exiting")
            return 0
        settings.permission_granted = True
        settings.save()
        logger.info("User granted permission on first launch")

    # ── Hotkey manager ─────────────────────────────────────────────────
    hotkey_mgr = HotkeyManager()

    # ── Main window ────────────────────────────────────────────────────
    window = MainWindow(settings, hotkey_mgr)
    window.show()

    logger.info("Main window displayed")
    exit_code = app.exec()
    logger.info("Application exited with code %d", exit_code)
    return exit_code


def _detect_system_theme() -> str:
    """Try to detect Windows dark/light mode preference."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return "Light" if value == 1 else "Dark"
    except Exception:
        return "Dark"  # Default to dark


if __name__ == "__main__":
    sys.exit(main())
