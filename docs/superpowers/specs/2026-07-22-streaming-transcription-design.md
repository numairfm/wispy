# Streaming Transcription with Pause-Based Slicing

## Problem

Current flow records the entire audio buffer, stops recording, then transcribes everything at once. Long recordings take proportionally longer to transcribe. The stop keyword feature exists but lacks a natural "pause after keyword" trigger.

## Goal

Slice audio on natural pauses (~1s silence), transcribe each slice independently while recording continues, and integrate stop keyword detection with pause-based stopping.

## Current State

- `Recorder._audio_cb` accumulates audio chunks into `_audio_buffer` and computes RMS level
- `_stop_recording` gets the full buffer, spawns `_transcribe_and_inject` thread
- `check_stop_keyword` strips keyword from text, returns `(text, should_send)`
- Injection is sequential via `ydotool`

## Design

### Recorder Changes

Add pause detection to `Recorder._audio_cb`:

- Track continuous silence duration using existing RMS level
- When `_current_level` drops below threshold for > 1.0s, call `on_pause(buffer_slice)`
- Reset slice buffer, continue recording
- Expose `on_pause` callback (set by WispyApp)

New state in Recorder:
```python
self._slice_buffer = []
self._silence_start = None  # monotonic time when silence began
self.on_pause = None        # callback(chunks: list[np.ndarray])
SILENCE_THRESHOLD = 0.01    # RMS level below this = silence
PAUSE_DURATION = 1.0        # seconds of silence before slice triggers
```

Modified `_audio_cb`:
```python
def _audio_cb(self, indata, frames, time_info, status):
    # existing: append to _audio_buffer AND _slice_buffer
    # existing: compute rms and _current_level
    # new: track silence duration
    if _current_level < SILENCE_THRESHOLD:
        if _silence_start is None:
            _silence_start = now
        elif now - _silence_start >= PAUSE_DURATION:
            # pause detected — emit slice
            if _slice_buffer and on_pause:
                on_pause(_slice_buffer)
                _slice_buffer = []
                _silence_start = None
    else:
        _silence_start = None
```

Thread safety: `on_pause` is called from the audio callback thread (PortAudio). The callback must not block. WispyApp will copy the buffer and dispatch to a worker thread.

### WispyApp Changes

New state:
```python
self._pending_keyword = False
self._injection_queue = queue.Queue()  # ordered results
self._transcription_thread = None
```

New `_on_pause(chunks)` handler (called from audio thread):
1. Copy chunks (they're owned by the audio buffer)
2. Dispatch `_transcribe_slice(chunks)` in a thread
3. If `_pending_keyword` is True and this pause is post-keyword:
   - Call `_stop_recording()` on the main thread

New `_transcribe_slice(chunks)`:
1. Transcribe using Transcriber (same as current)
2. Check for stop keyword → set `_pending_keyword` if found
3. Put result into `_injection_queue`
4. Process queue: inject results in order

Modified `_stop_recording`:
1. Stop recorder (get remaining buffer)
2. If remaining buffer has audio, transcribe it
3. Wait for any pending slice transcriptions to complete
4. Inject final results in order

### Stop Keyword Flow

1. User says "blah blah send it" → pause detected → slice sent for transcription
2. Transcription returns "blah blah send it" → keyword detected → `_pending_keyword = True`
3. User pauses again → `_on_pause` checks `_pending_keyword` → stops recording
4. If user keeps talking → next slice processes normally, `_pending_keyword` resets

The keyword flag only persists until the next pause. If the user keeps talking past the keyword, it's treated as part of normal speech.

### Result Ordering

Use a `queue.Queue` for injection results. A dedicated consumer thread dequeues and injects in order. This ensures:
- Results are injected in the order slices were created
- If slice2 finishes before slice1, slice1 still injects first
- Manual stop flushes the queue

### Overlay Feedback

When a slice is being transcribed, show "Transcribing..." in the overlay. This reuses the existing overlay — add a label that's visible during transcription.

### Extra Spaces Fix

In `LocalTranscriber.transcribe`, strip extra whitespace from the joined segment text:
```python
text = " ".join(seg.text for seg in segments)
text = re.sub(r'  +', ' ', text).strip()
```

## Files to Modify

1. `src/recorder.py` — add pause detection in `_audio_cb`
2. `src/main.py` — add `_on_pause`, `_transcribe_slice`, injection queue, modify `_stop_recording`
3. `src/local_transcriber.py` — fix extra spaces
4. `src/overlay.py` — add "Transcribing..." state label

## Files NOT Modified

- `src/transcriber.py` — no changes needed, `transcribe(chunks)` works as-is
- `src/injector.py` — no changes needed
- `src/exceptions.py` — no changes needed

## Edge Cases

- **Very short pause (< 1s)**: Not a slice, audio continues accumulating
- **Manual stop during transcription**: Flush remaining buffer, wait for pending, inject all
- **Stop keyword in middle of slice**: Keyword detected, `_pending_keyword` set, next pause stops
- **Multiple keywords in one slice**: Only last keyword matters
- **No API key + offline mode**: Local transcription works, no Groq calls
- **Transcription error on a slice**: Log error, skip that slice, continue recording
- **Recording too short slice**: Skip (existing `MIN_DURATION` check applies per-slice, could lower threshold)

## Risks

- **PortAudio callback threading**: `on_pause` must not block. Use `QMetaObject.invokeMethod` or signal to dispatch to main thread.
- **RMS threshold sensitivity**: `SILENCE_THRESHOLD = 0.01` may need tuning. Expose as config if needed.
- **ydotool ordering**: Sequential injection queue handles this. No concurrent `ydotool` calls.
