# Recorder Deepening — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pull audio capture + level metering out of `WispyApp` into a deep `Recorder` module, deduplicating device lookup with `SettingsDialog` and opening the level-metering logic to direct testing.

**Architecture:** `WispyApp` currently owns 7 scattered fields (`recording`, `audio_buffer`, `stream`, `current_level`, `_rms_buf`, `_start_time`, `_audio_lock`) and 5 methods (`_start_recording`, `_open_stream`, `_audio_cb`, `_stop_recording`, `_close_stream`) that form a cohesive recording session. After this refactor, `Recorder` owns the PortAudio stream, the background open/close race, the noise-floor smoothing, and the device lookup. `WispyApp` calls `Recorder.start()` / `Recorder.stop() -> list[ndarray]` / `Recorder.level() -> float`. `SettingsDialog` imports `resolve_device` from `Recorder`.

**Tech Stack:** Python 3.10+, sounddevice, numpy, PyQt6 (overlay calls `level()`)

**Testing:** `pytest` — tests run with `.venv/bin/python -m pytest tests/ -v`.

## Global Constraints

- `Recorder` must NOT import PyQt6 — it owns the PortAudio stream and level math, nothing GUI-related.
- `resolve_device(name, devices=None) -> int | None` is a pure helper: given a device name and a device list, return the index or `None`. The default `devices` arg calls `sounddevice.query_devices()` at runtime.
- `Recorder` exposes `level() -> float` for the overlay's QTimer; it does NOT call `update()` or emit signals.
- MIN_DURATION stays on `WispyApp` — Recorder doesn't know about duration policy.
- `_audio_lock` moves into `Recorder` — all thread safety for the stream is internal.

---

## File Structure

| File | Create/Modify | Responsibility |
|------|---------------|----------------|
| `src/recorder.py` | Create | `Recorder` class + `resolve_device` helper |
| `src/main.py` | Modify | Remove 7 fields + 5 methods; wire in `Recorder` |
| `src/overlay.py` | No change | Overlay calls `recorder.level()` via a getter |
| `tests/test_recorder.py` | Create | All `Recorder` + `resolve_device` tests |
| `tests/test_wispy.py` | No change | Existing CLI tests stay untouched |

---

### Task 1: resolve_device helper

**Files:**
- Create: `src/recorder.py`
- Test: `tests/test_recorder.py`

**Interfaces:**
- Produces: `resolve_device(name: str, devices: list | None = None) -> int | None` — given a device name, returns the index of the first matching input device, or `None` if not found. When `devices` is `None`, calls `sounddevice.query_devices()`.

- [ ] **Step 1: Write the failing test**

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from recorder import resolve_device

def test_resolve_device_found():
    devices = [
        {'name': 'default', 'max_input_channels': 0},
        {'name': 'mic1', 'max_input_channels': 1},
        {'name': 'mic2', 'max_input_channels': 2},
    ]
    assert resolve_device('mic1', devices=devices) == 1

def test_resolve_device_not_found():
    devices = [
        {'name': 'default', 'max_input_channels': 0},
        {'name': 'mic1', 'max_input_channels': 1},
    ]
    assert resolve_device('nonexistent', devices=devices) is None

def test_resolve_device_skips_output_only():
    devices = [
        {'name': 'speaker', 'max_input_channels': 0},
        {'name': 'mic', 'max_input_channels': 1},
    ]
    assert resolve_device('speaker', devices=devices) is None
    assert resolve_device('mic', devices=devices) == 1

def test_resolve_device_empty_name():
    devices = [{'name': 'mic', 'max_input_channels': 1}]
    assert resolve_device('', devices=devices) is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/numair/Projects/wispy && .venv/bin/python -m pytest tests/test_recorder.py::test_resolve_device_found -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'recorder'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/recorder.py

def resolve_device(name, devices=None):
    if not name:
        return None
    if devices is None:
        import sounddevice as sd
        devices = sd.query_devices()
    for i, d in enumerate(devices):
        if d['name'] == name and d['max_input_channels'] > 0:
            return i
    return None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/numair/Projects/wispy && .venv/bin/python -m pytest tests/test_recorder.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/recorder.py tests/test_recorder.py
