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
    background-color: #22c55e;
    border: 1px solid #22c55e;
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
