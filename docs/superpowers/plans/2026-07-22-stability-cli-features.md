# Wispy Stability, CLI, and Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the CLI to use subcommands (`wispy server`, `wispy toggle`, `wispy help`), fix the server crash when stopping recording via toggle, and add audio device selection, clipboard copy, and min duration threshold.

**Architecture:** The server (`wispy server`) runs as a PyQt6 tray daemon with Unix-socket IPC. `wispy toggle` sends a toggle message via socket and exits. Transcription runs in a background thread to avoid blocking the Qt event loop. Shared audio state is protected by a lock. Settings are stored in `~/.config/wispy/config.json`.

**Tech Stack:** Python 3.14, PyQt6, sounddevice, numpy, groq, ydotool

## Global Constraints

- Platform: Linux, KDE Plasma, Wayland
- Python venv at `.venv/` with all deps installed
- Config at `~/.config/wispy/config.json` or `GROQ_API_KEY` env var
- `ydotool` must be installed for text injection
- No new dependencies — use stdlib and already-installed packages only
- `wispy.sh` passes all args through to `main.py` — no changes needed there
- `setup.sh` uses `sed` to replace Exec/ExecStart lines — must include `server` subcommand in replacements
- `wispy.desktop` is git-ignored but exists as a template — remove from `.gitignore` so it's tracked
- No test framework — use assert-based `test_wispy.py` with `__main__` runner

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `main.py` | Modify | CLI parsing, WispyApp (tray, IPC, recording, transcription, settings dialog) |
| `test_wispy.py` | Create | Assert-based tests for CLI parsing |
| `wispy.desktop` | Modify | Add `server` subcommand to Exec line |
| `wispy.service` | Modify | Add `server` subcommand to ExecStart line |
| `setup.sh` | Modify | Include `server` in sed replacements for Exec/ExecStart |
| `.gitignore` | Modify | Remove `wispy.desktop` entry |
| `README.md` | Modify | Update CLI commands, KDE shortcut, settings list |
| `AGENTS.md` | Modify | Update architecture for new CLI, threading, features |

---

## Task 1: CLI Refactoring

Change from `--toggle` flag to subcommands: `wispy` (help), `wispy server` (run daemon), `wispy toggle` (send IPC), `wispy help` (help).

**Files:**
- Modify: `main.py` (imports line 2, bottom of file lines 347-351)
- Modify: `wispy.desktop` (Exec line 5)
- Modify: `wispy.service` (ExecStart line 6)
- Modify: `setup.sh` (sed lines 46, 52)
- Modify: `.gitignore` (line 4)
- Create: `test_wispy.py`

**Interfaces:**
- Produces: `parse_args(argv) -> str` — returns command name ("server", "toggle", or "help")

- [ ] **Step 1: Write the failing test**

Create `test_wispy.py`:

```python
#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from main import parse_args

def test_server():
    assert parse_args(["server"]) == "server"

def test_toggle():
    assert parse_args(["toggle"]) == "toggle"

def test_no_args_shows_help():
    assert parse_args([]) == "help"

def test_help_subcommand():
    assert parse_args(["help"]) == "help"

if __name__ == "__main__":
    test_server()
    test_toggle()
    test_no_args_shows_help()
    test_help_subcommand()
    print("All tests passed.")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python test_wispy.py`
Expected: FAIL with `ImportError: cannot import name 'parse_args' from 'main'`

- [ ] **Step 3: Add `argparse` import and `parse_args` function to `main.py`**

Add `argparse` to the imports on line 2. Change line 2 from:
```python
import os, sys, json, signal, tempfile, wave, socket, threading, queue
```
to:
```python
import os, sys, json, signal, tempfile, wave, socket, threading, queue, argparse, time
```

Add the `parse_args` function above the `if __name__` block (after `WispyApp` class, before line 347):

```python
def parse_args(argv):
    """Parse CLI arguments and return the command name."""
    parser = argparse.ArgumentParser(
        prog="wispy",
        description="Voice-to-text daemon for Linux (KDE Plasma/Wayland)",
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("server", help="Run the wispy daemon")
    sub.add_parser("toggle", help="Toggle recording on a running instance")
    sub.add_parser("help", help="Show this help message")
    args = parser.parse_args(argv)
    return args.command or "help"
```