git commit -m "feat: add resolve_device helper to Recorder"
```

---

### Task 2: Recorder constructor + level() getter

**Files:**
- Modify: `src/recorder.py`
- Modify: `tests/test_recorder.py`

**Interfaces:**
- Consumes: `resolve_device` from Task 1.
- Produces: `Recorder.__init__(device_name: str = "")` — initializes state fields. `Recorder.level() -> float` — returns current smoothed level (0.0 when not recording).

- [ ] **Step 1: Write the failing test**

```python
def test_recorder_initial_level():
    from recorder import Recorder
    r = Recorder()
    assert r.level() == 0.0

def test_recorder_stores_device():
    from recorder import Recorder
    r = Recorder(device_name="mic1")
    assert r.device_name == "mic1"

def test_recorder_elapsed_zero_before_start():
    from recorder import Recorder
    r = Recorder()
    assert r.elapsed() == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/numair/Projects/wispy && .venv/bin/python -m pytest tests/test_recorder.py::test_recorder_initial_level -v
```

Expected: FAIL — `ImportError: cannot import name 'Recorder'`

- [ ] **Step 3: Write minimal implementation**

```python
# Add to src/recorder.py, after resolve_device:

import threading, time

class Recorder:
    def __init__(self, device_name=""):
        self.device_name = device_name
        self._recording = False
        self._audio_buffer = None
        self._stream = None
        self._current_level = 0.0
        self._rms_buf = [0.0] * 20
        self._start_time = 0.0
        self._audio_lock = threading.Lock()

    def level(self):
        return self._current_level

    def elapsed(self):
        if self._start_time == 0.0:
            return 0.0
        return time.monotonic() - self._start_time
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/numair/Projects/wispy && .venv/bin/python -m pytest tests/test_recorder.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/recorder.py tests/test_recorder.py
git commit -m "feat: add Recorder constructor and level() getter"
```

---

### Task 3: Recorder.start() — open stream in background thread

**Files:**
- Modify: `src/recorder.py`
- Modify: `tests/test_recorder.py`

**Interfaces:**
- Consumes: `resolve_device` from Task 1, `Recorder.__init__` from Task 2.
- Produces: `Recorder.start()` — resets state, sets `_recording = True`, spawns background thread to open the PortAudio stream. If the stream open fails, sets `_recording = False` and stores the error. `Recorder.last_error -> str | None` — set if start() failed.

- [ ] **Step 1: Write the failing test**

```python
from unittest.mock import patch, MagicMock

def test_start_sets_recording_flag():
    from recorder import Recorder
    r = Recorder()
    mock_sd = MagicMock()
    mock_stream = MagicMock()
    mock_sd.InputStream.return_value = mock_stream
    mock_sd.query_devices.return_value = []
    with patch("recorder.sd", mock_sd):
        r.start()
    assert r._recording is True
    assert r._audio_buffer == []

def test_start_resolves_device():
    from recorder import Recorder
    r = Recorder(device_name="mic1")
    mock_sd = MagicMock()
    mock_stream = MagicMock()
    mock_sd.InputStream.return_value = mock_stream
    mock_sd.query_devices.return_value = [
        {'name': 'speaker', 'max_input_channels': 0},
        {'name': 'mic1', 'max_input_channels': 1},
    ]
    with patch("recorder.sd", mock_sd):
        r.start()
    # Should pass device=1 to InputStream
    call_kwargs = mock_sd.InputStream.call_args
    assert call_kwargs[1]['device'] == 1 or call_kwargs[1].get('device') == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/numair/Projects/wispy && .venv/bin/python -m pytest tests/test_recorder.py::test_start_sets_recording_flag -v
```

Expected: FAIL — `AttributeError: 'Recorder' object has no attribute 'start'`

- [ ] **Step 3: Write minimal implementation**

```python
# Add to Recorder class:

    def start(self):
        self._audio_buffer = []
        self._current_level = 0.0
        self._rms_buf = [0.0] * 20
        self._start_time = time.monotonic()
        self._recording = True
        self.last_error = None
        threading.Thread(target=self._open_stream, daemon=True).start()

    def _open_stream(self):
        import sounddevice as sd
        try:
            device = resolve_device(self.device_name)
            stream = sd.InputStream(
                callback=self._audio_cb,
                channels=1, samplerate=16000,
                dtype="float32", device=device,
            )
            stream.start()
            with self._audio_lock:
                if not self._recording:
                    stream.stop()
                    stream.close()
                    return
                self._stream = stream
        except Exception as e:
            self._recording = False
            self.last_error = str(e)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/numair/Projects/wispy && .venv/bin/python -m pytest tests/test_recorder.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/recorder.py tests/test_recorder.py
