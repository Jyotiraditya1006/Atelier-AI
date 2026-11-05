@echo off
title JobAgent AI - Setup
color 0B
echo.
echo  ============================================
echo   JobAgent AI - First Time Setup
echo  ============================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.11+ from https://python.org
    pause
    exit /b 1
)
echo [OK] Python found

:: Create virtual environment
if not exist ".venv" (
    echo [*] Creating virtual environment...
    python -m venv .venv
    echo [OK] Virtual environment created
) else (
    echo [OK] Virtual environment already exists
)

:: Activate and install packages
echo [*] Installing dependencies (this may take a few minutes)...
call .venv\Scripts\activate.bat
pip install -r requirements.txt --quiet

:: Install Playwright browsers
echo [*] Installing browser automation (Playwright)...
playwright install chromium --quiet

:: Setup .env
if not exist ".env" (
    echo [*] Creating .env from template...
    copy .env.example .env
    echo.
    echo [!] IMPORTANT: Open .env and add your Gemini API key!
    echo     Get one free at: https://aistudio.google.com/apikey
    echo.
    notepad .env
)

echo.
echo  ============================================
echo   Setup Complete! Run start.bat to launch
echo  ============================================
pause
