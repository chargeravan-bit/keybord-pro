"""
AutoKeyboard Pro — Reusable UI Widgets
"""

from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import (
    Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve, QRect, QSize, Property
)
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QFontMetrics
from PySide6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QVBoxLayout,
    QSizePolicy, QFrame, QLineEdit, QPushButton,
    QProgressBar, QGridLayout
)

from core.typing_engine import TypingState


# ──────────────────────────────────────────────────────────────────────────────
# Status Badge
# ──────────────────────────────────────────────────────────────────────────────

STATUS_COLORS = {
    TypingState.IDLE.value:      ("#5c5c70", "#9090a8"),
    TypingState.ARMED.value:     ("#7c6fcd", "#a89ae8"),
    TypingState.COUNTDOWN.value: ("#e0a040", "#f0b450"),
    TypingState.TYPING.value:    ("#52c97c", "#70e090"),
    TypingState.PAUSED.value:    ("#e0a040", "#f0b450"),
    TypingState.COMPLETED.value: ("#52c97c", "#70e090"),
    TypingState.STOPPED.value:   ("#e05252", "#f06060"),
    TypingState.ERROR.value:     ("#e05252", "#f06060"),
}


class StatusBadge(QFrame):
    """Animated status indicator pill."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._state = TypingState.IDLE.value
        self.setFixedHeight(32)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)

        self._dot = QLabel("●")
        self._dot.setFont(QFont("Segoe UI", 8))

        self._label = QLabel("IDLE")
        font = QFont("Segoe UI", 11, QFont.Weight.Bold)
        self._label.setFont(font)

        layout.addWidget(self._dot)
        layout.addWidget(self._label)

        self._blink_timer = QTimer(self)
        self._blink_timer.setInterval(600)
        self._blink_timer.timeout.connect(self._blink)
        self._blink_state = True

        self.set_state(TypingState.IDLE.value)

    def set_state(self, state: str) -> None:
        self._state = state
        colors = STATUS_COLORS.get(state, ("#5c5c70", "#9090a8"))
        bg, fg = colors

        self._label.setText(state)
        self._dot.setStyleSheet(f"color: {fg};")
        self._label.setStyleSheet(f"color: {fg}; background: transparent;")
        self.setStyleSheet(
            f"QFrame {{ background-color: {bg}22; border: 1.5px solid {bg}; "
            f"border-radius: 14px; }}"
        )

        # Blink the dot for active states
        if state in (TypingState.TYPING.value, TypingState.COUNTDOWN.value):
            self._blink_timer.start()
        else:
            self._blink_timer.stop()
            self._dot.setVisible(True)

    def _blink(self):
        self._blink_state = not self._blink_state
        self._dot.setVisible(self._blink_state)


# ──────────────────────────────────────────────────────────────────────────────
# Progress Panel
# ──────────────────────────────────────────────────────────────────────────────

class ProgressPanel(QFrame):
    """Displays typing progress: bar, chars, words, WPM, time remaining."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("card")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Header
        hdr = QHBoxLayout()
        lbl_typing = QLabel("TYPING PROGRESS")
        lbl_typing.setObjectName("section_label")
        hdr.addWidget(lbl_typing)
        hdr.addStretch()
        self._pct_label = QLabel("0%")
        self._pct_label.setObjectName("stat_value")
        hdr.addWidget(self._pct_label)
        layout.addLayout(hdr)

        # Progress bar
        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setFixedHeight(10)
        self._bar.setTextVisible(False)
        layout.addWidget(self._bar)

        # Stats grid
        grid = QGridLayout()
        grid.setSpacing(8)
        self._chars_label = self._make_stat(grid, 0, "CHARS", "0 / 0")
        self._words_label = self._make_stat(grid, 1, "WORDS", "0 / 0")
        self._wpm_label   = self._make_stat(grid, 2, "SPEED", "– WPM")
        self._time_label  = self._make_stat(grid, 3, "TIME LEFT", "–:––")
        layout.addLayout(grid)

    def _make_stat(self, grid: QGridLayout, col: int, title: str, value: str) -> QLabel:
        t = QLabel(title)
        t.setObjectName("section_label")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v = QLabel(value)
        v.setObjectName("stat_value")
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(t, 0, col)
        grid.addWidget(v, 1, col)
        return v

    def update_progress(self, done: int, total: int) -> None:
        pct = int((done / max(1, total)) * 100)
        self._bar.setValue(pct)
        self._pct_label.setText(f"{pct}%")
        self._chars_label.setText(f"{done:,} / {total:,}")

    def update_words(self, done: int, total: int) -> None:
        self._words_label.setText(f"{done:,} / {total:,}")

    def update_wpm(self, wpm: float) -> None:
        self._wpm_label.setText(f"{wpm:.0f} WPM")

    def update_time(self, seconds: float) -> None:
        if seconds < 0:
            seconds = 0
        mins = int(seconds) // 60
        secs = int(seconds) % 60
        self._time_label.setText(f"{mins}:{secs:02d}")

    def reset(self) -> None:
        self._bar.setValue(0)
        self._pct_label.setText("0%")
        self._chars_label.setText("0 / 0")
        self._words_label.setText("0 / 0")
        self._wpm_label.setText("– WPM")
        self._time_label.setText("–:––")


