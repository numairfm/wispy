# Wispy Housekeeping, Icon, and Prompt Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize the root directory into purpose-based subfolders, invert the icon colors to a black theme, and add LLM post-processing for retraction removal and automatic formatting.

**Architecture:** Python source moves to `src/`, shell scripts to `scripts/`, assets to `assets/`, system integration files to `system/`, tests to `tests/`. All path references are rewired. Icon colors inverted in SVG + programmatic fallback. LLM post-processing added as an optional step between Whisper transcription and text injection, using Groq's `openai/gpt-oss-20b` chat model with a system prompt that removes retractions and auto-formats.

**Tech Stack:** Python 3.14, PyQt6, sounddevice, numpy, groq, ydotool, PyInstaller

## Global Constraints

- Platform: Linux, KDE Plasma, Wayland
- Python venv at `.venv/` with all deps installed
- Config at `~/.config/wispy/config.json` or `GROQ_API_KEY` env var
- `ydotool` must be installed for text injection
- No new dependencies — use stdlib and already-installed packages only
- No test framework — use assert-based `tests/test_wispy.py` with `__main__` runner
- Run `AGENTS.md` updates past the user before committing (project convention)
- Git repo: commit after each task as specified

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `src/main.py` | Move + Modify | Icon path resolution, icon colors, LLM constants, settings checkbox, _clean_text method, _transcribe_and_inject |
| `src/overlay.py` | Move | No changes |
| `assets/wispy.svg` | Move + Modify | Invert colors (dark bg, light bars) |
| `scripts/wispy.sh` | Move + Modify | Update path to `src/main.py` |
| `scripts/wispy-toggle.sh` | Move | No changes (uses runtime socket path, no source paths) |
| `scripts/build.sh` | Move + Modify | Entry point → `src/main.py`, data paths → `../assets/` |
| `scripts/wispy.spec` | Move + Modify | Analysis path, datas path |
| `scripts/setup.sh` | Move + Modify | All source paths → `scripts/`, `assets/`, `system/` |
| `system/wispy.desktop` | Move | No changes (Exec/Icon set by setup.sh sed) |
| `system/wispy.service` | Move | No changes (ExecStart set by setup.sh sed) |
| `tests/test_wispy.py` | Move + Modify | sys.path → `../src`, add LLM_MODEL and CLEAN_PROMPT tests |
| `AGENTS.md` | Modify | Update file paths, add LLM post-processing description |
| `README.md` | Modify | Update command paths, add clean_text setting |
| `.gitignore` | Modify | Add `dist/`, `build/` already there |

---

## Task 1: Move Files Into Subfolders and Rewire Paths

This is the foundational task — all subsequent tasks operate on the new structure. Git tracks the moves as renames if we use `git mv`.

**Files:**
- Move: `main.py` → `src/main.py`
- Move: `overlay.py` → `src/overlay.py`
- Move: `build.sh` → `scripts/build.sh`
- Move: `setup.sh` → `scripts/setup.sh`
- Move: `wispy.sh` → `scripts/wispy.sh`
- Move: `wispy-toggle.sh` → `scripts/wispy-toggle.sh`
- Move: `wispy.spec` → `scripts/wispy.spec`
- Move: `wispy.svg` → `assets/wispy.svg`
- Move: `wispy.desktop` → `system/wispy.desktop`
- Move: `wispy.service` → `system/wispy.service`
- Move: `test_wispy.py` → `tests/test_wispy.py`
- Modify: `scripts/wispy.sh` — update path to `src/main.py`
- Modify: `src/main.py` — update `ICON_SVG` path resolution
- Modify: `scripts/build.sh` — update entry point and data paths
- Modify: `scripts/wispy.spec` — update Analysis path and datas
- Modify: `scripts/setup.sh` — update all source paths
- Modify: `tests/test_wispy.py` — update sys.path

**Interfaces:**
- Produces: new directory structure with all path references working

- [ ] **Step 1: Create the directories**

```sh
mkdir -p src scripts assets system tests
```

- [ ] **Step 2: Move files with git mv (preserves history)**

