@echo off
REM Build script for RPA Engine Windows executable
REM Run this on a Windows machine with Python 3.12+ installed

echo ============================================================
echo RPA Engine - Windows Executable Builder
echo ============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.12+ from https://www.python.org/
    pause
    exit /b 1
)

echo Installing dependencies...
pip install -r requirements-api.txt
pip install pyinstaller

echo.
echo Building executable...
python build/build_exe.py --windowed

echo.
echo ============================================================
echo Build complete!
echo Output: dist\RPA-Engine.exe
echo ============================================================
pause
