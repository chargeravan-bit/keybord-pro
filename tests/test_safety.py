"""
Tests for SafetyManager.
"""

import pytest
from unittest.mock import patch, MagicMock
from core.safety import SafetyManager, PermissionState


class TestPermissionState:
    def test_default_not_granted(self):
        p = PermissionState()
        assert p.granted is False

    def test_grant(self):
        p = PermissionState()
        p.grant()
        assert p.granted is True

    def test_revoke(self):
        p = PermissionState(granted=True)
        p.revoke()
        assert p.granted is False


class TestSafetyManagerDisabled:
    def test_disabled_always_returns_true(self):
        mgr = SafetyManager(enabled=False)
        # Even if window changes, disabled guard returns True (no stop)
        assert mgr.check_window_unchanged() is True

    def test_arm_returns_zero_when_win32_unavailable(self):
        with patch("core.safety._WIN32_AVAILABLE", False):
            mgr = SafetyManager(enabled=True)
            hwnd, title = mgr.arm()
            assert hwnd == 0

    def test_check_returns_true_when_win32_unavailable(self):
        with patch("core.safety._WIN32_AVAILABLE", False):
            mgr = SafetyManager(enabled=True)
            mgr.arm()
            assert mgr.check_window_unchanged() is True


class TestSafetyManagerEnabled:
    def test_same_window_returns_true(self):
        with patch("core.safety._WIN32_AVAILABLE", True), \
             patch("core.safety.win32gui") as mock_w32:
            mock_w32.GetForegroundWindow.return_value = 1234
            mock_w32.GetWindowText.return_value = "Test Window"

            mgr = SafetyManager(enabled=True)
            mgr.arm()
            result = mgr.check_window_unchanged()
            assert result is True

    def test_different_window_returns_false(self):
        with patch("core.safety._WIN32_AVAILABLE", True), \
             patch("core.safety.win32gui") as mock_w32:
            # First call: arm with window 1234
            mock_w32.GetForegroundWindow.side_effect = [1234, 9999]
            mock_w32.GetWindowText.return_value = "Test Window"

            mgr = SafetyManager(enabled=True)
            mgr.arm()
            result = mgr.check_window_unchanged()
            assert result is False

    def test_reset_clears_baseline(self):
        with patch("core.safety._WIN32_AVAILABLE", True), \
             patch("core.safety.win32gui") as mock_w32:
            mock_w32.GetForegroundWindow.return_value = 1234
            mock_w32.GetWindowText.return_value = "Test"

            mgr = SafetyManager(enabled=True)
            mgr.arm()
            mgr.reset()
            # After reset, no baseline → always True
            assert mgr.check_window_unchanged() is True
