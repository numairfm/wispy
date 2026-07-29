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
