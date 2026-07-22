# Streaming Transcription Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Slice audio on natural pauses (~1s silence), transcribe each slice independently while recording continues, and integrate stop keyword detection with pause-based stopping.

**Architecture:** Recorder detects silence in the audio callback and emits a pause event with the accumulated slice. WispyApp dispatches each slice for transcription in a background thread, queues results for ordered injection, and checks for stop keywords to trigger recording stop on the next pause.

**Tech Stack:** Python, PyQt6, sounddevice, numpy, groq/faster-whisper

## Global Constraints

- Python 3.14+, PyQt6>=6.5, sounddevice>=0.4.6, numpy>=1.24
- No new dependencies — uses existing threading, queue, and signal mechanisms
- All audio processing stays in the PortAudio callback thread; transcription dispatched to daemon threads
- Injection remains sequential via ydotool — no concurrent calls

---

### Task 1: Add pause detection to Recorder

**Files:**
- Modify: `src/recorder.py`

**Interfaces:**
- Produces: `Recorder.on_pause` callback attribute, `Recorder.SILENCE_THRESHOLD`, `Recorder.PAUSE_DURATION`

- [ ] **Step 1: Add pause detection constants and state**

Add to `Recorder.__init__`:
```python
self._slice_buffer = []
self._silence_start = None
self.on_pause = None
```

Add class constants:
```python
SILENCE_THRESHOLD = 0.01
PAUSE_DURATION = 1.0
```

- [ ] **Step 2: Modify `_audio_cb` to detect pauses and emit slices**

Replace `_audio_cb` with:
```python
def _audio_cb(self, indata, frames, time_info, status):
    with self._audio_lock:
        if not self._recording:
            return
        self._audio_buffer.append(indata.copy())
        self._slice_buffer.append(indata.copy())
    rms = float(np.sqrt(np.mean(indata ** 2)))
    self._rms_buf = self._rms_buf[1:] + [rms]
    noise = min(self._rms_buf) if self._rms_buf else rms
    signal = max(rms - noise, 0.0)
    raw = min(signal * 60.0, 1.0) if noise > 0.0001 else 0.0
    self._current_level = self._current_level * 0.55 + raw * 0.45

    # pause detection
    now = time.monotonic()
    if self._current_level < self.SILENCE_THRESHOLD:
        if self._silence_start is None:
            self._silence_start = now
        elif now - self._silence_start >= self.PAUSE_DURATION:
            if self._slice_buffer and self.on_pause:
                slice_data = list(self._slice_buffer)
                self._slice_buffer = []
                self._silence_start = None
                self.on_pause(slice_data)
    else:
        self._silence_start = None
```

- [ ] **Step 3: Reset slice state in `start`**

Add to `Recorder.start`:
```python
self._slice_buffer = []
self._silence_start = None
```

- [ ] **Step 4: Flush remaining slice in `stop`**

Add to `Recorder.stop` before returning buffer — return both full buffer and any remaining slice:
```python
remaining_slice = list(self._slice_buffer) if self._slice_buffer else []
self._slice_buffer = []
```
Change return to `return buffer, remaining_slice`.

Update callers in `main.py` (`_stop_recording`) to unpack the tuple.

- [ ] **Step 5: Verify**

Run `python -c "from recorder import Recorder; r = Recorder(); print(r.SILENCE_THRESHOLD, r.PAUSE_DURATION)"` — expect `0.01 1.0`.

---

### Task 2: Wire up slice transcription in WispyApp

**Files:**
- Modify: `src/main.py`

**Interfaces:**
- Consumes: `Recorder.on_pause` callback, `Transcriber.transcribe(chunks)`
- Produces: `_on_pause(chunks)`, `_transcribe_slice(chunks)`, `_injection_queue`

- [ ] **Step 1: Add imports and state to WispyApp.__init__**

Add import at top of file:
```python
import queue
```

Add to `WispyApp.__init__` after `self._running = True`:
```python
self._pending_keyword = False
self._injection_queue = queue.Queue()
self._injection_lock = threading.Lock()
```

- [ ] **Step 2: Set on_pause callback after recorder creation**

After `self.recorder = Recorder(...)`:
```python
self.recorder.on_pause = self._on_pause
```

- [ ] **Step 3: Implement `_on_pause`**

```python
def _on_pause(self, slice_data):
    """Called from audio thread on pause detection. Must not block."""
    threading.Thread(target=self._transcribe_slice,
                     args=(slice_data,), daemon=True).start()
```

- [ ] **Step 4: Implement `_transcribe_slice`**

```python
def _transcribe_slice(self, chunks):
    from transcriber import Transcriber
    from exceptions import InvalidAudioError
    from injector import check_stop_keyword
    if not chunks:
        return
    t = Transcriber(
        api_key=self.config.get("groq_api_key")
            or os.environ.get("GROQ_API_KEY", ""),
        model=self.config.get("groq_model", MODELS[0]),
        language=self.config.get("language") or None,
        clean=self.config.get("clean_text", False),
        engine_mode=self.config.get("engine_mode", "online"),
        local_model=self.config.get("local_model", LOCAL_MODELS[0]),
    )
    try:
        text = t.transcribe(chunks)
        if not text:
            return
        keyword = self.config.get("stop_keyword", "")
        text, should_send = check_stop_keyword(text, keyword)
        if should_send:
            self._pending_keyword = True
        self._injection_queue.put((text, should_send))
        self._process_injection_queue()
    except InvalidAudioError:
        pass
    except Exception as e:
        self._notify.emit("Wispy", str(e))
```

