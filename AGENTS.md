# Wispy — Agent Instructions

Lightweight voice-to-text for Linux (KDE Plasma/Wayland). Python + PyQt6, Groq Whisper API.

## Architecture

- `src/main.py` — entry point, CLI (subcommands: `server`, `toggle`, `help`), system tray daemon, Unix-socket IPC (QSocketNotifier, event-loop driven), audio capture (sounddevice), Groq transcription + optional LLM post-processing in background thread, `ydotool` text injection, clipboard copy, settings dialog (device selector, clipboard toggle, clean text toggle), programmatic tray icon
- `src/overlay.py` — frameless always-on-top PyQt6 pill (recording dot, waveform, timer, stop button), dark glass design, equal-gap layout
- IPC: QSocketNotifier monitors `$XDG_RUNTIME_DIR/wispy/wispy.sock` in the Qt event loop (no polling thread); `wispy toggle` sends a toggle message — handled instantly on the main thread
- Audio: 16kHz mono float32 via sounddevice InputStream, converted to WAV int16 for Groq; input device selectable in settings; shared state protected by threading.Lock
- Recording lifecycle: overlay show/hide is immediate (on the GUI thread); the PortAudio stream open/close runs in background daemon threads so device negotiation latency never blocks the UI. Stream-open race (user stops while opening) guarded by `_audio_lock` + `recording` flag check
- LLM post-processing: when `clean_text` is enabled, raw Whisper transcription is sent to Groq `openai/gpt-oss-20b` with a system prompt that removes retractions and auto-formats. Falls back to raw text on error. Skipped for < 5 words.
- Tray icon: drawn programmatically (QPainter) — black rounded square + light sound-wave bars; tries SVG first
- `scripts/wispy.sh` — self-contained launcher (activates venv, runs src/main.py)
- `scripts/wispy-toggle.sh` — instant toggle via system python3 (bypasses PyInstaller extraction)
- `scripts/build.sh` — PyInstaller build for standalone executable
- `scripts/setup.sh` — install/uninstall binary, icon, desktop file, systemd service
- `system/wispy.desktop` — KDE desktop entry for launcher/autostart
- `system/wispy.service` — systemd user service for auto-start on login
- `assets/wispy.svg` — tray icon (black theme)
- `tests/test_wispy.py` — CLI + constant tests

## Commands

```sh
./scripts/wispy.sh server       # start daemon
./scripts/wispy.sh toggle       # toggle overlay on running instance
./scripts/wispy.sh help         # show help
./scripts/build.sh              # build standalone executable → dist/wispy
./scripts/setup.sh install --build   # build + install (binary, icons, desktop, service)
./scripts/setup.sh uninstall         # remove installed files
```

No lint command. Run `.venv/bin/python tests/test_wispy.py` for CLI + constant tests.

## Key Dependencies

- PyQt6, sounddevice, numpy, groq

## Setup

Create + activate venv first, then `pip install -r requirements.txt`.

Config at `~/.config/wispy/config.json` or `GROQ_API_KEY` env var.

`ydotool` must be installed on the system (text injection via uinput).

## Conventions

- Run `AGENTS.md` updates past the user before committing.
