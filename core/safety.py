"""
AutoKeyboard Pro — Safety Manager
Handles:
  - First-launch permission tracking
  - Foreground window monitoring (stop-if-window-changes guard)
  - Permission state persisted to AppData settings

IMPORTANT: This module does NOT capture or record keystrokes.
           It only reads the foreground window title for safety comparison.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import win32gui; fail gracefully on non-Windows
try:
    import win32gui
    _WIN32_AVAILABLE = True
except ImportError:
    _WIN32_AVAILABLE = False
    logger.warning("pywin32 not available — window focus guard disabled")


class SafetyManager:
    """Manages window focus safety guard."""

    def __init__(self, enabled: bool = True):
        self._enabled = enabled
        self._baseline_hwnd: Optional[int] = None
        self._baseline_title: str = ""

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    @property
    def win32_available(self) -> bool:
        return _WIN32_AVAILABLE

    def snapshot_foreground(self) -> tuple[int, str]:
        """
        Capture the current foreground window handle and title.
        Returns (hwnd, title).  Returns (0, '') if win32 unavailable.
        """
        if not _WIN32_AVAILABLE:
            return (0, "")
        try:
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)
            return (hwnd, title)
        except Exception as exc:
            logger.error("Failed to get foreground window: %s", exc)
            return (0, "")

    def arm(self) -> tuple[int, str]:
        """
        Record the current foreground window as the target.
        Call this just before typing starts.
        """
        hwnd, title = self.snapshot_foreground()
        self._baseline_hwnd = hwnd
        self._baseline_title = title
        logger.info("Safety guard armed on window title (not logged for privacy)")
        return (hwnd, title)

    def check_window_unchanged(self) -> bool:
        """
        Returns True if the foreground window is still the same as when arm() was called.
        Returns True (no violation) if win32 unavailable or guard disabled.
        """
        if not self._enabled or not _WIN32_AVAILABLE:
            return True
        if self._baseline_hwnd is None:
            return True
        try:
            current_hwnd = win32gui.GetForegroundWindow()
            if current_hwnd != self._baseline_hwnd:
                logger.warning(
                    "Foreground window changed — safety guard triggered "
                    "(window titles not logged)"
                )
                return False
            return True
        except Exception as exc:
            logger.error("Window check failed: %s", exc)
            return True  # Don't stop on check failure

    def reset(self) -> None:
        self._baseline_hwnd = None
        self._baseline_title = ""


class PermissionState:
    """
    Tracks whether the user has granted permission for keyboard input generation.
    Persisted via AppSettings; this class is a runtime holder.
    """

    def __init__(self, granted: bool = False):
        self._granted = granted

    @property
    def granted(self) -> bool:
        return self._granted

    def grant(self) -> None:
        self._granted = True
        logger.info("User granted keyboard input permission")

    def revoke(self) -> None:
        self._granted = False
        logger.info("Keyboard input permission revoked")
