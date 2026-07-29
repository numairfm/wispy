# Dark Obsidian UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform Wispy's Qt settings, appearance dialogs, tray context menu, and controls into a sleek, minimalist Dark Obsidian & Indigo Glass UI with rounded corners and generous padding.

**Architecture:** Create `src/styles.py` defining `DARK_THEME_QSS`. Apply `DARK_THEME_QSS` globally to `QApplication` in `src/main.py`. Update form margins, section headers, preview card wrappers, and control spacing in `SettingsDialog` and `AppearanceDialog`.

**Tech Stack:** Python 3, PyQt6 (QSS stylesheet, QFormLayout, QDialog).

## Global Constraints

- Python 3.9+ with PyQt6.
- Existing test suite `.venv/bin/python tests/test_wispy.py` must pass at every task.
- Follow existing code conventions in `src/main.py` and `src/overlay.py`.

---

### Task 1: Create Global Dark Obsidian QSS Module

**Files:**
- Create: `src/styles.py`
- Modify: `src/main.py`
- Test: `tests/test_wispy.py`

**Interfaces:**
- Consumes: None
- Produces: `styles.DARK_THEME_QSS: str`

- [ ] **Step 1: Write the failing test**

Add `test_styles_module()` in `tests/test_wispy.py`:

```python
def test_styles_module():
    import styles
    assert hasattr(styles, "DARK_THEME_QSS")
    assert "background-color: #121318" in styles.DARK_THEME_QSS or "#121318" in styles.DARK_THEME_QSS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python tests/test_wispy.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'styles'`

- [ ] **Step 3: Create `src/styles.py`**

```python
"""
Dark Obsidian & Indigo Glass QSS Stylesheet for Wispy.
"""

DARK_THEME_QSS = """
QDialog {
    background-color: #121318;
    color: #f1f5f9;
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 13px;
}

QWidget {
    color: #f1f5f9;
}

QLabel {
    color: #cbd5e1;
}

QLineEdit {
    background-color: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    padding: 8px 12px;
    color: #f1f5f9;
    selection-background-color: #6366f1;
}

QLineEdit:focus {
    border: 1px solid #6366f1;
    background-color: rgba(255, 255, 255, 0.06);
}

QLineEdit:disabled {
    opacity: 0.5;
    background-color: rgba(255, 255, 255, 0.02);
}

QComboBox {
    background-color: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    padding: 8px 12px;
    color: #f1f5f9;
}

QComboBox:hover {
    background-color: rgba(255, 255, 255, 0.07);
    border: 1px solid rgba(255, 255, 255, 0.18);
}

QComboBox::drop-down {
    border: none;
    padding-right: 10px;
}

QComboBox QAbstractItemView {
    background-color: #1a1b22;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 10px;
    padding: 6px;
    outline: none;
    selection-background-color: rgba(99, 102, 241, 0.3);
    color: #f1f5f9;
}

QPushButton {
    background-color: rgba(255, 255, 255, 0.06);
    color: #cbd5e1;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    padding: 9px 20px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: rgba(255, 255, 255, 0.1);
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.2);
}

QPushButton:pressed {
    background-color: rgba(255, 255, 255, 0.14);
}

QPushButton[default="true"] {
    background-color: #6366f1;
    color: #ffffff;
    border: none;
    font-weight: 600;
}

QPushButton[default="true"]:hover {
    background-color: #4f46e5;
}

QPushButton[default="true"]:pressed {
    background-color: #4338ca;
}

QCheckBox {
    spacing: 8px;
    color: #cbd5e1;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    background-color: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.15);
}

QCheckBox::indicator:hover {
    border: 1px solid #818cf8;
}

QCheckBox::indicator:checked {
    background-color: #6366f1;
    border: 1px solid #6366f1;
}

QSlider::groove:horizontal {
    height: 4px;
    background-color: rgba(255, 255, 255, 0.1);
    border-radius: 2px;
}

QSlider::sub-page:horizontal {
    background-color: #6366f1;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
    background-color: #818cf8;
}

QSlider::handle:horizontal:hover {
    background-color: #a5b4fc;
}

QProgressBar {
    height: 8px;
    background-color: rgba(255, 255, 255, 0.06);
    border-radius: 4px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #6366f1;
    border-radius: 4px;
}

QScrollArea {
    background-color: transparent;
    border: none;
}

QScrollBar:vertical {
    width: 6px;
    background: transparent;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: rgba(255, 255, 255, 0.15);
    border-radius: 3px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: rgba(255, 255, 255, 0.3);
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QMenu {
    background-color: #1a1b22;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 12px;
    padding: 6px;
    color: #f1f5f9;
}

QMenu::item {
    padding: 8px 18px;
    border-radius: 6px;
}

QMenu::item:selected {
    background-color: rgba(99, 102, 241, 0.25);
    color: #ffffff;
}

QMenu::separator {
    height: 1px;
    background-color: rgba(255, 255, 255, 0.08);
    margin: 4px 6px;
}
"""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python tests/test_wispy.py`
Expected: PASS ("All tests passed.")

- [ ] **Step 5: Commit changes**

```bash
rtk git add src/styles.py tests/test_wispy.py
rtk git commit -m "feat(ui): add Dark Obsidian QSS design system module"
```

---

### Task 2: Apply Global QSS and Polish Settings & Appearance Dialog Layouts

**Files:**
- Modify: `src/main.py`
- Test: `tests/test_wispy.py`

**Interfaces:**
- Consumes: `styles.DARK_THEME_QSS`
- Produces: Polished `SettingsDialog`, `AppearanceDialog`, `_section_label` styling

- [ ] **Step 1: Write the failing test**

Add `test_app_qss_applied()` in `tests/test_wispy.py`:

```python
def test_app_qss_applied():
    from main import WispyApp
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    wispy_app = WispyApp()
    assert len(wispy_app.app.styleSheet()) > 0
```

- [ ] **Step 2: Apply QSS and update dialog layout styling in `src/main.py`**

1. Import `DARK_THEME_QSS` in `src/main.py`:
```python
from styles import DARK_THEME_QSS
```

2. In `WispyApp.__init__`:
```python
self.app.setStyleSheet(DARK_THEME_QSS)
```

3. Update `_section_label(text)`:
```python
def _section_label(text):
    lbl = QLabel(text.upper())
    lbl.setStyleSheet(
        "color: #818cf8; font-size: 11px; font-weight: 700; "
        "letter-spacing: 1px; margin-top: 14px; margin-bottom: 2px;"
    )
    return lbl
```

4. Update `SettingsDialog`:
   - Set content margins: `form.setContentsMargins(28, 24, 28, 24)`
   - Set vertical spacing: `form.setVerticalSpacing(12)`
   - Minimum width: `480`

5. Update `AppearanceDialog`:
   - Set content margins: `root.setContentsMargins(28, 24, 28, 24)`
   - Wrap `OverlayPreview` in a styled card box widget:
     `preview_card.setStyleSheet("background-color: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 14px; padding: 16px;")`
   - Form layout vertical spacing: `10`
   - Minimum width: `540`

- [ ] **Step 3: Run test to verify it passes**

Run: `.venv/bin/python tests/test_wispy.py`
Expected: PASS ("All tests passed.")

- [ ] **Step 4: Commit changes**

```bash
rtk git add src/main.py tests/test_wispy.py
rtk git commit -m "feat(ui): apply global Dark Obsidian QSS and polish dialog padding and card wrappers"
```

---

### Task 3: Complete Test Suite Verification

- [ ] **Step 1: Run complete test suite**

Run: `.venv/bin/python tests/test_wispy.py`
Expected: All tests pass cleanly.