```sh
git mv main.py src/main.py
git mv overlay.py src/overlay.py
git mv build.sh scripts/build.sh
git mv setup.sh scripts/setup.sh
git mv wispy.sh scripts/wispy.sh
git mv wispy-toggle.sh scripts/wispy-toggle.sh
git mv wispy.spec scripts/wispy.spec
git mv wispy.svg assets/wispy.svg
git mv wispy.desktop system/wispy.desktop
git mv wispy.service system/wispy.service
git mv test_wispy.py tests/test_wispy.py
```

- [ ] **Step 3: Update `scripts/wispy.sh`**

The script currently references `$DIR/main.py`. After the move, `main.py` is in `src/` which is one level up from `scripts/`. Replace the entire file:

```sh
#!/bin/sh
set -e
DIR="$(cd "$(dirname "$0")/.." && pwd)"
exec "$DIR/.venv/bin/python3" "$DIR/src/main.py" "$@"
```

- [ ] **Step 4: Update `src/main.py` — ICON_SVG path resolution**

Replace line 19 in `src/main.py`:

```python
ICON_SVG = Path(__file__).parent / "wispy.svg"
```

with:

```python
def _icon_path():
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / "wispy.svg"
    return Path(__file__).parent.parent / "assets" / "wispy.svg"

ICON_SVG = _icon_path()
```

- [ ] **Step 5: Update `scripts/build.sh`**

Replace the entire file:

```bash
#!/bin/bash
set -e
cd "$(dirname "$0")/.."

if ! command -v pyinstaller &>/dev/null; then
    echo "Installing PyInstaller..."
    pip install pyinstaller
fi

echo "Building wispy..."
pyinstaller \
    --name wispy \
    --onefile \
    --noconfirm \
    --clean \
    --add-data "../assets/wispy.svg:." \
    src/main.py

echo ""
echo "Done: dist/wispy"
echo "Copy to ~/.local/bin/ and run from anywhere."
```

Note: `overlay.py` is removed from `--add-data` because PyInstaller auto-detects Python imports. The `cd` now goes to project root (`..`) so paths are relative to root.

- [ ] **Step 6: Update `scripts/wispy.spec`**

Replace the `Analysis` call (line 4-16):

```python
a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[('../assets/wispy.svg', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
```

Note: `overlay.py` removed from `datas` — PyInstaller auto-detects Python imports.

- [ ] **Step 7: Update `scripts/setup.sh`**

The `SRC` variable currently points to the script's own directory (which is now `scripts/`). We need it to point to the project root. Replace line 11:

```bash
SRC="$(cd "$(dirname "$0")/.." && pwd)"
```

Then update all source file references. Replace the `do_install` function body (lines 23-83):

```bash
do_install() {
    if [ "$BUILD" = "1" ]; then
        do_build
    fi

    echo "Installing $NAME..."

    mkdir -p "$(dirname "$BIN")"

    # Install the toggle script (fast path — system python3, no PyInstaller extraction)
    cp "$SRC/scripts/$NAME-toggle.sh" "$TOGGLE_BIN"
    chmod +x "$TOGGLE_BIN"
    echo "  toggle  → $TOGGLE_BIN"

    # Install the server binary (PyInstaller or venv launcher)
    if [ -f "$SRC/dist/$NAME" ]; then
        cp "$SRC/dist/$NAME" "$SERVER_BIN"
        echo "  binary  → $SERVER_BIN"
    elif [ -f "$SRC/scripts/$NAME.sh" ]; then
        cp "$SRC/scripts/$NAME.sh" "$SERVER_BIN"
        chmod +x "$SERVER_BIN"
        echo "  launcher → $SERVER_BIN"
    else
        echo "Error: no binary or launcher found. Run with --build first."
        exit 1
    fi

    # Install wispy wrapper: toggle → instant python3, everything else → server binary
    cat > "$BIN" <<'WRAPPER'
#!/bin/sh
# wispy — fast toggle (system python3), delegates server to wispy-server
case "$1" in
    toggle) exec "$HOME/.local/bin/wispy-toggle.sh" ;;
    "")     exec "$HOME/.local/bin/wispy-server" "--help" ;;
    *)      exec "$HOME/.local/bin/wispy-server" "$@" ;;
esac
WRAPPER
    chmod +x "$BIN"
    echo "  wrapper → $BIN"

    mkdir -p "$(dirname "$ICON")"
    cp "$SRC/assets/$NAME.svg" "$ICON"
    echo "  icon    → $ICON"

    mkdir -p "$(dirname "$DESKTOP")"
    sed "s|Exec=.*|Exec=$SERVER_BIN server|;s|Icon=.*|Icon=$ICON|" \
        "$SRC/system/$NAME.desktop" > "$DESKTOP"
    echo "  desktop → $DESKTOP"

    if [ -f "$SRC/system/$NAME.service" ]; then
        mkdir -p "$(dirname "$SERVICE")"
        sed "s|ExecStart=.*|ExecStart=$SERVER_BIN server|" \
            "$SRC/system/$NAME.service" > "$SERVICE"
        echo "  service → $SERVICE"
    fi

    echo ""
    echo "Done. Run '$NAME' or enable the systemd service:"
    echo "  systemctl --user daemon-reload"
    echo "  systemctl --user enable --now $NAME"
}
```

