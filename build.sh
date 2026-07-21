#!/bin/bash
set -e
cd "$(dirname "$0")"

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
    --add-data "overlay.py:." \
    --add-data "wispy.svg:." \
    --add-data "wispy-toggle.svg:." \
    main.py

echo ""
echo "Done: dist/wispy"
echo "Copy to ~/.local/bin/ and run from anywhere."
