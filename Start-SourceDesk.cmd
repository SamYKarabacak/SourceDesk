@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% equ 0 (
    py -3 run.py %*
) else (
    python run.py %*
)
if errorlevel 1 (
    echo.
    echo SourceDesk could not start. Review the error above for details.
    echo If Python is missing, install Python 3.12 or newer from https://www.python.org/downloads/
    pause
)
