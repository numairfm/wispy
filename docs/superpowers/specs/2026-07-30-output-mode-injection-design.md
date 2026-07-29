# Design Spec: Output Mode Injection & Settings

Date: 2026-07-30
Status: Approved

## Overview

This specification adds configurable text output modes to Wispy (`paste`, `type`, `copy`) and updates `Injector` to support clipboard paste (`Ctrl+V` via `ydotool`) as the default output action.

---

## 1. Output Modes

Add a new configuration key `"output_mode"` with 3 values:

1. `"paste"` (Default): Copies transcribed text to system clipboard and sends `Ctrl+V` key sequence (`29:1 47:1 47:0 29:0`) via `ydotool key`.
2. `"type"`: Simulates character-by-character typing using `ydotool type -d 1 -H 1 <text>`.
3. `"copy"`: Copies transcribed text to system clipboard only, skipping key injection.

---

## 2. Component Changes

### 2.1 Injector (`src/injector.py`)

Update `Injector.inject(text, mode="paste", send_enter=False)`:
- `mode == "paste"`: Execute `ydotool key 29:1 47:1 47:0 29:0`.
- `mode == "type"`: Execute `ydotool type -d 1 -H 1 <text>`.
- `mode == "copy"`: No key action.
- If `send_enter` is `True`, execute `ydotool key 28:1 28:0` afterwards.

### 2.2 Application Lifecycle (`src/main.py`)

1. **Config Defaults**: Set default `"output_mode": "paste"` in `_load_config()`.
2. **Transcription & Injection (`_transcribe_and_inject`)**:
   - Retrieve `mode = self.config.get("output_mode", "paste")`.
   - If `mode in ("paste", "copy")` or `self.config.get("copy_to_clipboard")`, emit `_set_clipboard.emit(text)`.
   - Call `inj.inject(text, mode=mode, send_enter=self.config.get("send_enter", False))`.
3. **Settings Dialog (`SettingsDialog`)**:
   - Under "Behavior", add `Output Mode` `QComboBox` with options:
     - `Paste (Clipboard + Ctrl+V)` -> `"paste"`
     - `Type (character by character)` -> `"type"`
     - `Copy to Clipboard Only` -> `"copy"`
   - Save and load `output_mode` to/from `config.json`.

---

## 3. Testing Plan

1. Update `tests/test_wispy.py` to test `Injector.inject` mode handling (mocking `subprocess.run`).
2. Run test suite `.venv/bin/python tests/test_wispy.py`.
