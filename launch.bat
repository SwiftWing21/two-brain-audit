@echo off
cd /d "%~dp0"
python run_demo.py
if errorlevel 1 (
    echo.
    echo ERROR: Something went wrong. See above for details.
    pause
)