- [ ] **Step 5: Implement `_process_injection_queue`**

```python
def _process_injection_queue(self):
    from injector import Injector
    with self._injection_lock:
        inj = Injector()
        while not self._injection_queue.empty():
            text, should_send = self._injection_queue.get_nowait()
            if self.config.get("copy_to_clipboard"):
                self._set_clipboard.emit(text)
            inj.inject(text, press_enter=should_send)
```

- [ ] **Step 6: Update `_stop_recording` to handle new return value and flush**

Update `_stop_recording` to unpack tuple from `recorder.stop()` and flush remaining audio through the slice pipeline:
```python
def _stop_recording(self):
    self._pending_keyword = False
    result = self.recorder.stop()
    if result is None:
        return
    buffer, remaining_slice = result
    self.overlay.hide()
    elapsed = self.recorder.elapsed()
    if elapsed < MIN_DURATION:
        self.tray.showMessage("Wispy", "Recording too short (min 2s)",
                              QSystemTrayIcon.MessageIcon.Information, 2000)
        return
    # ponytail: flush remaining audio through slice pipeline
    full = (buffer or []) + (remaining_slice or [])
    if full:
        threading.Thread(target=self._transcribe_slice,
                         args=(full,), daemon=True).start()
```

- [ ] **Step 7: Verify**

Run `python -c "from main import WispyApp"` — expect no import errors.

---

### Task 3: Integrate stop keyword with pause-based stopping

**Files:**
- Modify: `src/main.py`

**Interfaces:**
- Consumes: `_pending_keyword` flag, `Recorder.on_pause`
- Produces: Stop recording on next pause after keyword

- [ ] **Step 1: Add stop check to `_on_pause`**

Modify `_on_pause` to check pending keyword before dispatching transcription:
```python
def _on_pause(self, slice_data):
    """Called from audio thread on pause detection. Must not block."""
    if self._pending_keyword:
        self._pending_keyword = False
        QTimer.singleShot(0, self._handle_keyword_stop)
    threading.Thread(target=self._transcribe_slice,
                     args=(slice_data,), daemon=True).start()
```

Add import at top of main.py:
```python
from PyQt6.QtCore import QTimer
```

- [ ] **Step 2: Implement `_handle_keyword_stop`**

```python
def _handle_keyword_stop(self):
    if self.overlay.isVisible():
        self._stop_recording()
```

- [ ] **Step 3: Reset pending keyword on manual stop**

Add to `_stop_recording` at the start:
```python
self._pending_keyword = False
```

- [ ] **Step 4: Verify**

Run `python -c "from main import WispyApp"` — expect no import errors.

---

### Task 4: Add "Transcribing..." state to overlay

**Files:**
- Modify: `src/overlay.py`

**Interfaces:**
- Consumes: `OverlayWindow.set_transcribing(bool)`
- Produces: Visual indicator during transcription

- [ ] **Step 1: Add transcribing state**

Add to `OverlayWindow.__init__`:
```python
self._transcribing = False
```

- [ ] **Step 2: Add `set_transcribing` method**

```python
def set_transcribing(self, active):
    self._transcribing = active
    self.update()
```

- [ ] **Step 3: Paint transcribing indicator in `paintEvent`**

After the waveform bars section, before the timer section, add:
```python
# transcribing indicator
if self._transcribing:
    p.setPen(QColor(255, 255, 255, 100))
    p.setFont(QFont("monospace", 7))
    p.drawText(_TM_L, 0, _TM_W, _H,
               Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter,
               "···")
```

- [ ] **Step 4: Wire up transcribing state in WispyApp**

In `_transcribe_slice`, add at start:
```python
self.overlay.set_transcribing.emit(True) if hasattr(self, 'overlay') else None
```
And at end (in finally block or after try/except):
```python
self.overlay.set_transcribing.emit(False) if hasattr(self, 'overlay') else None
```

Since `set_transcribing` is called from a background thread, make it thread-safe by using a signal:

Add to `OverlayWindow` class body (class-level):
```python
_transcribing_signal = pyqtSignal(bool)
```

In `__init__`:
```python
self._transcribing_signal.connect(self._on_transcribing)
```

```python
def _on_transcribing(self, active):
    self._transcribing = active
    self.update()
```

In `_transcribe_slice` (main.py):
```python
self.overlay._transcribing_signal.emit(True)
# ... transcribe ...
self.overlay._transcribing_signal.emit(False)
```

- [ ] **Step 5: Verify**

Run `python -c "from overlay import OverlayWindow"` — expect no import errors.

---

### Task 5: Fix extra spaces in local transcriber

**Files:**
- Modify: `src/local_transcriber.py`

- [ ] **Step 1: Add regex cleanup to transcribe method**

In `LocalTranscriber.transcribe`, after joining segments, add:
```python
import re
text = " ".join(seg.text for seg in segments).strip()
text = re.sub(r'  +', ' ', text)
```

Replace the existing:
```python
text = " ".join(seg.text for seg in segments).strip()
```

- [ ] **Step 2: Verify**

Run `python -c "from local_transcriber import LocalTranscriber"` — expect no import errors.

---

### Task 6: End-to-end verification

- [ ] **Step 1: Run existing tests**

Run: `.venv/bin/python tests/test_wispy.py`
Expected: All tests passed.

- [ ] **Step 2: Run the server and test manually**

Run: `./scripts/wispy.sh server`
- Toggle recording, speak a sentence, pause1s → should see transcription appear
- Speak another sentence with stop keyword, pause → recording should stop
- Verify no extra spaces in local model output
