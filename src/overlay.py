import math
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QFont, QPen

# ponytail: overlay appearance defaults, all tunable via config overlay.* keys
OVERLAY_DEFAULTS = {
    "width": 204,
    "height": 36,
    "corner_radius": 18,
    "bg_color": [0, 0, 0],
    "bg_alpha": 230,
    "border_color": [255, 255, 255],
    "border_alpha": 14,
    "dot_color": [255, 255, 255],
    "bar_color": [255, 255, 255],
    "bar_width": 3,
    "bar_gap": 2,
    "bar_count": 14,
    "bar_max_height": 6,
    "bar_fade_min": 0.35,
    "timer_alpha": 130,
    "timer_font_size": 8,
    "button_outline_alpha": 160,
    "button_fill_alpha": 20,
    "button_radius": 6,
    "button_corner_radius": 3,
    "section_gap": 9,
}


def _compute_layout(ap: dict) -> dict:
    """Center all elements within the pill. ponytail: one function."""
    w = ap["width"]
    gap = ap["section_gap"]
    n_bars = ap["bar_count"]
    bw, bg = ap["bar_width"], ap["bar_gap"]
    dot_r = ap["corner_radius"] // 4
    bt_r = ap["button_radius"]
    tm_w = 40
    wf_w = n_bars * (bw + bg)

    # total content width: dot + 3 gaps + waveform + timer + button
    total = 2 * dot_r + gap + wf_w + gap + tm_w + gap + 2 * bt_r

    # center within pill interior (drawn from x=1 to x=w-2)
    # clamp to prevent negative positions when content overflows
    start = max(1.0, 1.0 + ((w - 2) - total) / 2)

    dot_x = start + dot_r
    wf_l = dot_x + dot_r + gap
    wf_r = wf_l + wf_w
    tm_l = wf_r + gap
    bt_x = tm_l + tm_w + gap + bt_r

    return {
        "w": w, "h": ap["height"],
        "dot_x": int(dot_x), "wf_l": int(wf_l), "wf_r": int(wf_r),
        "tm_l": int(tm_l), "tm_w": tm_w, "bt_x": int(bt_x),
    }