Also update `do_build` (line 18-20):

```bash
do_build() {
    echo "Building $NAME..."
    "$SRC/scripts/build.sh"
}
```

- [ ] **Step 8: Update `tests/test_wispy.py` — sys.path**

Replace line 3:

```python
sys.path.insert(0, os.path.dirname(__file__))
```

with:

```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
```

- [ ] **Step 9: Run tests to verify paths work**

Run: `.venv/bin/python tests/test_wispy.py`
Expected: `All tests passed.`

- [ ] **Step 10: Verify syntax of all modified shell scripts**

```sh
bash -n scripts/wispy.sh && echo "wispy.sh OK"
bash -n scripts/build.sh && echo "build.sh OK"
bash -n scripts/setup.sh && echo "setup.sh OK"
bash -n scripts/wispy-toggle.sh && echo "wispy-toggle.sh OK"
```

- [ ] **Step 11: Verify Python syntax**

```sh
.venv/bin/python -c "import ast; ast.parse(open('src/main.py').read()); print('main.py OK')"
```

- [ ] **Step 12: Commit**

```bash
git add -A
git commit -m "refactor: reorganize root into src/, scripts/, assets/, system/, tests/"
```

---

## Task 2: Invert Icon Colors to Black Theme

**Files:**
- Modify: `assets/wispy.svg` — swap fill colors
- Modify: `src/main.py` — swap QColor values in `_draw_icon()`

**Interfaces:**
- None (visual only)

- [ ] **Step 1: Invert `assets/wispy.svg` colors**

Replace the entire file:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect x="6" y="6" width="52" height="52" rx="14" fill="#1E1E1E"/>
  <rect x="15" y="37" width="5" height="9" rx="2" fill="#F0F0F0"/>
  <rect x="22" y="26" width="5" height="20" rx="2" fill="#F0F0F0"/>
  <rect x="29" y="15" width="5" height="31" rx="2" fill="#F0F0F0"/>
  <rect x="36" y="26" width="5" height="20" rx="2" fill="#F0F0F0"/>
  <rect x="43" y="37" width="5" height="9" rx="2" fill="#F0F0F0"/>
</svg>
```

- [ ] **Step 2: Invert `_draw_icon()` colors in `src/main.py`**

In the `_draw_icon` function, change line 39:

```python
    p.setBrush(QColor(240, 240, 240))
```

to:

```python
    p.setBrush(QColor(30, 30, 30))
```

And change line 46:

```python
    p.setBrush(QColor(30, 30, 30))
```

to:

```python
    p.setBrush(QColor(240, 240, 240))
