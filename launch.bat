@echo off
REM DeskOS one-click launcher for Windows.
setlocal

cd /d "%~dp0"

if not exist ".venv" (
    echo Creating a private Python environment for DeskOS...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo Installing/updating dependencies (first run only takes a minute)...
pip install -q -r requirements.txt

echo.
echo Starting DeskOS...
echo A small transparent bubble will appear in the corner of your screen.
python -m deskos.assistant_app

pause
