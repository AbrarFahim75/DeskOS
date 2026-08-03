@echo off
REM ============================================================
REM  DeskOS one-click launcher for Windows.
REM
REM  Design note: this script deliberately never relies on PATH or on
REM  `activate.bat`. It calls the virtual environment's interpreter by
REM  full path and verifies every step, because a launcher that silently
REM  falls back to the system Python installs DeskOS in the wrong place
REM  and is very hard for a beginner to diagnose.
REM ============================================================
setlocal
cd /d "%~dp0"

set "VENV_PY=.venv\Scripts\python.exe"

REM --- 1. Is Python available at all? -------------------------
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Python was not found.
    echo.
    echo Install Python 3.10 or newer from https://python.org/downloads
    echo IMPORTANT: tick "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

REM --- 2. Repair a broken environment -------------------------
REM A .venv folder can exist while being unusable (copied between
REM machines, or built by a Python that has since been uninstalled).
REM Presence of the folder is not proof it works; the interpreter is.
if exist ".venv" (
    if not exist "%VENV_PY%" (
        echo Existing environment is broken. Rebuilding it...
        rmdir /s /q ".venv"
    )
)

REM --- 3. Create the environment if needed ---------------------
if not exist "%VENV_PY%" (
    echo Creating a private Python environment for DeskOS...
    python -m venv .venv
    if errorlevel 1 (
        echo.
        echo [ERROR] Could not create the environment in this folder.
        echo Check that you have permission to write here, and that the
        echo path contains no unusual characters.
        echo.
        pause
        exit /b 1
    )
)

REM --- 4. Refuse to continue without a working venv -------------
if not exist "%VENV_PY%" (
    echo.
    echo [ERROR] The environment was created but "%VENV_PY%" is missing.
    echo Run diagnose.bat and send the output for help.
    echo.
    pause
    exit /b 1
)

REM --- 5. Install DeskOS into the venv, never system-wide -------
echo Installing/updating DeskOS...
"%VENV_PY%" -m pip install -q --disable-pip-version-check -e .
if errorlevel 1 (
    echo.
    echo [ERROR] Installation failed. The message above explains why.
    echo.
    pause
    exit /b 1
)

REM --- 6. Prove we are running from the venv -------------------
for /f "delims=" %%v in ('"%VENV_PY%" --version') do set "PYVER=%%v"
echo Using %PYVER% from .venv
echo.

echo Starting DeskOS...
echo A small transparent bubble will appear in the corner of your screen.
echo.
"%VENV_PY%" -m deskos.assistant_app

echo.
echo DeskOS has stopped.
pause