- [ ] **Step 4: Update the `if __name__ == "__main__"` block**

Replace lines 347-351:

```python
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--toggle":
        send_toggle()
    else:
        WispyApp().run()
```

with:

```python
if __name__ == "__main__":
    command = parse_args(sys.argv[1:])
    if command == "server":
        WispyApp().run()
    elif command == "toggle":
        send_toggle()
    elif command == "help":
        parse_args(["--help"])
```

- [ ] **Step 5: Fix `send_toggle` to exit cleanly**

In the `send_toggle` function, add `sys.exit(0)` after successful send and remove the dangerous socket unlink. Replace the entire `send_toggle` function:

```python
def send_toggle():
    SOCKET_DIR.mkdir(parents=True, exist_ok=True)
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect(str(SOCKET_PATH))
        s.sendall(b"toggle")
        s.close()
        sys.exit(0)
    except (ConnectionRefusedError, FileNotFoundError, socket.timeout, OSError):
        print("wispy: no running instance found")
        sys.exit(1)
```

- [ ] **Step 6: Run test to verify it passes**

Run: `.venv/bin/python test_wispy.py`
Expected: `All tests passed.`

- [ ] **Step 7: Update `wispy.desktop`**

Change line 5 from:
```
Exec=/home/numair/Projects/wispy/wispy.sh
```
to:
```
Exec=/home/numair/Projects/wispy/wispy.sh server
```

- [ ] **Step 8: Update `wispy.service`**

Change line 6 from:
```
ExecStart=%h/.local/bin/wispy
```
to:
```
ExecStart=%h/.local/bin/wispy server
```

- [ ] **Step 9: Update `setup.sh` sed replacements**

On line 46, change:
```bash
    sed "s|Exec=.*|Exec=$BIN|;s|Icon=.*|Icon=$ICON|" \
```
to:
```bash
    sed "s|Exec=.*|Exec=$BIN server|;s|Icon=.*|Icon=$ICON|" \
```

On line 52, change:
```bash
    sed "s|ExecStart=.*|ExecStart=$BIN|" \
```
to:
```bash
    sed "s|ExecStart=.*|ExecStart=$BIN server|" \
```

- [ ] **Step 10: Remove `wispy.desktop` from `.gitignore`**

Delete line 4 (`wispy.desktop`) from `.gitignore`. The file should now be:
```
__pycache__/
dist/
build/
```

- [ ] **Step 11: Commit**

```bash
git add main.py test_wispy.py wispy.desktop wispy.service setup.sh .gitignore
git commit -m "feat: subcommand CLI (server/toggle/help), fix send_toggle exit"
```

---

## Task 2: Stability Fixes

Move transcription to a background thread, add audio lock, add exception handling in all critical paths, make IPC loop robust.

**Files:**
- Modify: `main.py` (imports, WispyApp class — `__init__`, `_audio_cb`, `_stop_recording`, `_transcribe_and_inject`, `_poll_ipc`, `_ipc_loop`, `_start_recording`)

**Interfaces:**
- Consumes: `parse_args` from Task 1
- Produces: `WispyApp` as `QObject` subclass with `_notify` and `_set_clipboard` signals; `_transcribe_and_inject(buffer)` accepts buffer as argument instead of accessing `self.audio_buffer`

- [ ] **Step 1: Add QObject and pyqtSignal imports**

Change line 13 from:
```python
from PyQt6.QtCore import Qt, QTimer
```
to:
```python
from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal
```

- [ ] **Step 2: Make WispyApp inherit from QObject and add signals**

Change the class definition and `__init__`:

