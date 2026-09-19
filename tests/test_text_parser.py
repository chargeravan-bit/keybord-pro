"""
Tests for TextParser.
"""

import pytest
from core.text_parser import (
    parse_text, text_statistics, estimate_duration_seconds,
    CharacterToken, TokenType
)


class TestBasicParsing:
    def test_lowercase(self):
        tokens = parse_text("abc")
        assert len(tokens) == 3
        for t in tokens:
            assert t.token_type == TokenType.LETTER_LOWER
            assert not t.requires_shift

    def test_uppercase(self):
        tokens = parse_text("ABC")
        for t in tokens:
            assert t.token_type == TokenType.LETTER_UPPER
            assert t.requires_shift

    def test_digits(self):
        tokens = parse_text("012")
        for t in tokens:
            assert t.token_type == TokenType.DIGIT

    def test_space(self):
        tokens = parse_text(" ")
        assert tokens[0].token_type == TokenType.SPACE

    def test_newline(self):
        tokens = parse_text("\n")
        assert tokens[0].token_type == TokenType.NEWLINE

    def test_tab(self):
        tokens = parse_text("\t")
        assert tokens[0].token_type == TokenType.TAB


class TestShiftCombos:
    def test_exclamation(self):
        tokens = parse_text("!")
        assert tokens[0].token_type == TokenType.SHIFT_COMBO
        assert tokens[0].requires_shift
        assert tokens[0].base_key == "1"

    def test_at_sign(self):
        tokens = parse_text("@")
        assert tokens[0].requires_shift
        assert tokens[0].base_key == "2"

    def test_question_mark(self):
        tokens = parse_text("?")
        assert tokens[0].requires_shift
        assert tokens[0].base_key == "/"


class TestPunctuationPauses:
    def test_comma_pause(self):
        tokens = parse_text(",")
        assert tokens[0].pause_multiplier > 1.0

    def test_period_pause(self):
        tokens = parse_text(".")
        assert tokens[0].pause_multiplier > 1.0

    def test_letter_no_extra_pause(self):
        tokens = parse_text("a")
        assert tokens[0].pause_multiplier == 1.0

    def test_newline_pause(self):
        tokens = parse_text("\n")
        assert tokens[0].pause_multiplier >= 2.0


class TestPreservation:
    def test_multiple_spaces(self):
        text = "hello   world"
        tokens = parse_text(text)
        # 3 spaces should be 3 SPACE tokens
        spaces = [t for t in tokens if t.token_type == TokenType.SPACE]
        assert len(spaces) == 3

    def test_multiple_newlines(self):
        text = "a\n\nb"
        tokens = parse_text(text)
        newlines = [t for t in tokens if t.token_type == TokenType.NEWLINE]
        assert len(newlines) == 2

    def test_mixed_case(self):
        tokens = parse_text("Hello World")
        assert tokens[0].token_type == TokenType.LETTER_UPPER
        assert tokens[1].token_type == TokenType.LETTER_LOWER


class TestUnicodeFallback:
    def test_emoji_fallback(self):
        tokens = parse_text("😊")
        assert tokens[0].token_type == TokenType.UNICODE_FALLBACK
        assert tokens[0].is_fallback

    def test_cjk_fallback(self):
        tokens = parse_text("中")
        assert tokens[0].token_type == TokenType.UNICODE_FALLBACK


class TestEmptyInput:
    def test_empty_string(self):
        tokens = parse_text("")
        assert tokens == []

    def test_whitespace_only(self):
        tokens = parse_text("   ")
        assert all(t.token_type == TokenType.SPACE for t in tokens)


class TestStatistics:
    def test_word_count(self):
        stats = text_statistics("hello world foo")
        assert stats["words"] == 3

    def test_char_count(self):
        stats = text_statistics("abc")
        assert stats["chars"] == 3

    def test_line_count(self):
        stats = text_statistics("line1\nline2\nline3")
        assert stats["lines"] == 3

    def test_empty(self):
        stats = text_statistics("")
        assert stats["chars"] == 0
        assert stats["words"] == 0


class TestDurationEstimate:
    def test_basic(self):
        # 300 chars at 60 WPM: 300/300 * 60 = 60 seconds
        text = "a" * 300
        dur = estimate_duration_seconds(text, 60)
        assert abs(dur - 60.0) < 0.01

    def test_zero_wpm(self):
        assert estimate_duration_seconds("hello", 0) == 0.0

    def test_empty_text(self):
        assert estimate_duration_seconds("", 60) == 0.0
