#!/usr/bin/env python3
from __future__ import annotations
import os, sys, json, signal, socket, threading, argparse
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QDialog,
    QVBoxLayout, QHBoxLayout, QFormLayout, QScrollArea,
    QLineEdit, QComboBox, QPushButton, QCheckBox, QSlider,
    QLabel, QProgressBar, QWidget, QColorDialog,
)
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QSocketNotifier, QThread
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter, QPen, QFont

from overlay import OVERLAY_DEFAULTS, _compute_layout


def _section_label(text):
    lbl = QLabel(text)
    f = lbl.font()
    f.setBold(True)
    lbl.setFont(f)
    return lbl


CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "wispy"
CONFIG_FILE = CONFIG_DIR / "config.json"
SOCKET_DIR = Path(os.environ.get("XDG_RUNTIME_DIR", Path.home() / ".cache")) / "wispy"
SOCKET_PATH = SOCKET_DIR / "wispy.sock"
def _icon_path():
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / "wispy.svg"
    return Path(__file__).parent.parent / "assets" / "wispy.svg"

ICON_SVG = _icon_path()

MODELS = [
    "whisper-large-v3",
    "whisper-large-v3-turbo",
    "distil-whisper-large-v3-en",
]

LOCAL_MODELS = [
    "tiny",      # ~75MB,  fastest, lowest accuracy
    "tiny.en",   # ~75MB,  fastest, English-only
    "base",      # ~150MB, fast, multilingual
    "base.en",   # ~150MB, fast, English-only
    "small",     # ~500MB, balanced, multilingual
    "small.en",  # ~500MB, balanced, English-only
    "medium",    # ~1.5GB, high accuracy, multilingual
    "medium.en", # ~1.5GB, high accuracy, English-only
    "large-v1",  # ~3GB,   best v1, multilingual
    "large-v2",  # ~3GB,   best v2, multilingual
    "large-v3",  # ~3GB,   best v3, multilingual
]

LOCAL_MODEL_SIZES = {
    "tiny": "~75MB", "tiny.en": "~75MB",
    "base": "~150MB", "base.en": "~150MB",
    "small": "~500MB", "small.en": "~500MB",
    "medium": "~1.5GB", "medium.en": "~1.5GB",
    "large-v1": "~3GB", "large-v2": "~3GB", "large-v3": "~3GB",
}

MIN_DURATION = 2.0


# ── icon helpers ────────────────────────────────────────────────

