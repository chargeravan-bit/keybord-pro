# AutoKeyboard Pro

> **Human-like keyboard automation for Windows**

AutoKeyboard Pro simulates realistic keyboard input in any Windows application — character by character, exactly as if typed on a physical keyboard — with configurable typing speed and natural-style timing variation.

---

## What It Does

- **Types text character-by-character** using Windows keyboard input events (not clipboard paste)
- **Configurable WPM** (10–300) with presets and a slider
- **Three timing modes**: Standard (consistent), Natural (natural-style variation), Custom
- **Global hotkeys** that work while another app is focused
- **Emergency STOP** (large button + hotkey) that halts all typing immediately
- **Window-change guard**: automatically stops if you switch to a different application
- **Pause / Resume** from the exact character position where you stopped
- **Progress tracking**: chars, words, WPM, time remaining
- **Test Mode**: type safely into an internal text box before targeting external apps
- **Dark / Light / System theme**
- Settings persisted to `%APPDATA%\AutoKeyboardPro\settings.json`

---

## Privacy & Safety

AutoKeyboard Pro does **NOT**:
- Record your keystrokes
- Capture passwords or credentials
- Monitor clipboard contents
- Upload any data
- Run hidden in the background

It **only** generates keyboard output when you explicitly arm and activate it.

---

## Requirements

- Windows 10 / 11
- Python 3.12 or later
- (Administrator rights may be needed for global hotkeys on some systems)

---

## Running in Development

### 1. Install dependencies

```bat
pip install -r requirements.txt
```

### 2. Run the application

```bat
python main.py
```

The app opens with a permission dialog on first launch. Accept to enable keyboard input generation.

---

## Default Global Hotkeys

| Action | Default Hotkey |
|--------|----------------|
| Start Typing | `Ctrl + Shift + Alt + T` |
| Pause / Resume | `Ctrl + Shift + Alt + P` |
| Emergency Stop | `Ctrl + Shift + Alt + X` |

These can be changed in **Settings → Hotkeys**.

---

## Workflow

1. **Enter/paste text** in the editor
2. **Choose WPM** using the slider or presets
3. **Choose mode**: Standard / Natural / Custom
4. Click **▶ ARM TYPING**
5. You have **5 seconds** to click the target application/text field
6. AutoKeyboard Pro begins typing — character by character
7. Use `Pause`, `Resume`, or `Stop Now` at any time

---

## Running Tests

```bat
pytest tests/ -v
```

Tests cover:
- WPM calculations
- Timing generation and bounds
- Text parsing and classification
- Punctuation and newline handling
- Pause/resume state machine
- Stop behaviour
- Hotkey conflict detection
- Window-change safety guard
- Empty text and edge cases

---

## Building the Executable

### Quick build

```bat
build.bat
```

This installs dependencies, runs tests, and produces:

```
dist\AutoKeyboardPro\AutoKeyboardPro.exe
```

### Manual build

```bat
pip install -r requirements.txt
pyinstaller AutoKeyboardPro.spec --noconfirm
```

The `.exe` is a standalone Windows executable. Distribute the entire `dist\AutoKeyboardPro\` folder.

---

## Administrator Note

The `keyboard` library (used for global hotkeys) may require Administrator privileges on Windows 11 to register hotkeys that fire while other applications are focused.

If hotkeys don't work:
1. Right-click `AutoKeyboardPro.exe` → **Run as administrator**
2. Or use the on-screen ARM TYPING button instead of hotkeys

The typing functionality itself (via pynput's `SendInput`) does not require Administrator.

---

## Project Structure

```
AutoKeyboardPro/
├── main.py                    ← Entry point
├── requirements.txt
├── build.bat                  ← Build script
├── AutoKeyboardPro.spec       ← PyInstaller configuration
│
├── core/
│   ├── text_parser.py         ← Converts text to CharacterTokens
│   ├── timing_engine.py       ← Computes per-character delays
│   ├── keyboard_controller.py ← Sends Win32 key events via pynput
│   ├── typing_engine.py       ← QThread worker + state machine
│   ├── hotkeys.py             ← Global hotkey manager
│   └── safety.py              ← Window focus guard + permission state
│
├── config/
│   └── settings.py            ← AppSettings (persisted JSON)
│
├── ui/
│   ├── main_window.py         ← Main dashboard
│   ├── settings_dialog.py     ← Settings tabs
│   ├── permission_dialog.py   ← First-launch consent
│   ├── widgets.py             ← Reusable components
│   └── theme.py               ← QSS dark/light stylesheets
│
├── assets/                    ← Icons and resources
└── tests/                     ← Automated tests
    ├── test_text_parser.py
    ├── test_timing_engine.py
    ├── test_typing_engine.py
    ├── test_hotkeys.py
    └── test_safety.py
```

---

## Timing Model

```
WPM (words per minute)
    1 word = 5 characters
    chars_per_minute = WPM × 5
    base_delay = 60 / chars_per_minute   (seconds between key presses)

Natural mode applies bounded Gaussian variation:
    factor ∈ [1 − variation%, 1 + variation%]
    delay = base_delay × factor × context_multiplier

Context multipliers (approximate, configurable):
    Space      → ×1.0
    Comma      → ×1.2
    Period/!/? → ×1.8
    Newline    → ×2.5
```

---

## License

MIT License. For personal and professional use.

---

*AutoKeyboard Pro v1.0.0 — Natural-style typing simulation for Windows*