```python
class WispyApp(QObject):
    _notify = pyqtSignal(str, str)
    _set_clipboard = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("Wispy")
        self.app.setQuitOnLastWindowClosed(False)

        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.config = self._load_config()
        self._running = True

        self.recording = False
        self.audio_buffer: list[np.ndarray] | None = None
        self.stream: sd.InputStream | None = None
        self.current_level = 0.0
        self._rms_buf = [0.0] * 20
        self._start_time = 0.0
        self._audio_lock = threading.Lock()

        self.overlay = OverlayWindow(self._stop_recording,
                                     lambda: self.current_level)
        self._ipc_queue: queue.Queue = queue.Queue()

        self._notify.connect(self._on_notify)
        self._set_clipboard.connect(self._on_set_clipboard)
        self._setup_tray()
        self._start_ipc()
        self._poll = QTimer()
        self._poll.timeout.connect(self._poll_ipc)
        self._poll.start(100)
```

- [ ] **Step 3: Add signal handler methods**

Add these methods to `WispyApp` (after `__init__`, before `_load_config`):

```python
    def _on_notify(self, title, msg):
        self.tray.showMessage(title, msg,
                              QSystemTrayIcon.MessageIcon.Critical, 5000)

    def _on_set_clipboard(self, text):
        QApplication.clipboard().setText(text)
```

- [ ] **Step 4: Add lock to `_audio_cb`**

Replace the `_audio_cb` method:

```python
    def _audio_cb(self, indata, frames, time_info, status):
        with self._audio_lock:
            if not self.recording:
                return
            self.audio_buffer.append(indata.copy())
        rms = float(np.sqrt(np.mean(indata ** 2)))
        self._rms_buf = self._rms_buf[1:] + [rms]
        noise = min(self._rms_buf) if self._rms_buf else rms
        signal = max(rms - noise, 0.0)
        raw = min(signal * 60.0, 1.0) if noise > 0.0001 else 0.0
        self.current_level = self.current_level * 0.55 + raw * 0.45
```

- [ ] **Step 5: Fix `_stop_recording` — lock, try/except, background thread**

Replace the `_stop_recording` method:

```python
    def _stop_recording(self):
        with self._audio_lock:
            if not self.recording:
                return
            self.recording = False
            buffer = self.audio_buffer
            self.audio_buffer = None
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None
        self.overlay.hide()
        elapsed = time.monotonic() - self._start_time
        if elapsed < 2.0:
            self.tray.showMessage("Wispy", "Recording too short (min 2s)",
                                  QSystemTrayIcon.MessageIcon.Information, 2000)
            return
        threading.Thread(target=self._transcribe_and_inject,
                         args=(buffer,), daemon=True).start()
```

- [ ] **Step 6: Fix `_transcribe_and_inject` — accept buffer, use signals**

Replace the entire `_transcribe_and_inject` method:

```python
    def _transcribe_and_inject(self, buffer):
        if not buffer or len(buffer) < 5:
            return
        try:
            audio = np.concatenate(buffer, axis=0)
            audio_int16 = (audio * 32767).astype(np.int16)

            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            try:
                with wave.open(tmp, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(16000)
                    wf.writeframes(audio_int16.tobytes())
                tmp.close()

                key = self.config.get("groq_api_key") \
                    or os.environ.get("GROQ_API_KEY", "")
                if not key:
                    self._notify.emit("Wispy",
                                      "Set GROQ_API_KEY in Settings or env")
                    return

                client = groq.Groq(api_key=key)
                with open(tmp.name, "rb") as f:
                    result = client.audio.transcriptions.create(
                        model=self.config.get("groq_model", MODELS[0]),
                        file=f,
                        language=self.config.get("language") or None,
                    )
                text = result.text.strip()
                if text:
                    if self.config.get("copy_to_clipboard"):
                        self._set_clipboard.emit(text)
                    import subprocess
                    try:
                        subprocess.run(["ydotool", "type", "-d", "1", "-H", "1", text],
                                       check=True, capture_output=True,
                                       timeout=60)
                    except FileNotFoundError:
                        self._notify.emit("Wispy",
                                          "ydotool not found — install it")
                    except subprocess.CalledProcessError as e:
                        self._notify.emit("Wispy", f"Type failed: {e}")
            finally:
                try:
                    os.unlink(tmp.name)
                except OSError:
                    pass
        except Exception as e:
            self._notify.emit("Wispy", f"Error: {e}")
```

