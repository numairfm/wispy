# Wispy

Voice-to-text for Linux. Press a key, speak, text appears in the active field.

Built with Python + PyQt6 — lightweight, native, Wayland/KDE Plasma.

## How it works

1. Press your configured shortcut → a floating pill overlay appears at screen bottom
2. Speak — waveform and timer show recording
3. Hit stop → audio sent to Groq Whisper API
4. Transcribed text is typed via `ydotool`

## Requirements

- Linux (KDE Plasma / Wayland)
- `ydotool` (`apt install ydotool` / `pacman -S ydotool` / `dnf install ydotool`)
- A [Groq](https://groq.com) API key

## Setup (from source)

```sh
cd wispy
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Running

```sh
./wispy.sh                   # start daemon (system tray)
./wispy.sh --toggle          # toggle recording on running instance
```

## Build standalone executable

No Python/venv needed at runtime — just one binary:

```sh
./build.sh                   # outputs dist/wispy
cp dist/wispy ~/.local/bin/
```

### Desktop launcher (optional)

```sh
cp wispy.desktop ~/.local/share/applications/
cp wispy.svg ~/.local/share/icons/hicolor/scalable/apps/
```

### KDE custom shortcut (recommended)

- System Settings → Shortcuts → Custom Shortcuts → Edit → New → Global Shortcut → Run Command
- Trigger: your preferred key combo (e.g. `Ctrl+Super+Space`)
- Action: `/path/to/wispy --toggle`

## Settings

Right-click the tray icon → **Settings…** to configure:

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
