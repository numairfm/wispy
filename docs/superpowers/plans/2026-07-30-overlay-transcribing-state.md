# Overlay Transcribing State & Prompt Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep the Wispy overlay window open after recording stops, displaying a "Transcribing..." status until text injection completes, ignore hotkey triggers while transcribing, and remove prompt bias contamination from Whisper.

**Architecture:** Add state machine (`"recording"`, `"transcribing"`, `"idle"`) to `OverlayWindow` in `src/overlay.py`. Emit thread-safe PyQt signals in `WispyApp` (`src/main.py`) to trigger state changes and window hiding upon completion/error. Replace hardcoded test prompt in `DEFAULT_WHISPER_PROMPT` in `src/transcriber.py`.

**Tech Stack:** Python 3, PyQt6 (QTimer, QPainter, pyqtSignal), sounddevice, Groq API.

## Global Constraints

- Python 3.9+ with PyQt6.
- All GUI operations (`overlay.show()`, `overlay.hide()`, `overlay.set_state()`) MUST execute on the main Qt event thread via PyQt signals or Qt slot connections.
- Existing test suite `.venv/bin/python tests/test_wispy.py` must pass at every task.
- Follow existing code conventions in `src/overlay.py`, `src/main.py`, and `src/transcriber.py`.

---

### Task 1: Prompt Bias Cleanup

**Files:**
- Modify: `src/transcriber.py:11-14`
- Test: `tests/test_wispy.py:23-26,39-43`

**Interfaces:**
- Consumes: None
- Produces: `DEFAULT_WHISPER_PROMPT` equal to `""`

- [ ] **Step 1: Write the failing test**

Edit `tests/test_wispy.py` to assert `DEFAULT_WHISPER_PROMPT == ""`.

```python
def test_whisper_prompt_default():
    assert isinstance(DEFAULT_WHISPER_PROMPT, str)
    assert DEFAULT_WHISPER_PROMPT == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python tests/test_wispy.py`
Expected: FAIL with `AssertionError: assert 'Open the file at slash goal...' == ''`

- [ ] **Step 3: Update `DEFAULT_WHISPER_PROMPT` in `src/transcriber.py`**

```python
DEFAULT_WHISPER_PROMPT = ""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python tests/test_wispy.py`
Expected: PASS ("All tests passed.")

- [ ] **Step 5: Commit changes**

```bash
rtk git add src/transcriber.py tests/test_wispy.py
rtk git commit -m "fix(transcriber): remove prompt bias contamination from DEFAULT_WHISPER_PROMPT"
```

---

### Task 2: Overlay Transcribing UI State

**Files:**
- Modify: `src/overlay.py:63-180`
- Test: `tests/test_wispy.py`

**Interfaces:**
- Consumes: None
- Produces: `OverlayWindow.set_state(state: str)`, `OverlayWindow.state` property (`"recording"`, `"transcribing"`, `"idle"`)

- [ ] **Step 1: Write the failing test**

Add `test_overlay_states()` in `tests/test_wispy.py`:

```python
def test_overlay_states():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from overlay import OverlayWindow
    ov = OverlayWindow(on_stop=lambda: None, level_getter=lambda: 0.0)
    assert ov.state == "recording"
    ov.set_state("transcribing")
    assert ov.state == "transcribing"
    ov.reset()
    assert ov.state == "recording"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python tests/test_wispy.py`
Expected: FAIL with `AttributeError: 'OverlayWindow' object has no attribute 'state'`

- [ ] **Step 3: Implement overlay state management and rendering**

In `src/overlay.py`:

1. In `OverlayWindow.__init__`, set `self.state = "recording"`.
2. Add method `set_state(self, state: str)`:
```python
def set_state(self, state: str):
    self.state = state
    self.update()
```
3. In `reset(self)`: set `self.state = "recording"`, reset levels and `elapsed_ticks`, start timer.
4. In `paintEvent(self, event)`:
   - If `self.state == "transcribing"`:
     - Draw pill background.
     - Draw pulsing blue dot at `lay["dot_x"]` with color `[100, 160, 255]`.
     - Draw text `"Transcribing…"` centered horizontally between `lay["wf_l"]` and `lay["bt_x"]`, using white color with pulsing alpha `int(160 + 75 * math.sin(self.elapsed_ticks * 0.15))`.
     - Skip drawing waveform bars, duration timer, and stop button.
   - Else (for `"recording"`): render standard waveform, timer, and stop button.
