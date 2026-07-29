# Dark Charcoal & White Silver UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign Wispy's QSS design system and dialog styling to Dark Charcoal (`#18181b`) and White Silver (`#ffffff` / `#f4f4f5` accent).

**Architecture:** Update `DARK_THEME_QSS` in `src/styles.py` with Dark Charcoal background (`#18181b`), control surfaces (`#27272a`), borders (`#3f3f46`), and pure white accents (`#ffffff`). Update `_section_label` and preview card box styling in `src/main.py`.

**Tech Stack:** Python 3, PyQt6 (QSS stylesheet, QFormLayout, QDialog).

## Global Constraints

- Python 3.9+ with PyQt6.
- Existing test suite `.venv/bin/python tests/test_wispy.py` must pass at every task.
- Follow existing code conventions in `src/styles.py`, `src/main.py`, and `tests/test_wispy.py`.

---

### Task 1: Update QSS Design System to Dark Charcoal & White Silver

**Files:**
- Modify: `src/styles.py`
- Test: `tests/test_wispy.py`

**Interfaces:**
- Consumes: None
- Produces: Updated `styles.DARK_THEME_QSS` (`#18181b` background, `#ffffff` primary accent)

- [ ] **Step 1: Write the failing test**

Update `test_styles_module()` in `tests/test_wispy.py`:

```python
def test_styles_module():
    import styles
    assert hasattr(styles, "DARK_THEME_QSS")
    assert "background-color: #18181b" in styles.DARK_THEME_QSS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python tests/test_wispy.py`
Expected: FAIL with `AssertionError: assert 'background-color: #18181b' in ...`

- [ ] **Step 3: Update `src/styles.py`**

```python
"""
Dark Charcoal & White Silver Accent QSS Stylesheet for Wispy.
"""

DARK_THEME_QSS = """
QDialog {
    background-color: #18181b;
    color: #f4f4f5;
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 13px;
}

QWidget {
    color: #f4f4f5;
}

QLabel {
    color: #e4e4e7;
}

QLineEdit {
    background-color: #27272a;
    border: 1px solid #3f3f46;
    border-radius: 10px;
    padding: 8px 12px;
    color: #f4f4f5;
    selection-background-color: #ffffff;
    selection-color: #18181b;
}

QLineEdit:focus {
    border: 1px solid #ffffff;
    background-color: #27272a;
}

QLineEdit:disabled {
    opacity: 0.5;
    background-color: #18181b;
}

QComboBox {
    background-color: #27272a;
    border: 1px solid #3f3f46;
    border-radius: 10px;
    padding: 8px 12px;
    color: #f4f4f5;
}

QComboBox:hover {
    background-color: #3f3f46;
    border: 1px solid #52525b;
}

QComboBox::drop-down {
    border: none;
    padding-right: 10px;
}

QComboBox QAbstractItemView {
    background-color: #18181b;
    border: 1px solid #3f3f46;
    border-radius: 10px;
    padding: 6px;
    outline: none;
    selection-background-color: #3f3f46;
    selection-color: #ffffff;
    color: #f4f4f5;
}

QPushButton {
    background-color: #27272a;
    color: #e4e4e7;
    border: 1px solid #3f3f46;
    border-radius: 10px;
    padding: 9px 20px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #3f3f46;
    color: #ffffff;
    border: 1px solid #52525b;
}

QPushButton:pressed {
    background-color: #52525b;
}

QPushButton[default="true"] {
    background-color: #ffffff;
    color: #18181b;
    border: none;
    font-weight: 600;
}

QPushButton[default="true"]:hover {
    background-color: #e4e4e7;
}

QPushButton[default="true"]:pressed {
    background-color: #d4d4d8;
}

QCheckBox {
    spacing: 8px;
    color: #e4e4e7;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    background-color: #27272a;
    border: 1px solid #3f3f46;
}

QCheckBox::indicator:hover {
    border: 1px solid #ffffff;
}

QCheckBox::indicator:checked {
    background-color: #ffffff;
    border: 1px solid #ffffff;
}

QSlider::groove:horizontal {
    height: 4px;
    background-color: #27272a;
    border-radius: 2px;
}

QSlider::sub-page:horizontal {
    background-color: #ffffff;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
    background-color: #ffffff;
}

QSlider::handle:horizontal:hover {
    background-color: #e4e4e7;
}

QProgressBar {
    height: 8px;
    background-color: #27272a;
    border-radius: 4px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #ffffff;
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
    background: #3f3f46;
    border-radius: 3px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #52525b;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QMenu {
    background-color: #18181b;
    border: 1px solid #3f3f46;
    border-radius: 12px;
    padding: 6px;
    color: #f4f4f5;
}

QMenu::item {
    padding: 8px 18px;
    border-radius: 6px;
}

QMenu::item:selected {
    background-color: #27272a;
    color: #ffffff;
}

QMenu::separator {
    height: 1px;
    background-color: #3f3f46;
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
rtk git commit -m "feat(ui): update QSS design system to Dark Charcoal & White Silver Accent"
```

---

### Task 2: Update Main Layout Helpers & Preview Card Styling

**Files:**
- Modify: `src/main.py`
- Test: `tests/test_wispy.py`

**Interfaces:**
- Consumes: None
- Produces: Updated `_section_label` color `#ffffff` and `AppearanceDialog` card box styling

- [ ] **Step 1: Write the failing test**

Update `test_app_qss_applied()` in `tests/test_wispy.py` to verify `#18181b` in stylesheet.

- [ ] **Step 2: Update `src/main.py`**

1. Update `_section_label`:
```python
def _section_label(text):
    lbl = QLabel(text.upper())
    lbl.setStyleSheet(
        "color: #ffffff; font-size: 11px; font-weight: 700; "
        "letter-spacing: 1px; margin-top: 14px; margin-bottom: 2px;"
    )
    return lbl
```

2. Update `AppearanceDialog` preview card:
```python
preview_card.setStyleSheet(
    "background-color: #27272a; "
    "border: 1px solid #3f3f46; "
    "border-radius: 14px; padding: 16px;"
)
```

- [ ] **Step 3: Run test to verify it passes**

Run: `.venv/bin/python tests/test_wispy.py`
Expected: PASS ("All tests passed.")

- [ ] **Step 4: Commit changes**

```bash
rtk git add src/main.py tests/test_wispy.py
rtk git commit -m "feat(ui): update section headers and card containers to Charcoal & White Silver theme"
```

---

### Task 3: Complete Test Suite Verification

- [ ] **Step 1: Run complete test suite**

Run: `.venv/bin/python tests/test_wispy.py`
Expected: All tests pass cleanly.
