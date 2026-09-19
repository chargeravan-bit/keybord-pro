@echo off
REM ─────────────────────────────────────────────────────────────────────────────
REM AutoKeyboard Pro — Build Script
REM Produces dist\AutoKeyboardPro\AutoKeyboardPro.exe (one-dir bundle)
REM Run from the project root directory.
REM ─────────────────────────────────────────────────────────────────────────────

echo.
echo ===============================
echo  AutoKeyboard Pro — Build
echo ===============================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH.
    echo Please install Python 3.12+ and add it to PATH.
    pause
    exit /b 1
)

REM Check pip
pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip not found.
    pause
    exit /b 1
)

echo [1/4] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo [2/4] Running tests...
pytest tests/ -v --tb=short
if errorlevel 1 (
    echo [WARNING] Some tests failed. Continuing build...
)

echo.
echo [3/4] Building executable...
pyinstaller AutoKeyboardPro.spec --noconfirm
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed.
    pause
    exit /b 1
)

echo.
echo [4/4] Build complete!
echo.
echo Executable:  dist\AutoKeyboardPro\AutoKeyboardPro.exe
echo.
echo You can also run the app directly:
echo   python main.py
echo.
pause
