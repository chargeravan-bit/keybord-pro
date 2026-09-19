"""
AutoKeyboard Pro — First-Launch Permission Dialog
Shown once to inform the user that the application can generate keyboard input.
Permission state is persisted in settings.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QSizePolicy
)


class PermissionDialog(QDialog):
    """
    Modal dialog shown on first launch.
    User must explicitly click 'I Understand & Enable' to proceed.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AutoKeyboard Pro — Keyboard Input Permission")
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowCloseButtonHint
        )
        self.setFixedWidth(520)
        self.setModal(True)
        self._accepted = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 28)
        layout.setSpacing(0)

        # ── Icon + title ───────────────────────────────────────────────
        title_row = QHBoxLayout()
        icon_lbl = QLabel("⌨")
        icon_lbl.setFont(QFont("Segoe UI Emoji", 32))
        icon_lbl.setStyleSheet("color: #7c6fcd; background: transparent;")
        icon_lbl.setFixedWidth(52)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        t = QLabel("Keyboard Input Permission")
        t.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        t.setStyleSheet("color: #e8e8f0; background: transparent;")
        subtitle = QLabel("AutoKeyboard Pro")
        subtitle.setStyleSheet("color: #7c6fcd; font-size: 12px; background: transparent;")
        title_col.addWidget(t)
        title_col.addWidget(subtitle)

        title_row.addWidget(icon_lbl)
        title_row.addLayout(title_col)
        title_row.addStretch()
        layout.addLayout(title_row)
        layout.addSpacing(20)

        # ── Separator ──────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #2e2e3e;")
        layout.addWidget(sep)
        layout.addSpacing(20)

        # ── Body text ──────────────────────────────────────────────────
        body_text = (
            "AutoKeyboard Pro can generate keyboard input in other Windows applications.\n\n"
            "When you arm the typing tool, it will simulate key presses in whichever "
            "application you select — exactly as if you typed the text yourself on a "
            "physical keyboard.\n\n"
            "Only enable this feature if you understand and authorize this behaviour."
        )
        body = QLabel(body_text)
        body.setWordWrap(True)
        body.setStyleSheet(
            "color: #9090a8; font-size: 13px; line-height: 1.6; background: transparent;"
        )
        layout.addWidget(body)
        layout.addSpacing(20)

        # ── Important notice box ───────────────────────────────────────
        notice_frame = QFrame()
        notice_frame.setStyleSheet(
            "QFrame { background: #1a1510; border: 1.5px solid #e0a040; border-radius: 8px; }"
        )
        notice_layout = QVBoxLayout(notice_frame)
        notice_layout.setContentsMargins(14, 12, 14, 12)
        notice_layout.setSpacing(4)

        notice_title = QLabel("⚠  Important")
        notice_title.setStyleSheet(
            "color: #e0a040; font-weight: bold; font-size: 12px; background: transparent;"
        )
        notice_body = QLabel(
            "AutoKeyboard Pro does NOT record your keystrokes, capture passwords, "
            "monitor clipboard content, or upload any data.\n"
            "It only generates output when you explicitly activate it."
        )
        notice_body.setWordWrap(True)
        notice_body.setStyleSheet(
            "color: #c0a060; font-size: 12px; background: transparent;"
        )
        notice_layout.addWidget(notice_title)
        notice_layout.addWidget(notice_body)
        layout.addWidget(notice_frame)
        layout.addSpacing(24)

        # ── Buttons ────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setObjectName("btn_secondary")
        self._cancel_btn.setFixedHeight(40)
        self._cancel_btn.clicked.connect(self._on_cancel)

        self._accept_btn = QPushButton("✓  I Understand & Enable")
        self._accept_btn.setObjectName("btn_arm")
        self._accept_btn.setFixedHeight(40)
        self._accept_btn.clicked.connect(self._on_accept)

        btn_row.addWidget(self._cancel_btn)
        btn_row.addWidget(self._accept_btn)
        layout.addLayout(btn_row)

    def _on_accept(self):
        self._accepted = True
        self.accept()

    def _on_cancel(self):
        self._accepted = False
        self.reject()

    @property
    def permission_granted(self) -> bool:
        return self._accepted
