"""
Tests for HotkeyManager.
"""

import pytest
from unittest.mock import patch, MagicMock
from core.hotkeys import HotkeyManager


@pytest.fixture
def mgr():
    """HotkeyManager with keyboard library mocked out."""
    with patch("core.hotkeys._kb") as mock_kb, \
         patch("core.hotkeys._KB_AVAILABLE", True):
        mock_kb.add_hotkey = MagicMock()
        mock_kb.remove_hotkey = MagicMock()
        yield HotkeyManager()


class TestRegistration:
    def test_register_success(self, mgr):
        ok = mgr.register("start", "ctrl+shift+alt+t", lambda: None, "Start")
        assert ok is True

    def test_register_conflict(self, mgr):
        mgr.register("start", "ctrl+shift+t", lambda: None)
        ok = mgr.register("pause", "ctrl+shift+t", lambda: None)
        assert ok is False

    def test_register_same_name_updates(self, mgr):
        mgr.register("start", "ctrl+shift+t", lambda: None)
        ok = mgr.register("start", "ctrl+shift+alt+t", lambda: None)
        assert ok is True
        assert mgr.get_combo("start") == "ctrl+shift+alt+t"

    def test_unregister(self, mgr):
        mgr.register("start", "ctrl+shift+t", lambda: None)
        mgr.unregister("start")
        assert mgr.get_combo("start") == ""

    def test_unregister_all(self, mgr):
        mgr.register("start", "ctrl+shift+t", lambda: None)
        mgr.register("stop",  "ctrl+shift+x", lambda: None)
        mgr.unregister_all()
        assert mgr.get_combo("start") == ""
        assert mgr.get_combo("stop") == ""


class TestConflictDetection:
    def test_detect_conflict(self, mgr):
        mgr.register("start", "ctrl+alt+t", lambda: None)
        assert mgr.check_conflict("ctrl+alt+t", exclude_name="other") is True

    def test_no_conflict_same_name(self, mgr):
        mgr.register("start", "ctrl+alt+t", lambda: None)
        # Same name is allowed to re-register
        assert mgr.check_conflict("ctrl+alt+t", exclude_name="start") is False


class TestDisplayFormatting:
    def test_format_single_char(self, mgr):
        mgr.register("start", "ctrl+shift+alt+t", lambda: None)
        display = mgr.format_combo_display("start")
        assert "Ctrl" in display
        assert "Shift" in display
        assert "Alt" in display
        assert "T" in display

    def test_empty_combo(self, mgr):
        result = mgr.format_combo_display("nonexistent")
        assert result == "Not set"