class OverlayWindow(QWidget):
    def __init__(self, on_stop, level_getter, appearance=None):
        super().__init__()
        self.on_stop = on_stop
        self.get_level = level_getter
        self.state = "recording"
        self.elapsed_ticks = 0

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Dialog
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.apply_appearance(appearance or {})
        self._ui = QTimer(self)
        self._ui.timeout.connect(self._tick)
        self._ui.setInterval(50)

        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            self.setGeometry(
                geom.center().x() - self._ap["width"] // 2,
                geom.bottom() - self._ap["height"] - 50,
                self._ap["width"], self._ap["height"],
            )

    def apply_appearance(self, appearance: dict):
        self._ap = {**OVERLAY_DEFAULTS, **appearance}
        self._lay = _compute_layout(self._ap)
        self.levels = [0.0] * self._ap["bar_count"]
        self.setFixedSize(self._ap["width"], self._ap["height"])
        if self.isVisible():
            self.update()

    def set_state(self, state: str):
        self.state = state
        self.update()

    def reset(self):
        self.state = "recording"
        self.levels = [0.0] * self._ap["bar_count"]
        self.elapsed_ticks = 0
        self._ui.start()

    def _tick(self):
        self.elapsed_ticks += 1
        self.levels = self.levels[1:] + [self.get_level()]
        self.update()

    # ── paint ───────────────────────────────────────────────────

    def paintEvent(self, event):
        ap, lay = self._ap, self._lay
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cy = ap["height"] // 2

        # pill bg
        bc = ap["border_color"]
        p.setPen(QPen(QColor(bc[0], bc[1], bc[2], ap["border_alpha"]), 1))
        bgc = ap["bg_color"]
        p.setBrush(QColor(bgc[0], bgc[1], bgc[2], ap["bg_alpha"]))
        p.drawRoundedRect(1, 1, lay["w"] - 2, ap["height"] - 2,
                          ap["corner_radius"], ap["corner_radius"])

        if self.state == "transcribing":
            # status dot (blue)
            a = int(180 + 75 * math.sin(self.elapsed_ticks * 0.15))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(100, 160, 255, a))
            dot_r = ap["corner_radius"] // 4
            p.drawEllipse(lay["dot_x"] - dot_r, cy - dot_r, dot_r * 2, dot_r * 2)

            # "Transcribing…" text
            alpha = int(160 + 75 * math.sin(self.elapsed_ticks * 0.15))
            p.setPen(QColor(255, 255, 255, alpha))
            p.setFont(QFont("sans-serif", 9))
            text_x = lay["wf_l"]
            text_w = lay["bt_x"] - lay["wf_l"]
            p.drawText(text_x, 0, text_w, ap["height"],
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter,
                       "Transcribing…")
            return

        if self.state == "corrected":
            # green dot — cloud retry succeeded, clipboard upgraded
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(76, 175, 80, 230))
            dot_r = ap["corner_radius"] // 4
            p.drawEllipse(lay["dot_x"] - dot_r, cy - dot_r, dot_r * 2, dot_r * 2)

            p.setPen(QColor(255, 255, 255, 220))
            p.setFont(QFont("sans-serif", 9))
            text_x = lay["wf_l"]
            text_w = lay["bt_x"] - lay["wf_l"]
            p.drawText(text_x, 0, text_w, ap["height"],
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter,
                       "Corrected✓")
            return

        # recording dot
        a = int(180 + 75 * math.sin(self.elapsed_ticks * 0.15))
        dc = ap["dot_color"]
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(dc[0], dc[1], dc[2], a))
        dot_r = ap["corner_radius"] // 4
        p.drawEllipse(lay["dot_x"] - dot_r, cy - dot_r, dot_r * 2, dot_r * 2)

        # waveform
        n_bars = ap["bar_count"]
        bw, bh_max = ap["bar_width"], ap["bar_max_height"]
        bgap, fade_min = ap["bar_gap"], ap["bar_fade_min"]
        brc = ap["bar_color"]
        for i in range(n_bars):
            idx = len(self.levels) - n_bars + i
            lvl = self.levels[idx]
            dist = abs(i - n_bars // 2) / max(1, n_bars // 2)
            fade = fade_min + (1.0 - fade_min) * (1.0 - dist)
            al = int(max(20, fade * 200))
            p.setBrush(QColor(brc[0], brc[1], brc[2], al))
            bh = max(1, int(lvl * bh_max))
            x = lay["wf_l"] + i * (bw + bgap)
            p.drawRoundedRect(x, cy - bh, bw, bh * 2, 1, 1)

        # timer
        secs = self.elapsed_ticks // 20
        p.setPen(QColor(255, 255, 255, ap["timer_alpha"]))
        p.setFont(QFont("monospace", ap["timer_font_size"]))
        p.drawText(lay["tm_l"], 0, lay["tm_w"], ap["height"],
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter,
                   f"{secs // 60:02d}:{secs % 60:02d}")

        # stop button
        bt_r = ap["button_radius"]
        bt_cr = ap["button_corner_radius"]
        p.setPen(QPen(QColor(255, 255, 255, ap["button_outline_alpha"]), 1.5))
        p.setBrush(QColor(255, 255, 255, ap["button_fill_alpha"]))
        p.drawRoundedRect(lay["bt_x"] - bt_r, cy - bt_r,
                          bt_r * 2, bt_r * 2, bt_cr, bt_cr)
        pad = 2
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, ap["button_outline_alpha"]))
        p.drawRoundedRect(lay["bt_x"] - bt_r + pad, cy - bt_r + pad,
                          (bt_r - pad) * 2, (bt_r - pad) * 2, 1, 1)

    # ── drag (Wayland: startSystemMove) ─────────────────────────

    def mousePressEvent(self, event):
        if self.state == "transcribing":
            return
        if event.button() == Qt.MouseButton.LeftButton:
            bt_r = self._ap["button_radius"]
            dx = event.position().x() - self._lay["bt_x"]
            dy = event.position().y() - self._ap["height"] // 2
            if dx * dx + dy * dy <= bt_r * bt_r:
                self._ui.stop()
                self.hide()
                self.on_stop()
            else:
                wh = self.windowHandle()
                if wh:
                    wh.startSystemMove()
