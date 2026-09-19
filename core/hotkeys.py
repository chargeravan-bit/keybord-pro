"""
AutoKeyboard Pro — Global Hotkey Manager
Registers/unregisters global hotkeys that fire even when another application is focused.

Uses the `keyboard` library which hooks into the Windows keyboard driver.

NOTE:
  - This module does NOT record keystrokes typed by the user.
  - It only listens for the specific configured hotkey combinations.
  - Hotkey callbacks fire on the keyboard library's background thread;
    all GUI interactions must be dispatched via Qt signals.

IMPORTANT: On some Windows 11 configurations the `keyboard` library
           requires Administrator privileges for global hotkey registration.
           The app shows a clear warning if registration fails.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

try:
    import keyboard as _kb
    _KB_AVAILABLE = True
except ImportError:
    _KB_AVAILABLE = False
    logger.warning("keyboard library not available — global hotkeys disabled")


@dataclass
class HotkeyAction:
    name: str
    default_combo: str
    description: str
    callback: Optional[Callable[[], None]] = field(default=None, repr=False)
    current_combo: str = ""

    def __post_init__(self):
        if not self.current_combo:
            self.current_combo = self.default_combo


class HotkeyManager:
    """
    Manages registration and unregistration of global hotkeys.
    Thread-safe — callbacks execute on keyboard library's thread.
    """

    DEFAULT_START   = "ctrl+shift+alt+t"
    DEFAULT_PAUSE   = "ctrl+shift+alt+p"
    DEFAULT_STOP    = "ctrl+shift+alt+x"

    def __init__(self):
        self._registered: Dict[str, str] = {}   # combo → hook_id-ish tracking
        self._actions: Dict[str, HotkeyAction] = {}
        self._lock = threading.Lock()
        self._available = _KB_AVAILABLE

    @property
    def available(self) -> bool:
        return self._available

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        name: str,
        combo: str,
        callback: Callable[[], None],
        description: str = "",
    ) -> bool:
        """
        Register a global hotkey.
        Returns True on success, False if unavailable or conflict.
        """
        if not self._available:
            logger.warning("Global hotkeys unavailable — keyboard library missing")
            return False

        combo = combo.lower().strip()

        with self._lock:
            # Conflict check
            if combo in self._registered and self._registered[combo] != name:
                logger.error(
                    "Hotkey conflict: '%s' already registered for '%s'",
                    combo, self._registered[combo],
                )
                return False

            # Remove existing if re-registering
            if name in self._actions:
                self._unregister_action(name)

            try:
                _kb.add_hotkey(combo, callback, suppress=False)
                action = HotkeyAction(
                    name=name,
                    default_combo=combo,
                    description=description,
                    callback=callback,
                    current_combo=combo,
                )
                self._actions[name] = action
                self._registered[combo] = name
                logger.info("Hotkey registered: name=%s combo=%s", name, combo)
                return True
            except Exception as exc:
                logger.error("Failed to register hotkey '%s': %s", combo, exc)
                return False

    def unregister(self, name: str) -> None:
        """Unregister a named hotkey."""
        with self._lock:
            self._unregister_action(name)

    def unregister_all(self) -> None:
        """Unregister all managed hotkeys."""
        with self._lock:
            for name in list(self._actions.keys()):
                self._unregister_action(name)

    def update_combo(
        self,
        name: str,
        new_combo: str,
        callback: Optional[Callable[[], None]] = None,
    ) -> bool:
        """Change the key combination for an existing action."""
        with self._lock:
            action = self._actions.get(name)
            if action is None:
                return False
            cb = callback or action.callback
            if cb is None:
                return False

        self.unregister(name)
        return self.register(name, new_combo, cb, action.description if action else "")

    def get_combo(self, name: str) -> str:
        """Get the current combo string for a named action."""
        action = self._actions.get(name)
        return action.current_combo if action else ""

    def get_all_combos(self) -> Dict[str, str]:
        return {n: a.current_combo for n, a in self._actions.items()}

    def check_conflict(self, combo: str, exclude_name: str = "") -> bool:
        """Return True if combo is already in use by a different action."""
        combo = combo.lower().strip()
        owner = self._registered.get(combo)
        if owner and owner != exclude_name:
            return True
        return False

    def format_combo_display(self, name: str) -> str:
        """Return a human-readable hotkey string (e.g. 'Ctrl+Shift+Alt+T')."""
        combo = self.get_combo(name)
        if not combo:
            return "Not set"
        parts = [p.capitalize() for p in combo.split("+")]
        # Normalize modifier display
        display_map = {"Ctrl": "Ctrl", "Shift": "Shift", "Alt": "Alt"}
        parts = [display_map.get(p, p.upper() if len(p) == 1 else p) for p in parts]
        return "+".join(parts)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _unregister_action(self, name: str) -> None:
        """Must be called under self._lock."""
        action = self._actions.pop(name, None)
        if action and self._available:
            try:
                _kb.remove_hotkey(action.current_combo)
                self._registered.pop(action.current_combo, None)
                logger.info("Hotkey unregistered: name=%s", name)
            except Exception as exc:
                logger.warning("Failed to unregister hotkey '%s': %s", name, exc)