```

- [ ] **Step 3: Verify Python syntax**

```sh
.venv/bin/python -c "import ast; ast.parse(open('src/main.py').read()); print('OK')"
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python tests/test_wispy.py`
Expected: `All tests passed.`

- [ ] **Step 5: Commit**

```bash
git add assets/wispy.svg src/main.py
git commit -m "ui: invert icon to black theme (dark bg, light bars)"
```

---

## Task 3: Add LLM Constants and Tests (TDD)

Add the `LLM_MODEL` and `CLEAN_PROMPT` constants, plus tests for them, before implementing the feature. This follows TDD — write the test first, then the constants.

**Files:**
- Modify: `tests/test_wispy.py` — add tests for new constants
- Modify: `src/main.py` — add `LLM_MODEL` and `CLEAN_PROMPT` constants

**Interfaces:**
- Produces: `LLM_MODEL` (str), `CLEAN_PROMPT` (str) — module-level constants in `src/main.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_wispy.py`, after the existing imports and before `test_server`:

```python
from main import parse_args, MIN_DURATION, LLM_MODEL, CLEAN_PROMPT
```

Add these test functions (after `test_min_duration`):

```python
def test_llm_model():
    assert isinstance(LLM_MODEL, str) and len(LLM_MODEL) > 0

def test_clean_prompt():
    assert isinstance(CLEAN_PROMPT, str)
    assert "retraction" in CLEAN_PROMPT.lower() or "nevermind" in CLEAN_PROMPT.lower()
```

Add `test_llm_model()` and `test_clean_prompt()` to the `__main__` runner block:

```python
if __name__ == "__main__":
    test_server()
    test_toggle()
    test_no_args_shows_help()
    test_help_subcommand()
    test_min_duration()
    test_llm_model()
    test_clean_prompt()
    print("All tests passed.")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python tests/test_wispy.py`
Expected: FAIL with `ImportError: cannot import name 'LLM_MODEL' from 'main'`

- [ ] **Step 3: Add constants to `src/main.py`**

After the `MIN_DURATION = 2.0` line (line 27), add:

```python
LLM_MODEL = "openai/gpt-oss-20b"

CLEAN_PROMPT = """You are a speech-to-text post-processor. Your input is raw transcribed speech.

Rules:
1. Remove retractions: if the speaker says something then takes it back
   ("wait nevermind", "actually no", "scratch that", "let me rephrase",
   "oh wait I meant"), keep ONLY their final intended message.
2. Format automatically: if the speech naturally describes a list or
   steps, format as bullet/numbered list. If there are distinct topics
   or pauses, add line breaks between them.
3. Fix obvious transcription errors and add proper punctuation.
4. Output ONLY the cleaned text. No explanations, no commentary, no
   meta-text, no quotes around the result."""
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python tests/test_wispy.py`
Expected: `All tests passed.`

- [ ] **Step 5: Commit**

```bash
git add tests/test_wispy.py src/main.py
git commit -m "feat: add LLM_MODEL and CLEAN_PROMPT constants with tests"
```

---

## Task 4: Add `clean_text` Setting to Config and Settings Dialog

Add the `clean_text` config default and the settings UI checkbox.

**Files:**
- Modify: `src/main.py` — `WispyApp._load_config`, `SettingsDialog.__init__`, `SettingsDialog._save`

**Interfaces:**
- Produces: `config["clean_text"]` (bool, default: False)

- [ ] **Step 1: Add `clean_text` default to `_load_config`**

In `src/main.py`, in the `_load_config` method, change:

```python
    def _load_config(self) -> dict:
        d = {"groq_api_key": os.environ.get("GROQ_API_KEY", ""),
             "groq_model": MODELS[0], "language": ""}
```

to:

```python
    def _load_config(self) -> dict:
        d = {"groq_api_key": os.environ.get("GROQ_API_KEY", ""),
             "groq_model": MODELS[0], "language": "",
             "clean_text": False}
```

- [ ] **Step 2: Add checkbox to `SettingsDialog.__init__`**

In the Behavior section, after the `copy_clipboard` checkbox and before the Buttons section, add:

```python
        self.clean_text = QCheckBox("Clean and format text with AI")
        self.clean_text.setChecked(config.get("clean_text", False))
        form.addRow(self.clean_text)
```

Insert this between the `form.addRow(self.copy_clipboard)` line and the `# ── Buttons ──` comment.

- [ ] **Step 3: Add save logic to `SettingsDialog._save`**

In `_save`, after the `copy_to_clipboard` line, add:

```python
        self.config["clean_text"] = self.clean_text.isChecked()
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python tests/test_wispy.py`
Expected: `All tests passed.`

- [ ] **Step 5: Commit**

