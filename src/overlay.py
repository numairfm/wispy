import math
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QFont, QPen

# Layout — equal 9px gaps, 6px side margins
_W = 204
_H = 36
_R = 18
_DOT_X = 27
_WF_L = 39
_N_BARS = 14
_BAR_W = 3
_BAR_GAP = 2
_WF_W = _N_BARS * (_BAR_W + _BAR_GAP)  # 70
_WF_R = _WF_L + _WF_W                   # 109
_TM_L = _WF_R + 9                        # 118
_TM_W = 40
_TM_R = _TM_L + _TM_W                    # 158
_BT_X = _TM_R + 9 + 6                    # 173
_BT_R = 6
_DOT_R = 3
_MAX_BAR_H = 6


class OverlayWindow(QWidget):
    _transcribing_signal = pyqtSignal(bool)

    def __init__(self, on_stop, level_getter):
        super().__init__()
        self.on_stop = on_stop
        self.get_level = level_getter
        self._transcribing = False
        self._transcribing_signal.connect(self._on_transcribing)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Dialog
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedSize(_W, _H)

        self.levels = [0.0] * _N_BARS
        self.elapsed_ticks = 0

        self._ui = QTimer(self)
        self._ui.timeout.connect(self._tick)
        self._ui.setInterval(50)

        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            self.setGeometry(
                geom.center().x() - _W // 2,
                geom.bottom() - _H - 50,
                _W, _H,
            )

    def reset(self):
        self.levels = [0.0] * _N_BARS
        self.elapsed_ticks = 0
        self._transcribing = False
        self._ui.start()

    def set_transcribing(self, active):
        self._transcribing = active
        self.update()

    def _on_transcribing(self, active):
        self._transcribing = active
        self.update()

    def _tick(self):
        self.elapsed_ticks += 1
        self.levels = self.levels[1:] + [self.get_level()]
        self.update()

    # ── paint ───────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cy = _H // 2

        # pill bg
        p.setPen(QPen(QColor(255, 255, 255, 14), 1))
        p.setBrush(QColor(0, 0, 0, 230))
        p.drawRoundedRect(1, 1, _W - 2, _H - 2, _R, _R)

        # recording dot
        a = int(180 + 75 * math.sin(self.elapsed_ticks * 0.15))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, a))
        p.drawEllipse(_DOT_X - _DOT_R, cy - _DOT_R, _DOT_R * 2, _DOT_R * 2)

        # waveform
        for i in range(_N_BARS):
            idx = len(self.levels) - _N_BARS + i
            lvl = self.levels[idx]
            dist = abs(i - _N_BARS // 2) / max(1, _N_BARS // 2)
            fade = 0.35 + 0.65 * (1.0 - dist)
            al = int(max(20, fade * 200))
            p.setBrush(QColor(255, 255, 255, al))
            bh = max(1, int(lvl * _MAX_BAR_H))
            x = _WF_L + i * (_BAR_W + _BAR_GAP)
            p.drawRoundedRect(x, cy - bh, _BAR_W, bh * 2, 1, 1)

        # transcribing indicator
        if self._transcribing:
            p.setPen(QColor(255, 255, 255, 100))
            p.setFont(QFont("monospace", 7))
            p.drawText(_TM_L, 0, _TM_W, _H,
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter,
                       "···")
            return

        # timer
        secs = self.elapsed_ticks // 20
        p.setPen(QColor(255, 255, 255, 130))
        p.setFont(QFont("monospace", 8))
        p.drawText(_TM_L, 0, _TM_W, _H,
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter,
                   f"{secs // 60:02d}:{secs % 60:02d}")

        # stop button
        p.setPen(QPen(QColor(255, 255, 255, 160), 1.5))
        p.setBrush(QColor(255, 255, 255, 20))
        p.drawRoundedRect(_BT_X - _BT_R, cy - _BT_R,
                          _BT_R * 2, _BT_R * 2, 3, 3)
        pad = 2
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 160))
        p.drawRoundedRect(_BT_X - _BT_R + pad, cy - _BT_R + pad,
                          (_BT_R - pad) * 2, (_BT_R - pad) * 2, 1, 1)

    # ── drag (Wayland: startSystemMove) ─────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            dx = event.position().x() - _BT_X
            dy = event.position().y() - _H // 2
            if dx * dx + dy * dy <= _BT_R * _BT_R:
                self._ui.stop()
                self.hide()
                self.on_stop()
            else:
                wh = self.windowHandle()
                if wh:
                    wh.startSystemMove()
