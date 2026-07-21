# Wispy Housekeeping, Icon, and Prompt Improvements Design

**Date:** 2026-07-22
**Status:** Approved (brainstorming complete)

## Overview

Three independent changes bundled into one implementation cycle:
1. Reorganize the root directory by purpose into subfolders
2. Invert the icon colors to a black theme
3. Add LLM post-processing for retraction removal and automatic formatting

## 1. Housekeeping — Folder Reorganization

### Current State

16 files in the project root — Python source, shell scripts, packaging, system integration, assets, and tests all mixed together.

### Proposed Structure

```
wispy/
├── src/
│   ├── main.py
│   └── overlay.py
├── scripts/
│   ├── build.sh
│   ├── setup.sh
│   ├── wispy.sh
│   ├── wispy-toggle.sh
│   └── wispy.spec
├── assets/
│   └── wispy.svg
├── system/
│   ├── wispy.desktop
│   └── wispy.service
├── tests/
│   └── test_wispy.py
├── docs/                  (existing, stays)
├── AGENTS.md
├── README.md
├── requirements.txt
└── .gitignore
```

### Rewiring (every file that references paths)

| File | Change |
|------|--------|
| `scripts/wispy.sh` | `main.py` → `src/main.py` (path relative to script location) |
| `src/main.py` | `ICON_SVG` path: use `sys._MEIPASS` when frozen (PyInstaller), else `Path(__file__).parent.parent / "assets" / "wispy.svg"` |
| `scripts/build.sh` | Entry point `main.py` → `src/main.py`; `--add-data` paths → `../assets/wispy.svg:.`; remove `overlay.py` from `--add-data` (PyInstaller auto-detects imports) |
| `scripts/wispy.spec` | `Analysis(['src/main.py'])`, `datas=[('../assets/wispy.svg', '.')]` |
| `scripts/setup.sh` | All `cp`/`sed` source paths updated with `scripts/`, `assets/`, `system/` prefixes |
| `tests/test_wispy.py` | `sys.path.insert` → point to `../src` relative to test file |
| `AGENTS.md` | Update architecture file paths to reflect new structure |
| `README.md` | Update quick start and command paths (`./wispy.sh` → `./scripts/wispy.sh`, etc.) |

### Path Resolution Strategy for `src/main.py`

The `ICON_SVG` constant currently uses `Path(__file__).parent / "wispy.svg"`. After the move, the SVG is in `assets/` (two levels up from `src/main.py` in source, or in `sys._MEIPASS` when frozen). The replacement:

```python
def _icon_path():
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / "wispy.svg"
    return Path(__file__).parent.parent / "assets" / "wispy.svg"

ICON_SVG = _icon_path()
```

This works in both development (run from source) and production (PyInstaller bundle).

## 2. Icon Color Inversion

### Current State

- `wispy.svg`: Light rounded square (`#F0F0F0`) with dark sound-wave bars (`#1E1E1E`)
- `_draw_icon()` in `main.py`: `QColor(240, 240, 240)` background, `QColor(30, 30, 30)` bars

### Change

Invert both to a black theme:

**`assets/wispy.svg`:**
- Rounded square: `fill="#1E1E1E"` (was `#F0F0F0`)
- All 5 sound-wave bars: `fill="#F0F0F0"` (was `#1E1E1E`)

**`src/main.py` — `_draw_icon()`:**
- Background `QColor(240, 240, 240)` → `QColor(30, 30, 30)`
- Bars `QColor(30, 30, 30)` → `QColor(240, 240, 240)`

No structural changes — two color swaps per file.

## 3. Prompt Improvements — Retraction Handling & Formatting

### Pipeline Change

```
Current:  Whisper transcribe → type text
New:      Whisper transcribe → LLM clean/format → type text (when enabled)
```

The LLM step runs in the same background thread as Whisper. The overlay still hides instantly; the text arrives ~200-500ms later when the LLM step is enabled. Togglable via settings.

### Model

`openai/gpt-oss-20b` — Groq's fastest free model (1,000 tokens/sec, free tier). This is the recommended replacement for `llama-3.1-8b-instant` which is being deprecated Aug 16, 2026. Hardcoded as default in config as `LLM_MODEL`. Editable in `config.json` if Groq's lineup changes. No UI model selector — YAGNI until requested.

### Setting

New checkbox in Settings → Behavior section: "Clean and format text with AI" (`config["clean_text"]`, default: `false` — opt-in).

### LLM System Prompt

```
You are a speech-to-text post-processor. Your input is raw transcribed speech.

Rules:
1. Remove retractions: if the speaker says something then takes it back
   ("wait nevermind", "actually no", "scratch that", "let me rephrase",
   "oh wait I meant"), keep ONLY their final intended message.
2. Format automatically: if the speech naturally describes a list or
   steps, format as bullet/numbered list. If there are distinct topics
   or pauses, add line breaks between them.
3. Fix obvious transcription errors and add proper punctuation.
4. Output ONLY the cleaned text. No explanations, no commentary, no
   meta-text, no quotes around the result.
```

User prompt: the raw Whisper transcription text.

### Error Handling

- If the LLM call fails (network error, rate limit, timeout): fall back to the raw Whisper text. Never lose the user's speech.
- If the LLM returns empty or whitespace-only: fall back to the raw Whisper text.

### Short-Circuit

If Whisper returns fewer than 5 words, skip the LLM call entirely — not worth the latency for "yes" or "thank you". The raw text is used directly.

### Files Touched

- `src/main.py` only:
  - `_transcribe_and_inject`: add LLM step after Whisper transcription, before text injection
  - `SettingsDialog`: add "Clean and format text with AI" checkbox in Behavior section
  - `SettingsDialog._save`: save `config["clean_text"]`
  - `WispyApp._load_config`: add `clean_text` default (`false`)
  - New constant `LLM_MODEL = "openai/gpt-oss-20b"`
  - New constant `CLEAN_PROMPT` (module-level string containing the system prompt above)

### Implementation Detail — LLM Call

```python
def _clean_text(self, raw_text, key):
    import groq
    client = groq.Groq(api_key=key)
    result = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": CLEAN_PROMPT},
            {"role": "user", "content": raw_text},
        ],
        temperature=0.3,
        max_tokens=2048,
    )
    cleaned = result.choices[0].message.content.strip()
    return cleaned if cleaned else raw_text
```

Called inside `_transcribe_and_inject` after Whisper returns, guarded by:
```python
if self.config.get("clean_text") and len(raw_text.split()) >= 5:
    try:
        text = self._clean_text(text, key)
    except Exception:
        pass  # fall back to raw Whisper text
```

## Non-Goals

- No voice command system (explicit "new line", "bullet" commands) — automatic detection only
- No LLM model selector in settings UI — `config.json` edit only
- No streaming/chunked LLM output — simple request/response is fast enough at 1,000 TPS
- No changes to the overlay UI or recording lifecycle
- No changes to the IPC or toggle mechanism

## Testing

- `tests/test_wispy.py`: existing tests must pass (CLI parsing, constants)
- New test: `LLM_MODEL` constant exists and is a non-empty string
- New test: `CLEAN_PROMPT` constant exists and contains the retraction rules
- Manual smoke test: toggle with `clean_text` on, speak a retraction, verify cleaned output
- Manual smoke test: toggle with `clean_text` off, verify raw Whisper text as before
