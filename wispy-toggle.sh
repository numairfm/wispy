#!/bin/sh
# wispy-toggle — instant toggle via system python3 (bypasses PyInstaller extraction)
SOCKET="${XDG_RUNTIME_DIR:-$HOME/.cache}/wispy/wispy.sock"
python3 -c "
import socket, sys
s = socket.socket(socket.AF_UNIX); s.settimeout(2)
try:
    s.connect('$SOCKET'); s.sendall(b'toggle'); s.close()
except (ConnectionRefusedError, FileNotFoundError, OSError):
    print('wispy: no running instance found', file=sys.stderr); sys.exit(1)
"
