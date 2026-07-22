# Transcriber Deepening — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pull the transcription pipeline out of `WispyApp` into a deep `Transcriber` module and an adjacent `Injector` module, opening the first real test path for the entire pipeline.

**Architecture:** `WispyApp` currently owns WAV encoding, two Groq API calls, a 5-word gate, clipboard emission, and a ydotool subprocess in a single 60-line `_transcribe_and_inject` method with four nested try/excepts and no test surface. After this refactor, `Transcriber` owns WAV encoding + Groq Whisper + clean-text gate and raises typed exceptions; `Injector` owns ydotool + clipboard behind a seam. `WispyApp` calls `transcriber.transcribe(chunks)` then `injector.inject(text)` — errors arrive as exception types, not Qt signal strings.

**Tech Stack:** Python 3.10+, groq SDK, numpy, PyQt6 (for `Injector` clipboard only)

**Testing:** `pytest` — no new dependencies; tests run with `.venv/bin/python -m pytest tests/ -v`.

## Global Constraints

- `Transcriber` must not import PyQt6 — it's a pure function of its inputs.
- `Injector` imports PyQt6 only for `QApplication.clipboard()` — `inject()` uses subprocess, no Qt.
- Config dict must NOT cross the seam; `WispyApp` passes only the fields each module needs.
- `TranscribeError` hierarchy lives in `src/exceptions.py`; no new top-level files beyond these two modules.

---

## File Structure

| File | Create/Modify | Responsibility |
|------|---------------|----------------|
| `src/exceptions.py` | Create | `TranscribeError` hierarchy |
| `src/transcriber.py` | Create | `Transcriber` class — WAV encode + Groq Whisper + clean-text gate |
| `src/injector.py` | Create | `Injector` class — `inject(text)` via ydotool + `copy(text)` via clipboard |
| `src/main.py` | Modify | Remove `_transcribe_and_inject` + `_clean_text`; wire in `Transcriber` + `Injector` |
| `tests/test_transcriber.py` | Create | All `Transcriber` + `Injector` tests |
| `tests/test_wispy.py` | No change | Existing CLI tests stay untouched |

---

### Task 1: Define the exception hierarchy

**Files:**
- Create: `src/exceptions.py`
- Test: `tests/test_transcriber.py`

**Interfaces:**
- Produces: `TranscribeError`, `MissingKeyError`, `GroqError`, `InvalidAudioError` — all subclasses; `TranscribeError` is the parent. Later tasks catch `TranscribeError` at the `WispyApp` boundary.

- [ ] **Step 1: Write the failing test**

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from exceptions import (
    TranscribeError, MissingKeyError, GroqError, InvalidAudioError,
)

def test_hierarchy():
    assert issubclass(MissingKeyError, TranscribeError)
    assert issubclass(GroqError, TranscribeError)
    assert issubclass(InvalidAudioError, TranscribeError)

def test_hierarchy_not_each_other():
    assert not issubclass(MissingKeyError, GroqError)
    assert not issubclass(GroqError, InvalidAudioError)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/numair/Projects/wispy && .venv/bin/python -m pytest tests/test_transcriber.py::test_hierarchy -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'exceptions'`

- [ ] **Step 3: Write minimal implementation**

```python
class TranscribeError(Exception):
    pass

class MissingKeyError(TranscribeError):
    pass

class GroqError(TranscribeError):
    pass

class InvalidAudioError(TranscribeError):
    pass
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/numair/Projects/wispy && .venv/bin/python -m pytest tests/test_transcriber.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/exceptions.py tests/test_transcriber.py
git commit -m "feat: add TranscribeError exception hierarchy"
```

---

### Task 2: Transcriber — WAV encoding

**Files:**
- Create: `src/transcriber.py`
- Modify: `tests/test_transcriber.py`

**Interfaces:**
- Consumes: `exceptions.py` from Task 1.
- Produces: `Transcriber.__init__(api_key, model, language, clean)` — plain fields, no config dict. `Transcriber._encode_wav(chunks) -> bytes` — static/instance method, internal; later called by `transcribe()`.

- [ ] **Step 1: Write the failing test**

```python
import numpy as np
import wave, io

