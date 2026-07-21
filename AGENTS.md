# Wispy — Agent Instructions

Lightweight voice-to-text for Linux (KDE Plasma/Wayland). Python + PyQt6, Groq Whisper API.

## Architecture

- `main.py` — entry point, CLI (subcommands: `server`, `toggle`, `help`), system tray daemon, Unix-socket IPC, audio capture (sounddevice), Groq transcription in background thread, `ydotool` text injection, clipboard copy, settings dialog (device selector, clipboard toggle), programmatic tray icon
- `overlay.py` — frameless always-on-top PyQt6 pill (recording dot, waveform, timer, stop button), dark glass design, equal-gap layout
- IPC: background thread listens on `$XDG_RUNTIME_DIR/wispy/wispy.sock`; `wispy toggle` sends a toggle message
- Transcription: runs in background daemon thread to avoid blocking Qt event loop; communicates errors via pyqtSignal (`_notify`, `_set_clipboard`)
- Audio: 16kHz mono float32 via sounddevice InputStream, converted to WAV int16 for Groq; input device selectable in settings; shared state protected by threading.Lock
- Tray icon: drawn programmatically (QPainter) — dark rounded square + white sound-wave bars; tries SVG first
- `wispy.sh` — self-contained launcher (activates venv, runs main.py)
- `wispy.desktop` — KDE desktop entry for launcher/autostart
- `wispy.service` — systemd user service for auto-start on login
- `build.sh` — PyInstaller build for standalone executable

## Commands

```sh
./wispy.sh server       # start daemon
./wispy.sh toggle       # toggle overlay on running instance
./wispy.sh help         # show help
./build.sh              # build standalone executable → dist/wispy
./setup.sh install --build   # build + install (binary, icons, desktop, service)
./setup.sh uninstall         # remove installed files
```

No lint command. Run `.venv/bin/python test_wispy.py` for CLI + constant tests.

## Key Dependencies

- PyQt6, sounddevice, numpy, groq

## Setup

Create + activate venv first, then `pip install -r requirements.txt`.

Config at `~/.config/wispy/config.json` or `GROQ_API_KEY` env var.

`ydotool` must be installed on the system (text injection via uinput).

## Conventions

- Run `AGENTS.md` updates past the user before committing.
