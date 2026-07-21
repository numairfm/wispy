# Wispy — Agent Instructions

Lightweight voice-to-text for Linux (KDE Plasma/Wayland). Python + PyQt6, Groq Whisper API.

## Architecture

- `main.py` — entry point, system tray daemon, Unix-socket IPC (`--toggle`), audio capture (sounddevice), Groq transcription, `ydotool` text injection, settings dialog, programmatic tray icon
- `overlay.py` — frameless always-on-top PyQt6 pill (recording dot, waveform, timer, stop button), dark glass design with teal accent
- IPC: background thread listens on `$XDG_RUNTIME_DIR/wispy/wispy.sock`; `--toggle` sends a toggle message
- Audio: 16kHz mono float32 via sounddevice InputStream, converted to WAV int16 for Groq
- Tray icon: drawn programmatically (QPainter) — teal rounded rect + white sound-wave bars
- `wispy.sh` — self-contained launcher (activates venv, runs main.py)
- `wispy.desktop` — KDE desktop entry for launcher/autostart

## Commands

```sh
./wispy.sh              # start daemon
./wispy.sh --toggle     # toggle overlay on running instance
```

No test/lint commands established yet.

## Key Dependencies

- PyQt6, sounddevice, numpy, groq

## Setup

Create + activate venv first, then `pip install -r requirements.txt`.

Config at `~/.config/wispy/config.json` or `GROQ_API_KEY` env var.

`ydotool` must be installed on the system (text injection via uinput).

## Conventions

- Run `AGENTS.md` updates past the user before committing.
