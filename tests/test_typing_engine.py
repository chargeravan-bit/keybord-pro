"""
Tests for TypingEngine state machine (no actual keyboard I/O).
Uses mocking to avoid real key events during tests.

NOTE: TypingWorker uses Qt signals so a QApplication must be running.
      The `qapp` fixture (provided by pytest-qt) handles this.
      We call worker.run() directly (not in a thread) so the test is synchronous.
"""

import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from core.typing_engine import TypingWorker, TypingState
from core.text_parser import parse_text
from core.timing_engine import TimingEngine, TimingConfig, TypingMode
from core.keyboard_controller import KeyboardController
from core.safety import SafetyManager


def make_worker(text: str = "hello world", wpm: int = 200):
    """Create a TypingWorker with mocked keyboard controller (no real key events)."""
    tokens = parse_text(text)
    cfg = TimingConfig(wpm=wpm, mode=TypingMode.STANDARD, seed=0)
    timing = TimingEngine(cfg)

    kb = MagicMock(spec=KeyboardController)
    kb.send_token = MagicMock(return_value=None)

    safety = SafetyManager(enabled=False)  # Disable window guard

    worker = TypingWorker(
        tokens=tokens,
        timing_engine=timing,
        keyboard_controller=kb,
        safety_manager=safety,
        countdown_seconds=0,   # No countdown delay in tests
    )
    return worker, kb


class TestWorkerStateTransitions:
    def test_completes_successfully(self, qapp):
        worker, kb = make_worker("hi", wpm=500)
        states = []
        worker.state_changed.connect(lambda s: states.append(s))

        worker.run()  # Synchronous in tests

        assert TypingState.TYPING.value in states
        assert TypingState.COMPLETED.value in states

    def test_stop_before_start(self, qapp):
        worker, kb = make_worker("hello world", wpm=500)
        states = []
        worker.state_changed.connect(lambda s: states.append(s))

        # Stop before run() so countdown (0s) + stop event both hit
        worker.request_stop()
        worker.run()

        assert TypingState.STOPPED.value in states
        assert TypingState.COMPLETED.value not in states

    def test_sends_correct_character_count(self, qapp):
        text = "abc"
        worker, kb = make_worker(text, wpm=500)
        worker.run()
        # Each character in the text must produce exactly one send_token call
        assert kb.send_token.call_count == len(text)

    def test_pause_and_resume(self, qapp):
        """Pause at character 3, then resume after 0.15s — completes successfully."""
        worker, kb = make_worker("hello world test", wpm=500)
        states = []
        worker.state_changed.connect(lambda s: states.append(s))

        call_count = [0]

        def patched_send(token):
            call_count[0] += 1
            if call_count[0] == 3:
                worker.request_pause()
                def resume():
                    time.sleep(0.15)
                    worker.request_resume()
                threading.Thread(target=resume, daemon=True).start()

        kb.send_token.side_effect = patched_send
        worker.run()

        assert TypingState.PAUSED.value in states
        assert TypingState.COMPLETED.value in states

    def test_stop_during_typing(self, qapp):
        """Stop at character 5 — should not type all characters."""
        total_text = "hello world test string"
        worker, kb = make_worker(total_text, wpm=500)
        states = []
        worker.state_changed.connect(lambda s: states.append(s))

        call_count = [0]

        def patched_send(token):
            call_count[0] += 1
            if call_count[0] == 5:
                worker.request_stop()

        kb.send_token.side_effect = patched_send
        worker.run()

        assert TypingState.STOPPED.value in states
        assert TypingState.COMPLETED.value not in states
        # At most 5 or 6 chars were sent (stop may fire between checks)
        assert kb.send_token.call_count <= 8


class TestEmptyText:
    def test_empty_tokens_complete(self, qapp):
        """Zero tokens — engine should complete immediately."""
        tokens = []
        cfg = TimingConfig(wpm=60, mode=TypingMode.STANDARD, seed=0)
        timing = TimingEngine(cfg)
        kb = MagicMock(spec=KeyboardController)
        safety = SafetyManager(enabled=False)

        worker = TypingWorker(
            tokens=tokens,
            timing_engine=timing,
            keyboard_controller=kb,
            safety_manager=safety,
            countdown_seconds=0,
        )
        states = []
        worker.state_changed.connect(lambda s: states.append(s))
        worker.run()
        assert TypingState.COMPLETED.value in states
        assert kb.send_token.call_count == 0


class TestWindowSafetyGuard:
    def test_window_change_stops_typing(self, qapp):
        """Window changes after 3 chars — engine must stop."""
        worker, kb = make_worker("hello world test", wpm=500)
        states = []
        errors = []
        worker.state_changed.connect(lambda s: states.append(s))
        worker.error_occurred.connect(lambda e: errors.append(e))

        # Inject mocked safety that reports window change after 3 checks
        mock_safety = MagicMock()
        mock_safety.arm.return_value = (1234, "Test Window")
        check_results = [True, True, True] + [False] * 100
        check_iter = iter(check_results)
        mock_safety.check_window_unchanged.side_effect = lambda: next(check_iter, False)

        worker._safety = mock_safety
        worker.run()

        assert TypingState.STOPPED.value in states
        assert len(errors) > 0  # Error message emitted
