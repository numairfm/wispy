#!/bin/bash
# Listens for Right Shift key press and toggles wispy.
# Requires: ydotoold (from ydotool package), root access.
# Run: sudo ./wispy-rshift.sh
#
# To run at boot, add a systemd service or add to /etc/rc.local.
# Or run via sudo in a .desktop file under ~/.config/autostart/.

WISPY_TOGGLE="$HOME/.local/bin/wispy-toggle.sh"
RIGHT_SHIFT_KEYCODE=54  # KEY_RIGHTSHIFT in linux input

if [ ! -x "$WISPY_TOGGLE" ]; then
    echo "Error: $WISPY_TOGGLE not found or not executable"
    exit 1
fi

echo "Listening for Right Shift to toggle wispy... (Ctrl+C to stop)"

# ydotoold outputs raw key events; we filter for Right Shift press
ydotoold | while read -r line; do
    # Look for keycode 54 (Right Shift) press events
    if echo "$line" | grep -q "key.*54.*1"; then
        "$WISPY_TOGGLE" &
    fi
done
