"""
AutoKeyboard Pro — Keyboard Controller
Sends individual key events to Windows via pynput (uses Win32 SendInput under the hood).

Character flow:
    CharacterToken
        → KeyboardController.send_token()
            → pynput press/release sequences
                → Windows keyboard input system
                    → focused application

Unicode fallback:
    Characters that cannot be expressed as a direct key combination
    (e.g. emoji, CJK) are sent via pynput's Controller.type() which
    uses a different Win32 path.  This is documented, logged (type only,
    never the actual character), and does NOT use the clipboard.

IMPORTANT: This module NEVER logs the actual characters typed.
           It only logs token_type for diagnostics.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from pynput.keyboard import Controller, Key, KeyCode

from core.text_parser import CharacterToken, TokenType

logger = logging.getLogger(__name__)

# Map of special token types to pynput Key constants
_SPECIAL_KEY_MAP: dict[TokenType, Key] = {
    TokenType.NEWLINE:   Key.enter,
    TokenType.TAB:       Key.tab,
    TokenType.BACKSPACE: Key.backspace,
    TokenType.SPACE:     Key.space,
}

# Shift-required symbol: base_key → actual pynput KeyCode
# pynput can derive this automatically, but we store for reference


class KeyboardController:
    """
    Sends individual key press/release events via pynput.
    Thread-safe for use from a QThread worker.
    """

    def __init__(self):
        self._controller = Controller()
        self._initialized = False

    def initialize(self) -> bool:
        """Verify pynput controller is available."""
        try:
            # Lightweight check — just instantiate
            _ = Controller()
            self._controller = Controller()
            self._initialized = True
            logger.info("KeyboardController initialized successfully")
            return True
        except Exception as exc:
            logger.error("KeyboardController failed to initialize: %s", exc)
            self._initialized = False
            return False

    def send_token(self, token: CharacterToken) -> None:
        """
        Send the keyboard event(s) for a single CharacterToken.
        Raises RuntimeError if not initialized.
        """
        if not self._initialized:
            raise RuntimeError("KeyboardController not initialized")

        tt = token.token_type

        # --- Special keys (Enter, Tab, Backspace, Space) ---
        if tt in _SPECIAL_KEY_MAP:
            key = _SPECIAL_KEY_MAP[tt]
            self._tap(key)
            logger.debug("Sent special key: %s", tt.name)
            return

        # --- Unicode fallback ---
        if tt == TokenType.UNICODE_FALLBACK or token.is_fallback:
            self._send_unicode_fallback(token)
            return

        # --- Uppercase letters (Shift + base_key) ---
        if tt == TokenType.LETTER_UPPER:
            self._tap_with_shift(KeyCode.from_char(token.base_key or token.char.lower()))
            logger.debug("Sent uppercase letter (token_type=%s)", tt.name)
            return

        # --- Shift-combo symbols (!, @, #, …) ---
        if tt == TokenType.SHIFT_COMBO:
            base = token.base_key or token.char
            self._tap_with_shift(KeyCode.from_char(base))
            logger.debug("Sent shift-combo (token_type=%s)", tt.name)
            return

        # --- Lowercase letters, digits, direct punctuation ---
        char_key = KeyCode.from_char(token.char)
        self._tap(char_key)
        logger.debug("Sent character (token_type=%s)", tt.name)

    def send_backspace(self) -> None:
        """Send a single Backspace keystroke."""
        self._tap(Key.backspace)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _tap(self, key) -> None:
        """Press and release a key."""
        self._controller.press(key)
        self._controller.release(key)

    def _tap_with_shift(self, key) -> None:
        """Press Shift, press key, release key, release Shift."""
        with self._controller.pressed(Key.shift):
            self._controller.press(key)
            self._controller.release(key)

    def _send_unicode_fallback(self, token: CharacterToken) -> None:
        """
        Fallback for characters that cannot be sent as direct key combos.
        Uses pynput's Controller.type() which handles Unicode internally.
        NOTE: This is NOT clipboard-based.  Logged at WARNING level with
        only the token type — never the actual character.
        """
        logger.warning(
            "Unicode fallback used for character (category=%s). "
            "Character not logged for privacy.",
            self._unicode_category(token.char),
        )
        try:
            self._controller.type(token.char)
        except Exception as exc:
            logger.error("Unicode fallback failed: %s", exc)
            raise

    @staticmethod
    def _unicode_category(char: str) -> str:
        import unicodedata
        try:
            return unicodedata.category(char)
        except Exception:
            return "Unknown"
