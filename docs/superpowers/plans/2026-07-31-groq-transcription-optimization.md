# Groq Transcription Pipeline Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate per-request client re-instantiation and temporary disk file I/O in Wispy's Groq transcription pipeline for faster, lower-latency voice-to-text response times.

**Architecture:** Refactor `Transcriber` in `src/transcriber.py` to hold a persistent `groq.Groq` client instance backed by an `httpx.Client` connection pool (`keepalive`), and replace `tempfile.NamedTemporaryFile` with `io.BytesIO` in `_whisper()`. Pass single pre-encoded `wav_bytes` across hybrid and retry execution paths in `src/main.py`.

**Tech Stack:** Python 3.10+, Groq Python SDK (`groq`), `httpx`, `PyQt6`, `pytest`

## Global Constraints
- All tests must pass via `.venv/bin/python tests/test_wispy.py`.
- No broken existing imports or signatures.
- Clean up any temporary resources.

---

### Task 1: Add Unit Tests for Persistent Client and `io.BytesIO` Audio Stream

**Files:**
- Modify: `tests/test_wispy.py`

**Interfaces:**
- Consumes: `Transcriber` class from `src/transcriber.py`
- Produces: Tests verifying `Transcriber._client` persistence and `io.BytesIO` handling in `_whisper`

- [ ] **Step 1: Write the failing unit tests in `tests/test_wispy.py`**

Add tests to `tests/test_wispy.py` for client persistence and `io.BytesIO` memory stream handling:

```python
def test_transcriber_client_persistence():
    from transcriber import Transcriber
    t = Transcriber(api_key="test_key", model="whisper-large-v3-turbo")
    client1 = t.get_client()
    client2 = t.get_client()
    assert client1 is client2
    assert client1 is not None

def test_whisper_uses_bytesio_without_disk(monkeypatch):
    import io
    from transcriber import Transcriber
    t = Transcriber(api_key="dummy_key", model="whisper-large-v3-turbo")
    
    called_with_file = [None]
    class DummyTranscriptions:
        def create(self, model, file, language=None, prompt=""):
            called_with_file[0] = file
            class Res:
                text = "hello world"
            return Res()

    class DummyAudio:
        transcriptions = DummyTranscriptions()

    class DummyGroqClient:
        audio = DummyAudio()

    t._client = DummyGroqClient()
    res = t._whisper(b"RIFFdummywavbytes")
    assert res == "hello world"
    assert isinstance(called_with_file[0], io.BytesIO)
    assert called_with_file[0].getvalue() == b"RIFFdummywavbytes"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python tests/test_wispy.py`
Expected: FAIL (AttributeError: 'Transcriber' object has no attribute 'get_client')

- [ ] **Step 3: Commit initial test modifications**

```bash
git add tests/test_wispy.py
git commit -m "test: add tests for transcriber persistent client and bytesio handling"
```

---

### Task 2: Refactor `src/transcriber.py` for Persistent Client and `io.BytesIO` Streaming

**Files:**
- Modify: `src/transcriber.py`

**Interfaces:**
- Consumes: `groq.Groq`, `httpx.Client`, `io.BytesIO`
- Produces: `Transcriber.get_client()`, zero-disk `Transcriber._whisper(wav_bytes)`

- [ ] **Step 1: Refactor `src/transcriber.py`**

Modify `src/transcriber.py`:
1. Add `import io` and `import httpx`.
2. Update `Transcriber.__init__` to initialize `self._client = None`.
3. Add `get_client()` method:
```python
    def get_client(self):
        if not self.api_key:
            return None
        if self._client is None:
            http_client = httpx.Client(
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10, keepalive_expiry=120.0)
            )
            self._client = groq.Groq(api_key=self.api_key, http_client=http_client)
        return self._client
```
4. Update `_whisper()` to use `io.BytesIO` and `get_client()`:
```python
    def _whisper(self, wav_bytes, timeout=None):
        client = self.get_client()
        if not client:
            raise GroqError("No API key provided")
        buf = io.BytesIO(wav_bytes)
        buf.name = "speech.wav"
        try:
            result = client.audio.transcriptions.create(
                model=self.model,
                file=buf,
                language=self.language or None,
                prompt=self.whisper_prompt,
            )
            return result.text.strip()
        except Exception as e:
            raise GroqError(str(e)) from e
```

- [ ] **Step 2: Run test to verify it passes**

Run: `.venv/bin/python tests/test_wispy.py`
Expected: PASS

- [ ] **Step 3: Commit implementation**

```bash
git add src/transcriber.py
git commit -m "refactor: use persistent groq client and in-memory BytesIO in Transcriber"
```

---

### Task 3: Avoid Redundant Audio Byte Encoding in `src/main.py`

**Files:**
- Modify: `src/main.py`

**Interfaces:**
- Consumes: `encode_wav(buffer)`
- Produces: Cached `wav_bytes` passed into `transcribe` and retry pipelines

- [ ] **Step 1: Refactor `_transcribe_and_inject` in `src/main.py`**

Modify `_transcribe_and_inject` in `src/main.py` so `wav_bytes = encode_wav(buffer)` is calculated once before checking engine mode or retry pathways:
```python
                wav_bytes = encode_wav(buffer)
                if self.config.get("engine_mode") == "hybrid" and t.api_key:
                    text, used_local = t.transcribe_cloud_first(wav_bytes, buffer)
                    text = t._casual(text)
                else:
                    text = t.transcribe(buffer)
```
And inside the background retry check:
```python
                if used_local and t.api_key:
                    def on_retry_success(cloud_text):
                        cleaned = t._casual(cloud_text)
                        self._set_clipboard.emit(cleaned)
                        self._corrected.emit()

                    def on_retry_fail():
                        pass  # local result stands

                    t.retry_cloud_async(wav_bytes, on_retry_success, on_retry_fail)
```

- [ ] **Step 2: Run tests to verify existing suite passes**

Run: `.venv/bin/python tests/test_wispy.py`
Expected: PASS

- [ ] **Step 3: Commit main.py refactoring**

```bash
git add src/main.py
git commit -m "perf: reuse encoded wav bytes in hybrid and retry transcription paths"
```

---

### Task 4: Full Suite Verification & Final Check

- [ ] **Step 1: Run the full test suite**

Run: `.venv/bin/python tests/test_wispy.py`
Expected: All tests PASS with exit code 0.

- [ ] **Step 2: Commit final state**

```bash
git commit --allow-empty -m "chore: verify Groq transcription pipeline optimization"
```
