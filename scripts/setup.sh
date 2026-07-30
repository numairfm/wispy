#!/bin/bash
set -e

NAME="wispy"
BIN="$HOME/.local/bin/$NAME"
SERVER_BIN="$HOME/.local/bin/$NAME-server"
TOGGLE_BIN="$HOME/.local/bin/$NAME-toggle.sh"
ICON="$HOME/.local/share/icons/hicolor/scalable/apps/$NAME.svg"
DESKTOP="$HOME/.local/share/applications/$NAME.desktop"
SERVICE="$HOME/.config/systemd/user/$NAME.service"
SRC="$(cd "$(dirname "$0")/.." && pwd)"

usage() {
    echo "Usage: $0 {install|uninstall} [--build]"
    exit 1
}

do_build() {
    echo "Building $NAME..."
    "$SRC/scripts/build.sh"
}

do_install() {
    if [ "$BUILD" = "1" ]; then
        do_build
    fi

    echo "Installing $NAME..."

    mkdir -p "$(dirname "$BIN")"

    # Install the toggle script (fast path — system python3, no PyInstaller extraction)
    cp "$SRC/scripts/$NAME-toggle.sh" "$TOGGLE_BIN"
    chmod +x "$TOGGLE_BIN"
    echo "  toggle  → $TOGGLE_BIN"

    # Install the server binary (PyInstaller or venv launcher)
    if [ -f "$SRC/dist/$NAME" ]; then
        cp "$SRC/dist/$NAME" "$SERVER_BIN"
        echo "  binary  → $SERVER_BIN"
    elif [ -f "$SRC/scripts/$NAME.sh" ]; then
        cp "$SRC/scripts/$NAME.sh" "$SERVER_BIN"
        chmod +x "$SERVER_BIN"
        echo "  launcher → $SERVER_BIN"
    else
        echo "Error: no binary or launcher found. Run with --build first."
        exit 1
    fi

    # Install wispy wrapper: toggle → instant python3, everything else → server binary
    cat > "$BIN" <<'WRAPPER'
#!/bin/sh
# wispy — fast toggle (system python3), delegates server to wispy-server
case "$1" in
    toggle) exec "$HOME/.local/bin/wispy-toggle.sh" ;;
    "")     exec "$HOME/.local/bin/wispy-server" "server" ;;
    help)   exec "$HOME/.local/bin/wispy-server" "--help" ;;
    *)      exec "$HOME/.local/bin/wispy-server" "$@" ;;
esac
WRAPPER
    chmod +x "$BIN"
    echo "  wrapper → $BIN"

    mkdir -p "$(dirname "$ICON")"
    cp "$SRC/assets/$NAME.svg" "$ICON"
    echo "  icon    → $ICON"

    mkdir -p "$(dirname "$DESKTOP")"
    sed "s|Exec=.*|Exec=$SERVER_BIN server|;s|Icon=.*|Icon=$ICON|" \
        "$SRC/system/$NAME.desktop" > "$DESKTOP"
    echo "  desktop → $DESKTOP"

    if [ -f "$SRC/system/$NAME.service" ]; then
        mkdir -p "$(dirname "$SERVICE")"
        sed "s|ExecStart=.*|ExecStart=$SERVER_BIN server|" \
            "$SRC/system/$NAME.service" > "$SERVICE"
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

    for f in "$BIN" "$SERVER_BIN" "$TOGGLE_BIN" "$ICON" "$DESKTOP" "$SERVICE"; do
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