def test_encode_wav_shape():
    """WAV bytes should be valid 16kHz mono int16."""
    from transcriber import Transcriber
    t = Transcriber(api_key="x", model="m", language=None, clean=False)
    # 1 second of silence at 16kHz, float32
    chunk = np.zeros((16000, 1), dtype=np.float32)
    wav_bytes = t._encode_wav([chunk])
    assert isinstance(wav_bytes, bytes)
    # decode and verify
    buf = io.BytesIO(wav_bytes)
    with wave.open(buf, 'rb') as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 16000
        frames = wf.readframes(wf.getnframes())
    assert len(frames) == 16000 * 2  # 16000 samples * 2 bytes
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/numair/Projects/wispy && .venv/bin/python -m pytest tests/test_transcriber.py::test_encode_wav_shape -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'transcriber'`

- [ ] **Step 3: Write minimal implementation**

```python
import wave, io, tempfile, os
import numpy as np

class Transcriber:
    def __init__(self, api_key, model, language=None, clean=False):
        self.api_key = api_key
        self.model = model
        self.language = language
        self.clean = clean

    def _encode_wav(self, chunks):
        audio = np.concatenate(chunks, axis=0)
        audio_int16 = (audio * 32767).astype(np.int16)
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(audio_int16.tobytes())
        return buf.getvalue()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/numair/Projects/wispy && .venv/bin/python -m pytest tests/test_transcriber.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/transcriber.py tests/test_transcriber.py
git commit -m "feat: add Transcriber with WAV encoding"
```

---

### Task 3: Transcriber — empty/short audio guard

**Files:**
- Modify: `src/transcriber.py`
- Modify: `tests/test_transcriber.py`

**Interfaces:**
- Consumes: `Transcriber._encode_wav` from Task 2, `InvalidAudioError` from Task 1.
- Produces: Guard at the top of `transcribe()` — raises `InvalidAudioError` when buffer is empty or has fewer than 5 frames.

- [ ] **Step 1: Write the failing test**

```python
def test_transcribe_empty_raises():
    from transcriber import Transcriber
    from exceptions import InvalidAudioError
    t = Transcriber(api_key="x", model="m", language=None, clean=False)
    try:
        t.transcribe([])
        assert False, "should have raised"
    except InvalidAudioError:
        pass

def test_transcribe_short_raises():
    from transcriber import Transcriber
    from exceptions import InvalidAudioError
    t = Transcriber(api_key="x", model="m", language=None, clean=False)
    chunk = np.zeros((100, 1), dtype=np.float32)
    try:
        t.transcribe([chunk])  # 1 chunk < 5
        assert False, "should have raised"
    except InvalidAudioError:
        pass
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/numair/Projects/wispy && .venv/bin/python -m pytest tests/test_transcriber.py::test_transcribe_empty_raises -v
```

Expected: FAIL — `AttributeError: 'Transcriber' object has no attribute 'transcribe'`

- [ ] **Step 3: Write minimal implementation**

```python
from exceptions import InvalidAudioError, MissingKeyError

