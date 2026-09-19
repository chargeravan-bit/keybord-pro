"""
AutoKeyboard Pro — Typing Engine
Orchestrates the typing workflow in a QThread worker.

State machine:
    IDLE → ARMED → COUNTDOWN → TYPING ↔ PAUSED → COMPLETED
                                                 ↘ STOPPED
                                                 ↘ ERROR

Thread model:
    TypingWorker runs in a QThread.
    Stop and Pause use threading.Event for immediate response.
    The GUI communicates via Qt signals (thread-safe).

IMPORTANT:
  - This module NEVER logs the actual text being typed.
  - Progress signals carry only counts (int), never text content.
"""

from __future__ import annotations

import logging
import time
import threading
from enum import Enum, auto
from typing import List, Optional

from PySide6.QtCore import QObject, QThread, Signal, Slot

from core.text_parser import CharacterToken, parse_text, TokenType
from core.timing_engine import TimingEngine, TimingConfig, TypingMode
from core.keyboard_controller import KeyboardController
from core.safety import SafetyManager

logger = logging.getLogger(__name__)


class TypingState(Enum):
    IDLE      = "IDLE"
    ARMED     = "ARMED"
    COUNTDOWN = "COUNTDOWN"
    TYPING    = "TYPING"
    PAUSED    = "PAUSED"
    COMPLETED = "COMPLETED"
    STOPPED   = "STOPPED"
    ERROR     = "ERROR"


class TypingWorker(QObject):
    """
    Runs in a QThread.  Does the actual countdown + typing loop.
    All state changes are communicated via signals.
    """

    # Signals — never carry raw text content
    state_changed      = Signal(str)          # TypingState.value
    progress_updated   = Signal(int, int)     # chars_done, chars_total
    words_updated      = Signal(int, int)     # words_done, words_total
    countdown_tick     = Signal(int)          # seconds remaining
    wpm_measured       = Signal(float)        # live measured WPM
    time_remaining     = Signal(float)        # seconds remaining
    target_window_info = Signal(str)          # window title (safe to show)
    error_occurred     = Signal(str)          # error message
    finished           = Signal()

    def __init__(
        self,
        tokens: List[CharacterToken],
        timing_engine: TimingEngine,
        keyboard_controller: KeyboardController,
        safety_manager: SafetyManager,
        countdown_seconds: int = 5,
        require_confirm_stop: bool = False,
    ):
        super().__init__()
        self._tokens = tokens
        self._timing = timing_engine
        self._kb = keyboard_controller
        self._safety = safety_manager
        self._countdown_secs = countdown_seconds

        # Thread control events
        self._stop_event   = threading.Event()
        self._pause_event  = threading.Event()  # set = paused

        # Resume tracking
        self._resume_event = threading.Event()
        self._resume_event.set()  # initially not paused

        self._position = 0  # current token index
        self._total_chars = len(tokens)
        self._total_words = max(1, self._count_words(tokens))

        # Timing measurement
        self._start_time: Optional[float] = None
        self._chars_typed = 0

    # ------------------------------------------------------------------
    # Control (thread-safe)
    # ------------------------------------------------------------------

    def request_stop(self) -> None:
        self._stop_event.set()
        self._resume_event.set()  # unblock if paused

    def request_pause(self) -> None:
        if not self._pause_event.is_set():
            self._pause_event.set()

    def request_resume(self) -> None:
        if self._pause_event.is_set():
            self._pause_event.clear()
            self._resume_event.set()

    @property
    def is_paused(self) -> bool:
        return self._pause_event.is_set()

    # ------------------------------------------------------------------
    # Main run loop
    # ------------------------------------------------------------------

    @Slot()
    def run(self) -> None:
        try:
            self._run_impl()
        except Exception as exc:
            logger.error("TypingWorker unhandled exception: %s", exc, exc_info=True)
            self.state_changed.emit(TypingState.ERROR.value)
            self.error_occurred.emit(str(exc))
        finally:
            self.finished.emit()

    def _run_impl(self) -> None:
        # ── COUNTDOWN ─────────────────────────────────────────────────
        self.state_changed.emit(TypingState.COUNTDOWN.value)

        for remaining in range(self._countdown_secs, 0, -1):
            if self._stop_event.is_set():
                self.state_changed.emit(TypingState.STOPPED.value)
                return
            self.countdown_tick.emit(remaining)
            time.sleep(1.0)

        if self._stop_event.is_set():
            self.state_changed.emit(TypingState.STOPPED.value)
            return

        # ── ARM safety guard ──────────────────────────────────────────
        hwnd, title = self._safety.arm()
        self.target_window_info.emit(title)

        # ── TYPING LOOP ───────────────────────────────────────────────
        self.state_changed.emit(TypingState.TYPING.value)
        self._start_time = time.monotonic()

        while self._position < len(self._tokens):
            # Emergency stop check
            if self._stop_event.is_set():
                self.state_changed.emit(TypingState.STOPPED.value)
                return

            # Pause check
            if self._pause_event.is_set():
                self.state_changed.emit(TypingState.PAUSED.value)
                # Block until resumed or stopped
                while self._pause_event.is_set() and not self._stop_event.is_set():
                    time.sleep(0.05)
                if self._stop_event.is_set():
                    self.state_changed.emit(TypingState.STOPPED.value)
                    return
                self.state_changed.emit(TypingState.TYPING.value)

            # Window-change safety guard
            if not self._safety.check_window_unchanged():
                logger.warning("Window changed — stopping typing for safety")
                self.state_changed.emit(TypingState.STOPPED.value)
                self.error_occurred.emit(
                    "Stopped: the target application window changed.\n"
                    "Text was not fully typed."
                )
                return

            # Send character
            token = self._tokens[self._position]
            try:
                self._kb.send_token(token)
            except Exception as exc:
                logger.error("Key send failed at position %d: %s", self._position, exc)
                self.error_occurred.emit(f"Keyboard input error: {exc}")
                self.state_changed.emit(TypingState.ERROR.value)
                return

            self._position += 1
            self._chars_typed += 1

            # Update progress
            self.progress_updated.emit(self._chars_typed, self._total_chars)
            self._emit_words()
            self._emit_wpm()
            self._emit_time_remaining()

            # Compute and wait for the character delay
            delay = self._timing.get_delay(token)

            # Sleep in small increments so stop/pause are responsive
            end_time = time.monotonic() + delay
            while time.monotonic() < end_time:
                if self._stop_event.is_set() or self._pause_event.is_set():
                    break
                time.sleep(min(0.02, end_time - time.monotonic()))

        # ── COMPLETED ─────────────────────────────────────────────────
        if not self._stop_event.is_set():
            self.state_changed.emit(TypingState.COMPLETED.value)
            logger.info("Typing completed successfully")

    # ------------------------------------------------------------------
    # Progress helpers
    # ------------------------------------------------------------------

    def _count_words(self, tokens: List[CharacterToken]) -> int:
        text = "".join(t.char for t in tokens)
        return len(text.split())

    def _emit_words(self) -> None:
        typed_text = "".join(t.char for t in self._tokens[:self._position])
        done = len(typed_text.split()) if typed_text.strip() else 0
        self.words_updated.emit(done, self._total_words)

    def _emit_wpm(self) -> None:
        if self._start_time and self._chars_typed > 0:
            elapsed_min = (time.monotonic() - self._start_time) / 60.0
            if elapsed_min > 0:
                measured = (self._chars_typed / 5) / elapsed_min
                self.wpm_measured.emit(round(measured, 1))

    def _emit_time_remaining(self) -> None:
        base_delay = self._timing.get_base_delay()
        chars_left = self._total_chars - self._chars_typed
        remaining_secs = chars_left * base_delay
        self.time_remaining.emit(remaining_secs)