git commit -m "feat: add Recorder.start() with background stream open"
```

---

### Task 4: Recorder._audio_cb — level metering

**Files:**
- Modify: `src/recorder.py`
- Modify: `tests/test_recorder.py`

**Interfaces:**
- Consumes: `Recorder._audio_lock` and state from Task 2.
- Produces: `Recorder._audio_cb(indata, frames, time_info, status)` — appends to buffer under lock, computes smoothed level with 20-sample noise floor. Internal method, tested indirectly.

- [ ] **Step 1: Write the failing test**

```python
import numpy as np

def test_audio_cb_appends_and_levels():
    from recorder import Recorder
    r = Recorder()
    r._recording = True
    r._audio_buffer = []
    # simulate a callback with 100 samples of silence
    data = np.zeros((100, 1), dtype=np.float32)
    r._audio_cb(data, 100, None, None)
    assert len(r._audio_buffer) == 1
    # level should still be 0.0 for silence
    assert r.level() == 0.0

def test_audio_cb_ignores_when_not_recording():
    from recorder import Recorder
    r = Recorder()
    r._recording = False
    r._audio_buffer = []
    data = np.zeros((100, 1), dtype=np.float32)
    r._audio_cb(data, 100, None, None)
    assert len(r._audio_buffer) == 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/numair/Projects/wispy && .venv/bin/python -m pytest tests/test_recorder.py::test_audio_cb_appends_and_levels -v
```

Expected: FAIL — `AttributeError: 'Recorder' object has no attribute '_audio_cb'`

- [ ] **Step 3: Write minimal implementation**

```python
# Add to Recorder class:

    def _audio_cb(self, indata, frames, time_info, status):
        import numpy as np
        with self._audio_lock:
            if not self._recording:
                return
            self._audio_buffer.append(indata.copy())
        rms = float(np.sqrt(np.mean(indata ** 2)))
        self._rms_buf = self._rms_buf[1:] + [rms]
        noise = min(self._rms_buf) if self._rms_buf else rms
        signal = max(rms - noise, 0.0)
        raw = min(signal * 60.0, 1.0) if noise > 0.0001 else 0.0
        self._current_level = self._current_level * 0.55 + raw * 0.45
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/numair/Projects/wispy && .venv/bin/python -m pytest tests/test_recorder.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/recorder.py tests/test_recorder.py
git commit -m "feat: add Recorder._audio_cb with level metering"
```

---

### Task 5: Recorder.stop() — return chunks, async close

**Files:**
- Modify: `src/recorder.py`
- Modify: `tests/test_recorder.py`

**Interfaces:**
- Consumes: All state from Tasks 2-4.
- Produces: `Recorder.stop() -> list[np.ndarray] | None` — under lock, sets `_recording = False`, grabs buffer, returns it. Spawns background thread to close the stream. Returns `None` if not recording.

- [ ] **Step 1: Write the failing test**

```python
def test_stop_returns_buffer():
    from recorder import Recorder
    r = Recorder()
    r._recording = True
    r._audio_buffer = [np.zeros((100, 1), dtype=np.float32) for _ in range(3)]
    r._stream = MagicMock()
    result = r.stop()
    assert result is not None
    assert len(result) == 3
    assert r._recording is False

def test_stop_returns_none_when_not_recording():
    from recorder import Recorder
    r = Recorder()
    r._recording = False
    assert r.stop() is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/numair/Projects/wispy && .venv/bin/python -m pytest tests/test_recorder.py::test_stop_returns_buffer -v
