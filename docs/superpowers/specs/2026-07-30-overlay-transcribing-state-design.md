# Design Spec: Wispy Overlay Transcribing State & Accuracy Improvements

Date: 2026-07-30
Status: Approved

## Overview

This specification details the transition of Wispy's overlay window to remain visible after recording stops, displaying a "Transcribing..." state until audio processing and text injection complete. Additionally, it addresses transcription accuracy fixes (removing prompt bias) and outlines model speed recommendations.

---

## 1. Scope Breakdown

- **Task 1 (Primary)**: Overlay "Transcribing..." UI state, state machine, and thread-safe Qt signaling for window visibility lifecycle.
- **Task 2 (Accuracy Fix)**: Remove prompt bias contamination in `DEFAULT_WHISPER_PROMPT` in `Transcriber`.
- **Task 3 (Speed Optimization)**: Guide/configure fast online models (`whisper-large-v3-turbo`, `distil-whisper-large-v3-en`).

---

## 2. Technical Architecture & Components

### 2.1 Overlay State Machine (`src/overlay.py`)

Add an explicit state tracking mechanism (`RECORDING`, `TRANSCRIBING`, `IDLE`) to `OverlayWindow`:

1. **State Enum / Constants**:
   - `State.RECORDING` (0): Active recording state with pulsing red/white dot, level-driven audio waveform, timer display, and functional stop button.
   - `State.TRANSCRIBING` (1): Processing state with pulsing blue/violet status dot (`rgb(100, 160, 255)`), centered `"Transcribing…"` text with pulse alpha, no waveform, no timer, and disabled stop/click actions.

2. **UI Layout & Rendering (`paintEvent`)**:
   - In `RECORDING` state: Render standard waveform bars, duration timer, and stop button.
   - In `TRANSCRIBING` state: Render `"Transcribing…"` text in place of waveform/timer. Calculate label position using existing pill geometry to keep it horizontally and vertically centered.
   - Oscillate text/dot alpha in `_tick()` during `TRANSCRIBING` to indicate active progress.

3. **Event Handling (`mousePressEvent`)**:
   - When in `TRANSCRIBING` state, click actions on the overlay and stop button are ignored to prevent premature cancellation.

---

### 2.2 Main Application Lifecycle & Signal Flow (`src/main.py`)

1. **Qt Signal for Thread-Safe Completion**:
   - Define PyQt signals on `WispyApp`: `_transcribe_finished = pyqtSignal()` and `_transcribe_error = pyqtSignal(str)`.
   - Thread-safety requirement: Calls to `overlay.hide()` or UI state changes must run on the Qt main GUI thread.

2. **Recording Stop & Transcribe Workflow**:
   - In `_stop_recording()`:
     - Stop audio input stream.
     - Check minimum duration (2s). If too short, hide overlay and return.
     - Call `overlay.set_state("transcribing")` to transition the UI instead of immediately hiding `overlay.hide()`.
     - Spawn background daemon thread for `_transcribe_and_inject(buffer)`.

3. **Transcription & Injection Thread (`_transcribe_and_inject`)**:
   - Perform transcription via `Transcriber`.
   - Copy to clipboard if configured.
   - Inject text using `Injector`.
   - In a `finally` block, emit `_transcribe_finished` signal.
   - Signal handler on GUI thread executes `self.overlay.hide()` and resets overlay state to `RECORDING`.

4. **Hotkey / Toggle Guards**:
   - `toggle_overlay()` checks current overlay state. If overlay is visible and state is `TRANSCRIBING`, the toggle request is ignored.

---

### 2.3 Transcription Accuracy Fix (`src/transcriber.py`)

1. **Prompt Bias Removal**:
   - `DEFAULT_WHISPER_PROMPT` currently contains arbitrary text (`"Open the file at slash goal dot dot..."`).
   - Replace with an empty string `""` or neutral formatting prompt. This eliminates vocabulary contamination during Whisper inference.

---

## 3. Error & Edge Case Handling

1. **Short Recording (< 2s)**: Immediate overlay hide + tray notification (no transition to `TRANSCRIBING`).
2. **Transcription Error / Exception**: `_notify` signal handles critical notification; `finally` block guarantees overlay hides safely without getting stuck in `TRANSCRIBING` state.
3. **App Exit**: `quit()` ensures active streams and overlay timers are safely stopped.

---

## 4. Verification Plan

1. **Automated Tests**:
   - Run test suite `.venv/bin/python tests/test_wispy.py` to ensure CLI and constants remain valid.
2. **Runtime Manual Verification**:
   - Start Wispy daemon (`./scripts/wispy.sh server`).
   - Trigger recording toggle (`./scripts/wispy.sh toggle`).
   - Speak a brief sentence and toggle off.
   - Verify overlay switches to `"Transcribing…"` with blue pulsing indicator.
   - Verify overlay stays visible until transcription completes and text is injected.
   - Verify hotkey triggers during transcription are ignored.