```bash
git add src/main.py
git commit -m "feat: add clean_text setting to config and settings dialog"
```

---

## Task 5: Implement LLM Post-Processing in `_transcribe_and_inject`

Add the `_clean_text` method and wire it into the transcription pipeline.

**Files:**
- Modify: `src/main.py` — add `_clean_text` method, modify `_transcribe_and_inject`

**Interfaces:**
- Consumes: `LLM_MODEL`, `CLEAN_PROMPT` from Task 3, `config["clean_text"]` from Task 4
- Produces: `WispyApp._clean_text(raw_text, key) -> str`

- [ ] **Step 1: Add `_clean_text` method to `WispyApp`**

Add this method after `_close_stream` and before the `# ── transcription & injection` comment:

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

- [ ] **Step 2: Wire LLM step into `_transcribe_and_inject`**

In `_transcribe_and_inject`, after the Whisper transcription returns and before the clipboard/ydotool injection. Change:

```python
                text = result.text.strip()
                if text:
                    if self.config.get("copy_to_clipboard"):
                        self._set_clipboard.emit(text)
```

to:

```python
                text = result.text.strip()
                if text:
                    if self.config.get("clean_text") and len(text.split()) >= 5:
                        try:
                            text = self._clean_text(text, key)
                        except Exception:
                            pass
                    if self.config.get("copy_to_clipboard"):
                        self._set_clipboard.emit(text)
```

- [ ] **Step 3: Verify Python syntax**

```sh
.venv/bin/python -c "import ast; ast.parse(open('src/main.py').read()); print('OK')"
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python tests/test_wispy.py`
Expected: `All tests passed.`

- [ ] **Step 5: Commit**

```bash
git add src/main.py
git commit -m "feat: LLM post-processing for retraction removal and formatting"
```

---

## Task 6: Update Documentation

Update `AGENTS.md` and `README.md` to reflect the new folder structure and the LLM post-processing feature.

**Files:**
- Modify: `AGENTS.md`
- Modify: `README.md`

- [ ] **Step 1: Update `AGENTS.md` architecture section**

Replace the Architecture section (lines 7-16):

```markdown
- `src/main.py` — entry point, CLI (subcommands: `server`, `toggle`, `help`), system tray daemon, Unix-socket IPC (QSocketNotifier, event-loop driven), audio capture (sounddevice), Groq transcription + optional LLM post-processing in background thread, `ydotool` text injection, clipboard copy, settings dialog (device selector, clipboard toggle, clean text toggle), programmatic tray icon
- `src/overlay.py` — frameless always-on-top PyQt6 pill (recording dot, waveform, timer, stop button), dark glass design, equal-gap layout
- IPC: QSocketNotifier monitors `$XDG_RUNTIME_DIR/wispy/wispy.sock` in the Qt event loop (no polling thread); `wispy toggle` sends a toggle message — handled instantly on the main thread
- Audio: 16kHz mono float32 via sounddevice InputStream, converted to WAV int16 for Groq; input device selectable in settings; shared state protected by threading.Lock
- Recording lifecycle: overlay show/hide is immediate (on the GUI thread); the PortAudio stream open/close runs in background daemon threads so device negotiation latency never blocks the UI. Stream-open race (user stops while opening) guarded by `_audio_lock` + `recording` flag check
- LLM post-processing: when `clean_text` is enabled, raw Whisper transcription is sent to Groq `openai/gpt-oss-20b` with a system prompt that removes retractions and auto-formats. Falls back to raw text on error. Skipped for < 5 words.
- Tray icon: drawn programmatically (QPainter) — black rounded square + light sound-wave bars; tries SVG first
- `scripts/wispy.sh` — self-contained launcher (activates venv, runs src/main.py)
- `scripts/wispy-toggle.sh` — instant toggle via system python3 (bypasses PyInstaller extraction)
- `scripts/build.sh` — PyInstaller build for standalone executable
- `scripts/setup.sh` — install/uninstall binary, icon, desktop file, systemd service
- `system/wispy.desktop` — KDE desktop entry for launcher/autostart
- `system/wispy.service` — systemd user service for auto-start on login
- `assets/wispy.svg` — tray icon (black theme)
- `tests/test_wispy.py` — CLI + constant tests
```

