#!/usr/bin/env bash
# DeskOS one-click launcher for macOS/Linux.
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "Creating a private Python environment for DeskOS..."
    python3 -m venv .venv
fi

source .venv/bin/activate

echo "Installing/updating dependencies (first run only takes a minute)..."
pip install -q -r requirements.txt

echo ""
echo "Starting DeskOS..."
python -m deskos.main
