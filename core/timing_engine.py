"""
AutoKeyboard Pro — Timing Engine
Computes per-character delays based on WPM, typing mode, and context.

Timing formula:
    1 word = 5 characters
    chars_per_minute = WPM × 5
    base_delay = 60 / chars_per_minute   (seconds per character)

Modes:
    Standard  — fixed base_delay for every character
    Natural   — bounded random variation around base_delay
    Custom    — user-configured variation percentage
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

from core.text_parser import CharacterToken, TokenType


class TypingMode(Enum):
    STANDARD = "Standard"
    NATURAL = "Natural"
    CUSTOM = "Custom"


# Minimum and maximum bounds to prevent unsafe delay values
MIN_DELAY_SECONDS = 0.010   # 10 ms — fast but not instant
MAX_DELAY_SECONDS = 5.000   # 5 s — catches ridiculous low WPM


@dataclass
class TimingConfig:
    wpm: int = 60
    mode: TypingMode = TypingMode.NATURAL
    # Variation as a fraction of base_delay (e.g. 0.25 = ±25%)
    variation_pct: float = 0.25
    # Extra multiplier for specific punctuation classes (on top of token's own multiplier)
    comma_pause_mult: float = 1.2
    period_pause_mult: float = 1.8
    paragraph_pause_mult: float = 2.5
    # Seed for reproducible tests; None = random
    seed: Optional[int] = None

    def __post_init__(self):
        if self.wpm < 1:
            self.wpm = 1
        if self.wpm > 2000:
            self.wpm = 2000
        self.variation_pct = max(0.0, min(1.0, self.variation_pct))


class TimingEngine:
    """
    Computes per-character delay in seconds.
    Use a fixed seed for deterministic behaviour in tests.
    """

    def __init__(self, config: TimingConfig):
        self.config = config
        self._rng = random.Random(config.seed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_delay(self, token: CharacterToken) -> float:
        """Return the delay (in seconds) to wait AFTER sending this character."""
        base = self._base_delay()
        delay = self._apply_mode(base)
        delay = self._apply_context(delay, token)
        delay = max(MIN_DELAY_SECONDS, min(MAX_DELAY_SECONDS, delay))
        return delay

    def get_base_delay(self) -> float:
        """Return the raw base delay in seconds (no variation applied)."""
        return self._base_delay()

    def update_config(self, config: TimingConfig) -> None:
        self.config = config
        self._rng = random.Random(config.seed)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _base_delay(self) -> float:
        """Base seconds-per-character from WPM."""
        chars_per_minute = self.config.wpm * 5
        return 60.0 / chars_per_minute

    def _apply_mode(self, base: float) -> float:
        """Apply timing mode variation."""
        mode = self.config.mode
        if mode == TypingMode.STANDARD:
            return base

        var = self.config.variation_pct
        if mode in (TypingMode.NATURAL, TypingMode.CUSTOM):
            # Bounded variation: multiply base by a factor in [1-var, 1+var]
            # Use a slightly skewed beta-like distribution for realism:
            # Gaussian clamped to [1-var, 1+var]
            factor = self._rng.gauss(1.0, var / 3.0)
            factor = max(1.0 - var, min(1.0 + var, factor))
            return base * factor

        return base

    def _apply_context(self, delay: float, token: CharacterToken) -> float:
        """Apply context-aware extra pause based on character type."""
        tt = token.token_type
        cfg = self.config

        if tt == TokenType.NEWLINE:
            return delay * cfg.paragraph_pause_mult
        if tt == TokenType.SPACE:
            return delay  # spaces use base delay

        # Apply the token's own pause_multiplier (set by text_parser)
        delay *= token.pause_multiplier

        return delay


# ------------------------------------------------------------------
# Convenience factory
# ------------------------------------------------------------------

def make_timing_engine(
    wpm: int = 60,
    mode: TypingMode = TypingMode.NATURAL,
    variation_pct: float = 0.25,
    seed: Optional[int] = None,
) -> TimingEngine:
    cfg = TimingConfig(wpm=wpm, mode=mode, variation_pct=variation_pct, seed=seed)
    return TimingEngine(cfg)
