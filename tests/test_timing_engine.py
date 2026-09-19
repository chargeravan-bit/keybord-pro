"""
Tests for TimingEngine.
Uses a fixed seed for deterministic results.
"""

import pytest
from core.timing_engine import TimingEngine, TimingConfig, TypingMode
from core.text_parser import parse_text, CharacterToken, TokenType


def make_engine(wpm=60, mode=TypingMode.NATURAL, variation=0.25, seed=42):
    cfg = TimingConfig(wpm=wpm, mode=mode, variation_pct=variation, seed=seed)
    return TimingEngine(cfg)


class TestBaseDelay:
    def test_60_wpm_base(self):
        engine = make_engine(60, TypingMode.STANDARD)
        # 60 WPM × 5 chars = 300 CPM → 60/300 = 0.2s
        assert abs(engine.get_base_delay() - 0.2) < 1e-9

    def test_120_wpm_base(self):
        engine = make_engine(120, TypingMode.STANDARD)
        # 120 × 5 = 600 → 60/600 = 0.1s
        assert abs(engine.get_base_delay() - 0.1) < 1e-9

    def test_10_wpm_base(self):
        engine = make_engine(10, TypingMode.STANDARD)
        # 10 × 5 = 50 → 60/50 = 1.2s
        assert abs(engine.get_base_delay() - 1.2) < 1e-9

    def test_200_wpm_base(self):
        engine = make_engine(200, TypingMode.STANDARD)
        # 200 × 5 = 1000 → 60/1000 = 0.06s
        assert abs(engine.get_base_delay() - 0.06) < 1e-9


class TestStandardMode:
    def test_all_delays_equal(self):
        engine = make_engine(60, TypingMode.STANDARD)
        tokens = parse_text("hello world")
        delays = [engine.get_delay(t) for t in tokens]
        # In standard mode with no context variation, non-punctuation delays should be equal
        base = engine.get_base_delay()
        for t, d in zip(tokens, delays):
            if t.token_type == TokenType.SPACE:
                assert abs(d - base) < 1e-9, f"Space delay mismatch: {d}"


class TestNaturalMode:
    def test_delays_vary(self):
        engine = make_engine(60, TypingMode.NATURAL, variation=0.25, seed=1)
        tokens = parse_text("hello")
        delays = [engine.get_delay(t) for t in tokens]
        # There should be variation
        assert len(set(round(d, 6) for d in delays)) > 1

    def test_delays_within_bounds(self):
        engine = make_engine(60, TypingMode.NATURAL, variation=0.25, seed=99)
        tokens = parse_text("The quick brown fox jumps over the lazy dog. Hello!")
        base = engine.get_base_delay()
        for token in tokens:
            delay = engine.get_delay(token)
            # Delay must be within reasonable bounds
            assert delay >= 0.010, f"Delay too short: {delay}"
            assert delay <= 5.0,   f"Delay too long: {delay}"

    def test_seed_reproducible(self):
        tokens = parse_text("hello world")
        e1 = make_engine(60, TypingMode.NATURAL, seed=42)
        e2 = make_engine(60, TypingMode.NATURAL, seed=42)
        d1 = [e1.get_delay(t) for t in tokens]
        d2 = [e2.get_delay(t) for t in tokens]
        assert d1 == d2


class TestContextPauses:
    def test_newline_longer(self):
        engine = make_engine(60, TypingMode.STANDARD)
        tokens = parse_text("a\n")
        letter_delay = engine.get_delay(tokens[0])
        newline_delay = engine.get_delay(tokens[1])
        assert newline_delay > letter_delay

    def test_period_longer_than_letter(self):
        engine = make_engine(60, TypingMode.STANDARD)
        tokens_letter = parse_text("a")
        tokens_period = parse_text(".")
        letter_delay = engine.get_delay(tokens_letter[0])
        period_delay  = engine.get_delay(tokens_period[0])
        assert period_delay >= letter_delay


class TestEdgeCases:
    def test_wpm_clamped_low(self):
        cfg = TimingConfig(wpm=0)
        assert cfg.wpm == 1

    def test_wpm_clamped_high(self):
        cfg = TimingConfig(wpm=9999)
        assert cfg.wpm == 2000

    def test_variation_clamped(self):
        cfg = TimingConfig(variation_pct=5.0)
        assert cfg.variation_pct == 1.0
        cfg2 = TimingConfig(variation_pct=-1.0)
        assert cfg2.variation_pct == 0.0
