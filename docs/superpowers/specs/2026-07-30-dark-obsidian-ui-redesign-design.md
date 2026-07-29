# Design Spec: Wispy Dark Obsidian & Indigo Glass UI Redesign

Date: 2026-07-30
Status: Approved

## Overview

This specification details a complete UI redesign of Wispy's desktop configuration and appearance dialogs, tray menus, and controls, replacing default Qt/KDE widget styling with a minimalist, high-end Dark Obsidian & Indigo Glass design system.

---

## 1. Design System Tokens (`src/styles.py`)

### 1.1 Color Palette
- **Background Base**: `#121318` (Obsidian dark)
- **Card / Input Surface**: `rgba(255, 255, 255, 0.04)` / `#1a1b22`
- **Border Overlay**: `rgba(255, 255, 255, 0.08)` / `rgba(255, 255, 255, 0.12)`
- **Accent Primary**: `#6366f1` (Indigo primary)
- **Accent Hover / Light**: `#818cf8` / `#4f46e5`
- **Text Main**: `#f1f5f9` (Slate 100)
- **Text Muted / Subtitle**: `#94a3b8` (Slate 400)
- **Section Headers**: `#818cf8` (Indigo 400)

### 1.2 Layout & Geometry
- **Dialog Border Radius**: `14px`
- **Control Border Radius**: `10px` (inputs, combo boxes, buttons)
- **Small Control Radius**: `6px` (checkboxes, handles)
- **Dialog Padding / Margins**: `28px` horizontal, `24px` vertical
- **Control Padding**: `9px 14px` for inputs/combos, `9px 20px` for push buttons

---

## 2. Component Styling Specifications

### 2.1 Main Application QSS (`DARK_THEME_QSS`)
- **`QDialog`**:
  - Background `#121318`, color `#f1f5f9`, border `1px solid rgba(255, 255, 255, 0.08)`, radius `14px`.
- **Section Headers (`_section_label`)**:
  - Font size `11px`, weight `700`, color `#818cf8`, uppercase letter-spacing `1px`, padding `12px 0 4px 0`.
- **`QLineEdit` & `QComboBox`**:
  - Background `rgba(255, 255, 255, 0.04)`, border `1px solid rgba(255, 255, 255, 0.1)`, radius `10px`, padding `8px 12px`, color `#f1f5f9`.
  - Focus state: border `1px solid #6366f1`, background `rgba(255, 255, 255, 0.06)`.
  - `QComboBox` Popup (`QAbstractItemView`): background `#1a1b22`, border `1px solid rgba(255, 255, 255, 0.12)`, radius `10px`, padding `6px`, selection background `rgba(99, 102, 241, 0.25)`.
- **`QPushButton`**:
  - Primary (Save / Default): `background: #6366f1; color: #ffffff; border-radius: 10px; padding: 9px 20px; font-weight: 600; border: none;`
  - Hover: `background: #4f46e5;`
  - Secondary (Cancel / Reset): `background: rgba(255, 255, 255, 0.06); color: #cbd5e1; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 10px; padding: 9px 20px; font-weight: 500;`
- **`QCheckBox`**:
  - Indicator: `width: 18px; height: 18px; border-radius: 5px; background: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.15);`
  - Checked: `background: #6366f1; border-color: #6366f1;`
- **`QSlider`**:
  - Groove: `height: 4px; background: rgba(255, 255, 255, 0.1); border-radius: 2px;`
  - Handle: `width: 16px; height: 16px; margin: -6px 0; border-radius: 8px; background: #818cf8;`
- **`QMenu` (System Tray Menu)**:
  - Background `#1a1b22`, border `1px solid rgba(255, 255, 255, 0.12)`, radius `12px`, padding `6px`.
  - Hover item: `background: rgba(99, 102, 241, 0.25); color: #ffffff; border-radius: 6px;`.

### 2.2 Layout Polish (`src/main.py`)
- Apply `DARK_THEME_QSS` globally to `QApplication` in `WispyApp`.
- Increase `SettingsDialog` and `AppearanceDialog` margins and vertical spacing to give controls breathing room.
- Update `OverlayPreview` container box in `AppearanceDialog` to sit cleanly inside a dark card surface.

---

## 3. Verification Plan

1. Run test suite `.venv/bin/python tests/test_wispy.py` to ensure CLI and logic pass.
2. Launch Wispy server (`./scripts/wispy.sh server`) and open Settings & Appearance dialogs to verify dark obsidian styling, rounded corners, padding, and combo popups.