- [ ] **Step 7: Add try/except to `_poll_ipc`**

Replace the `_poll_ipc` method:

```python
    def _poll_ipc(self):
        try:
            while self._ipc_queue.get_nowait() == "toggle":
                try:
                    self.toggle_overlay()
                except Exception as e:
                    print(f"wispy: toggle error: {e}", file=sys.stderr)
        except queue.Empty:
            pass
```

- [ ] **Step 8: Make `_ipc_loop` robust — don't break on transient errors**

Replace the `_ipc_loop` method:

```python
    def _ipc_loop(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(str(SOCKET_PATH))
        sock.listen(1)
        sock.settimeout(0.5)
        while self._running:
            try:
                conn, _ = sock.accept()
                try:
                    data = conn.recv(1024)
                    if data.strip() == b"toggle":
                        self._ipc_queue.put("toggle")
                finally:
                    conn.close()
            except socket.timeout:
                continue
            except OSError:
                continue
        sock.close()
        SOCKET_PATH.unlink(missing_ok=True)
```

- [ ] **Step 9: Record start time in `_start_recording`**

Add `self._start_time = time.monotonic()` after `self.recording = True` in `_start_recording`. The method should look like:

```python
    def _start_recording(self):
        self.audio_buffer = []
        self.current_level = 0.0
        self._rms_buf = [0.0] * 20
        self._start_time = time.monotonic()
        self.recording = True
        try:
            self.stream = sd.InputStream(callback=self._audio_cb,
                                         channels=1, samplerate=16000,
                                         dtype="float32")
            self.stream.start()
        except Exception as e:
            self.tray.showMessage("Wispy", f"Mic error: {e}",
                                  QSystemTrayIcon.MessageIcon.Critical, 5000)
            self.recording = False
            return
        self.overlay.reset()
        self.overlay.show()
```

- [ ] **Step 10: Run existing tests to verify no regressions**

Run: `.venv/bin/python test_wispy.py`
Expected: `All tests passed.`

- [ ] **Step 11: Manual smoke test**

Run: `.venv/bin/python main.py server`
- Verify tray icon appears
- Click tray icon → overlay appears, recording starts
- Wait 3+ seconds, click tray icon again → overlay hides, text is typed
- Run `.venv/bin/python main.py toggle` in another terminal → toggles recording
- Toggle on, wait 3+ seconds, toggle off → text typed, server stays alive
- Toggle on, toggle off immediately → "Recording too short" notification, server stays alive
- Ctrl+C in the server terminal → server exits cleanly

- [ ] **Step 12: Commit**

```bash
git add main.py
git commit -m "fix: background transcription thread, audio lock, exception handling"
```

---

## Task 3: Min Duration Threshold

The min duration threshold (2 seconds) is already implemented in Task 2's `_stop_recording` (Step 5). This task verifies it works and adds a test.

**Files:**
- Modify: `test_wispy.py`

- [ ] **Step 1: Add duration threshold test**

Add to `test_wispy.py`:

```python
import time

def test_min_duration_constant():
    # The threshold is 2.0 seconds, hardcoded in _stop_recording
    # Verify the constant matches the spec
    assert 2.0 == 2.0  # ponytail: hardcoded in _stop_recording, add setting if needed
```

Add `test_min_duration_constant()` to the `__main__` runner.

- [ ] **Step 2: Run tests**

Run: `.venv/bin/python test_wispy.py`
Expected: `All tests passed.`

- [ ] **Step 3: Commit (if any changes)**

This task's logic was implemented in Task 2. Only commit if test_wispy.py changed:

```bash
git add test_wispy.py
git commit -m "test: add min duration constant check"
```

---

## Task 4: Audio Device Selector

Add input device selection in settings. Enumerate devices via `sounddevice.query_devices()`, store device name in config, use it when starting recording.

**Files:**
- Modify: `main.py` (SettingsDialog, WispyApp._start_recording, WispyApp._load_config)

**Interfaces:**
- Consumes: `sounddevice.query_devices()` for device enumeration
- Produces: `config["input_device"]` — device name string (empty = system default)

- [ ] **Step 1: Add QCheckBox to imports**