def _draw_icon(s=64):
    pm = QPixmap(s, s)
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    m = 2
    p.setBrush(QColor(30, 30, 30))
    p.drawRoundedRect(m, m, s - 2 * m, s - 2 * m, s // 5, s // 5)
    bw, bg, n = 5, 5, 5
    total_w = n * bw + (n - 1) * bg
    bx = (s - total_w) // 2
    cy = s // 2
    hs = [9, 17, 26, 17, 9]
    p.setBrush(QColor(240, 240, 240))
    for i, h in enumerate(hs):
        x = bx + i * (bw + bg)
        p.drawRoundedRect(x, cy - h // 2, bw, h, 2, 2)
    p.end()
    return pm


def _make_icon():
    if ICON_SVG.exists():
        ico = QIcon(str(ICON_SVG))
        if not ico.isNull():
            return ico
    ico = QIcon.fromTheme("audio-input-microphone",
                          QIcon.fromTheme("microphone"))
    if not ico.isNull():
        return ico
    ico = QIcon()
    for sz in (16, 22, 32, 64):
        ico.addPixmap(_draw_icon(sz))
    return ico


# ── IPC ─────────────────────────────────────────────────────────

def send_toggle():
    SOCKET_DIR.mkdir(parents=True, exist_ok=True)
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect(str(SOCKET_PATH))
        s.sendall(b"toggle")
        s.close()
        sys.exit(0)
    except (ConnectionRefusedError, FileNotFoundError, socket.timeout, OSError):
        print("wispy: no running instance found")
        sys.exit(1)


# ── model download worker ───────────────────────────────────────

class DownloadWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, model_name, dest_dir, parent=None):
        super().__init__(parent)
        self.model_name = model_name
        self.dest_dir = dest_dir

    def run(self):
        try:
            import io, contextlib
            from huggingface_hub import snapshot_download
            from huggingface_hub.utils import tqdm as hf_tqdm

            worker = self
            repo_id = f"Systran/faster-whisper-{self.model_name}"

            class ProgressTqdm(hf_tqdm):
                def update(self, n=1):
                    super().update(n)
                    if self.total and self.total > 0:
                        worker.progress.emit(int(self.n / self.total * 100))

            kwargs = {"tqdm_class": ProgressTqdm}
            if self.dest_dir:
                kwargs["local_dir"] = self.dest_dir

            # ponytail: suppress noisy huggingface_hub console output
            with contextlib.redirect_stdout(io.StringIO()), \
                 contextlib.redirect_stderr(io.StringIO()):
                path = snapshot_download(repo_id, **kwargs)
            self.finished.emit(path)
        except Exception as e:
            self.error.emit(str(e))


# ── settings dialog ─────────────────────────────────────────────

class SettingsDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Wispy Settings")
        self.setMinimumWidth(420)
        self.setWindowFlags(self.windowFlags()
                            & ~Qt.WindowType.WindowContextHelpButtonHint)

        form = QFormLayout(self)
        form.setContentsMargins(24, 20, 24, 20)
        form.setVerticalSpacing(10)

        # ── Transcription ──
        form.addRow(_section_label("Transcription"))

        self.engine_mode = QComboBox()
        self.engine_mode.addItems(["Online Only (Groq)", "Offline Only (Local)", "Hybrid (Cloud + Fallback)"])
        mode_map = {"online": 0, "offline": 1, "hybrid": 2}
        self.engine_mode.setCurrentIndex(mode_map.get(config.get("engine_mode", "online"), 0))
        self.engine_mode.currentIndexChanged.connect(self._on_engine_changed)
        form.addRow("Engine", self.engine_mode)

        self.api_key = QLineEdit(config.get("groq_api_key", ""))
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("gsk_...")
        form.addRow("Groq API Key", self.api_key)

        self.model = QComboBox()
        self.model.addItems(MODELS)
        cur = config.get("groq_model", MODELS[0])
        if cur in MODELS:
            self.model.setCurrentText(cur)
        form.addRow("Model", self.model)

        self.language = QLineEdit(config.get("language", ""))
        self.language.setPlaceholderText("Optional, e.g. en")
        form.addRow("Language", self.language)

        self.whisper_prompt = QLineEdit(config.get("whisper_prompt", ""))
        self.whisper_prompt.setPlaceholderText("Optional hint for Whisper")
        form.addRow("Whisper Prompt", self.whisper_prompt)

        # ── Local Model ──
        form.addRow(_section_label("Local Model"))

        self.local_model = QComboBox()
        self.local_model.addItems(LOCAL_MODELS)
        cur_local = config.get("local_model", LOCAL_MODELS[0])
        if cur_local in LOCAL_MODELS:
            self.local_model.setCurrentText(cur_local)
        self.local_model.currentTextChanged.connect(self._on_local_model_changed)
        form.addRow("Model", self.local_model)

        dl_row = QHBoxLayout()
        self.dl_btn = QPushButton("Download")
        self.dl_btn.clicked.connect(self._download_model)
        self.dl_progress = QProgressBar()
        self.dl_progress.setVisible(False)
        self.dl_progress.setRange(0, 100)
        dl_row.addWidget(self.dl_btn)
        dl_row.addWidget(self.dl_progress)
        form.addRow(dl_row)

        self.model_status = QLabel("")
        self.model_status.setStyleSheet("color: gray; font-size: 11px;")
        form.addRow(self.model_status)
        self._update_model_status()

        # ── Audio ──
        form.addRow(_section_label("Audio"))

        import sounddevice as sd
        self.device = QComboBox()
        self.device.addItem("System Default", "")
        for i, d in enumerate(sd.query_devices()):
            if d['max_input_channels'] > 0:
                self.device.addItem(d['name'], d['name'])
        cur_dev = config.get("input_device", "")
        if cur_dev:
            idx = self.device.findData(cur_dev)
            if idx >= 0:
                self.device.setCurrentIndex(idx)
        form.addRow("Input Device", self.device)

        # ── Behavior ──
        form.addRow(_section_label("Behavior"))

        self.output_mode = QComboBox()
        self.output_mode.addItems(["Paste Automatically (Clipboard + Paste)", "Save to Clipboard Only"])
        mode_map = {"paste": 0, "copy": 1}
        self.output_mode.setCurrentIndex(mode_map.get(config.get("output_mode", "paste"), 0))
        form.addRow("Output Mode", self.output_mode)

        self.copy_clipboard = QCheckBox("Copy transcribed text to clipboard")
        self.copy_clipboard.setChecked(config.get("copy_to_clipboard", False))
        form.addRow(self.copy_clipboard)

        self.send_enter = QCheckBox("Press Enter after injection")
        self.send_enter.setChecked(config.get("send_enter", False))
        form.addRow(self.send_enter)

        # ── Notifications ──
        form.addRow(_section_label("Notifications"))

        self.notify_errors = QCheckBox("Show error notifications")
        self.notify_errors.setChecked(config.get("notify_errors", True))
        form.addRow(self.notify_errors)

        self.notify_short = QCheckBox("Show 'recording too short' warning")
        self.notify_short.setChecked(config.get("notify_short_recording", True))
        form.addRow(self.notify_short)

        # ── Experimental ──
        form.addRow(_section_label("Experimental"))

        self.clean_text = QCheckBox("AI Clean (punctuation, formatting)")
        self.clean_text.setChecked(config.get("clean_text", False))
        self.clean_text.toggled.connect(self._on_clean_toggled)
        form.addRow(self.clean_text)

        self.clean_prompt = QLineEdit(config.get("clean_prompt", ""))
        self.clean_prompt.setPlaceholderText("System prompt for AI cleanup")
        self.clean_prompt.setEnabled(config.get("clean_text", False))
        form.addRow("Clean Prompt", self.clean_prompt)

        # ── Buttons ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save")
        save.setDefault(True)
        save.clicked.connect(self._save)
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        form.addRow(btn_row)

        self._on_engine_changed(self.engine_mode.currentIndex())

    def _on_engine_changed(self, idx):
        online = idx != 1  # enabled for online(0) and hybrid(2), disabled for offline(1)
        self.api_key.setEnabled(online)
        self.model.setEnabled(online)
        self.language.setEnabled(online)
        self.whisper_prompt.setEnabled(online)

    def _on_clean_toggled(self, checked):
        self.clean_prompt.setEnabled(checked)

    def _on_local_model_changed(self, name):
        self._update_model_status()

    def _update_model_status(self):
        import os
        name = self.local_model.currentText()
        size = LOCAL_MODEL_SIZES.get(name, "")
        pattern = os.path.expanduser(
            f"~/.cache/huggingface/hub/models--Systran--faster-whisper-{name}")
        has_model = False
        if os.path.isdir(pattern):
            for root, dirs, files in os.walk(pattern):
                if any(f == 'model.bin' or f.endswith('.ct2') for f in files):
                    has_model = True
                    break
        if has_model:
            self.model_status.setText(f"✓ {name} ready")
            self.model_status.setStyleSheet("color: green; font-size: 11px;")
            self.dl_btn.setText("Re-download")
        else:
            self.model_status.setText(f"{name} ({size}) — not downloaded yet")
            self.model_status.setStyleSheet("color: gray; font-size: 11px;")
            self.dl_btn.setText("Download")

    def _download_model(self):
        name = self.local_model.currentText()
        self.dl_btn.setEnabled(False)
        self.dl_progress.setValue(0)
        self.dl_progress.setVisible(True)
        self.model_status.setText(f"Downloading {name}…")
        self.model_status.setStyleSheet("color: gray; font-size: 11px;")

        self._download_worker = DownloadWorker(name, "")
        self._download_worker.progress.connect(self.dl_progress.setValue)
        self._download_worker.finished.connect(self._on_download_done)
        self._download_worker.error.connect(self._on_download_error)
        self._download_worker.start()

    def _on_download_done(self, path):
        self.dl_btn.setEnabled(True)
        self.dl_progress.setVisible(False)
        self._update_model_status()

    def _on_download_error(self, msg):
        self.dl_btn.setEnabled(True)
        self.dl_progress.setVisible(False)
        self.model_status.setText(f"Download failed: {msg}")
        self.model_status.setStyleSheet("color: red; font-size: 11px;")

    def _save(self):
        mode_idx = self.engine_mode.currentIndex()
        mode_map = {0: "online", 1: "offline", 2: "hybrid"}
        self.config["engine_mode"] = mode_map[mode_idx]
        self.config["groq_api_key"] = self.api_key.text().strip()
        self.config["groq_model"] = self.model.currentText()
        self.config["language"] = self.language.text().strip()
        self.config["local_model"] = self.local_model.currentText()
        self.config["input_device"] = self.device.currentData() or ""
        self.config["copy_to_clipboard"] = self.copy_clipboard.isChecked()
        mode_rev_map = {0: "paste", 1: "copy"}
        self.config["output_mode"] = mode_rev_map.get(self.output_mode.currentIndex(), "paste")
        self.config["send_enter"] = self.send_enter.isChecked()
        self.config["clean_text"] = self.clean_text.isChecked()
        self.config["clean_prompt"] = self.clean_prompt.text().strip()
        self.config["whisper_prompt"] = self.whisper_prompt.text().strip()
        self.config["notify_errors"] = self.notify_errors.isChecked()
        self.config["notify_short_recording"] = self.notify_short.isChecked()
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=2)
        self.accept()