# ──────────────────────────────────────────────────────────────────────────────
# Stat Bar (shows text statistics below editor)
# ──────────────────────────────────────────────────────────────────────────────

class StatBar(QWidget):
    """Shows character / word / line count and estimated duration."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(20)

        self._chars = self._pill("0 chars")
        self._words = self._pill("0 words")
        self._lines = self._pill("0 lines")
        self._time  = self._pill("~0:00")

        for w in (self._chars, self._words, self._lines, self._time):
            layout.addWidget(w)
        layout.addStretch()

    def _pill(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("muted")
        return lbl

    def update_stats(self, chars: int, words: int, lines: int, duration_secs: float) -> None:
        self._chars.setText(f"{chars:,} chars")
        self._words.setText(f"{words:,} words")
        self._lines.setText(f"{lines:,} lines")
        mins = int(duration_secs) // 60
        secs = int(duration_secs) % 60
        self._time.setText(f"~{mins}:{secs:02d}")


# ──────────────────────────────────────────────────────────────────────────────
# Countdown Display
# ──────────────────────────────────────────────────────────────────────────────

class CountdownWidget(QFrame):
    """Large countdown + target window info."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("card")
        self.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._title = QLabel("ARMED — Select your target window")
        self._title.setObjectName("heading")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._target = QLabel("Target: —")
        self._target.setObjectName("subheading")
        self._target.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._number = QLabel("5")
        num_font = QFont("Segoe UI", 64, QFont.Weight.Bold)
        self._number.setFont(num_font)
        self._number.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._number.setStyleSheet("color: #7c6fcd;")

        self._hint = QLabel("seconds until typing begins")
        self._hint.setObjectName("muted")
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self._title)
        layout.addWidget(self._target)
        layout.addSpacing(8)
        layout.addWidget(self._number)
        layout.addWidget(self._hint)

    def show_countdown(self, seconds: int, target_title: str = "") -> None:
        self._number.setText(str(seconds))
        if target_title:
            # Truncate for display, don't log
            truncated = target_title[:60] + ("…" if len(target_title) > 60 else "")
            self._target.setText(f"Target: {truncated}")
        self.show()

    def hide_countdown(self) -> None:
        self.hide()

    def set_target(self, title: str) -> None:
        truncated = title[:60] + ("…" if len(title) > 60 else "")
        self._target.setText(f"Target: {truncated}")


# ──────────────────────────────────────────────────────────────────────────────
# Hotkey Display Label
# ──────────────────────────────────────────────────────────────────────────────

class HotkeyLabel(QLabel):
    """Pill-style label showing a keyboard shortcut."""

    def __init__(self, combo: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.set_combo(combo)
        self.setStyleSheet(
            "QLabel { background: #2a2a35; color: #a89ae8; "
            "border: 1px solid #3e3e50; border-radius: 6px; "
            "padding: 3px 10px; font-size: 11px; font-family: 'Consolas', monospace; }"
        )

    def set_combo(self, combo: str) -> None:
        parts = [p.capitalize() for p in combo.split("+")]
        display_map = {"Ctrl": "Ctrl", "Shift": "Shift", "Alt": "Alt"}
        parts = [display_map.get(p, p.upper() if len(p) == 1 else p) for p in parts]
        self.setText("+".join(parts))


# ──────────────────────────────────────────────────────────────────────────────
# Separator
# ──────────────────────────────────────────────────────────────────────────────

def make_separator(horizontal: bool = True) -> QFrame:
    sep = QFrame()
    sep.setFrameShape(
        QFrame.Shape.HLine if horizontal else QFrame.Shape.VLine
    )
    sep.setFrameShadow(QFrame.Shadow.Plain)
    return sep