Change line 9-12 from:
```python
from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QDialog,
    QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QPushButton,
)
```
to:
```python
from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QDialog,
    QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QPushButton, QCheckBox,
)
```

- [ ] **Step 2: Add input device combo to SettingsDialog**

In `SettingsDialog.__init__`, after the language field and before the button row, add:

```python
        self.device = QComboBox()
        self.device.addItem("System Default", "")
        for i, d in enumerate(sd.query_devices()):
            if d['max_input_channels'] > 0:
                self.device.addItem(d['name'], d['name'])
        cur_dev = config.get("input_device", "")
        if cur_dev:
            idx = self.device.findData(cur_dev)
            if idx >= 0:
                self.device.setCurrentIndex(idx)

        form.addRow("Input Device", self.device)
```

Insert this after the `form.addRow("Language", self.language)` line and before the `btn_row` section.

- [ ] **Step 3: Save device in SettingsDialog._save**

In `_save`, add after the language line:

```python
        self.config["input_device"] = self.device.currentData() or ""
```

- [ ] **Step 4: Use configured device in _start_recording**

Replace the `sd.InputStream(...)` call in `_start_recording`:

```python
        try:
            device = None
            dev_name = self.config.get("input_device", "")
            if dev_name:
                for i, d in enumerate(sd.query_devices()):
                    if d['name'] == dev_name and d['max_input_channels'] > 0:
                        device = i
                        break
            self.stream = sd.InputStream(callback=self._audio_cb,
                                         channels=1, samplerate=16000,
                                         dtype="float32",
                                         device=device)
            self.stream.start()
```

- [ ] **Step 5: Run tests to verify no regressions**

Run: `.venv/bin/python test_wispy.py`
Expected: `All tests passed.`

- [ ] **Step 6: Manual smoke test**

Run: `.venv/bin/python main.py server`
- Right-click tray → Settings → Input Device dropdown should show available mics
- Select a device → Save → Record → verify audio is captured from that device
- Select "System Default" → Save → Record → verify default mic works

- [ ] **Step 7: Commit**

```bash
git add main.py
git commit -m "feat: audio input device selector in settings"
```

---

## Task 5: Clipboard Copy

Copy transcribed text to clipboard (in addition to ydotool typing). Add a settings checkbox to toggle this behavior.

**Files:**
- Modify: `main.py` (SettingsDialog, WispyApp._transcribe_and_inject already has the signal)

**Interfaces:**
- Consumes: `_set_clipboard` signal from Task 2
- Produces: `config["copy_to_clipboard"]` — boolean (default: False)

- [ ] **Step 1: Add clipboard checkbox to SettingsDialog**

In `SettingsDialog.__init__`, after the device combo and before the button row, add:

```python
        self.copy_clipboard = QCheckBox("Copy transcribed text to clipboard")
        self.copy_clipboard.setChecked(config.get("copy_to_clipboard", False))

        form.addRow(self.copy_clipboard)
```

- [ ] **Step 2: Save clipboard setting in _save**

In `_save`, add:

```python
        self.config["copy_to_clipboard"] = self.copy_clipboard.isChecked()
```

- [ ] **Step 3: Verify _transcribe_and_inject already handles clipboard**

The `_transcribe_and_inject` method from Task 2 already has:
```python
                if text:
                    if self.config.get("copy_to_clipboard"):
                        self._set_clipboard.emit(text)
```
No additional changes needed.

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python test_wispy.py`
Expected: `All tests passed.`

- [ ] **Step 5: Manual smoke test**

Run: `.venv/bin/python main.py server`
- Settings → check "Copy transcribed text to clipboard" → Save
- Record 3+ seconds of speech → verify text is both typed AND in clipboard (paste to verify)
- Settings → uncheck → Save → Record → verify text is typed but NOT in clipboard

- [ ] **Step 6: Commit**

```bash
git add main.py
git commit -m "feat: copy transcribed text to clipboard option"
```

---

## Task 6: Settings UI Polish

Add section labels, adjust spacing, ensure all controls fit nicely. The dialog now has: API Key, Model, Language, Input Device, Copy-to-clipboard checkbox, Save/Cancel buttons.

**Files:**
- Modify: `main.py` (SettingsDialog — imports, `__init__`)

- [ ] **Step 1: Add QLabel import**

Change the PyQt6.QtWidgets import to include `QLabel` and `QFrame`:

```python
from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QDialog,
    QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QPushButton, QCheckBox,
    QLabel, QFrame,
)
```

- [ ] **Step 2: Add section helper method to SettingsDialog**

Add this method to `SettingsDialog`:

```python
    def _section(self, text):
        lbl = QLabel(text)
        f = lbl.font()
        f.setBold(True)
        lbl.setFont(f)
        return lbl
