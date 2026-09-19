"""
AutoKeyboard Pro — Theme Manager
Provides Windows 11-inspired dark and light QSS stylesheets.
Uses the Inter font from Google Fonts (bundled as a web import fallback to Segoe UI).
"""

from __future__ import annotations

DARK_PALETTE = {
    "bg_primary":     "#0f0f10",
    "bg_secondary":   "#1a1a1f",
    "bg_card":        "#1e1e26",
    "bg_input":       "#16161c",
    "bg_hover":       "#2a2a35",
    "bg_active":      "#252530",
    "accent":         "#7c6fcd",
    "accent_hover":   "#9283e0",
    "accent_light":   "#a89ae8",
    "danger":         "#e05252",
    "danger_hover":   "#f06060",
    "success":        "#52c97c",
    "warning":        "#e0a040",
    "text_primary":   "#e8e8f0",
    "text_secondary": "#9090a8",
    "text_muted":     "#5c5c70",
    "border":         "#2e2e3e",
    "border_focus":   "#7c6fcd",
    "scrollbar":      "#3a3a4a",
    "scrollbar_hover":"#5a5a6a",
}

LIGHT_PALETTE = {
    "bg_primary":     "#f4f4f8",
    "bg_secondary":   "#ffffff",
    "bg_card":        "#ffffff",
    "bg_input":       "#f0f0f5",
    "bg_hover":       "#e8e8f2",
    "bg_active":      "#e0e0ee",
    "accent":         "#5b50b8",
    "accent_hover":   "#6d60cc",
    "accent_light":   "#8074d8",
    "danger":         "#cc3333",
    "danger_hover":   "#dd4444",
    "success":        "#2d9a5a",
    "warning":        "#b87010",
    "text_primary":   "#1a1a2e",
    "text_secondary": "#505068",
    "text_muted":     "#8888a0",
    "border":         "#d4d4e4",
    "border_focus":   "#5b50b8",
    "scrollbar":      "#c8c8d8",
    "scrollbar_hover":"#a0a0b8",
}


