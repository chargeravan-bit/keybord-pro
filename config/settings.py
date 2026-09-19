"""
AutoKeyboard Pro — Application Settings
Persisted to %APPDATA%/AutoKeyboardPro/settings.json
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

APP_NAME = "AutoKeyboardPro"


def get_app_data_dir() -> Path:
    """Return the application's AppData directory, creating it if needed."""
    base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    app_dir = base / APP_NAME
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


@dataclass
class AppSettings:
    # Typing
    default_wpm: int = 60
    typing_mode: str = "Natural"      # Standard | Natural | Custom
    variation_pct: float = 0.25
    comma_pause_mult: float = 1.2
    period_pause_mult: float = 1.8
    paragraph_pause_mult: float = 2.5
    countdown_seconds: int = 5

    # Safety
    stop_on_window_change: bool = True
    require_confirm_start: bool = False
    emergency_stop_enabled: bool = True

    # Hotkeys
    hotkey_start: str = "ctrl+shift+alt+t"
    hotkey_pause: str = "ctrl+shift+alt+p"
    hotkey_stop:  str = "ctrl+shift+alt+x"

    # Appearance
    theme: str = "Dark"               # Dark | Light | System

    # AI Brain
    ai_provider: str = "OpenRouter"    # OpenRouter | OpenAI | Gemini | Custom
    ai_api_key: str = ""
    ai_base_url: str = "https://openrouter.ai/api/v1"  # custom endpoint base URL
    ai_model: str = "google/gemma-4-31b-it:free"     # any model slug
    ai_brain_hotkey: str = "ctrl+shift+alt+b"

    # Permission
    permission_granted: bool = False

    # Log path (not user-configurable via UI)
    log_file: str = ""

    def __post_init__(self):
        if not self.log_file:
            self.log_file = str(get_app_data_dir() / "app.log")

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @classmethod
    def load(cls) -> "AppSettings":
        path = get_app_data_dir() / "settings.json"
        if path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                inst = cls()
                for key, val in data.items():
                    if hasattr(inst, key):
                        setattr(inst, key, val)
                logger.info("Settings loaded from %s", path)
                return inst
            except Exception as exc:
                logger.warning("Failed to load settings, using defaults: %s", exc)
        return cls()

    def save(self) -> None:
        path = get_app_data_dir() / "settings.json"
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, indent=2)
            logger.info("Settings saved")
        except Exception as exc:
            logger.error("Failed to save settings: %s", exc)

    def to_timing_config(self):
        """Convert to a TimingConfig for the timing engine."""
        from core.timing_engine import TimingConfig, TypingMode
        mode_map = {
            "Standard": TypingMode.STANDARD,
            "Natural":  TypingMode.NATURAL,
            "Custom":   TypingMode.CUSTOM,
        }
        return TimingConfig(
            wpm=self.default_wpm,
            mode=mode_map.get(self.typing_mode, TypingMode.NATURAL),
            variation_pct=self.variation_pct,
            comma_pause_mult=self.comma_pause_mult,
            period_pause_mult=self.period_pause_mult,
            paragraph_pause_mult=self.paragraph_pause_mult,
        )