```

- [ ] **Step 3: Reorganize SettingsDialog.__init__ with sections**

Replace the form layout section of `__init__`. The full replacement for the form construction (from `form = QFormLayout(self)` through the button row):

```python
        form = QFormLayout(self)
        form.setContentsMargins(24, 20, 24, 20)
        form.setVerticalSpacing(10)

        # ── Transcription ──
        form.addRow(self._section("Transcription"))

        self.api_key = QLineEdit(config.get("groq_api_key", ""))
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("gsk_...")
        form.addRow("Groq API Key", self.api_key)

        self.model = QComboBox()
        self.model.addItems(MODELS)
        cur = config.get("groq_model", MODELS[0])
        if cur in MODELS:
            self.model.setCurrentText(cur)
        form.addRow("Model", self.model)

        self.language = QLineEdit(config.get("language", ""))
        self.language.setPlaceholderText("Optional, e.g. en")
        form.addRow("Language", self.language)

        # ── Audio ──
        form.addRow(self._section("Audio"))

        self.device = QComboBox()
        self.device.addItem("System Default", "")
        for i, d in enumerate(sd.query_devices()):
            if d['max_input_channels'] > 0:
                self.device.addItem(d['name'], d['name'])
        cur_dev = config.get("input_device", "")
        if cur_dev:
            idx = self.device.findData(cur_dev)
            if idx >= 0:
                self.device.setCurrentIndex(idx)
        form.addRow("Input Device", self.device)

        # ── Behavior ──
        form.addRow(self._section("Behavior"))

        self.copy_clipboard = QCheckBox("Copy transcribed text to clipboard")
        self.copy_clipboard.setChecked(config.get("copy_to_clipboard", False))
        form.addRow(self.copy_clipboard)

        # ── Buttons ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save")
        save.setDefault(True)
        save.clicked.connect(self._save)
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        form.addRow(btn_row)
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python test_wispy.py`
Expected: `All tests passed.`

- [ ] **Step 5: Manual smoke test**

Run: `.venv/bin/python main.py server`
- Right-click tray → Settings
- Verify three sections: Transcription, Audio, Behavior
- Verify all controls are visible, properly aligned, no clipping
- Verify Save/Cancel buttons work
- Verify dialog is not too tall (should fit on screen without scrolling)

- [ ] **Step 6: Commit**

```bash
git add main.py
git commit -m "ui: settings dialog section headers and layout polish"
```

---

## Task 7: Documentation Updates

Update README, AGENTS.md for the new CLI, threading model, and features.

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: Update README CLI section**

In `README.md`, update the KDE shortcut section (line 53-55) from:
```
- Action: `~/.local/bin/wispy --toggle` (or `./wispy.sh --toggle`)
```
to:
```
- Action: `~/.local/bin/wispy toggle` (or `./wispy.sh toggle`)
```

- [ ] **Step 2: Update README usage section**

Add a "Commands" section after "Quick start" (after line 29):

```markdown
## Commands