def _build_stylesheet(p: dict) -> str:
    return f"""
/* ──────────────────────────────────────────────────────────── */
/* AutoKeyboard Pro QSS — Windows 11 inspired                  */
/* ──────────────────────────────────────────────────────────── */

QWidget {{
    background-color: {p['bg_primary']};
    color: {p['text_primary']};
    font-family: "Segoe UI", "Inter", "Arial", sans-serif;
    font-size: 13px;
    border: none;
    outline: none;
}}

QMainWindow {{
    background-color: {p['bg_primary']};
}}

/* ── Cards / Panels ───────────────────────────────────────── */
QFrame#card {{
    background-color: {p['bg_card']};
    border: 1px solid {p['border']};
    border-radius: 12px;
}}

QFrame#sidebar {{
    background-color: {p['bg_secondary']};
    border-right: 1px solid {p['border']};
}}

/* ── Text Editor ──────────────────────────────────────────── */
QPlainTextEdit, QTextEdit {{
    background-color: {p['bg_input']};
    color: {p['text_primary']};
    border: 1.5px solid {p['border']};
    border-radius: 10px;
    padding: 12px;
    font-size: 14px;
    selection-background-color: {p['accent']};
    selection-color: #ffffff;
}}
QPlainTextEdit:focus, QTextEdit:focus {{
    border-color: {p['border_focus']};
}}

/* ── Labels ───────────────────────────────────────────────── */
QLabel {{
    background: transparent;
    color: {p['text_primary']};
}}
QLabel#heading {{
    font-size: 20px;
    font-weight: 700;
    color: {p['text_primary']};
}}
QLabel#subheading {{
    font-size: 12px;
    color: {p['text_secondary']};
    font-weight: 400;
}}
QLabel#section_label {{
    font-size: 11px;
    font-weight: 700;
    color: {p['text_muted']};
    letter-spacing: 1.2px;
}}
QLabel#muted {{
    color: {p['text_muted']};
    font-size: 12px;
}}
QLabel#stat_value {{
    color: {p['accent_light']};
    font-size: 13px;
    font-weight: 600;
}}

/* ── Buttons ──────────────────────────────────────────────── */
QPushButton {{
    background-color: {p['bg_hover']};
    color: {p['text_primary']};
    border: 1.5px solid {p['border']};
    border-radius: 8px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: {p['bg_active']};
    border-color: {p['accent']};
}}
QPushButton:pressed {{
    background-color: {p['accent']};
    color: #ffffff;
    border-color: {p['accent']};
}}
QPushButton:disabled {{
    color: {p['text_muted']};
    border-color: {p['border']};
    background-color: {p['bg_secondary']};
}}

/* Accent / Primary button */
QPushButton#btn_arm {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {p['accent']}, stop:1 {p['accent_hover']});
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 12px 32px;
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 0.5px;
}}
QPushButton#btn_arm:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {p['accent_hover']}, stop:1 {p['accent_light']});
}}
QPushButton#btn_arm:disabled {{
    background: {p['bg_hover']};
    color: {p['text_muted']};
}}

/* Danger / Stop button */
QPushButton#btn_stop {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {p['danger']}, stop:1 #cc2020);
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 12px 32px;
    font-size: 15px;
    font-weight: 700;
}}
QPushButton#btn_stop:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {p['danger_hover']}, stop:1 {p['danger']});
}}

/* Icon button (settings gear) */
QPushButton#btn_icon {{
    background: transparent;
    border: none;
    padding: 6px;
    border-radius: 6px;
    font-size: 18px;
}}
QPushButton#btn_icon:hover {{
    background-color: {p['bg_hover']};
}}

/* Small secondary buttons */
QPushButton#btn_secondary {{
    background-color: transparent;
    color: {p['accent_light']};
    border: 1.5px solid {p['accent']};
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
}}
QPushButton#btn_secondary:hover {{
    background-color: {p['accent']};
    color: #ffffff;
}}

/* ── Slider ───────────────────────────────────────────────── */
QSlider::groove:horizontal {{
    height: 4px;
    background: {p['border']};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    width: 18px;
    height: 18px;
    background: {p['accent']};
    border-radius: 9px;
    margin: -7px 0;
    border: 2px solid {p['bg_primary']};
}}
QSlider::handle:horizontal:hover {{
    background: {p['accent_hover']};
}}
QSlider::sub-page:horizontal {{
    background: {p['accent']};
    border-radius: 2px;
}}

/* ── SpinBox ──────────────────────────────────────────────── */
QSpinBox, QDoubleSpinBox {{
    background-color: {p['bg_input']};
    color: {p['text_primary']};
    border: 1.5px solid {p['border']};
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 13px;
    selection-background-color: {p['accent']};
}}
QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {p['border_focus']};
}}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    background: {p['bg_hover']};
    border: none;
    border-radius: 4px;
    width: 16px;
}}

/* ── ComboBox ─────────────────────────────────────────────── */
QComboBox {{
    background-color: {p['bg_input']};
    color: {p['text_primary']};
    border: 1.5px solid {p['border']};
    border-radius: 8px;
    padding: 7px 12px;
    font-size: 13px;
}}
QComboBox:focus {{
    border-color: {p['border_focus']};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background-color: {p['bg_card']};
    color: {p['text_primary']};
    border: 1px solid {p['border']};
    border-radius: 8px;
    selection-background-color: {p['accent']};
    outline: none;
}}

/* ── Radio / CheckBox ─────────────────────────────────────── */
QRadioButton, QCheckBox {{
    color: {p['text_primary']};
    font-size: 13px;
    spacing: 8px;
    background: transparent;
}}
QRadioButton::indicator, QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 8px;
    border: 1.5px solid {p['border']};
    background: {p['bg_input']};
}}
QCheckBox::indicator {{
    border-radius: 4px;
}}
QRadioButton::indicator:checked, QCheckBox::indicator:checked {{
    background: {p['accent']};
    border-color: {p['accent']};
}}

/* ── Progress Bar ─────────────────────────────────────────── */
QProgressBar {{
    background-color: {p['bg_input']};
    border: none;
    border-radius: 6px;
    height: 10px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {p['accent']}, stop:1 {p['accent_hover']});
    border-radius: 6px;
}}

/* ── Tab Widget ───────────────────────────────────────────── */
QTabWidget::pane {{
    background: {p['bg_card']};
    border: 1px solid {p['border']};
    border-radius: 10px;
    top: -1px;
}}
QTabBar::tab {{
    background: {p['bg_secondary']};
    color: {p['text_secondary']};
    padding: 8px 20px;
    border-bottom: 2px solid transparent;
    font-size: 13px;
    font-weight: 500;
}}
QTabBar::tab:selected {{
    color: {p['accent_light']};
    border-bottom-color: {p['accent']};
    background: {p['bg_card']};
}}
QTabBar::tab:hover {{
    color: {p['text_primary']};
}}

/* ── ScrollBar ────────────────────────────────────────────── */
QScrollBar:vertical {{
    background: {p['bg_secondary']};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {p['scrollbar']};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {p['scrollbar_hover']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: {p['bg_secondary']};
    height: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {p['scrollbar']};
    border-radius: 4px;
}}

/* ── Tooltip ──────────────────────────────────────────────── */
QToolTip {{
    background-color: {p['bg_card']};
    color: {p['text_primary']};
    border: 1px solid {p['border']};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}}

/* ── Separator ────────────────────────────────────────────── */
QFrame[frameShape="4"], QFrame[frameShape="5"] {{
    color: {p['border']};
    background: {p['border']};
    max-height: 1px;
    border: none;
}}

/* ── Dialog ───────────────────────────────────────────────── */
QDialog {{
    background-color: {p['bg_primary']};
}}

/* ── LineEdit ─────────────────────────────────────────────── */
QLineEdit {{
    background-color: {p['bg_input']};
    color: {p['text_primary']};
    border: 1.5px solid {p['border']};
    border-radius: 8px;
    padding: 7px 12px;
    font-size: 13px;
    selection-background-color: {p['accent']};
}}
QLineEdit:focus {{
    border-color: {p['border_focus']};
}}

/* ── GroupBox ─────────────────────────────────────────────── */
QGroupBox {{
    border: 1.5px solid {p['border']};
    border-radius: 10px;
    margin-top: 16px;
    padding: 12px;
    font-weight: 600;
    color: {p['text_secondary']};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: {p['text_secondary']};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
}}
"""


class ThemeManager:
    """Manages QSS theme application."""

    def __init__(self):
        self._current = "Dark"

    def apply(self, app, theme: str = "Dark") -> None:
        """Apply a theme to the QApplication."""
        self._current = theme
        palette = DARK_PALETTE if theme != "Light" else LIGHT_PALETTE
        app.setStyleSheet(_build_stylesheet(palette))

    def get_color(self, key: str, theme: str = "") -> str:
        t = theme or self._current
        palette = DARK_PALETTE if t != "Light" else LIGHT_PALETTE
        return palette.get(key, "#ffffff")

    @property
    def current(self) -> str:
        return self._current
