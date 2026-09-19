"""
AutoKeyboard Pro — Settings Dialog
Tabbed settings: Typing | Safety | Hotkeys | Appearance
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QKeySequence
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QSlider, QSpinBox, QDoubleSpinBox, QComboBox,
    QCheckBox, QRadioButton, QPushButton, QButtonGroup,
    QFormLayout, QGroupBox, QLineEdit, QFrame, QSizePolicy,
    QDialogButtonBox
)

from config.settings import AppSettings
from core.hotkeys import HotkeyManager


class HotkeyEdit(QLineEdit):
    """
    Line edit that captures a key combination when the user presses keys.
    Converts the pressed sequence into a combo string (ctrl+shift+alt+x).
    """

    combo_changed = Signal(str)

    def __init__(self, combo: str = "", parent=None):
        super().__init__(parent)
        self._combo = combo
        self.setText(self._format_display(combo))
        self.setReadOnly(True)
        self.setPlaceholderText("Click and press keys…")
        self.setToolTip("Click here, then press your desired key combination")

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.setPlaceholderText("Press keys now…")
        self.setText("")

    def keyPressEvent(self, event):
        key = event.key()
        mods = event.modifiers()

        # Ignore standalone modifier presses
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            return

        parts = []
        if mods & Qt.KeyboardModifier.ControlModifier:
            parts.append("ctrl")
        if mods & Qt.KeyboardModifier.ShiftModifier:
            parts.append("shift")
        if mods & Qt.KeyboardModifier.AltModifier:
            parts.append("alt")

        key_name = QKeySequence(key).toString().lower()
        if key_name:
            parts.append(key_name)

        if len(parts) >= 2:
            self._combo = "+".join(parts)
            self.setText(self._format_display(self._combo))
            self.combo_changed.emit(self._combo)
        else:
            self.setText(self._format_display(self._combo))

    def _format_display(self, combo: str) -> str:
        if not combo:
            return ""
        parts = [p.capitalize() for p in combo.split("+")]
        return "+".join(parts)

    @property
    def combo(self) -> str:
        return self._combo


class SettingsDialog(QDialog):
    """Modal settings dialog."""

    settings_changed = Signal(AppSettings)

    def __init__(self, settings: AppSettings, hotkey_mgr: HotkeyManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings — AutoKeyboard Pro")
        self.setMinimumWidth(560)
        self.setMinimumHeight(500)
        self._settings = AppSettings(**{
            k: getattr(settings, k) for k in settings.__dataclass_fields__
        })
        self._hotkey_mgr = hotkey_mgr
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setStyleSheet(
            "QFrame { background: #1e1e26; border-bottom: 1px solid #2e2e3e; }"
        )
        hdr_layout = QHBoxLayout(header)
        hdr_layout.setContentsMargins(24, 16, 24, 16)
        title = QLabel("⚙  Settings")
        title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        title.setStyleSheet("color: #e8e8f0; background: transparent;")
        hdr_layout.addWidget(title)
        layout.addWidget(header)

        # Tabs
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        layout.addWidget(self._tabs, 1)

        self._tabs.addTab(self._build_typing_tab(), "Typing")
        self._tabs.addTab(self._build_safety_tab(), "Safety")
        self._tabs.addTab(self._build_hotkeys_tab(), "Hotkeys")
        self._tabs.addTab(self._build_appearance_tab(), "Appearance")

        # Buttons
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.setContentsMargins(16, 8, 16, 16)
        btn_box.accepted.connect(self._on_save)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    # ──────────────────────────────────────────────────────────────────
    # Tab builders
    # ──────────────────────────────────────────────────────────────────

    def _build_typing_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Default WPM
        wpm_group = QGroupBox("DEFAULT TYPING SPEED")
        wpm_form = QFormLayout(wpm_group)
        wpm_form.setSpacing(10)

        self._wpm_spin = QSpinBox()
        self._wpm_spin.setRange(10, 300)
        self._wpm_spin.setValue(self._settings.default_wpm)
        self._wpm_spin.setSuffix(" WPM")
        wpm_form.addRow("Default WPM:", self._wpm_spin)
        layout.addWidget(wpm_group)

        # Mode
        mode_group = QGroupBox("TYPING MODE")
        mode_layout = QVBoxLayout(mode_group)
        mode_layout.setSpacing(8)
        self._mode_group = QButtonGroup(self)
        for i, mode in enumerate(["Standard", "Natural", "Custom"]):
            rb = QRadioButton(mode)
            rb.setChecked(mode == self._settings.typing_mode)
            self._mode_group.addButton(rb, i)
            mode_layout.addWidget(rb)
        layout.addWidget(mode_group)

        # Timing variation
        var_group = QGroupBox("TIMING VARIATION")
        var_form = QFormLayout(var_group)
        self._var_spin = QDoubleSpinBox()
        self._var_spin.setRange(0.0, 1.0)
        self._var_spin.setSingleStep(0.05)
        self._var_spin.setValue(self._settings.variation_pct)
        self._var_spin.setDecimals(2)
        self._var_spin.setSuffix("  (0=none, 0.25=±25%)")
        var_form.addRow("Variation:", self._var_spin)

        self._paragraph_spin = QDoubleSpinBox()
        self._paragraph_spin.setRange(1.0, 10.0)
        self._paragraph_spin.setSingleStep(0.5)
        self._paragraph_spin.setValue(self._settings.paragraph_pause_mult)
        self._paragraph_spin.setSuffix("× base delay")
        var_form.addRow("Paragraph pause:", self._paragraph_spin)
        layout.addWidget(var_group)

        # Countdown
        countdown_group = QGroupBox("COUNTDOWN")
        countdown_form = QFormLayout(countdown_group)
        self._countdown_spin = QSpinBox()
        self._countdown_spin.setRange(1, 15)
        self._countdown_spin.setValue(self._settings.countdown_seconds)
        self._countdown_spin.setSuffix(" seconds")
        countdown_form.addRow("Start countdown:", self._countdown_spin)
        layout.addWidget(countdown_group)

        layout.addStretch()
        return w

    def _build_safety_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        safety_group = QGroupBox("SAFETY OPTIONS")
        safety_layout = QVBoxLayout(safety_group)
        safety_layout.setSpacing(10)

        self._stop_window_chk = QCheckBox(
            "Stop typing if the target window changes"
        )
        self._stop_window_chk.setChecked(self._settings.stop_on_window_change)
        self._stop_window_chk.setToolTip(
            "Stops typing immediately if you switch to a different application window"
        )

        self._confirm_start_chk = QCheckBox(
            "Require confirmation before starting"
        )
        self._confirm_start_chk.setChecked(self._settings.require_confirm_start)

        self._emergency_stop_chk = QCheckBox(
            "Enable global emergency stop hotkey"
        )
        self._emergency_stop_chk.setChecked(self._settings.emergency_stop_enabled)

        safety_layout.addWidget(self._stop_window_chk)
        safety_layout.addWidget(self._confirm_start_chk)
        safety_layout.addWidget(self._emergency_stop_chk)
        layout.addWidget(safety_group)

        # Notice
        notice = QLabel(
            "ℹ  AutoKeyboard Pro does not record keystrokes, store passwords, "
            "capture clipboard contents, or upload any data. It only generates "
            "output when you explicitly arm and activate typing."
        )
        notice.setWordWrap(True)
        notice.setStyleSheet(
            "color: #7070a0; font-size: 12px; background: #16161c; "
            "border: 1px solid #2e2e3e; border-radius: 8px; padding: 12px;"
        )
        layout.addWidget(notice)
        layout.addStretch()
        return w

    def _build_hotkeys_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        hk_group = QGroupBox("GLOBAL HOTKEYS")
        hk_form = QFormLayout(hk_group)
        hk_form.setSpacing(12)
        hk_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._hk_start = HotkeyEdit(self._settings.hotkey_start)
        self._hk_pause = HotkeyEdit(self._settings.hotkey_pause)
        self._hk_stop  = HotkeyEdit(self._settings.hotkey_stop)

        hk_form.addRow("Start typing:", self._hk_start)
        hk_form.addRow("Pause / Resume:", self._hk_pause)
        hk_form.addRow("Emergency Stop:", self._hk_stop)

        layout.addWidget(hk_group)

        note = QLabel(
            "Click a hotkey field and press your desired key combination.\n"
            "Requires at least one modifier key (Ctrl, Shift, or Alt).\n"
            "Note: Global hotkeys may require Administrator on some Windows systems."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #7070a0; font-size: 12px; background: transparent;")
        layout.addWidget(note)
        layout.addStretch()
        return w

    def _build_appearance_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        theme_group = QGroupBox("THEME")
        theme_layout = QVBoxLayout(theme_group)
        theme_layout.setSpacing(8)
        self._theme_group = QButtonGroup(self)
        for i, theme in enumerate(["Dark", "Light", "System"]):
            rb = QRadioButton(theme)
            rb.setChecked(theme == self._settings.theme)
            self._theme_group.addButton(rb, i)
            theme_layout.addWidget(rb)
        layout.addWidget(theme_group)
        layout.addStretch()
        return w

    # ──────────────────────────────────────────────────────────────────
    # Save
    # ──────────────────────────────────────────────────────────────────

    def _on_save(self):
        s = self._settings

        # Typing
        s.default_wpm = self._wpm_spin.value()
        modes = ["Standard", "Natural", "Custom"]
        s.typing_mode = modes[self._mode_group.checkedId()]
        s.variation_pct = self._var_spin.value()
        s.paragraph_pause_mult = self._paragraph_spin.value()
        s.countdown_seconds = self._countdown_spin.value()

        # Safety
        s.stop_on_window_change = self._stop_window_chk.isChecked()
        s.require_confirm_start = self._confirm_start_chk.isChecked()
        s.emergency_stop_enabled = self._emergency_stop_chk.isChecked()

        # Hotkeys
        s.hotkey_start = self._hk_start.combo or s.hotkey_start
        s.hotkey_pause = self._hk_pause.combo or s.hotkey_pause
        s.hotkey_stop  = self._hk_stop.combo  or s.hotkey_stop

        # Appearance
        themes = ["Dark", "Light", "System"]
        s.theme = themes[self._theme_group.checkedId()]

        s.save()
        self.settings_changed.emit(s)
        self.accept()