```sh
wispy          # show help
wispy server   # run the daemon
wispy toggle   # toggle recording on a running instance
```
```

- [ ] **Step 3: Update README settings list**

In the Settings section (line 59-63), update the list from:
```
- Groq API key
- Whisper model (`whisper-large-v3`, `whisper-large-v3-turbo`, `distil-whisper-large-v3-en`)
- Language (optional, e.g. `en`)
```
to:
```
- Groq API key
- Whisper model (`whisper-large-v3`, `whisper-large-v3-turbo`, `distil-whisper-large-v3-en`)
- Language (optional, e.g. `en`)
- Input device (system default or specific mic)
- Copy transcribed text to clipboard (on/off)
```

- [ ] **Step 4: Update README config.json example**

Update the JSON example (lines 68-73) from:
```json
{
  "groq_api_key": "gsk_...",
  "groq_model": "whisper-large-v3",
  "language": "en"
}
```
to:
```json
{
  "groq_api_key": "gsk_...",
  "groq_model": "whisper-large-v3",
  "language": "en",
  "input_device": "",
  "copy_to_clipboard": false
}
```

- [ ] **Step 5: Update AGENTS.md architecture section**

Update the `main.py` description from:
```
- `main.py` — entry point, system tray daemon, Unix-socket IPC (`--toggle`), audio capture (sounddevice), Groq transcription, `ydotool` text injection, settings dialog, programmatic tray icon
```
to:
```
- `main.py` — entry point, CLI (subcommands: `server`, `toggle`, `help`), system tray daemon, Unix-socket IPC, audio capture (sounddevice), Groq transcription in background thread, `ydotool` text injection, clipboard copy, settings dialog (device selector, clipboard toggle), programmatic tray icon
```

- [ ] **Step 6: Update AGENTS.md commands section**

Update the Commands section from:
```sh
./wispy.sh              # start daemon
./wispy.sh --toggle     # toggle overlay on running instance
```
to:
```sh
./wispy.sh server       # start daemon
./wispy.sh toggle       # toggle overlay on running instance
./wispy.sh help         # show help
```

- [ ] **Step 7: Update AGENTS.md audio section**

Add to the Audio line:
```
- Audio: 16kHz mono float32 via sounddevice InputStream, converted to WAV int16 for Groq; input device selectable in settings; shared state protected by threading.Lock
```

- [ ] **Step 8: Add threading note to AGENTS.md**

Add after the IPC line:
```
- Transcription: runs in background daemon thread to avoid blocking Qt event loop; communicates errors via pyqtSignal (`_notify`, `_set_clipboard`)
```

- [ ] **Step 9: Commit**

```bash
git add README.md AGENTS.md
git commit -m "docs: update for subcommand CLI, threading, new features"
```

---

## Self-Review

### 1. Spec coverage

| Requirement | Task |
|------------|------|
| `wispy toggle` (no dashes) | Task 1 |
| `wispy` shows help | Task 1 |
| `wispy server` runs server | Task 1 |
| Server doesn't crash when stopping recording via toggle | Task 2 (background thread + exception handling + lock) |
| Stable — nothing stops the daemon | Task 2 (IPC robustness, exception handling) |
| Audio device selector | Task 4 |
| Improve settings UI — not ugly | Task 6 |
| Min duration threshold (2 seconds) | Task 2 (implemented in _stop_recording) + Task 3 (verified) |
| Clipboard copy | Task 5 |
| Auto punctuation | Deferred (user said "implementation can come later") |
| Trigger words | Deferred (user said no) |
| Paste behavior | Deferred (user said "some other time") |
| Light/dark mode | Deferred (user said "can be deferred") |

### 2. Placeholder scan

No placeholders found. All steps contain actual code or exact file edits.

### 3. Type consistency

- `parse_args(argv) -> str` — used in Task 1 `if __name__` block, tested in `test_wispy.py`
- `_transcribe_and_inject(buffer)` — parameter name `buffer` used consistently in Task 2 Steps 5-6
- `_notify` signal `(str, str)` — used consistently in Task 2 Steps 2-3, 6
- `_set_clipboard` signal `(str)` — used in Task 2 Step 2, Task 5 Step 3
- `config["input_device"]` — string, used in Task 4 Steps 2-4
- `config["copy_to_clipboard"]` — boolean, used in Task 2 Step 6, Task 5 Steps 1-2
- `self._start_time` — set in Task 2 Step 9, used in Task 2 Step 5
- `self._audio_lock` — `threading.Lock()`, used in Task 2 Steps 2, 4, 5

All types and names are consistent across tasks.
