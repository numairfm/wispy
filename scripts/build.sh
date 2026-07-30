#!/bin/bash
set -e
cd "$(dirname "$0")/.."

# Use the venv interpreter so PyInstaller analyzes the venv's installed packages
# (PyQt6 etc.). Bare `pyinstaller` may resolve to a --user install bound to
# system Python, which lacks the project deps and bakes a broken binary.
PYTHON=".venv/bin/python"
if [ ! -x "$PYTHON" ]; then
    PYTHON="python3"
fi
if ! "$PYTHON" -c "import PyInstaller" 2>/dev/null; then
    echo "Installing PyInstaller..."
    "$PYTHON" -m pip install pyinstaller
fi

echo "Building wispy..."
"$PYTHON" -m PyInstaller \
    --name wispy \
    --onefile \
    --noconfirm \
    --clean \
    --add-data "assets/wispy.svg:." \
    --hidden-import=transcriber \
    --hidden-import=injector \
    --hidden-import=exceptions \
    --hidden-import=recorder \
    src/main.py

echo ""
echo "Done: dist/wispy"
echo "Copy to ~/.local/bin/ and run from anywhere."