- [ ] **Step 2: Update `AGENTS.md` commands section**

Replace the Commands section (lines 18-27):

```sh
./scripts/wispy.sh server       # start daemon
./scripts/wispy.sh toggle       # toggle overlay on running instance
./scripts/wispy.sh help         # show help
./scripts/build.sh              # build standalone executable → dist/wispy
./scripts/setup.sh install --build   # build + install (binary, icons, desktop, service)
./scripts/setup.sh uninstall         # remove installed files
```

- [ ] **Step 3: Update `AGENTS.md` test command**

Replace line 29:

```sh
No lint command. Run `.venv/bin/python tests/test_wispy.py` for CLI + constant tests.
```

- [ ] **Step 4: Update `README.md` quick start**

Replace line 26:

```sh
./scripts/wispy.sh server
```

- [ ] **Step 5: Update `README.md` install section**

Replace lines 46-52:

```sh
# Build + install (binary, icon, desktop file, systemd service)
./scripts/setup.sh install --build

# Install without building (uses wispy.sh launcher)
./scripts/setup.sh install

# Remove everything
./scripts/setup.sh uninstall
```

Replace line 55:

```sh
Manual build only: `./scripts/build.sh` → `dist/wispy`
```

- [ ] **Step 6: Update `README.md` settings list**

Replace lines 74-78:

```
- Groq API key
- Whisper model (`whisper-large-v3`, `whisper-large-v3-turbo`, `distil-whisper-large-v3-en`)
- Language (optional, e.g. `en`)
- Input device (system default or specific mic)
- Copy transcribed text to clipboard (on/off)
- Clean and format text with AI (on/off)
```

- [ ] **Step 7: Update `README.md` config.json example**

Replace lines 83-89:

```json
{
  "groq_api_key": "gsk_...",
  "groq_model": "whisper-large-v3",
  "language": "en",
  "input_device": "",
  "copy_to_clipboard": false,
  "clean_text": false
}
```

- [ ] **Step 8: Show AGENTS.md changes to user (project convention)**

Per the project convention "Run `AGENTS.md` updates past the user before committing", show the user the AGENTS.md diff and get approval before committing.

- [ ] **Step 9: Commit**

```bash
git add AGENTS.md README.md
git commit -m "docs: update for new folder structure and LLM post-processing feature"
```

---

## Self-Review

### 1. Spec coverage

| Spec requirement | Task |
|------------------|------|
| Reorganize root into src/, scripts/, assets/, system/, tests/ | Task 1 |
| Rewire all path references | Task 1 (wispy.sh, main.py, build.sh, wispy.spec, setup.sh, test_wispy.py) |
| Invert wispy.svg colors to black theme | Task 2 |
| Invert _draw_icon() colors to black theme | Task 2 |
| LLM_MODEL constant | Task 3 |
| CLEAN_PROMPT constant | Task 3 |
| clean_text config default (false) | Task 4 |
| Settings dialog checkbox | Task 4 |
| _clean_text method | Task 5 |
| Wire LLM into _transcribe_and_inject with short-circuit (< 5 words) | Task 5 |
| Error handling (fall back to raw text) | Task 5 |
| Update AGENTS.md | Task 6 |
| Update README.md | Task 6 |
| Test: LLM_MODEL exists | Task 3 |
| Test: CLEAN_PROMPT exists | Task 3 |

### 2. Placeholder scan

No placeholders found. All steps contain exact code or exact file edits.

### 3. Type consistency

- `LLM_MODEL` (str) — defined in Task 3, used in Task 5 `_clean_text`
- `CLEAN_PROMPT` (str) — defined in Task 3, used in Task 5 `_clean_text`
- `config["clean_text"]` (bool) — set in Task 4 `_load_config` and `_save`, read in Task 5 `_transcribe_and_inject`
- `_clean_text(raw_text, key) -> str` — defined in Task 5, called in Task 5
- `ICON_SVG` — modified in Task 1 (path resolution), unchanged by Task 2 (color only)
- All paths use the new structure (`src/`, `scripts/`, `assets/`, `system/`, `tests/`) consistently across all tasks
