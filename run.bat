@echo off
echo ============================================================
echo   AI Capstone System - Launcher
echo ============================================================
echo.
echo   [1] Run Demo Script        (no hardware required)
echo   [2] Launch CLI             (voice or keyboard)
echo   [3] Launch GUI             (Tkinter)
echo   [4] Run Tests              (pytest)
echo   [5] Install Dependencies
echo   [6] Exit
echo.
set /p choice="Enter choice (1-6): "

if "%choice%"=="1" python demo\demo_script.py --slow
if "%choice%"=="2" python cli\main_cli.py --simulated --no-mic
if "%choice%"=="3" python gui\main_gui.py --simulated --no-tts
if "%choice%"=="4" python -m pytest tests\ -v
if "%choice%"=="5" pip install -r requirements.txt && pause
if "%choice%"=="6" exit
pause
