# Cloud-First Transcription with Parallel Local Race + Background Backoff

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the race-based hybrid mode with cloud-first transcription that races local processing against cloud retries in parallel. First result to arrive wins. Background retry continues after local injection for clipboard upgrade.

**Architecture:** Try cloud first. On connection error, start local transcription in a thread and simultaneously retry cloud with short backoff (1s, 2s). Whichever finishes first — local or cloud retry — is returned. If local wins, background retry continues with longer backoff (4s→60s, up to 8 more attempts) for clipboard upgrade. Other API errors (auth, rate limit) → local fallback, no retry.

**Tech Stack:** Python, groq SDK, faster-whisper (local fallback), PyQt6 (overlay)

## Global Constraints

- Tests run with `.venv/bin/python tests/test_wispy.py`, not pytest
- No new dependencies
- Text is injected exactly once. Never replace injected text. Clipboard-only upgrade.
- No arbitrary timeouts — connection errors trigger the parallel race, not elapsed time
- Overlay transitions: recording → transcribing → hide (normal) or recording → transcribing → corrected → hide (retry success)

---

### Task 1: Add connection error detection to Transcriber

**Files:**
- Modify: `src/transcriber.py`
- Test: `tests/test_wispy.py`

**Interfaces:**
- Produces: `Transcriber._is_connection_error(exc) -> bool`

- [ ] **Step 1: Add `_is_connection_error` method**

In `transcriber.py`, add after `__init__`:

```python
def _is_connection_error(self, exc):
    """True for network-level failures worth retrying."""
    import groq
    return isinstance(exc, (groq.APIConnectionError, groq.APITimeoutError))
```

- [ ] **Step 2: Add test**

In `tests/test_wispy.py`:

```python
def test_is_connection_error():
    import groq
    t = Transcriber(api_key="x", model="x")
    assert t._is_connection_error(groq.APIConnectionError(request=None, body=None)) is True
    assert t._is_connection_error(groq.APITimeoutError(request=None, body=None)) is True
    assert t._is_connection_error(groq.AuthenticationError(message="x", response=None, body=None)) is False
    assert t._is_connection_error(groq.RateLimitError(message="x", response=None, body=None)) is False
    assert t._is_connection_error(Exception("generic")) is False
```

- [ ] **Step 3: Run tests** — `.venv/bin/python tests/test_wispy.py`
- [ ] **Step 4: Commit** — `git commit -m "feat: add connection error classification to Transcriber"`

---

### Task 2: Replace `_race_hybrid` with cloud-first + parallel local race

**Files:**
- Modify: `src/transcriber.py`
- Test: `tests/test_wispy.py`

**Interfaces:**
- Removes: `_race_hybrid()` method
- Produces: `Transcriber.transcribe_cloud_first(wav_bytes, chunks) -> tuple[str, bool]` — tries cloud, on connection error races local vs cloud retries. Returns (text, used_local_fallback).
- Produces: `Transcriber.retry_cloud_async(wav_bytes, on_success, on_fail)` — background retry with exponential backoff

- [ ] **Step 1: Add constants**

At the top of `transcriber.py`, after imports:

```python
import threading
import time
import random

# Fast cloud retries: race against local processing
FAST_RETRY_BACKOFF = [1.0, 2.0]

# Background retry: continues after local wins, longer backoff
BG_INITIAL_BACKOFF = 4.0
BG_MAX_BACKOFF = 60.0
BG_MAX_ATTEMPTS = 8
```

- [ ] **Step 2: Implement `transcribe_cloud_first`**

Replace `_race_hybrid` with:

```python
def transcribe_cloud_first(self, wav_bytes, chunks):
    """Try cloud first. On connection error, race local vs cloud retries.
    Returns (text, used_local_fallback)."""
    # First cloud attempt
    try:
        return self._whisper(wav_bytes), False
    except Exception as e:
        if not self._is_connection_error(e):
            if isinstance(e, GroqError):
                return self._transcribe_local(chunks), True
            raise

    # Connection error — start local in parallel, retry cloud
    local_result = [None]
    local_done = threading.Event()
    def run_local():
        try:
            local_result[0] = self._transcribe_local(chunks)
        finally:
            local_done.set()
    local_thread = threading.Thread(target=run_local, daemon=True)
    local_thread.start()

    # Fast cloud retries — race against local
    for backoff in FAST_RETRY_BACKOFF:
        local_done.wait(timeout=backoff)
        if local_done.is_set():
            return local_result[0], True
        try:
            return self._whisper(wav_bytes), False
        except Exception as e:
            if not self._is_connection_error(e):
                if isinstance(e, GroqError):
                    local_done.wait()
                    return local_result[0], True
                raise

    # Fast retries exhausted — wait for local
    local_done.wait()
    return local_result[0], True
```

