# Wispy Groq Transcription Pipeline Optimization Design

## Overview
This design improves Wispy's audio transcription speed and responsiveness by eliminating per-request client re-instantiation and temporary disk file I/O when communicating with the Groq API.

## Problem Statement
1. **Per-Request HTTP Connection Handshakes**: `groq.Groq(api_key=...)` is re-created on every transcription request in `Transcriber._whisper()`. This destroys underlying HTTP socket pools, forcing a fresh TCP 3-way handshake and TLS negotiation for every audio recording (~100ms–300ms latency penalty).
2. **Physical Disk I/O**: Recorded audio PCM frames are encoded and written to temporary disk files (`tempfile.NamedTemporaryFile`), flushed, opened for HTTP POST transmission, and unlinked. This adds file system wait time (~20ms–80ms latency penalty).
3. **Redundant WAV Encoding**: In hybrid and retry modes, `encode_wav()` is invoked multiple times on the same audio buffer.

## Design Details

### 1. Persistent Groq Client with Connection Pooling (`src/transcriber.py`)
- Maintain a persistent `groq.Groq` instance on `Transcriber`.
- Configure an explicit `httpx.Client` backend with connection pooling:
  `limits = httpx.Limits(max_connections=20, max_keepalive_connections=10, keepalive_expiry=120.0)`
- Reuse the client across transcription calls. Re-instantiate only if the API key is changed.

### 2. In-Memory `io.BytesIO` Streaming (`src/transcriber.py`)
- Remove `tempfile.NamedTemporaryFile` and `os.unlink()` from `_whisper()`.
- Wrap `wav_bytes` in `io.BytesIO(wav_bytes)`.
- Pass `file=("speech.wav", buffer, "audio/wav")` to `client.audio.transcriptions.create()`.

### 3. Single WAV Byte Encoding & Buffer Reuse (`src/main.py`)
- In `_transcribe_and_inject()`, compute `wav_bytes = encode_wav(buffer)` once.
- Pass `wav_bytes` directly into `t.transcribe(wav_bytes)` and `t.transcribe_cloud_first(wav_bytes)`.

### 4. Testing & Regression Prevention (`tests/test_wispy.py`)
- Update and expand `tests/test_wispy.py` to verify:
  - `_whisper` handles `io.BytesIO` in-memory tuple formats properly without error.
  - Client instance is preserved across calls.
  - All existing CLI and unit tests pass.

## Trade-offs & Security
- **Memory Footprint**: `io.BytesIO` holds audio in RAM for the duration of the API call (a few hundred KB for short voice clips). Memory is freed immediately after the request completes.
- **Socket Idle Timeout**: If Groq closes idle keep-alive connections after inactivity, `httpx` automatically handles reconnecting on the next request.
