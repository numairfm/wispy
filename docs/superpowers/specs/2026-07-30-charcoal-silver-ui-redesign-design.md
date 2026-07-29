# Design Spec: Wispy Dark Charcoal & White Silver Accent UI Redesign

Date: 2026-07-30
Status: Approved

## Overview

This specification details the transition of Wispy's QSS stylesheet and component layouts to a clean, high-contrast Dark Charcoal & White Silver design system (`#18181b` base, `#27272a` surfaces, `#3f3f46` borders, `#ffffff` white/silver primary accents).

---

## 1. Design System Tokens (`src/styles.py`)

### 1.1 Color Tokens
- **Background Base**: `#18181b` (Dark Charcoal / Zinc 900)
- **Surface / Controls**: `#27272a` (Zinc 800)
- **Borders & Outlines**: `#3f3f46` (Zinc 700)
- **Primary Accent**: `#ffffff` (Pure White)
- **Accent Hover**: `#e4e4e7` (Silver / Zinc 200)
- **Text Main**: `#f4f4f5` (Zinc 100)
- **Text Muted**: `#a1a1aa` (Zinc 400)
- **Section Headers**: `#ffffff` (Pure White 11px uppercase bold)

### 1.2 Widget Specifications
- **`QDialog`**: Background `#18181b`, text `#f4f4f5`, border `1px solid #3f3f46`, radius `14px`.
- **`QLineEdit` & `QComboBox`**: Background `#27272a`, border `1px solid #3f3f46`, radius `10px`, padding `8px 12px`, color `#f4f4f5`. Focus state: `border: 1px solid #ffffff`.
- **`QComboBox QAbstractItemView`**: Background `#18181b`, border `1px solid #3f3f46`, radius `10px`, padding `6px`, selection background `#3f3f46`, selection text `#ffffff`.
- **`QPushButton`**:
  - Primary (Save / Default): `background: #ffffff; color: #18181b; border-radius: 10px; padding: 9px 20px; font-weight: 600; border: none;` (hover: `#e4e4e7`).
  - Secondary (Cancel / Reset): `background: #27272a; color: #e4e4e7; border: 1px solid #3f3f46; border-radius: 10px; padding: 9px 20px; font-weight: 500;` (hover: `#3f3f46`).
- **`QCheckBox`**: Indicator `#27272a`, border `1px solid #3f3f46`, radius `5px`. Checked: `background: #ffffff; border-color: #ffffff;`.
- **`QSlider`**: Groove `#27272a`, active sub-page `#ffffff`, handle `#ffffff` (hover `#e4e4e7`).
- **`QProgressBar`**: Track `#27272a`, chunk `#ffffff`.
- **`QMenu`**: Background `#18181b`, border `1px solid #3f3f46`, radius `12px`, item selection `#27272a`.

---

## 2. Layout & Card Adjustments (`src/main.py`)

- Update `_section_label(text)` color to `#ffffff`.
- Update `AppearanceDialog` preview card box: `background-color: #27272a; border: 1px solid #3f3f46; border-radius: 14px; padding: 16px;`.

---

## 3. Verification Plan

1. Run test suite `.venv/bin/python tests/test_wispy.py`.
2. Launch Wispy server and inspect Settings & Appearance dialogs.