5. In `mousePressEvent(self, event)`:
   - If `self.state == "transcribing"`, return without triggering `on_stop` or system move.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python tests/test_wispy.py`
Expected: PASS ("All tests passed.")

- [ ] **Step 5: Commit changes**

```bash
rtk git add src/overlay.py tests/test_wispy.py
rtk git commit -m "feat(overlay): add transcribing state visual rendering and state machine"
```

---

### Task 3: Application Lifecycle & Thread-Safe Signal Integration

**Files:**
- Modify: `src/main.py:623-800`
- Test: `tests/test_wispy.py`

**Interfaces:**
- Consumes: `OverlayWindow.set_state`, `OverlayWindow.state`
- Produces: Thread-safe transcription completion handling, guarded `toggle_overlay`

- [ ] **Step 1: Write the failing test**

Add `test_toggle_ignored_during_transcribing()` in `tests/test_wispy.py`:

```python
def test_toggle_ignored_during_transcribing():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from main import WispyApp
    wispy_app = WispyApp()
    wispy_app.overlay.set_state("transcribing")
    wispy_app.overlay.show()
    # toggle_overlay should be ignored when state is transcribing
    wispy_app.toggle_overlay()
    assert wispy_app.overlay.isVisible()
    assert wispy_app.overlay.state == "transcribing"
    wispy_app.overlay.hide()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python tests/test_wispy.py`
Expected: FAIL because `toggle_overlay()` currently calls `_stop_recording()` when visible regardless of state.

- [ ] **Step 3: Update `WispyApp` in `src/main.py`**

1. Add signals and slot:
```python
_transcribe_finished = pyqtSignal()
```
In `__init__`:
```python
self._transcribe_finished.connect(self._on_transcribe_finished)
```
Add handler:
```python
def _on_transcribe_finished(self):
    self.overlay.hide()
    self.overlay.set_state("recording")
```

2. Update `toggle_overlay(self)`:
```python
def toggle_overlay(self):
    if self.overlay.state == "transcribing":
        return
    if self.overlay.isVisible():
        self._stop_recording()
    else:
        self._start_recording()
```

3. Update `_stop_recording(self)`:
```python
def _stop_recording(self):
    buffer = self.recorder.stop()
    if buffer is None:
        return
    elapsed = self.recorder.elapsed()
    if elapsed < MIN_DURATION:
        self.overlay.hide()
        if self.config.get("notify_short_recording", True):
            self.tray.showMessage("Wispy", "Recording too short (min 2s)",
                                  QSystemTrayIcon.MessageIcon.Information, 2000)
        return
    self.overlay.set_state("transcribing")
    threading.Thread(target=self._transcribe_and_inject,
                     args=(buffer,), daemon=True).start()
```

4. Update `_transcribe_and_inject(self, buffer)`:
Wrap transcription/injection in `try...finally`:
```python
def _transcribe_and_inject(self, buffer):
    try:
        from transcriber import Transcriber
        from exceptions import InvalidAudioError
        from injector import Injector
        if not buffer:
            return
        t = Transcriber(...)
        inj = Injector()
        try:
            text = t.transcribe(buffer)
            if not text:
                return
            if self.config.get("copy_to_clipboard"):
                self._set_clipboard.emit(text)
            inj.inject(text, send_enter=self.config.get("send_enter", False))
        except InvalidAudioError:
            pass
        except Exception as e:
            self._notify.emit("Wispy", str(e))
    finally:
        self._transcribe_finished.emit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python tests/test_wispy.py`
Expected: PASS ("All tests passed.")

- [ ] **Step 5: Commit changes**

```bash
rtk git add src/main.py tests/test_wispy.py
rtk git commit -m "feat(app): keep overlay visible during transcription and handle completion via signals"
```

---

### Task 4: Complete Test Suite Verification

- [ ] **Step 1: Run complete test suite**

Run: `.venv/bin/python tests/test_wispy.py`
Expected: All tests pass cleanly.

- [ ] **Step 2: Commit any remaining changes**

```bash
rtk git status
```
Ensure working tree is clean.