# Inside Transcriber class:
    def transcribe(self, chunks):
        if not chunks or len(chunks) < 5:
            raise InvalidAudioError("Recording too short")
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/numair/Projects/wispy && .venv/bin/python -m pytest tests/test_transcriber.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/transcriber.py tests/test_transcriber.py
git commit -m "feat: add empty/short audio guard to Transcriber"
```

---

### Task 4: Transcriber — missing key guard

**Files:**
- Modify: `src/transcriber.py`
- Modify: `tests/test_transcriber.py`

**Interfaces:**
- Consumes: `MissingKeyError` from Task 1.
- Produces: Guard at the top of `transcribe()` — raises `MissingKeyError` when `api_key` is empty.

- [ ] **Step 1: Write the failing test**

```python
def test_transcribe_no_key_raises():
    from transcriber import Transcriber
    from exceptions import MissingKeyError
    t = Transcriber(api_key="", model="m", language=None, clean=False)
    chunk = np.zeros((16000, 1), dtype=np.float32)
    try:
        t.transcribe([chunk] * 5)
        assert False, "should have raised"
    except MissingKeyError:
        pass
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/numair/Projects/wispy && .venv/bin/python -m pytest tests/test_transcriber.py::test_transcribe_no_key_raises -v
```

Expected: FAIL — should hit `MissingKeyError` but currently raises `InvalidAudioError` (chunks >= 5 check passes, key check not yet added)

- [ ] **Step 3: Write minimal implementation**

```python
# Inside transcribe(), after the short-audio guard:
        if not self.api_key:
            raise MissingKeyError("Set GROQ_API_KEY in Settings or env")
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/numair/Projects/wispy && .venv/bin/python -m pytest tests/test_transcriber.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/transcriber.py tests/test_transcriber.py
git commit -m "feat: add missing-key guard to Transcriber"
```

---

### Task 5: Transcriber — Groq Whisper call (mocked)

**Files:**
- Modify: `src/transcriber.py`
- Modify: `tests/test_transcriber.py`

**Interfaces:**
- Consumes: `Transcriber._encode_wav` from Task 2, `GroqError` from Task 1.
- Produces: `_whisper(wav_bytes) -> str` — internal method, calls `groq.audio.transcriptions.create`, raises `GroqError` on failure. Called by `transcribe()`.

- [ ] **Step 1: Write the failing test**

```python
from unittest.mock import patch, MagicMock

def test_whisper_calls_groq():
    """_whisper should call groq client and return result.text."""
    from transcriber import Transcriber
    t = Transcriber(api_key="test-key", model="whisper-large-v3", language="en", clean=False)
    fake_wav = b"RIFF" + b"\x00" * 100

    mock_client = MagicMock()
    mock_result = MagicMock()
    mock_result.text = " hello world "
    mock_client.audio.transcriptions.create.return_value = mock_result

    with patch("transcriber.groq") as mock_groq:
        mock_groq.Groq.return_value = mock_client
        result = t._whisper(fake_wav)

    assert result == "hello world"
    mock_client.audio.transcriptions.create.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/numair/Projects/wispy && .venv/bin/python -m pytest tests/test_transcriber.py::test_whisper_calls_groq -v
```

Expected: FAIL — `AttributeError: 'Transcriber' object has no attribute '_whisper'`

- [ ] **Step 3: Write minimal implementation**

```python
import groq  # at top of file

# Inside Transcriber class:
    def _whisper(self, wav_bytes):
        client = groq.Groq(api_key=self.api_key)
        import tempfile, os
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        try:
            tmp.write(wav_bytes)
            tmp.close()
            with open(tmp.name, "rb") as f:
                result = client.audio.transcriptions.create(
                    model=self.model,
                    file=f,
                    language=self.language or None,
                )
            return result.text.strip()
        except Exception as e:
            raise GroqError(str(e)) from e
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/numair/Projects/wispy && .venv/bin/python -m pytest tests/test_transcriber.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/transcriber.py tests/test_transcriber.py
git commit -m "feat: add Groq Whisper call to Transcriber"
```

---

### Task 6: Transcriber — clean-text gate

**Files:**
- Modify: `src/transcriber.py`
- Modify: `tests/test_transcriber.py`

**Interfaces:**
- Consumes: `GroqError` from Task 1. `Transcriber.clean` field from constructor.
- Produces: `_clean(raw_text) -> str` — internal method; skips if `not self.clean` or `< 5 words`; calls `groq.chat.completions.create` with `CLEAN_PROMPT`; returns raw text on failure. Called by `transcribe()`.

- [ ] **Step 1: Write the failing test**

```python
def test_clean_skips_short_text():
    from transcriber import Transcriber
    t = Transcriber(api_key="k", model="m", language=None, clean=True)
    assert t._clean("hi there") == "hi there"  # <5 words, skipped

def test_clean_skips_when_disabled():
    from transcriber import Transcriber
    t = Transcriber(api_key="k", model="m", language=None, clean=False)
    assert t._clean("one two three four five") == "one two three four five"

def test_clean_calls_groq_when_enabled():
    from transcriber import Transcriber
    t = Transcriber(api_key="k", model="m", language=None, clean=True)
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "cleaned text"
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])
    with patch("transcriber.groq") as mock_groq:
        mock_groq.Groq.return_value = mock_client
        result = t._clean("one two three four five six")
    assert result == "cleaned text"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/numair/Projects/wispy && .venv/bin/python -m pytest tests/test_transcriber.py::test_clean_skips_short_text -v