# ── appearance dialog ───────────────────────────────────────────

class OverlayPreview(QWidget):
    """Renders the overlay at 2x scale for live preview."""
    SCALE = 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ap = dict(OVERLAY_DEFAULTS)
        self._lay = _compute_layout(self._ap)
        w, h = self._ap["width"], self._ap["height"]
        self.setFixedSize(w * self.SCALE, h * self.SCALE)
        self._elapsed = 0
        self._levels = [0.0] * self._ap["bar_count"]

    def set_appearance(self, ap):
        self._ap = dict(OVERLAY_DEFAULTS, **ap)
        self._lay = _compute_layout(self._ap)
        w, h = self._ap["width"], self._ap["height"]
        self.setFixedSize(w * self.SCALE, h * self.SCALE)
        n = self._ap["bar_count"]
        self._levels = [0.0] * n
        self._elapsed = 0
        self.update()

    def paintEvent(self, event):
        import math
        s = self.SCALE
        ap, lay = self._ap, self._lay
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(s, s)
        cy = ap["height"] // 2

        # pill bg
        bc = ap["border_color"]
        p.setPen(QPen(QColor(bc[0], bc[1], bc[2], ap["border_alpha"]), 1))
        bgc = ap["bg_color"]
        p.setBrush(QColor(bgc[0], bgc[1], bgc[2], ap["bg_alpha"]))
        p.drawRoundedRect(1, 1, lay["w"] - 2, ap["height"] - 2,
                          ap["corner_radius"], ap["corner_radius"])

        # recording dot (static, no pulse in preview)
        dc = ap["dot_color"]
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(dc[0], dc[1], dc[2], 200))
        dot_r = ap["corner_radius"] // 4
        p.drawEllipse(lay["dot_x"] - dot_r, cy - dot_r, dot_r * 2, dot_r * 2)

        # waveform (static bars at 60% height for preview)
        n_bars = ap["bar_count"]
        bw, bh_max = ap["bar_width"], ap["bar_max_height"]
        bgap, fade_min = ap["bar_gap"], ap["bar_fade_min"]
        brc = ap["bar_color"]
        for i in range(n_bars):
            dist = abs(i - n_bars // 2) / max(1, n_bars // 2)
            fade = fade_min + (1.0 - fade_min) * (1.0 - dist)
            al = int(max(20, fade * 200))
            p.setBrush(QColor(brc[0], brc[1], brc[2], al))
            bh = max(1, int(0.6 * bh_max))
            x = lay["wf_l"] + i * (bw + bgap)
            p.drawRoundedRect(x, cy - bh, bw, bh * 2, 1, 1)

        # timer
        p.setPen(QColor(255, 255, 255, ap["timer_alpha"]))
        p.setFont(QFont("monospace", ap["timer_font_size"]))
        p.drawText(lay["tm_l"], 0, lay["tm_w"], ap["height"],
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter,
                   "00:05")

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


def _color_btn(initial, on_change):
    """Create a button that shows a color and opens QColorDialog on click."""
    r, g, b = initial
    btn = QPushButton()
    btn.setFixedSize(60, 24)
    btn.setStyleSheet(f"background-color: rgb({r},{g},{b}); border: 1px solid #555;")
    def pick():
        c = QColorDialog.getColor(QColor(r, g, b), btn, "Choose Color",
                                  QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if c.isValid():
            on_change(c.red(), c.green(), c.blue())
            btn.setStyleSheet(
                f"background-color: rgb({c.red()},{c.green()},{c.blue()});"
                " border: 1px solid #555;")
    btn.clicked.connect(pick)
    return btn


class AppearanceDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.ap = dict(OVERLAY_DEFAULTS, **(config.get("overlay") or {}))
        self.setWindowTitle("Overlay Appearance")
        self.setMinimumWidth(500)
        self.setWindowFlags(self.windowFlags()
                            & ~Qt.WindowType.WindowContextHelpButtonHint)
        self._color_btns = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)

        # preview
        self.preview = OverlayPreview()
        self.preview.set_appearance(self.ap)
        root.addWidget(self.preview, alignment=Qt.AlignmentFlag.AlignHCenter)

        # scrollable controls
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(340)
        form = QWidget()
        fl = QFormLayout(form)
        fl.setContentsMargins(8, 8, 8, 8)
        fl.setVerticalSpacing(6)

        # ── Pill ──
        fl.addRow(_section_label("Pill"))
        self._add_slider(fl, "Width", "width", 100, 400)
        self._add_slider(fl, "Height", "height", 24, 80)
        self._add_slider(fl, "Corner Radius", "corner_radius", 4, 40)
        self._add_color(fl, "Background", "bg_color")
        self._add_slider(fl, "Bg Alpha", "bg_alpha", 0, 255)
        self._add_color(fl, "Border", "border_color")
        self._add_slider(fl, "Border Alpha", "border_alpha", 0, 255)

        # ── Dot ──
        fl.addRow(_section_label("Recording Dot"))
        self._add_color(fl, "Color", "dot_color")

        # ── Waveform ──
        fl.addRow(_section_label("Waveform"))
        self._add_color(fl, "Bar Color", "bar_color")
        self._add_slider(fl, "Bar Width", "bar_width", 1, 8)
        self._add_slider(fl, "Bar Gap", "bar_gap", 0, 6)
        self._add_slider(fl, "Bar Count", "bar_count", 4, 30)
        self._add_slider(fl, "Max Bar Height", "bar_max_height", 2, 16)
        self._add_slider(fl, "Fade Minimum", "bar_fade_min", 0, 100, scale=0.01)

        # ── Timer ──
        fl.addRow(_section_label("Timer"))
        self._add_slider(fl, "Alpha", "timer_alpha", 0, 255)
        self._add_slider(fl, "Font Size", "timer_font_size", 6, 14)

        # ── Stop Button ──
        fl.addRow(_section_label("Stop Button"))
        self._add_slider(fl, "Outline Alpha", "button_outline_alpha", 0, 255)
        self._add_slider(fl, "Fill Alpha", "button_fill_alpha", 0, 255)
        self._add_slider(fl, "Radius", "button_radius", 3, 12)
        self._add_slider(fl, "Corner Radius", "button_corner_radius", 0, 6)

        # ── Layout ──
        fl.addRow(_section_label("Layout"))
        self._add_slider(fl, "Section Gap", "section_gap", 4, 20)

        scroll.setWidget(form)
        root.addWidget(scroll)

        # buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        reset = QPushButton("Reset Defaults")
        reset.clicked.connect(self._reset)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save")
        save.setDefault(True)
        save.clicked.connect(self._save)
        btn_row.addWidget(reset)
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        root.addLayout(btn_row)

    def _add_slider(self, form, label, key, lo, hi, scale=1):
        val = self.ap.get(key, OVERLAY_DEFAULTS[key])
        sl = QSlider(Qt.Orientation.Horizontal)
        sl.setRange(lo, hi)
        sl.setValue(int(val / scale) if scale != 1 else val)
        sl.setTickPosition(QSlider.TickPosition.NoTicks)
        sl.setProperty("ap_key", key)
        sl.setProperty("scale", scale)
        lbl_val = QLabel(str(val))
        lbl_val.setFixedWidth(40)
        def update(v, k=key, s=scale, l=lbl_val):
            real = v * s if s != 1 else v
            self.ap[k] = real if s == 1 else round(real, 2)
            l.setText(str(self.ap[k]))
            self.preview.set_appearance(self.ap)
        sl.valueChanged.connect(update)
        row = QHBoxLayout()
        row.addWidget(sl)
        row.addWidget(lbl_val)
        w = QWidget()
        w.setLayout(row)
        form.addRow(label, w)

    def _add_color(self, form, label, key):
        initial = self.ap.get(key, OVERLAY_DEFAULTS[key])
        def change(r, g, b, k=key):
            self.ap[k] = [r, g, b]
            self.preview.set_appearance(self.ap)
        btn = _color_btn(initial, change)
        self._color_btns[key] = btn
        form.addRow(label, btn)

    def _reset(self):
        self.ap = dict(OVERLAY_DEFAULTS)
        self.preview.set_appearance(self.ap)
        for sl in self.findChildren(QSlider):
            key = sl.property("ap_key")
            scale = sl.property("scale")
            if key:
                val = self.ap.get(key, OVERLAY_DEFAULTS.get(key, 0))
                sl.setValue(int(val / scale) if scale else val)
        for key, btn in self._color_btns.items():
            r, g, b = self.ap.get(key, OVERLAY_DEFAULTS[key])
            btn.setStyleSheet(
                f"background-color: rgb({r},{g},{b}); border: 1px solid #555;")

    def _save(self):
        self.config["overlay"] = self.ap
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=2)
        self.accept()


