#!/bin/bash
set -e

NAME="wispy"
BIN="$HOME/.local/bin/$NAME"
ICON="$HOME/.local/share/icons/hicolor/scalable/apps/$NAME.svg"
DESKTOP="$HOME/.local/share/applications/$NAME.desktop"
SERVICE="$HOME/.config/systemd/user/$NAME.service"
SRC="$(cd "$(dirname "$0")" && pwd)"

usage() {
    echo "Usage: $0 {install|uninstall} [--build]"
    exit 1
}

do_build() {
    echo "Building $NAME..."
    "$SRC/build.sh"
}

do_install() {
    if [ "$BUILD" = "1" ]; then
        do_build
    fi

    echo "Installing $NAME..."

    mkdir -p "$(dirname "$BIN")"
    if [ -f "$SRC/dist/$NAME" ]; then
        cp "$SRC/dist/$NAME" "$BIN"
        echo "  binary  → $BIN"
    elif [ -f "$SRC/$NAME.sh" ]; then
        cp "$SRC/$NAME.sh" "$BIN"
        chmod +x "$BIN"
        echo "  launcher → $BIN"
    else
        echo "Error: no binary or launcher found. Run with --build first."
        exit 1
    fi

    mkdir -p "$(dirname "$ICON")"
    cp "$SRC/$NAME.svg" "$ICON"
    echo "  icon    → $ICON"

    mkdir -p "$(dirname "$DESKTOP")"
    sed "s|Exec=.*|Exec=$BIN server|;s|Icon=.*|Icon=$ICON|" \
        "$SRC/$NAME.desktop" > "$DESKTOP"
    echo "  desktop → $DESKTOP"

    if [ -f "$SRC/$NAME.service" ]; then
        mkdir -p "$(dirname "$SERVICE")"
        sed "s|ExecStart=.*|ExecStart=$BIN server|" \
            "$SRC/$NAME.service" > "$SERVICE"
        echo "  service → $SERVICE"
    fi

    echo ""
    echo "Done. Run '$NAME' or enable the systemd service:"
    echo "  systemctl --user daemon-reload"
    echo "  systemctl --user enable --now $NAME"
}

do_uninstall() {
    echo "Uninstalling $NAME..."

    systemctl --user stop "$NAME" 2>/dev/null || true
    systemctl --user disable "$NAME" 2>/dev/null || true

    for f in "$BIN" "$ICON" "$DESKTOP" "$SERVICE"; do
        if [ -f "$f" ]; then
            rm "$f"
            echo "  removed $f"
        fi
    done

    systemctl --user daemon-reload 2>/dev/null || true
    echo "Done."
}

BUILD=0
ACTION=""

for arg in "$@"; do
    case "$arg" in
        install|uninstall) ACTION="$arg" ;;
        --build)           BUILD=1 ;;
        *)                 usage ;;
    esac
done

[ -z "$ACTION" ] && usage

"do_$ACTION"
