# Design Spec: Ctrl+Shift+V Auto-Paste & Simplified Output Options

Date: 2026-07-30
Status: Approved

## Overview

This specification updates Wispy's paste sequence to `Ctrl+Shift+V` (`29:1 42:1 47:1 47:0 42:0 29:0` via `ydotool`) for instant compatibility across terminals and desktop windows, and simplifies the Output Mode settings to two options: `Paste Automatically` and `Save to Clipboard Only`.

---

## 1. Simplified Output Modes

Output Mode configuration key `"output_mode"` now accepts 2 values:

1. `"paste"` (Default): Copies text to clipboard and executes `Ctrl+Shift+V` key sequence `29:1 42:1 47:1 47:0 42:0 29:0`.
2. `"copy"`: Copies text to clipboard only, without sending key strokes.

---

## 2. Component Changes

### 2.1 Injector (`src/injector.py`)

Update `Injector.inject(text, mode="paste", send_enter=False)`:
- `mode == "paste"`: Execute `ydotool key 29:1 42:1 47:1 47:0 42:0 29:0`.
- `mode == "copy"`: No key action.
- If `send_enter` is `True`, execute `ydotool key 28:1 28:0` afterwards.

### 2.2 Settings & Lifecycle (`src/main.py`)

1. **Config Defaults**: `"output_mode"` defaults to `"paste"`.
2. **Settings Dialog**:
   - Simplify Output Mode dropdown to:
     - `Paste Automatically (Clipboard + Paste)` -> `"paste"`
     - `Save to Clipboard Only` -> `"copy"`
   - Remove `"type"` mode option.

---

## 3. Testing Plan

1. Update `tests/test_wispy.py` to assert `ydotool key 29:1 42:1 47:1 47:0 42:0 29:0` for paste mode.
2. Run test suite `.venv/bin/python tests/test_wispy.py`.