- [ ] **Step 3: Implement `retry_cloud_async`**

```python
def retry_cloud_async(self, wav_bytes, on_success, on_fail):
    """Background retry with exponential backoff after local wins."""
    def _retry():
        backoff = BG_INITIAL_BACKOFF
        for attempt in range(BG_MAX_ATTEMPTS):
            time.sleep(backoff + random.uniform(0, backoff * 0.3))
            try:
                text = self._whisper(wav_bytes)
                if text:
                    on_success(text)
                    return
            except Exception as e:
                if not self._is_connection_error(e):
                    on_fail()
                    return
            backoff = min(backoff * 2, BG_MAX_BACKOFF)
        on_fail()
    threading.Thread(target=_retry, daemon=True).start()
```

- [ ] **Step 4: Update `transcribe` method**

Replace the `transcribe` method body:

```python
def transcribe(self, chunks):
    if not chunks or len(chunks) < 5:
        raise InvalidAudioError("Recording too short")

    if self.engine_mode == "offline":
        return self._clean(self._transcribe_local(chunks))

    if not self.api_key:
        raise MissingKeyError("Set GROQ_API_KEY in Settings or env")

    wav_bytes = encode_wav(chunks)

    if self.engine_mode == "hybrid":
        text, used_local = self.transcribe_cloud_first(wav_bytes, chunks)
        return self._clean(text)

    return self._clean(self._whisper(wav_bytes))
```

- [ ] **Step 5: Remove `_race_hybrid` entirely**

- [ ] **Step 6: Add tests**

```python
def test_cloud_first_cloud_success():
    t = Transcriber(api_key="test", model="whisper-large-v3-turbo")
    t._whisper = lambda wav, timeout=None: "cloud result"
    text, used_local = t.transcribe_cloud_first(b"fake-wav", [1, 2, 3, 4, 5])
    assert text == "cloud result"
    assert used_local is False


def test_cloud_first_local_wins_race():
    """Connection errors → local processes while cloud retries → local wins."""
    import groq
    import transcriber as tm

    call_count = [0]
    def failing_whisper(wav, timeout=None):
        call_count[0] += 1
        raise groq.APIConnectionError(request=None, body=None)

    t = Transcriber(api_key="test", model="whisper-large-v3-turbo")
    t._whisper = failing_whisper
    t._transcribe_local = lambda chunks: "local wins"

    old_backoff = tm.FAST_RETRY_BACKOFF
    tm.FAST_RETRY_BACKOFF = [0.01, 0.01]
    try:
        text, used_local = t.transcribe_cloud_first(b"fake-wav", [1, 2, 3, 4, 5])
        assert text == "local wins"
        assert used_local is True
        assert call_count[0] == 3  # initial + 2 fast retries
    finally:
        tm.FAST_RETRY_BACKOFF = old_backoff


def test_cloud_first_cloud_wins_during_retry():
    """Connection error then cloud recovers during fast retry."""
    import groq
    import transcriber as tm

    call_count = [0]
    def recovering_whisper(wav, timeout=None):
        call_count[0] += 1
        if call_count[0] == 1:
            raise groq.APIConnectionError(request=None, body=None)
        return "cloud recovered"

    t = Transcriber(api_key="test", model="whisper-large-v3-turbo")
    t._whisper = recovering_whisper
    t._transcribe_local = lambda chunks: "local"

    old_backoff = tm.FAST_RETRY_BACKOFF
    tm.FAST_RETRY_BACKOFF = [0.01, 2.0]
    try:
        text, used_local = t.transcribe_cloud_first(b"fake-wav", [1, 2, 3, 4, 5])
        assert text == "cloud recovered"
        assert used_local is False
        assert call_count[0] == 2
    finally:
        tm.FAST_RETRY_BACKOFF = old_backoff
```

- [ ] **Step 7: Run tests** — `.venv/bin/python tests/test_wispy.py`
- [ ] **Step 8: Commit** — `git commit -m "feat: replace race hybrid with cloud-first + parallel local race"`

---

### Task 3: Wire hybrid mode in main.py with retry + clipboard upgrade

