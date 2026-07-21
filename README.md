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
./scripts/wispy.sh server
```

Click tray icon → Settings → enter your Groq API key.

## Commands

```sh
wispy          # show help
wispy server   # run the daemon
wispy toggle   # toggle recording on a running instance
```

## Install / Uninstall

```sh
# Activate venv first (required for build)
source .venv/bin/activate

# Build + install (binary, icon, desktop file, systemd service)
./scripts/setup.sh install --build

# Install without building (uses wispy.sh launcher)
./scripts/setup.sh install

# Remove everything
./scripts/setup.sh uninstall
```

Manual build only: `./scripts/build.sh` → `dist/wispy`

Check service: `systemctl --user status wispy`

## KDE shortcut

System Settings → Keyboard → Shortcuts → Custom Shortcuts → New → Global Shortcut → Command/URL:
- **Name:** Wispy Toggle
- **Comment:** Toggle Wispy recording
- **Trigger:** your key combo (e.g. `Ctrl+Super+Space`)
- **Action:** `$HOME/.local/bin/wispy-toggle.sh`

KDE runs command shortcuts as a shell environment — bash scripts work reliably.
Use the installed wrapper script rather than calling `wispy` directly.

## Settings

Tray icon → right-click → **Settings…** to configure:

- Groq API key
- Whisper model (`whisper-large-v3`, `whisper-large-v3-turbo`, `distil-whisper-large-v3-en`)
- Language (optional, e.g. `en`)
- Input device (system default or specific mic)
- Copy transcribed text to clipboard (on/off)
- Clean and format text with AI (on/off)

Or edit `~/.config/wispy/config.json`:

```json
{
  "groq_api_key": "gsk_...",
  "groq_model": "whisper-large-v3",
  "language": "en",
  "input_device": "",
  "copy_to_clipboard": false,
  "clean_text": false
}
```

## License

MIT
