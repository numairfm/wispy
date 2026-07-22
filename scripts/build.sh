#!/bin/bash
set -e
cd "$(dirname "$0")/.."

if ! command -v pyinstaller &>/dev/null; then
    echo "Installing PyInstaller..."
    pip install pyinstaller
fi

echo "Building wispy..."
pyinstaller \
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
