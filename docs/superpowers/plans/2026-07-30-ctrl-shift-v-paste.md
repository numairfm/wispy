# Ctrl+Shift+V Auto-Paste & Simplified Options Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update `Injector` in Wispy to paste via `Ctrl+Shift+V` (`ydotool key 29:1 42:1 47:1 47:0 42:0 29:0`) and simplify the Output Mode setting to `Paste Automatically` and `Save to Clipboard Only`.

**Architecture:** Modify `Injector.inject` in `src/injector.py` to send `Ctrl+Shift+V` key sequence for `"paste"` mode. Update `SettingsDialog` in `src/main.py` to offer 2 simplified dropdown choices. Update unit test assertions in `tests/test_wispy.py`.

**Tech Stack:** Python 3, PyQt6, subprocess (`ydotool`).

## Global Constraints

- Python 3.9+ with PyQt6.
- Existing test suite `.venv/bin/python tests/test_wispy.py` must pass at every task.
- Follow existing code conventions in `src/injector.py` and `src/main.py`.

---

### Task 1: Update Injector to Use Ctrl+Shift+V Key Sequence

**Files:**
- Modify: `src/injector.py`
- Test: `tests/test_wispy.py`

**Interfaces:**
- Consumes: None
- Produces: `Injector.inject(text: str, mode: str = "paste", send_enter: bool = False)` firing `29:1 42:1 47:1 47:0 42:0 29:0` for `"paste"`

- [ ] **Step 1: Write the failing test**

Update `test_injector_modes()` in `tests/test_wispy.py`:

```python
def test_injector_modes():
    from unittest.mock import patch
    from injector import Injector
    inj = Injector()

    with patch("subprocess.run") as mock_run:
        # paste mode (Ctrl+Shift+V)
        inj.inject("hello", mode="paste", send_enter=False)
        mock_run.assert_called_once_with(
            ["ydotool", "key", "29:1", "42:1", "47:1", "47:0", "42:0", "29:0"],
            check=True, capture_output=True, timeout=5,
        )

    with patch("subprocess.run") as mock_run:
        # copy mode (no subprocess call)
        inj.inject("hello", mode="copy", send_enter=False)
        mock_run.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python tests/test_wispy.py`
Expected: FAIL with `AssertionError: Expected call: ['ydotool', 'key', '29:1', '42:1', '47:1', '47:0', '42:0', '29:0']`

- [ ] **Step 3: Update `src/injector.py`**

```python
import subprocess
from exceptions import InjectError


class Injector:
    def inject(self, text, mode="paste", send_enter=False):
        try:
            if mode == "paste":
                subprocess.run(
                    ["ydotool", "key", "29:1", "42:1", "47:1", "47:0", "42:0", "29:0"],
                    check=True, capture_output=True, timeout=5,
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
rtk git commit -m "feat(injector): update paste mode to send Ctrl+Shift+V key sequence"
```

---

### Task 2: Simplify Settings UI Dropdown

**Files:**
- Modify: `src/main.py`
- Test: `tests/test_wispy.py`

**Interfaces:**
- Consumes: None
- Produces: Simplified `SettingsDialog` dropdown (`Paste Automatically`, `Save to Clipboard Only`)

- [ ] **Step 1: Write the failing test**

Update `test_config_output_mode()` in `tests/test_wispy.py` to check `assert wispy_app.config.get("output_mode") in ("paste", "copy")`.

- [ ] **Step 2: Update `src/main.py` SettingsDialog**

```python
self.output_mode = QComboBox()
self.output_mode.addItems(["Paste Automatically (Clipboard + Paste)", "Save to Clipboard Only"])
mode_map = {"paste": 0, "copy": 1}
self.output_mode.setCurrentIndex(mode_map.get(config.get("output_mode", "paste"), 0))
form.addRow("Output Mode", self.output_mode)
```

In `_save(self)`:
```python
mode_rev_map = {0: "paste", 1: "copy"}
self.config["output_mode"] = mode_rev_map.get(self.output_mode.currentIndex(), "paste")
```

- [ ] **Step 3: Run test to verify it passes**

Run: `.venv/bin/python tests/test_wispy.py`
Expected: PASS ("All tests passed.")

- [ ] **Step 4: Commit changes**

```bash
rtk git add src/main.py tests/test_wispy.py
rtk git commit -m "feat(settings): simplify output mode choices to paste and copy only"
```

---

### Task 3: Complete Test Suite Verification

- [ ] **Step 1: Run complete test suite**

Run: `.venv/bin/python tests/test_wispy.py`
Expected: All tests pass cleanly.
