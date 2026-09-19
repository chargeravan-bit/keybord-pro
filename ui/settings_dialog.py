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
    QDialogButtonBox, QMessageBox
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
        self._tabs.addTab(self._build_ai_brain_tab(), "🧠 AI Brain")

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

    def _build_ai_brain_tab(self) -> QWidget:
        """AI Brain settings: provider, API key, base URL, model, hotkey."""
        from core.ai_brain import PROVIDER_PRESETS

        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # ── Provider ──────────────────────────────────────────────────
        provider_group = QGroupBox("AI PROVIDER")
        provider_form = QFormLayout(provider_group)
        provider_form.setSpacing(10)

        self._ai_provider_combo = QComboBox()
        self._ai_provider_combo.addItems(["OpenRouter", "OpenAI", "Gemini", "Custom"])
        idx = self._ai_provider_combo.findText(self._settings.ai_provider)
        self._ai_provider_combo.setCurrentIndex(max(0, idx))
        self._ai_provider_combo.currentTextChanged.connect(self._on_ai_provider_changed)
        provider_form.addRow("Provider:", self._ai_provider_combo)

        self._ai_key_edit = QLineEdit(self._settings.ai_api_key)
        self._ai_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._ai_key_edit.setPlaceholderText("Paste your API key here…")
        self._ai_key_edit.setToolTip("Your API key — stored locally on this machine only")

        key_row = QHBoxLayout()
        key_row.setSpacing(6)
        key_row.addWidget(self._ai_key_edit, 1)
        self._show_key_btn = QPushButton("👁")
        self._show_key_btn.setFixedWidth(36)
        self._show_key_btn.setCheckable(True)
        self._show_key_btn.setToolTip("Show / hide API key")
        self._show_key_btn.toggled.connect(
            lambda on: self._ai_key_edit.setEchoMode(
                QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password
            )
        )
        key_row.addWidget(self._show_key_btn)
        self._test_api_btn = QPushButton("⚡ Test")
        self._test_api_btn.setFixedWidth(72)
        self._test_api_btn.setToolTip("Send a quick test request to verify the key works")
        self._test_api_btn.clicked.connect(self._test_ai_connection)
        key_row.addWidget(self._test_api_btn)

        provider_form.addRow("API Key:", key_row)

        self._ai_base_url_edit = QLineEdit(self._settings.ai_base_url)
        self._ai_base_url_edit.setPlaceholderText("https://openrouter.ai/api/v1")
        self._ai_base_url_edit.setToolTip(
            "Base URL for any OpenAI-compatible endpoint\n"
            "(auto-filled when you choose a preset provider)"
        )
        provider_form.addRow("Base URL:", self._ai_base_url_edit)

        self._ai_model_edit = QLineEdit(self._settings.ai_model)
        self._ai_model_edit.setPlaceholderText("e.g. google/gemma-3n-e4b-it:free")
        self._ai_model_edit.setToolTip(
            "Model slug sent to the API.\n"
            "OpenRouter examples: google/gemma-3n-e4b-it:free, mistralai/mistral-7b-instruct:free\n"
            "OpenAI examples: gpt-4o, gpt-4o-mini\n"
            "Gemini examples: gemini-2.0-flash"
        )
        provider_form.addRow("Model:", self._ai_model_edit)

        layout.addWidget(provider_group)

        # ── Hotkey ────────────────────────────────────────────────────
        hk_group = QGroupBox("AI BRAIN HOTKEY")
        hk_form = QFormLayout(hk_group)
        self._hk_ai_brain = HotkeyEdit(self._settings.ai_brain_hotkey)
        hk_form.addRow("Trigger:", self._hk_ai_brain)
        layout.addWidget(hk_group)

        # ── Privacy notice ────────────────────────────────────────────
        notice = QLabel(
            "⚠  When triggered, AI Brain takes a screenshot of your entire screen "
            "and reads your clipboard, then sends both to the configured AI provider "
            "over the internet. No data is stored on disk by AutoKeyboard Pro. "
            "Ensure you are comfortable with your chosen provider's privacy policy."
        )
        notice.setWordWrap(True)
        notice.setStyleSheet(
            "color: #9090a8; font-size: 11px; background: #1a1016; "
            "border: 1px solid #5a2e2e; border-radius: 8px; padding: 10px;"
        )
        layout.addWidget(notice)
        layout.addStretch()
        return w

    def _on_ai_provider_changed(self, provider: str):
        """Auto-fill base URL and model when a preset provider is selected."""
        from core.ai_brain import PROVIDER_PRESETS
        preset = PROVIDER_PRESETS.get(provider, {})
        if preset.get("base_url"):
            self._ai_base_url_edit.setText(preset["base_url"])
        if preset.get("default_model"):
            self._ai_model_edit.setText(preset["default_model"])

    def _test_ai_connection(self):
        """Send a minimal text-only ping to verify the API key and endpoint."""
        import threading
        import json
        import urllib.request
        import urllib.error

        key = self._ai_key_edit.text().strip()
        base_url = self._ai_base_url_edit.text().strip()
        model = self._ai_model_edit.text().strip()

        if not key:
            QMessageBox.warning(self, "API Key Missing", "Please enter an API key first.")
            return
        if not base_url:
            QMessageBox.warning(self, "Base URL Missing", "Please enter a base URL.")
            return

        self._test_api_btn.setEnabled(False)
        self._test_api_btn.setText("…")

        def _do_test():
            try:
                endpoint = base_url.rstrip("/") + "/chat/completions"
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
                    "max_tokens": 8,
                }
                data = json.dumps(payload).encode()
                req = urllib.request.Request(
                    endpoint, data=data,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {key}",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    result = json.loads(resp.read())
                    answer = result["choices"][0]["message"]["content"].strip()
                from PySide6.QtCore import QMetaObject, Qt
                from PySide6.QtWidgets import QApplication
                # Post result to GUI thread
                self._test_result = (True, f"✓ Connected!  Model replied: {answer!r}")
            except Exception as exc:
                self._test_result = (False, str(exc))
            from PySide6.QtCore import QMetaObject, Qt
            QMetaObject.invokeMethod(self, "_show_test_result", Qt.ConnectionType.QueuedConnection)

        threading.Thread(target=_do_test, daemon=True).start()

    def _show_test_result(self):
        """Called on the GUI thread after _test_ai_connection finishes."""
        self._test_api_btn.setEnabled(True)
        self._test_api_btn.setText("⚡ Test")
        ok, msg = getattr(self, "_test_result", (False, "No result"))
        if ok:
            QMessageBox.information(self, "AI Connection Test", msg)
        else:
            QMessageBox.warning(self, "AI Connection Test Failed", msg)


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

        # AI Brain
        s.ai_provider    = self._ai_provider_combo.currentText()
        s.ai_api_key     = self._ai_key_edit.text().strip()
        s.ai_base_url    = self._ai_base_url_edit.text().strip()
        s.ai_model       = self._ai_model_edit.text().strip()
        s.ai_brain_hotkey = self._hk_ai_brain.combo or s.ai_brain_hotkey

        s.save()
        self.settings_changed.emit(s)
        self.accept()
