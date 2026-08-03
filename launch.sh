#!/usr/bin/env bash
# ============================================================
#  DeskOS one-click launcher for macOS/Linux.
#
#  Mirrors launch.bat: never relies on PATH or `activate`, calls the
#  virtual environment's interpreter by full path, and fails loudly
#  rather than silently falling back to the system Python.
# ============================================================
set -euo pipefail
cd "$(dirname "$0")"

VENV_PY=".venv/bin/python"

# --- 1. Is Python available at all? -------------------------
if ! command -v python3 >/dev/null 2>&1; then
    echo ""
    echo "[ERROR] Python 3 was not found."
    echo "Install Python 3.10 or newer from https://python.org/downloads"
    echo ""
    exit 1
fi

# --- 2. Repair a broken environment -------------------------
# A .venv directory can exist while being unusable (copied between
# machines, or built by a Python that has since been removed).
if [ -d ".venv" ] && [ ! -x "$VENV_PY" ]; then
    echo "Existing environment is broken. Rebuilding it..."
    rm -rf .venv
fi

# --- 3. Create the environment if needed ---------------------
if [ ! -x "$VENV_PY" ]; then
    echo "Creating a private Python environment for DeskOS..."
    if ! python3 -m venv .venv; then
        echo ""
        echo "[ERROR] Could not create the environment."
        echo "On Debian/Ubuntu you may need: sudo apt install python3-venv"
        echo ""
        exit 1
    fi
fi

# --- 4. Refuse to continue without a working venv -------------
if [ ! -x "$VENV_PY" ]; then
    echo ""
    echo "[ERROR] The environment was created but $VENV_PY is missing."
    echo ""
    exit 1
fi

# --- 5. Install DeskOS into the venv, never system-wide -------
echo "Installing/updating DeskOS..."
"$VENV_PY" -m pip install -q --disable-pip-version-check -e .

# --- 6. Prove we are running from the venv -------------------
echo "Using $("$VENV_PY" --version) from .venv"
echo ""

echo "Starting DeskOS..."
echo "A small transparent bubble will appear in the corner of your screen."
echo ""
"$VENV_PY" -m deskos.assistant_app