```

Expected: FAIL — `AttributeError: 'Transcriber' object has no attribute '_clean'`

- [ ] **Step 3: Write minimal implementation**

```python
from main import CLEAN_PROMPT  # at top of file

# Inside Transcriber class:
    def _clean(self, raw_text):
        if not self.clean or len(raw_text.split()) < 5:
            return raw_text
        try:
            client = groq.Groq(api_key=self.api_key)
            result = client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[
                    {"role": "system", "content": CLEAN_PROMPT},
                    {"role": "user", "content": raw_text},
                ],
                temperature=0.3,
                max_tokens=2048,
            )
            cleaned = result.choices[0].message.content.strip()
            return cleaned if cleaned else raw_text
        except Exception:
            return raw_text  # ponytail: fall back to raw, don't raise
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/numair/Projects/wispy && .venv/bin/python -m pytest tests/test_transcriber.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/transcriber.py tests/test_transcriber.py
git commit -m "feat: add clean-text gate to Transcriber"
```

---

### Task 7: Transcriber — wire `transcribe()` end-to-end

**Files:**
- Modify: `src/transcriber.py`
- Modify: `tests/test_transcriber.py`

**Interfaces:**
- Consumes: All internals from Tasks 2–6.
- Produces: `transcribe(chunks) -> str` — public interface. Validates → encodes → whisper → clean. Returns final text string.

- [ ] **Step 1: Write the failing test**

```python
def test_transcribe_end_to_end():
    """Full pipeline: encode → whisper → clean → return text."""
    from transcriber import Transcriber
    t = Transcriber(api_key="test-key", model="m", language=None, clean=False)
    chunks = [np.zeros((16000, 1), dtype=np.float32) for _ in range(5)]
    mock_client = MagicMock()
    mock_result = MagicMock()
    mock_result.text = "hello world"
    mock_client.audio.transcriptions.create.return_value = mock_result
    with patch("transcriber.groq") as mock_groq:
        mock_groq.Groq.return_value = mock_client
        result = t.transcribe(chunks)
    assert result == "hello world"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/numair/Projects/wispy && .venv/bin/python -m pytest tests/test_transcriber.py::test_transcribe_end_to_end -v
```

Expected: FAIL — `transcribe` returns `None` (method body only has guards, no pipeline call)

- [ ] **Step 3: Write minimal implementation**

```python
# Complete transcribe() method body:
    def transcribe(self, chunks):
        if not chunks or len(chunks) < 5:
            raise InvalidAudioError("Recording too short")
        if not self.api_key:
            raise MissingKeyError("Set GROQ_API_KEY in Settings or env")
        wav = self._encode_wav(chunks)
        text = self._whisper(wav)
        if not text:
            return ""
        return self._clean(text)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/numair/Projects/wispy && .venv/bin/python -m pytest tests/test_transcriber.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/transcriber.py tests/test_transcriber.py