**Files:**
- Modify: `src/main.py`
- Modify: `src/overlay.py`
- Test: `tests/test_wispy.py`

**Interfaces:**
- New signal: `WispyApp._corrected = pyqtSignal()` — emitted on background retry success
- Overlay: `set_state("corrected")` — green dot, auto-hides after 2s

- [ ] **Step 1: Add `_corrected` signal**

In `main.py`, add to WispyApp signals:

```python
_corrected = pyqtSignal()
```

Connect in `__init__`:

```python
self._corrected.connect(self._on_corrected)
```

Add handler:

```python
def _on_corrected(self):
    self.overlay.set_state("corrected")
    QTimer.singleShot(2000, self.overlay.hide)
```

- [ ] **Step 2: Add "corrected" state to overlay**

In `overlay.py`, accept "corrected" in `set_state`. In paint, dot color:

```python
dot_color = QColor(76, 175, 80) if self.state == "corrected" else QColor(*ap["dot_color"])
```

- [ ] **Step 3: Update `_transcribe_and_inject`**

Replace the method:

```python
def _transcribe_and_inject(self, buffer):
    try:
        import time
        from transcriber import Transcriber
        from exceptions import InvalidAudioError
        from injector import Injector
        if not buffer:
            return
        t = Transcriber(
            api_key=self.config.get("groq_api_key")
                or os.environ.get("GROQ_API_KEY", ""),
            model=self.config.get("groq_model", MODELS[0]),
            language=self.config.get("language") or None,
            clean=self.config.get("clean_text", False),
            engine_mode=self.config.get("engine_mode", "online"),
            local_model=self.config.get("local_model", LOCAL_MODELS[0]),
            whisper_prompt=self.config.get("whisper_prompt", ""),
            clean_prompt=self.config.get("clean_prompt", ""),
        )
        inj = Injector()
        try:
            from recorder import encode_wav
            output_mode = self.config.get("output_mode", "paste")
            used_local = False

            if self.config.get("engine_mode") == "hybrid" and t.api_key:
                wav_bytes = encode_wav(buffer)
                text, used_local = t.transcribe_cloud_first(wav_bytes, buffer)
                text = t._clean(text)
            else:
                text = t.transcribe(buffer)

            if not text:
                return
            self._set_clipboard.emit(text)
            self._transcribe_finished.emit()

            if output_mode == "paste":
                time.sleep(0.15)
                inj.inject(text, mode=output_mode, send_enter=self.config.get("send_enter", False))

            # Local won — start background cloud retry for clipboard upgrade
            if used_local and t.api_key:
                wav_bytes = encode_wav(buffer)

                def on_retry_success(cloud_text):
                    cleaned = t._clean(cloud_text)
                    self._set_clipboard.emit(cleaned)
                    self._corrected.emit()

                def on_retry_fail():
                    pass  # local result stands

                t.retry_cloud_async(wav_bytes, on_retry_success, on_retry_fail)

        except InvalidAudioError:
            pass
        except Exception as e:
            self._notify.emit("Wispy", str(e))
    finally:
        self._transcribe_finished.emit()
```

`ponytail: double encode_wav in hybrid path, cache if profiling matters.`

- [ ] **Step 4: Add test**

```python
def test_corrected_signal_exists():
    from main import WispyApp
    assert hasattr(WispyApp, '_corrected')
```

- [ ] **Step 5: Run tests** — `.venv/bin/python tests/test_wispy.py`
- [ ] **Step 6: Commit** — `git commit -m "feat: wire parallel race + background retry + clipboard upgrade"`

---

### Task 4: Manual end-to-end verification

- [ ] **Step 1: Happy path** — Record short phrase, cloud succeeds immediately, text injected, overlay hides.
- [ ] **Step 2: WiFi drop → cloud recovers during retry** — Disconnect WiFi, record, reconnect within ~3s. Cloud result injected, no local fallback.
- [ ] **Step 3: WiFi drop → local wins, background upgrade** — Disconnect WiFi, record, keep off >5s. Local text injected. Reconnect WiFi. Clipboard upgrades, green dot flashes.
- [ ] **Step 4: Long recording + WiFi drop** — Record 5+ minutes, disconnect WiFi. Local processes in parallel, fires when ready. Background retry upgrades if WiFi returns.
- [ ] **Step 5: Offline mode** — Set engine_mode to "offline", verify local-only with no cloud attempts.
- [ ] **Step 6: Commit** — `git commit -m "feat: cloud-first transcription with parallel local race"`
