# Output Mode Injection & Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add configurable output modes (`paste`, `type`, `copy`) with automatic `Ctrl+V` clipboard pasting as the default injection method in Wispy.

**Architecture:** Extend `Injector.inject` in `src/injector.py` to support `mode="paste"|"type"|"copy"`. Update `WispyApp` and `SettingsDialog` in `src/main.py` to add `"output_mode"` config setting and handle automatic clipboard updates and mode selection.

**Tech Stack:** Python 3, PyQt6, subprocess (`ydotool`).

## Global Constraints

- Python 3.9+ with PyQt6.
- Existing test suite `.venv/bin/python tests/test_wispy.py` must pass at every task.
- Follow existing code conventions in `src/injector.py` and `src/main.py`.

---

### Task 1: Update Injector to Support Output Modes

**Files:**
- Modify: `src/injector.py:6-21`
- Test: `tests/test_wispy.py`

**Interfaces:**
- Consumes: None
- Produces: `Injector.inject(text: str, mode: str = "paste", send_enter: bool = False)`

- [ ] **Step 1: Write the failing test**

Add `test_injector_modes()` in `tests/test_wispy.py`:

```python
def test_injector_modes():
    from unittest.mock import patch
    from injector import Injector
    inj = Injector()

    with patch("subprocess.run") as mock_run:
        # paste mode
        inj.inject("hello", mode="paste", send_enter=False)
        mock_run.assert_called_once_with(
            ["ydotool", "key", "29:1", "47:1", "47:0", "29:0"],
            check=True, capture_output=True, timeout=5,
        )

    with patch("subprocess.run") as mock_run:
        # copy mode (no subprocess call)
        inj.inject("hello", mode="copy", send_enter=False)
        mock_run.assert_not_called()

    with patch("subprocess.run") as mock_run:
        # type mode
        inj.inject("hello", mode="type", send_enter=False)
        mock_run.assert_called_once_with(
            ["ydotool", "type", "-d", "1", "-H", "1", "hello"],
            check=True, capture_output=True, timeout=60,
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python tests/test_wispy.py`
Expected: FAIL with `TypeError: inject() got an unexpected keyword argument 'mode'`

- [ ] **Step 3: Implement mode support in `src/injector.py`**

Update `Injector.inject`:

```python
import subprocess
from exceptions import InjectError


class Injector:
    def inject(self, text, mode="paste", send_enter=False):
        try:
            if mode == "paste":
                subprocess.run(
                    ["ydotool", "key", "29:1", "47:1", "47:0", "29:0"],
                    check=True, capture_output=True, timeout=5,
                )
            elif mode == "type":
                subprocess.run(
                    ["ydotool", "type", "-d", "1", "-H", "1", text],
                    check=True, capture_output=True, timeout=60,
                )
            elif mode == "copy":
                pass

            if send_enter:
                subprocess.run(
                    ["ydotool", "key", "28:1", "28:0"],
                    check=True, capture_output=True, timeout=5,
                )
        except FileNotFoundError:
            raise InjectError("ydotool not found — install it")
        except subprocess.CalledProcessError as e:
            raise InjectError(f"Injection failed: {e}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python tests/test_wispy.py`
Expected: PASS ("All tests passed.")

- [ ] **Step 5: Commit changes**

```bash
rtk git add src/injector.py tests/test_wispy.py
rtk git commit -m "feat(injector): add paste, type, and copy output modes"
```

---

### Task 2: Settings UI & Application Workflow Integration

**Files:**
- Modify: `src/main.py`
- Test: `tests/test_wispy.py`

**Interfaces:**
- Consumes: `Injector.inject(mode=...)`
- Produces: `"output_mode"` config setting in `SettingsDialog` and `_transcribe_and_inject`

- [ ] **Step 1: Write the failing test**

Add `test_config_output_mode()` in `tests/test_wispy.py`:

```python
def test_config_output_mode():
    from main import WispyApp
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    wispy_app = WispyApp()
    assert wispy_app.config.get("output_mode") in ("paste", "type", "copy", None)
```

- [ ] **Step 2: Run test to verify it fails/runs**

Run: `.venv/bin/python tests/test_wispy.py`

- [ ] **Step 3: Update `src/main.py`**

1. In `_load_config()`: set default `"output_mode": "paste"`.
2. In `_transcribe_and_inject(self, buffer)`:
```python
output_mode = self.config.get("output_mode", "paste")
if output_mode in ("paste", "copy") or self.config.get("copy_to_clipboard"):
    self._set_clipboard.emit(text)
inj.inject(text, mode=output_mode, send_enter=self.config.get("send_enter", False))
```
3. In `SettingsDialog`:
   Under `Behavior` section, add `Output Mode` dropdown:
```python
self.output_mode = QComboBox()
self.output_mode.addItems(["Paste (Clipboard + Ctrl+V)", "Type (character by character)", "Copy to Clipboard Only"])
mode_map = {"paste": 0, "type": 1, "copy": 2}
self.output_mode.setCurrentIndex(mode_map.get(config.get("output_mode", "paste"), 0))
form.addRow("Output Mode", self.output_mode)
```
In `_save(self)`:
```python
mode_rev_map = {0: "paste", 1: "type", 2: "copy"}
self.config["output_mode"] = mode_rev_map[self.output_mode.currentIndex()]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python tests/test_wispy.py`
Expected: PASS ("All tests passed.")

- [ ] **Step 5: Commit changes**

```bash
rtk git add src/main.py tests/test_wispy.py
rtk git commit -m "feat(settings): add output mode setting (paste, type, copy) and automatic paste integration"
```

---

### Task 3: Complete Test Suite Verification

- [ ] **Step 1: Run complete test suite**

Run: `.venv/bin/python tests/test_wispy.py`
Expected: All tests pass cleanly.