class TypingEngine(QObject):
    """
    Public facade that manages the TypingWorker and QThread lifecycle.
    The main window interacts only with this class.
    """

    # Mirror worker signals
    state_changed      = Signal(str)
    progress_updated   = Signal(int, int)
    words_updated      = Signal(int, int)
    countdown_tick     = Signal(int)
    wpm_measured       = Signal(float)
    time_remaining     = Signal(float)
    target_window_info = Signal(str)
    error_occurred     = Signal(str)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._thread: Optional[QThread] = None
        self._worker: Optional[TypingWorker] = None
        self._kb = KeyboardController()
        self._safety = SafetyManager()
        self._current_state = TypingState.IDLE

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_safety_enabled(self, enabled: bool) -> None:
        self._safety.enabled = enabled

    # ------------------------------------------------------------------
    # Control
    # ------------------------------------------------------------------

    def start(
        self,
        text: str,
        timing_config: TimingConfig,
        countdown_seconds: int = 5,
    ) -> bool:
        """Parse text, initialize keyboard, and start the typing worker."""
        if not text.strip():
            self.error_occurred.emit("No text to type. Please enter some text first.")
            return False

        if not self._kb.initialize():
            self.error_occurred.emit(
                "Failed to initialize keyboard input.\n"
                "Try running as Administrator."
            )
            return False

        tokens = parse_text(text)
        timing = TimingEngine(timing_config)

        # Clean up any previous thread
        self._cleanup_thread()

        self._thread = QThread()
        self._worker = TypingWorker(
            tokens=tokens,
            timing_engine=timing,
            keyboard_controller=self._kb,
            safety_manager=self._safety,
            countdown_seconds=countdown_seconds,
        )
        self._worker.moveToThread(self._thread)

        # Wire signals
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._worker.state_changed.connect(self.state_changed)
        self._worker.progress_updated.connect(self.progress_updated)
        self._worker.words_updated.connect(self.words_updated)
        self._worker.countdown_tick.connect(self.countdown_tick)
        self._worker.wpm_measured.connect(self.wpm_measured)
        self._worker.time_remaining.connect(self.time_remaining)
        self._worker.target_window_info.connect(self.target_window_info)
        self._worker.error_occurred.connect(self.error_occurred)

        self.state_changed.emit(TypingState.ARMED.value)
        self._thread.start()
        logger.info("Typing engine started")
        return True

    def stop(self) -> None:
        """Emergency stop — immediate."""
        if self._worker:
            self._worker.request_stop()
        logger.info("Typing engine STOP requested")

    def pause(self) -> None:
        if self._worker:
            self._worker.request_pause()

    def resume(self) -> None:
        if self._worker:
            self._worker.request_resume()

    def toggle_pause(self) -> None:
        if self._worker:
            if self._worker.is_paused:
                self.resume()
            else:
                self.pause()

    def is_active(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def _cleanup_thread(self) -> None:
        if self._thread and self._thread.isRunning():
            if self._worker:
                self._worker.request_stop()
            self._thread.quit()
            self._thread.wait(3000)
        self._thread = None
        self._worker = None

    def shutdown(self) -> None:
        """Call on application exit."""
        self._cleanup_thread()
