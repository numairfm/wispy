# Wispy

Voice-to-text for Linux. Press a key, speak, text appears in the active field.

Built with Python + PyQt6 — lightweight, native, Wayland/KDE Plasma.

## How it works

1. Click the tray icon (or press your shortcut) → recording starts
2. Speak — waveform and timer show recording
3. Hit stop → audio sent to Groq Whisper API
4. Transcribed text is typed via `ydotool`

## Requirements

- Linux (KDE Plasma / Wayland)
- `ydotool` — text injection via uinput (`dnf install ydotool` / `pacman -S ydotool` / `apt install ydotool`)
- A [Groq](https://groq.com) API key

## Quick start

```sh
git clone <repo> && cd wispy
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./wispy.sh
```

Click tray icon → Settings → enter your Groq API key.

## Install / Uninstall

```sh
# Build + install (binary, icon, desktop file, systemd service)
./setup.sh install --build

# Install without building (uses wispy.sh launcher)
./setup.sh install

# Remove everything
./setup.sh uninstall
```

Manual build only: `./build.sh` → `dist/wispy`

Check service: `systemctl --user status wispy`

## KDE shortcut

System Settings → Shortcuts → Custom Shortcuts → New → Global Shortcut → Run Command:
- Trigger: your key combo (e.g. `Ctrl+Super+Space`)
- Action: `~/.local/bin/wispy --toggle` (or `./wispy.sh --toggle`)

## Settings

Tray icon → right-click → **Settings…** to configure:

- Groq API key
- Whisper model (`whisper-large-v3`, `whisper-large-v3-turbo`, `distil-whisper-large-v3-en`)
- Language (optional, e.g. `en`)

Or edit `~/.config/wispy/config.json`:

```json
{
  "groq_api_key": "gsk_...",
  "groq_model": "whisper-large-v3",
  "language": "en"
}
```

## License

MIT
