@echo off
title JobAgent AI
color 0B
echo.
echo  =============================================
echo   JobAgent AI - Starting...
echo  =============================================
echo.

:: Activate virtual environment
if not exist ".venv" (
    echo [!] Virtual environment not found. Running setup first...
    call setup.bat
)

call .venv\Scripts\activate.bat

:: Check .env exists
if not exist ".env" (
    copy .env.example .env
    echo [!] Please add your Gemini API key to .env
    notepad .env
)

:: Start the server
echo [*] Starting JobAgent AI server...
echo [*] Opening browser in 3 seconds...

:: Open browser after 3 seconds
start /min cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8000"

:: Run FastAPI
cd backend
python main.py

pause
