"""
AutoKeyboard Pro — AI Brain Overlay
A small, always-on-top floating widget that indicates the AI is processing.
Shows animated dots and a status message, dismisses automatically.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QFont, QColor, QPainter, QBrush, QGuiApplication
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QApplication


class _DotWidget(QWidget):
    """Three animated pulsing dots."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(48, 16)
        self._phase = 0
        self._timer = QTimer(self)
        self._timer.setInterval(150)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self):
        self._phase = (self._phase + 1) % 6
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        dot_r = 5
        spacing = 14
        x0 = 4
        y = self.height() // 2
        for i in range(3):
            active = (self._phase % 3) == i
            color = QColor("#7c6fcd") if active else QColor("#3a3a5a")
            p.setBrush(QBrush(color))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(x0 + i * spacing, y - dot_r, dot_r * 2, dot_r * 2)

    def stop(self):
        self._timer.stop()


class AiOverlay(QWidget):
    """
    Frameless floating overlay that shows while the AI Brain is working.
    Usage::

        overlay = AiOverlay()
        overlay.show()
        overlay.set_status("🧠  Thinking…")
        # later …
        overlay.close()
    """

    def __init__(self, parent=None):
        super().__init__(
            parent,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(340, 88)

        self._build_ui()
        self._center_on_screen()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # Card
        card = QWidget(self)
        card.setObjectName("ai_overlay_card")
        card.setStyleSheet(
            """
            QWidget#ai_overlay_card {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1a2e, stop:1 #16213e);
                border: 1px solid #4040a0;
                border-radius: 18px;
            }
            """
        )
        card.setFixedSize(340, 88)

        inner = QHBoxLayout(card)
        inner.setContentsMargins(20, 16, 20, 16)
        inner.setSpacing(16)

        # Brain icon
        icon = QLabel("🧠")
        icon.setFont(QFont("Segoe UI Emoji", 24))
        icon.setStyleSheet("background: transparent;")
        inner.addWidget(icon)

        # Text + dots
        text_col = QVBoxLayout()
        text_col.setSpacing(4)

        self._status_label = QLabel("Capturing screen…")
        self._status_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        self._status_label.setStyleSheet("color: #c8c8e8; background: transparent;")

        sub = QLabel("AutoKeyboard Pro — AI Brain")
        sub.setFont(QFont("Segoe UI", 9))
        sub.setStyleSheet("color: #6060a8; background: transparent;")

        dot_row = QHBoxLayout()
        dot_row.setSpacing(6)
        self._dots = _DotWidget()
        dot_row.addWidget(self._dots)
        dot_row.addStretch()

        text_col.addWidget(self._status_label)
        text_col.addLayout(dot_row)
        text_col.addWidget(sub)

        inner.addLayout(text_col, 1)

        root.addWidget(card)

    def _center_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + geo.height() - self.height() - 80   # bottom-centre
            self.move(x, y)

    def set_status(self, text: str):
        """Update the status message (safe to call from any thread via Qt signal)."""
        self._status_label.setText(text)

    def closeEvent(self, event):
        self._dots.stop()
        super().closeEvent(event)
