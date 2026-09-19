"""
AutoKeyboard Pro — Main Window
The primary application interface.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

from PySide6.QtCore import (
    Qt, QTimer, Signal, Slot, QSize, QThread
)
from PySide6.QtGui import QFont, QIcon, QTextCursor, QAction
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QPlainTextEdit, QSlider,
    QSpinBox, QRadioButton, QCheckBox, QButtonGroup,
    QFrame, QSizePolicy, QScrollArea, QTabWidget,
    QMessageBox, QSplitter, QStatusBar, QToolBar
)

from config.settings import AppSettings
from core.typing_engine import TypingEngine, TypingState
from core.timing_engine import TimingConfig, TypingMode
from core.hotkeys import HotkeyManager
from core.text_parser import text_statistics, estimate_duration_seconds
from ui.widgets import (
    StatusBadge, ProgressPanel, StatBar,
    CountdownWidget, HotkeyLabel, make_separator
)
from ui.settings_dialog import SettingsDialog
from ui.permission_dialog import PermissionDialog
from ui.ai_overlay import AiOverlay

logger = logging.getLogger(__name__)

WPM_PRESETS = [10, 20, 30, 40, 50, 60, 80, 100, 120, 150, 200]


class MainWindow(QMainWindow):
    """AutoKeyboard Pro main window."""

    def __init__(self, settings: AppSettings, hotkey_mgr: HotkeyManager):
        super().__init__()
        self._settings = settings
        self._hotkey_mgr = hotkey_mgr
        self._engine = TypingEngine(self)
        self._current_state = TypingState.IDLE.value
        self._is_test_mode = False
        self._ai_worker: Optional[object] = None
        self._ai_overlay: Optional[AiOverlay] = None

        self._setup_window()
        self._build_ui()
        self._connect_engine()
        self._register_hotkeys()
        self._refresh_stats()

    # ──────────────────────────────────────────────────────────────────
    # Window setup
    # ──────────────────────────────────────────────────────────────────

    def _setup_window(self):
        self.setWindowTitle("AutoKeyboard Pro")
        self.setMinimumSize(860, 700)
        self.resize(960, 780)
        self.setWindowIcon(QIcon())

        # Status bar
        self._status_bar = QStatusBar(self)
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Ready")

    # ──────────────────────────────────────────────────────────────────
    # UI construction
    # ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Left sidebar ───────────────────────────────────────────────
        sidebar = self._build_sidebar()
        root.addWidget(sidebar)

        # ── Main content area ──────────────────────────────────────────
        content = self._build_content()
        root.addWidget(content, 1)

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 20, 16, 20)
        layout.setSpacing(8)

        # ── App title ──────────────────────────────────────────────────
        icon_lbl = QLabel("⌨")
        icon_lbl.setFont(QFont("Segoe UI Emoji", 26))
        icon_lbl.setStyleSheet("color: #7c6fcd; background: transparent;")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("AutoKeyboard Pro")
        title.setObjectName("heading")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setWordWrap(True)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Human-like keyboard\nautomation for Windows")
        subtitle.setObjectName("subheading")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)

        layout.addWidget(icon_lbl)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(8)
        layout.addWidget(make_separator())
        layout.addSpacing(8)

        # ── Status badge ───────────────────────────────────────────────
        status_lbl = QLabel("STATUS")
        status_lbl.setObjectName("section_label")
        layout.addWidget(status_lbl)

        self._status_badge = StatusBadge()
        layout.addWidget(self._status_badge)
        layout.addSpacing(12)

        # ── Hotkey reference ───────────────────────────────────────────
        hk_lbl = QLabel("GLOBAL HOTKEYS")
        hk_lbl.setObjectName("section_label")
        layout.addWidget(hk_lbl)

        def hk_row(label: str, combo: str) -> QWidget:
            w = QWidget()
            w.setStyleSheet("background: transparent;")
            h = QHBoxLayout(w)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(6)
            l = QLabel(label)
            l.setObjectName("muted")
            l.setFixedWidth(54)
            hk = HotkeyLabel(combo)
            h.addWidget(l)
            h.addWidget(hk)
            h.addStretch()
            return w

        self._hk_start_row = hk_row("Start:", self._settings.hotkey_start)
        self._hk_pause_row = hk_row("Pause:", self._settings.hotkey_pause)
        self._hk_stop_row  = hk_row("Stop:",  self._settings.hotkey_stop)
        layout.addWidget(self._hk_start_row)
        layout.addWidget(self._hk_pause_row)
        layout.addWidget(self._hk_stop_row)

        layout.addStretch()
        layout.addWidget(make_separator())

        # ── Settings button ────────────────────────────────────────────
        self._settings_btn = QPushButton("⚙  Settings")
        self._settings_btn.setObjectName("btn_secondary")
        self._settings_btn.clicked.connect(self._open_settings)
        layout.addWidget(self._settings_btn)

        return sidebar

    def _build_content(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # ── Tabs: Main / Test Mode ─────────────────────────────────────
        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_main_tab(), "  Type  ")
        self._tabs.addTab(self._build_test_tab(), "  Test Mode  ")
        self._tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self._tabs, 1)

        # ── Progress panel ─────────────────────────────────────────────
        self._progress_panel = ProgressPanel()
        self._progress_panel.setVisible(False)
        layout.addWidget(self._progress_panel)

        # ── Countdown widget ───────────────────────────────────────────
        self._countdown_widget = CountdownWidget()
        layout.addWidget(self._countdown_widget)

        # ── Control buttons ────────────────────────────────────────────
        layout.addWidget(self._build_controls())

        return content

    def _build_main_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(12)

        # TEXT section
        text_lbl = QLabel("TEXT")
        text_lbl.setObjectName("section_label")
        layout.addWidget(text_lbl)

        self._text_editor = QPlainTextEdit()
        self._text_editor.setPlaceholderText(
            "Paste or type your text here…\n\n"
            "AutoKeyboard Pro will simulate typing this text character by character, "
            "exactly as if typed on a physical keyboard."
        )
        self._text_editor.setMinimumHeight(160)
        self._text_editor.textChanged.connect(self._refresh_stats)
        layout.addWidget(self._text_editor)

        self._stat_bar = StatBar()
        layout.addWidget(self._stat_bar)

        layout.addWidget(make_separator())

        # SPEED section
        speed_lbl = QLabel("TYPING SPEED")
        speed_lbl.setObjectName("section_label")
        layout.addWidget(speed_lbl)

        speed_row = QHBoxLayout()
        speed_row.setSpacing(10)

        self._wpm_slider = QSlider(Qt.Orientation.Horizontal)
        self._wpm_slider.setRange(10, 200)
        self._wpm_slider.setValue(self._settings.default_wpm)
        self._wpm_slider.setTickPosition(QSlider.TickPosition.NoTicks)
        self._wpm_slider.valueChanged.connect(self._on_slider_changed)

        self._wpm_spin = QSpinBox()
        self._wpm_spin.setRange(10, 300)
        self._wpm_spin.setValue(self._settings.default_wpm)
        self._wpm_spin.setSuffix(" WPM")
        self._wpm_spin.setFixedWidth(100)
        self._wpm_spin.valueChanged.connect(self._on_spin_changed)

        speed_row.addWidget(QLabel("10"))
        speed_row.addWidget(self._wpm_slider, 1)
        speed_row.addWidget(QLabel("200"))
        speed_row.addWidget(self._wpm_spin)
        layout.addLayout(speed_row)

        # WPM presets
        presets_row = QHBoxLayout()
        presets_row.setSpacing(6)
        for wpm in WPM_PRESETS:
            btn = QPushButton(str(wpm))
            btn.setFixedHeight(28)
            btn.setFixedWidth(44)
            btn.setObjectName("btn_secondary")
            btn.clicked.connect(lambda _, w=wpm: self._set_wpm(w))
            presets_row.addWidget(btn)
        presets_row.addStretch()
        layout.addLayout(presets_row)

        layout.addWidget(make_separator())

        # MODE section
        mode_lbl = QLabel("TYPING MODE")
        mode_lbl.setObjectName("section_label")
        layout.addWidget(mode_lbl)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(20)
        self._mode_bg = QButtonGroup(self)
        mode_descriptions = {
            "Standard": "Consistent timing based on selected WPM",
            "Natural":  "Natural-style typing simulation with subtle timing variation",
            "Custom":   "Advanced — configure timing variation in Settings",
        }
        for i, mode in enumerate(["Standard", "Natural", "Custom"]):
            rb = QRadioButton(mode)
            rb.setChecked(mode == self._settings.typing_mode)
            rb.setToolTip(mode_descriptions[mode])
            self._mode_bg.addButton(rb, i)
            mode_row.addWidget(rb)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        # Safety checkbox
        self._stop_window_chk = QCheckBox("Stop if active window changes")
        self._stop_window_chk.setChecked(self._settings.stop_on_window_change)
        self._stop_window_chk.toggled.connect(
            lambda v: setattr(self._settings, "stop_on_window_change", v)
        )
        layout.addWidget(self._stop_window_chk)

        layout.addStretch()
        return w

    def _build_test_tab(self) -> QWidget:
        """Safe internal test mode — types into an internal text box."""
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(12)

        notice = QLabel(
            "🧪  Test Mode — AutoKeyboard Pro will type into the text box below instead of "
            "an external application. Use this to verify timing and behaviour safely."
        )
        notice.setWordWrap(True)
        notice.setStyleSheet(
            "color: #9090a8; background: #16161c; border: 1px solid #2e2e3e; "
            "border-radius: 8px; padding: 10px; font-size: 12px;"
        )
        layout.addWidget(notice)

        src_lbl = QLabel("SOURCE TEXT")
        src_lbl.setObjectName("section_label")
        layout.addWidget(src_lbl)

        self._test_source = QPlainTextEdit()
        self._test_source.setPlaceholderText("Enter text to type in test mode…")
        self._test_source.setFixedHeight(100)
        self._test_source.textChanged.connect(self._refresh_stats)
        layout.addWidget(self._test_source)

        out_lbl = QLabel("OUTPUT (typed here)")
        out_lbl.setObjectName("section_label")
        layout.addWidget(out_lbl)

        self._test_output = QPlainTextEdit()
        self._test_output.setPlaceholderText("Typed output will appear here…")
        self._test_output.setReadOnly(True)
        layout.addWidget(self._test_output)

        layout.addStretch()
        return w

    def _build_controls(self) -> QWidget:
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._arm_btn = QPushButton("▶  ARM TYPING")
        self._arm_btn.setObjectName("btn_arm")
        self._arm_btn.setMinimumHeight(48)
        self._arm_btn.clicked.connect(self._on_arm)

        self._pause_btn = QPushButton("⏸  PAUSE")
        self._pause_btn.setObjectName("btn_secondary")
        self._pause_btn.setMinimumHeight(48)
        self._pause_btn.setVisible(False)
        self._pause_btn.clicked.connect(self._on_pause_resume)

        self._stop_btn = QPushButton("⏹  STOP NOW")
        self._stop_btn.setObjectName("btn_stop")
        self._stop_btn.setMinimumHeight(48)
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._on_stop)

        layout.addWidget(self._arm_btn, 2)
        layout.addWidget(self._pause_btn, 1)
        layout.addWidget(self._stop_btn, 1)

        return w

    # ──────────────────────────────────────────────────────────────────
    # Engine wiring
    # ──────────────────────────────────────────────────────────────────

    def _connect_engine(self):
        self._engine.state_changed.connect(self._on_state_changed)
        self._engine.progress_updated.connect(self._on_progress)
        self._engine.words_updated.connect(self._on_words)
        self._engine.countdown_tick.connect(self._on_countdown)
        self._engine.wpm_measured.connect(self._on_wpm_measured)
        self._engine.time_remaining.connect(self._on_time_remaining)
        self._engine.target_window_info.connect(self._on_target_window)
        self._engine.error_occurred.connect(self._on_error)

    # ──────────────────────────────────────────────────────────────────
    # Hotkey registration
    # ──────────────────────────────────────────────────────────────────

    def _register_hotkeys(self):
        ok_start = self._hotkey_mgr.register(
            "start", self._settings.hotkey_start,
            self._trigger_arm, "Start typing"
        )
        ok_pause = self._hotkey_mgr.register(
            "pause", self._settings.hotkey_pause,
            self._trigger_pause, "Pause/Resume"
        )
        ok_stop = self._hotkey_mgr.register(
            "stop", self._settings.hotkey_stop,
            self._trigger_stop, "Emergency Stop"
        )
        ok_ai = self._hotkey_mgr.register(
            "ai_brain", self._settings.ai_brain_hotkey,
            self._trigger_ai_brain, "AI Brain"
        )
        if not (ok_start and ok_pause and ok_stop):
            logger.warning("One or more global hotkeys failed to register")
            self._status_bar.showMessage(
                "Warning: Global hotkeys could not be registered. "
                "Try running as Administrator.",
                8000
            )
        if not ok_ai:
            logger.warning("AI Brain hotkey failed to register")

    def _trigger_arm(self):
        """Called from hotkey thread — must post to GUI thread."""
        from PySide6.QtCore import QMetaObject, Qt
        QMetaObject.invokeMethod(self, "_on_arm", Qt.ConnectionType.QueuedConnection)

    def _trigger_pause(self):
        from PySide6.QtCore import QMetaObject, Qt
        QMetaObject.invokeMethod(self, "_on_pause_resume", Qt.ConnectionType.QueuedConnection)

    def _trigger_stop(self):
        from PySide6.QtCore import QMetaObject, Qt
        QMetaObject.invokeMethod(self, "_on_stop", Qt.ConnectionType.QueuedConnection)

    def _trigger_ai_brain(self):
        """Called from hotkey thread — posts AI Brain trigger to GUI thread."""
        from PySide6.QtCore import QMetaObject, Qt
        QMetaObject.invokeMethod(self, "_on_ai_brain", Qt.ConnectionType.QueuedConnection)

    # ──────────────────────────────────────────────────────────────────
    # AI Brain
    # ──────────────────────────────────────────────────────────────────

    @Slot()
    def _on_ai_brain(self):
        """Hotkey handler: capture screen + clipboard, query AI, auto-type result."""
        from core.ai_brain import AiBrainWorker

        # Guard: already running?
        if self._ai_worker is not None and self._ai_worker.isRunning():
            self._status_bar.showMessage("AI Brain is already running…", 3000)
            return

        # Guard: no API key configured
        if not self._settings.ai_api_key.strip():
            self._show_error(
                "AI Brain — API Key Missing",
                "Please open Settings → 🧠 AI Brain and enter your API key first."
            )
            return

        # Show overlay
        self._ai_overlay = AiOverlay()
        self._ai_overlay.show()

        # Build and start worker
        worker = AiBrainWorker(
            api_key=self._settings.ai_api_key,
            base_url=self._settings.ai_base_url,
            model=self._settings.ai_model,
            parent=self,
        )
        worker.status.connect(self._on_ai_status)
        worker.result.connect(self._on_ai_result)
        worker.error.connect(self._on_ai_error)
        worker.finished.connect(self._on_ai_finished)
        self._ai_worker = worker
        worker.start()
        logger.info("AI Brain worker started")

    @Slot(str)
    def _on_ai_status(self, msg: str):
        """Update overlay and status bar with progress message."""
        self._status_bar.showMessage(msg)
        if self._ai_overlay:
            self._ai_overlay.set_status(msg)

    @Slot(str)
    def _on_ai_result(self, text: str):
        """AI returned a result — put it in the text editor and auto-arm."""
        logger.info("AI Brain result received (%d chars)", len(text))
        # Switch to the Type tab
        self._tabs.setCurrentIndex(0)
        self._text_editor.setPlainText(text)
        # Auto-arm typing
        self._on_arm()

    @Slot(str)
    def _on_ai_error(self, msg: str):
        """AI request failed."""
        logger.error("AI Brain error: %s", msg)
        self._status_bar.showMessage(f"AI Brain error: {msg}", 8000)
        self._show_error("AI Brain Error", msg)

    @Slot()
    def _on_ai_finished(self):
        """Worker thread done — dismiss overlay."""
        if self._ai_overlay:
            self._ai_overlay.close()
            self._ai_overlay = None
        self._ai_worker = None

    # ──────────────────────────────────────────────────────────────────
    # User actions
    # ──────────────────────────────────────────────────────────────────

    @Slot()
    def _on_arm(self):
        """ARM TYPING button handler."""
        if self._engine.is_active():
            return

        # Validate
        text = self._get_active_text()
        if not text or not text.strip():
            self._show_error("No text to type", "Please enter some text before arming.")
            return

        wpm = self._wpm_spin.value()
        if wpm < 10 or wpm > 300:
            self._show_error("Invalid WPM", f"WPM must be between 10 and 300. Got: {wpm}")
            return

        if self._settings.require_confirm_start:
            reply = QMessageBox.question(
                self, "Confirm Start",
                f"Start typing {len(text)} characters at {wpm} WPM?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        # Build config
        modes = ["Standard", "Natural", "Custom"]
        mode_str = modes[self._mode_bg.checkedId()]
        mode_map = {
            "Standard": TypingMode.STANDARD,
            "Natural":  TypingMode.NATURAL,
            "Custom":   TypingMode.CUSTOM,
        }
        cfg = TimingConfig(
            wpm=wpm,
            mode=mode_map[mode_str],
            variation_pct=self._settings.variation_pct,
            comma_pause_mult=self._settings.comma_pause_mult,
            period_pause_mult=self._settings.period_pause_mult,
            paragraph_pause_mult=self._settings.paragraph_pause_mult,
        )

        self._engine.set_safety_enabled(self._stop_window_chk.isChecked())

        # Start
        ok = self._engine.start(
            text=text,
            timing_config=cfg,
            countdown_seconds=self._settings.countdown_seconds,
        )
        if not ok:
            return

        self._progress_panel.reset()
        self._progress_panel.setVisible(True)
        self._arm_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        logger.info("Typing armed")

    @Slot()
    def _on_pause_resume(self):
        if not self._engine.is_active():
            return
        self._engine.toggle_pause()

    @Slot()
    def _on_stop(self):
        """Emergency stop."""
        self._engine.stop()
        logger.info("STOP triggered by user")

    # ──────────────────────────────────────────────────────────────────
    # Engine signal handlers
    # ──────────────────────────────────────────────────────────────────

    @Slot(str)
    def _on_state_changed(self, state: str):
        self._current_state = state
        self._status_badge.set_state(state)
        self._status_bar.showMessage(f"Status: {state}")

        # Update controls
        is_typing = state == TypingState.TYPING.value
        is_paused = state == TypingState.PAUSED.value
        is_countdown = state == TypingState.COUNTDOWN.value
        is_active = state in (
            TypingState.TYPING.value,
            TypingState.PAUSED.value,
            TypingState.COUNTDOWN.value,
            TypingState.ARMED.value,
        )
        is_done = state in (
            TypingState.COMPLETED.value,
            TypingState.STOPPED.value,
            TypingState.ERROR.value,
        )

        self._arm_btn.setEnabled(not is_active)
        self._stop_btn.setEnabled(is_active)
        self._pause_btn.setVisible(is_typing or is_paused)
        self._pause_btn.setText("▶  RESUME" if is_paused else "⏸  PAUSE")

        self._countdown_widget.setVisible(is_countdown)
        if not is_countdown:
            self._countdown_widget.hide_countdown()

        if is_done:
            self._arm_btn.setEnabled(True)
            self._stop_btn.setEnabled(False)
            self._pause_btn.setVisible(False)
            if state == TypingState.COMPLETED.value:
                self._status_bar.showMessage("✓  Typing completed successfully!", 5000)

    @Slot(int, int)
    def _on_progress(self, done: int, total: int):
        self._progress_panel.update_progress(done, total)

    @Slot(int, int)
    def _on_words(self, done: int, total: int):
        self._progress_panel.update_words(done, total)

    @Slot(int)
    def _on_countdown(self, remaining: int):
        self._countdown_widget.show_countdown(remaining)

    @Slot(float)
    def _on_wpm_measured(self, wpm: float):
        self._progress_panel.update_wpm(wpm)

    @Slot(float)
    def _on_time_remaining(self, secs: float):
        self._progress_panel.update_time(secs)

    @Slot(str)
    def _on_target_window(self, title: str):
        self._countdown_widget.set_target(title)

    @Slot(str)
    def _on_error(self, msg: str):
        self._show_error("AutoKeyboard Pro — Error", msg)
        logger.error("Error: %s", msg)

    # ──────────────────────────────────────────────────────────────────
    # Speed controls
    # ──────────────────────────────────────────────────────────────────

    def _on_slider_changed(self, value: int):
        self._wpm_spin.blockSignals(True)
        self._wpm_spin.setValue(value)
        self._wpm_spin.blockSignals(False)
        self._refresh_stats()

    def _on_spin_changed(self, value: int):
        self._wpm_slider.blockSignals(True)
        self._wpm_slider.setValue(min(200, value))
        self._wpm_slider.blockSignals(False)
        self._refresh_stats()

    def _set_wpm(self, wpm: int):
        self._wpm_spin.setValue(wpm)

    # ──────────────────────────────────────────────────────────────────
    # Tab
    # ──────────────────────────────────────────────────────────────────

    def _on_tab_changed(self, index: int):
        self._is_test_mode = (index == 1)

    def _get_active_text(self) -> str:
        if self._is_test_mode:
            return self._test_source.toPlainText()
        return self._text_editor.toPlainText()

    # ──────────────────────────────────────────────────────────────────
    # Stats refresh
    # ──────────────────────────────────────────────────────────────────

    def _refresh_stats(self):
        text = self._get_active_text()
        stats = text_statistics(text)
        wpm = self._wpm_spin.value() if hasattr(self, "_wpm_spin") else 60
        duration = estimate_duration_seconds(text, wpm)

        if hasattr(self, "_stat_bar"):
            self._stat_bar.update_stats(
                stats["chars"], stats["words"], stats["lines"], duration
            )

    # ──────────────────────────────────────────────────────────────────
    # Settings
    # ──────────────────────────────────────────────────────────────────

    def _open_settings(self):
        dlg = SettingsDialog(self._settings, self._hotkey_mgr, self)
        dlg.settings_changed.connect(self._apply_settings)
        dlg.exec()

    @Slot(object)
    def _apply_settings(self, new_settings: AppSettings):
        self._settings = new_settings
        self._wpm_spin.setValue(new_settings.default_wpm)
        self._wpm_slider.setValue(min(200, new_settings.default_wpm))
        self._stop_window_chk.setChecked(new_settings.stop_on_window_change)

        # Re-register hotkeys
        self._hotkey_mgr.unregister_all()
        self._register_hotkeys()

        # Update hotkey labels in sidebar
        self._rebuild_hotkey_labels()

        # Apply theme
        from PySide6.QtWidgets import QApplication
        from ui.theme import ThemeManager
        ThemeManager().apply(QApplication.instance(), new_settings.theme)

        logger.info("Settings applied")

    def _rebuild_hotkey_labels(self):
        # Refresh sidebar hotkey display
        # Find and update the HotkeyLabel widgets inside the rows
        for row, combo_attr in [
            (self._hk_start_row, "hotkey_start"),
            (self._hk_pause_row, "hotkey_pause"),
            (self._hk_stop_row,  "hotkey_stop"),
        ]:
            combo = getattr(self._settings, combo_attr, "")
            for child in row.findChildren(HotkeyLabel):
                child.set_combo(combo)

    # ──────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────

    def _show_error(self, title: str, message: str):
        QMessageBox.critical(self, title, message)

    # ──────────────────────────────────────────────────────────────────
    # Cleanup
    # ──────────────────────────────────────────────────────────────────

    def closeEvent(self, event):
        self._engine.stop()
        self._hotkey_mgr.unregister_all()
        self._settings.save()
        logger.info("Application closing")
        event.accept()