```

Expected: FAIL — `AttributeError: 'Recorder' object has no attribute 'stop'`

- [ ] **Step 3: Write minimal implementation**

```python
# Add to Recorder class:

    def stop(self):
        with self._audio_lock:
            if not self._recording:
                return None
            self._recording = False
            buffer = self._audio_buffer
            self._audio_buffer = None
        stream = self._stream
        self._stream = None
        if stream:
            threading.Thread(target=self._close_stream,
                             args=(stream,), daemon=True).start()
        return buffer

    def _close_stream(self, stream):
        try:
            stream.stop()
            stream.close()
        except Exception:
            pass
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/numair/Projects/wispy && .venv/bin/python -m pytest tests/test_recorder.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/recorder.py tests/test_recorder.py
git commit -m "feat: add Recorder.stop() with async stream close"
```

---

### Task 6: Wire Recorder into WispyApp

**Files:**
- Modify: `src/main.py`
- Modify: `src/overlay.py`

**Interfaces:**
- Consumes: `Recorder` from `src/recorder.py`. `resolve_device` from `src/recorder.py`.
- Produces: `WispyApp` loses 7 fields + 5 methods. `_start_recording` becomes `self.recorder.start()` + overlay show. `_stop_recording` becomes `self.recorder.stop()` + duration check + overlay hide + thread dispatch. `OverlayWindow` gets `level_getter` pointing at `self.recorder.level`.

- [ ] **Step 1: Write the failing guard test**

```python
def test_wispyapp_has_recorder():
    """WispyApp should reference a Recorder instance."""
    import importlib
    import main
    importlib.reload(main)
    # Can't instantiate WispyApp without display, but check the class
    # has _start_recording and _stop_recording methods
    assert hasattr(main.WispyApp, '_start_recording')
    assert hasattr(main.WispyApp, '_stop_recording')
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/numair/Projects/wispy && .venv/bin/python -m pytest tests/test_recorder.py::test_wispyapp_has_recorder -v
```

Expected: PASS (methods already exist) — this is a guard test.

- [ ] **Step 3: Refactor WispyApp**

In `WispyApp.__init__`, replace:
```python
        self.recording = False
        self.audio_buffer: list[np.ndarray] | None = None
        self.stream: sd.InputStream | None = None
        self.current_level = 0.0
        self._rms_buf = [0.0] * 20
        self._start_time = 0.0
        self._audio_lock = threading.Lock()
```
with:
```python
        from recorder import Recorder
        self.recorder = Recorder(device_name=self.config.get("input_device", ""))
```

Update overlay construction:
```python
        from overlay import OverlayWindow
        self.overlay = OverlayWindow(self._stop_recording,
                                     lambda: self.recorder.level())
```

Replace `_start_recording` with:
```python
    def _start_recording(self):
        self.recorder.device_name = self.config.get("input_device", "")
        self.recorder.start()
        self.overlay.reset()
        self.overlay.show()
```

Replace `_stop_recording` with:
```python
    def _stop_recording(self):
        buffer = self.recorder.stop()
        if buffer is None:
            return
        self.overlay.hide()
        elapsed = self.recorder.elapsed()
        if elapsed < MIN_DURATION:
            self.tray.showMessage("Wispy", "Recording too short (min 2s)",
                                  QSystemTrayIcon.MessageIcon.Information, 2000)
            return
        threading.Thread(target=self._transcribe_and_inject,
                         args=(buffer,), daemon=True).start()
```

Remove `_open_stream`, `_audio_cb`, `_close_stream` methods entirely.

In `_on_rec_error`, replace `self.recording = False` with nothing (Recorder handles its own state).

In `quit()`, replace `self._stop_recording()` with `self.recorder.stop()`.

In `SettingsDialog.__init__`, replace the device enumeration loop with:
```python
        from recorder import resolve_device
        import sounddevice as sd
        self.device = QComboBox()
        self.device.addItem("System Default", "")
        for i, d in enumerate(sd.query_devices()):
            if d['max_input_channels'] > 0:
                self.device.addItem(d['name'], d['name'])
```
(Keep the loop for populating the combo box — `resolve_device` is for lookup by name, the dialog still needs to list all input devices.)

- [ ] **Step 4: Run all tests**

```bash
cd /home/numair/Projects/wispy && .venv/bin/python -m pytest tests/ -v
```

Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/main.py
git commit -m "refactor: wire Recorder into WispyApp, remove 7 fields + 3 methods"
```

---

### Task 7: Final verification

**Files:**
- No file changes

- [ ] **Step 1: Run all tests**

```bash
cd /home/numair/Projects/wispy && .venv/bin/python -m pytest tests/ -v
```

Expected: ALL PASS

- [ ] **Step 2: Verify dead code removed**

```bash
cd /home/numair/Projects/wispy && grep -n '_audio_cb\|_open_stream\|_close_stream\|_rms_buf' src/main.py
```

Expected: no output

- [ ] **Step 3: Verify new module is importable**

```bash
cd /home/numair/Projects/wispy && PYTHONPATH=src .venv/bin/python -c "from recorder import Recorder, resolve_device; r = Recorder(); print('level:', r.level()); print('resolve:', resolve_device('', devices=[])); print('ok')"
```

Expected: `level: 0.0`, `resolve: None`, `ok`
