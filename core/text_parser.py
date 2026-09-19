"""
AutoKeyboard Pro — Text Parser
Converts a string into a sequence of CharacterTokens for the typing engine.
Each token carries the character, its type, and any required modifier keys.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional


class TokenType(Enum):
    LETTER_LOWER = auto()   # a-z
    LETTER_UPPER = auto()   # A-Z (requires Shift)
    DIGIT = auto()          # 0-9
    SPACE = auto()          # ordinary space
    NEWLINE = auto()        # \n → press Enter
    TAB = auto()            # \t → press Tab
    BACKSPACE = auto()      # \b → press Backspace
    PUNCTUATION = auto()    # , . ; : ' " etc.
    SYMBOL = auto()         # ! @ # $ % ^ & * ( ) _ + - = [ ] { } | \ / < > ~ `
    SHIFT_COMBO = auto()    # characters that need Shift (!, @, #, etc.)
    UNICODE_FALLBACK = auto()  # chars that cannot be sent as direct key combos


# Characters that require Shift on a standard US keyboard
SHIFT_MAP: dict[str, str] = {
    '!': '1', '@': '2', '#': '3', '$': '4', '%': '5',
    '^': '6', '&': '7', '*': '8', '(': '9', ')': '0',
    '_': '-', '+': '=', '{': '[', '}': ']', '|': '\\',
    ':': ';', '"': "'", '<': ',', '>': '.', '?': '/',
    '~': '`',
}

# Characters directly available without Shift
DIRECT_CHARS = set(
    'abcdefghijklmnopqrstuvwxyz'
    '0123456789'
    '`-=[]\\;\',./~'
)

# Punctuation characters that cause context-aware pauses
PAUSE_LIGHT = {',', ';'}        # short extra pause
PAUSE_MEDIUM = {':', '!', '?'}  # medium extra pause
PAUSE_HEAVY = {'.', '!', '?'}   # heavy pause (sentence end — duplicated intentionally for weight)


@dataclass
class CharacterToken:
    char: str
    token_type: TokenType
    requires_shift: bool = False
    base_key: Optional[str] = None   # the key to press (without shift)
    pause_multiplier: float = 1.0    # extra timing weight
    is_fallback: bool = False        # True if unicode fallback is needed


def _classify(char: str) -> CharacterToken:
    """Classify a single character into a CharacterToken."""
    # Special control characters
    if char == '\n':
        return CharacterToken(char=char, token_type=TokenType.NEWLINE, pause_multiplier=2.0)
    if char == '\t':
        return CharacterToken(char=char, token_type=TokenType.TAB)
    if char == '\b':
        return CharacterToken(char=char, token_type=TokenType.BACKSPACE)
    if char == ' ':
        return CharacterToken(char=char, token_type=TokenType.SPACE)

    # Lowercase letters
    if char.islower() and char.isalpha() and char.isascii():
        return CharacterToken(char=char, token_type=TokenType.LETTER_LOWER,
                              base_key=char)

    # Uppercase letters
    if char.isupper() and char.isalpha() and char.isascii():
        return CharacterToken(char=char, token_type=TokenType.LETTER_UPPER,
                              requires_shift=True, base_key=char.lower())

    # Digits
    if char.isdigit() and char.isascii():
        return CharacterToken(char=char, token_type=TokenType.DIGIT, base_key=char)

    # Shift-required symbols (US keyboard)
    if char in SHIFT_MAP:
        pause_mult = 1.0
        if char in PAUSE_LIGHT:
            pause_mult = 1.2
        elif char in PAUSE_MEDIUM:
            pause_mult = 1.5
        elif char in PAUSE_HEAVY:
            pause_mult = 1.8
        return CharacterToken(
            char=char, token_type=TokenType.SHIFT_COMBO,
            requires_shift=True, base_key=SHIFT_MAP[char],
            pause_multiplier=pause_mult,
        )

    # Direct characters (no shift needed)
    if char in DIRECT_CHARS:
        pause_mult = 1.0
        if char in PAUSE_LIGHT:
            pause_mult = 1.2
        elif char in PAUSE_HEAVY:
            pause_mult = 1.8
        return CharacterToken(char=char, token_type=TokenType.PUNCTUATION,
                              base_key=char, pause_multiplier=pause_mult)

    # Everything else → unicode fallback
    return CharacterToken(
        char=char,
        token_type=TokenType.UNICODE_FALLBACK,
        is_fallback=True,
        pause_multiplier=1.0,
    )


def parse_text(text: str) -> List[CharacterToken]:
    """
    Parse input text into a list of CharacterTokens.
    Preserves all whitespace, newlines, and tabs exactly.
    Unicode characters that cannot be sent as key combos are marked as fallback.
    """
    tokens: List[CharacterToken] = []
    for char in text:
        tokens.append(_classify(char))
    return tokens


def text_statistics(text: str) -> dict:
    """Return character, word, and line counts plus estimated duration at a given WPM."""
    char_count = len(text)
    word_count = len(text.split()) if text.strip() else 0
    line_count = text.count('\n') + 1 if text else 0
    return {
        'chars': char_count,
        'words': word_count,
        'lines': line_count,
    }


def estimate_duration_seconds(text: str, wpm: int) -> float:
    """Estimate typing duration in seconds using 1 word = 5 characters."""
    if wpm <= 0 or not text:
        return 0.0
    chars = len(text)
    chars_per_minute = wpm * 5
    return (chars / chars_per_minute) * 60.0