# ── app ─────────────────────────────────────────────────────────

class WispyApp(QObject):
    _notify = pyqtSignal(str, str)
    _set_clipboard = pyqtSignal(str)
    _rec_error = pyqtSignal(str)
    _transcribe_finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.app.setApplicationName("Wispy")
        self.app.setQuitOnLastWindowClosed(False)

        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.config = self._load_config()

        from recorder import Recorder
        self.recorder = Recorder(
            device_name=self.config.get("input_device", ""),
            on_error=lambda msg: self._rec_error.emit(msg),
        )

        from overlay import OverlayWindow
        self.overlay = OverlayWindow(self._stop_recording,
                                     lambda: self.recorder.level(),
                                     self.config.get("overlay"))

        self._notify.connect(self._on_notify)
        self._set_clipboard.connect(self._on_set_clipboard)
        self._rec_error.connect(self._on_rec_error)
        self._transcribe_finished.connect(self._on_transcribe_finished)
        self._setup_tray()
        self._start_ipc()

    def _on_notify(self, title, msg):
        if self.config.get("notify_errors", True):
            self.tray.showMessage(title, msg,
                                  QSystemTrayIcon.MessageIcon.Critical, 5000)

    def _on_set_clipboard(self, text):
        QApplication.clipboard().setText(text)
        try:
            import subprocess
            subprocess.Popen(["wl-copy", text], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def _on_rec_error(self, msg):
        self.overlay.hide()
        if self.config.get("notify_errors", True):
            self.tray.showMessage("Wispy", msg,
                                  QSystemTrayIcon.MessageIcon.Critical, 5000)

    def _on_transcribe_finished(self):
        self.overlay.hide()
        self.overlay.set_state("recording")

    # ── config ──────────────────────────────────────────────────

    def _load_config(self) -> dict:
        d = {"groq_api_key": os.environ.get("GROQ_API_KEY", ""),
             "groq_model": MODELS[0], "language": "",
             "clean_text": False, "engine_mode": "online",
             "local_model": LOCAL_MODELS[0],
             "output_mode": "paste"}
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE) as f:
                d.update(json.load(f))
        return d

    # ── tray ────────────────────────────────────────────────────

    def _setup_tray(self):
        self.tray = QSystemTrayIcon(_make_icon())
        self.tray.setToolTip("Wispy — click to record")
        self.tray.activated.connect(self._on_tray)

        menu = QMenu()
        menu.addAction("Toggle Recording", self.toggle_overlay)
        menu.addSeparator()
        menu.addAction("Settings…", self._show_settings)
        menu.addAction("Appearance…", self._show_appearance)
        menu.addSeparator()
        menu.addAction("Quit", self.quit)
        self.tray.setContextMenu(menu)
        self.tray.show()

    def _on_tray(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_overlay()

    def _show_settings(self):
        dlg = SettingsDialog(self.config)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.config = self._load_config()

    def _show_appearance(self):
        dlg = AppearanceDialog(self.config)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.config = self._load_config()
            self.overlay.apply_appearance(self.config.get("overlay"))

    # ── IPC ─────────────────────────────────────────────────────

    def _start_ipc(self):
        SOCKET_DIR.mkdir(parents=True, exist_ok=True)
        SOCKET_PATH.unlink(missing_ok=True)
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.bind(str(SOCKET_PATH))
        self._sock.listen(1)
        self._sock.setblocking(False)
        self._notifier = QSocketNotifier(
            self._sock.fileno(), QSocketNotifier.Type.Read)
        self._notifier.activated.connect(self._on_ipc_ready)

    def _on_ipc_ready(self):
        try:
            conn, _ = self._sock.accept()
        except (BlockingIOError, OSError):
            return
        with conn:
            try:
                data = conn.recv(1024)
                if data.strip() == b"toggle":
                    self.toggle_overlay()
            except OSError:
                pass

    # ── recording lifecycle ─────────────────────────────────────

    def toggle_overlay(self):
        if self.overlay.state == "transcribing":
            return
        if self.overlay.isVisible():
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        self.recorder.device_name = self.config.get("input_device", "")
        self.recorder.start()
        self.overlay.reset()
        self.overlay.show()

    def _stop_recording(self):
        buffer = self.recorder.stop()
        if buffer is None:
            return
        elapsed = self.recorder.elapsed()
        if elapsed < MIN_DURATION:
            self.overlay.hide()
            if self.config.get("notify_short_recording", True):
                self.tray.showMessage("Wispy", "Recording too short (min 2s)",
                                      QSystemTrayIcon.MessageIcon.Information, 2000)
            return
        self.overlay.set_state("transcribing")
        threading.Thread(target=self._transcribe_and_inject,
                         args=(buffer,), daemon=True).start()

    # ── transcription & injection ───────────────────────────────

    def _transcribe_and_inject(self, buffer):
        try:
            import time
            from transcriber import Transcriber
            from exceptions import InvalidAudioError
            from injector import Injector
            if not buffer:
                return
            t = Transcriber(
                api_key=self.config.get("groq_api_key")
                    or os.environ.get("GROQ_API_KEY", ""),
                model=self.config.get("groq_model", MODELS[0]),
                language=self.config.get("language") or None,
                clean=self.config.get("clean_text", False),
                engine_mode=self.config.get("engine_mode", "online"),
                local_model=self.config.get("local_model", LOCAL_MODELS[0]),
                whisper_prompt=self.config.get("whisper_prompt", ""),
                clean_prompt=self.config.get("clean_prompt", ""),
            )
            inj = Injector()
            try:
                text = t.transcribe(buffer)
                if not text:
                    return
                output_mode = self.config.get("output_mode", "paste")
                self._set_clipboard.emit(text)

                # Emit completion signal FIRST so overlay hides immediately and active window recovers focus
                self._transcribe_finished.emit()

                if output_mode == "paste":
                    # Sleep 150ms to allow KDE Plasma / Wayland compositor to restore input focus to the target app
                    time.sleep(0.15)
                    inj.inject(text, mode=output_mode, send_enter=self.config.get("send_enter", False))
            except InvalidAudioError:
                pass
            except Exception as e:
                self._notify.emit("Wispy", str(e))
        finally:
            self._transcribe_finished.emit()

    def quit(self):
        self.recorder.stop()
        self._notifier.setEnabled(False)
        self._sock.close()
        SOCKET_PATH.unlink(missing_ok=True)
        self.app.quit()

    def run(self):
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        sys.exit(self.app.exec())


def parse_args(argv):
    """Parse CLI arguments and return the command name."""
    # ponytail: multiprocessing resource tracker leaks junk into sys.argv
    known = {"server", "toggle", "help"}
    argv = [a for a in argv if a in known]
    parser = argparse.ArgumentParser(
        prog="wispy",
        description="Voice-to-text daemon for Linux (KDE Plasma/Wayland)",
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("server", help="Run the wispy daemon")
    sub.add_parser("toggle", help="Toggle recording on a running instance")
    sub.add_parser("help", help="Show this help message")
    args = parser.parse_args(argv)
    return args.command or "help"


if __name__ == "__main__":
    command = parse_args(sys.argv[1:])
    if command == "server":
        WispyApp().run()
    elif command == "toggle":
        send_toggle()
    elif command == "help":
        parse_args(["--help"])