git commit -m "feat: wire Transcriber.transcribe() end-to-end"
```

---

### Task 8: Injector module

**Files:**
- Create: `src/injector.py`
- Modify: `tests/test_transcriber.py`

**Interfaces:**
- Consumes: nothing from Transcriber; standalone module.
- Produces: `Injector.inject(text)` — calls `subprocess.run(["ydotool", "type", ...])`, raises `InjectError` on failure. `Injector.copy(text)` — calls `QApplication.clipboard().setText(text)`. `InjectError` added to `src/exceptions.py`.

- [ ] **Step 1: Write the failing test**

```python
def test_inject_calls_ydotool():
    from injector import Injector
    inj = Injector()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        inj.inject("hello world")
    mock_run.assert_called_once()
    args = mock_run.call_args
    assert args[0][0] == ["ydotool", "type", "-d", "1", "-H", "1", "hello world"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/numair/Projects/wispy && .venv/bin/python -m pytest tests/test_transcriber.py::test_inject_calls_ydotool -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'injector'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/injector.py
import subprocess
from exceptions import TranscribeError

class InjectError(TranscribeError):
    pass

class Injector:
    def inject(self, text):
        try:
            subprocess.run(
                ["ydotool", "type", "-d", "1", "-H", "1", text],
                check=True, capture_output=True, timeout=60,
            )
        except FileNotFoundError:
            raise InjectError("ydotool not found — install it")
        except subprocess.CalledProcessError as e:
            raise InjectError(f"Type failed: {e}")

    def copy(self, text):
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)
```

Also update `src/exceptions.py`:
```python
from exceptions import InjectError  # add to test imports
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/numair/Projects/wispy && .venv/bin/python -m pytest tests/test_transcriber.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/injector.py src/exceptions.py tests/test_transcriber.py
git commit -m "feat: add Injector module with ydotool + clipboard"
```

---

### Task 9: Wire modules into WispyApp

**Files:**
- Modify: `src/main.py`

**Interfaces:**
- Consumes: `Transcriber`, `Injector`, all exception types from Tasks 1–8.
- Produces: `WispyApp._transcribe_and_inject` reduced to ~15 lines: instantiate `Transcriber` + `Injector`, call `transcribe`, call `inject` or `copy`, catch typed exceptions and emit to tray.

- [ ] **Step 1: Write the failing test**

```python
def test_transcribe_and_inject_exists():
    """WispyApp should have the method (integration smoke)."""
    # We can't instantiate WispyApp without a display, so just verify
    # the imports work and the module loads.
    import importlib
    import main
    importlib.reload(main)
    assert hasattr(main.WispyApp, '_transcribe_and_inject')
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/numair/Projects/wispy && .venv/bin/python -m pytest tests/test_transcriber.py::test_transcribe_and_inject_exists -v
```

Expected: PASS (method already exists) — this is a guard test. The real work is the refactor below.

- [ ] **Step 3: Refactor `_transcribe_and_inject` and `_clean_text`**

Remove `_clean_text` method entirely. Replace `_transcribe_and_inject` body with:

```python
    def _transcribe_and_inject(self, buffer):
        from transcriber import Transcriber, TranscribeError, InvalidAudioError
        from injector import Injector
        if not buffer:
            return
        t = Transcriber(
            api_key=self.config.get("groq_api_key")
                or os.environ.get("GROQ_API_KEY", ""),
            model=self.config.get("groq_model", MODELS[0]),
            language=self.config.get("language") or None,
            clean=self.config.get("clean_text", False),
        )
        inj = Injector()
        try:
            text = t.transcribe(buffer)
            if not text:
                return
            if self.config.get("copy_to_clipboard"):
                self._set_clipboard.emit(text)
            inj.inject(text)
        except InvalidAudioError:
            pass  # silently drop, same as old behavior
        except Exception as e:
            self._notify.emit("Wispy", str(e))
```

- [ ] **Step 4: Run existing tests to verify nothing broke**

```bash
cd /home/numair/Projects/wispy && .venv/bin/python -m pytest tests/test_wispy.py tests/test_transcriber.py -v
```

Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/main.py
git commit -m "refactor: wire Transcriber + Injector into WispyApp"
```

---

### Task 10: Final verification

**Files:**
- No file changes

- [ ] **Step 1: Run all tests**

```bash
cd /home/numair/Projects/wispy && .venv/bin/python -m pytest tests/ -v
```

Expected: ALL PASS

- [ ] **Step 2: Verify no leftover dead code**

```bash
cd /home/numair/Projects/wispy && grep -n '_clean_text\|_transcribe_and_inject' src/main.py
```

Expected: only `_transcribe_and_inject` appears (the method still exists, now refactored). `_clean_text` should not appear.

- [ ] **Step 3: Verify new modules are importable**

```bash
cd /home/numair/Projects/wispy && .venv/bin/python -c "from transcriber import Transcriber; from injector import Injector; from exceptions import TranscribeError, MissingKeyError, GroqError, InvalidAudioError, InjectError; print('all imports ok')"
```

Expected: `all imports ok`

- [ ] **Step 4: Commit the plan itself**

```bash
git add docs/superpowers/plans/
git commit -m "docs: add transcriber deepening plan"
```
