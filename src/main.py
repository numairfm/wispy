#!/usr/bin/env python3
from __future__ import annotations
import os, sys, json, signal, socket, threading, argparse
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QDialog,
    QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QPushButton, QCheckBox,
    QLabel, QFileDialog, QProgressBar,
)
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QSocketNotifier, QThread
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter, QPen

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

LLM_MODEL = "llama-3.1-8b-instant"


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
        form.addRow(self._section("Transcription"))

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

        # ── Local Model ──
        form.addRow(self._section("Local Model"))

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
        form.addRow(self._section("Audio"))

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
        form.addRow(self._section("Behavior"))

        self.copy_clipboard = QCheckBox("Copy transcribed text to clipboard")
        self.copy_clipboard.setChecked(config.get("copy_to_clipboard", False))
        form.addRow(self.copy_clipboard)

        # ── Experimental ──
        form.addRow(self._section("Experimental"))

        self.clean_text = QCheckBox("Clean and format text with AI")
        self.clean_text.setChecked(config.get("clean_text", False))
        form.addRow(self.clean_text)

        self.stop_keyword_cb = QCheckBox("Enable stop keyword (press Enter when keyword detected)")
        self.stop_keyword_cb.setChecked(bool(config.get("stop_keyword", "")))
        self.stop_keyword_cb.toggled.connect(self._on_stop_keyword_toggled)
        form.addRow(self.stop_keyword_cb)

        self.stop_keyword = QLineEdit(config.get("stop_keyword", ""))
        self.stop_keyword.setPlaceholderText("e.g. send it, enter, done")
        form.addRow("Stop keyword", self.stop_keyword)
        self._on_stop_keyword_toggled(self.stop_keyword_cb.isChecked())

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

    def _section(self, text):
        lbl = QLabel(text)
        f = lbl.font()
        f.setBold(True)
        lbl.setFont(f)
        return lbl

    def _on_engine_changed(self, idx):
        online = idx != 1  # enabled for online(0) and hybrid(2), disabled for offline(1)
        self.api_key.setEnabled(online)
        self.model.setEnabled(online)
        self.language.setEnabled(online)

    def _on_stop_keyword_toggled(self, checked):
        self.stop_keyword.setEnabled(checked)

    def _on_local_model_changed(self, name):
        self._update_model_status()

    def _update_model_status(self):
        import os, glob
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
        self.config["clean_text"] = self.clean_text.isChecked()
        self.config["stop_keyword"] = self.stop_keyword.text().strip() if self.stop_keyword_cb.isChecked() else ""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=2)
        self.accept()


# ── app ─────────────────────────────────────────────────────────

class WispyApp(QObject):
    _notify = pyqtSignal(str, str)
    _set_clipboard = pyqtSignal(str)
    _rec_error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("Wispy")
        self.app.setQuitOnLastWindowClosed(False)

        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.config = self._load_config()
        self._running = True
        self._warmup_local_model()

        from recorder import Recorder
        self.recorder = Recorder(
            device_name=self.config.get("input_device", ""),
            on_error=lambda msg: self._rec_error.emit(msg),
        )

        from overlay import OverlayWindow
        self.overlay = OverlayWindow(self._stop_recording,
                                     lambda: self.recorder.level())

        self._notify.connect(self._on_notify)
        self._set_clipboard.connect(self._on_set_clipboard)
        self._rec_error.connect(self._on_rec_error)
        self._setup_tray()
        self._start_ipc()

    def _on_notify(self, title, msg):
        self.tray.showMessage(title, msg,
                              QSystemTrayIcon.MessageIcon.Critical, 5000)

    def _on_set_clipboard(self, text):
        QApplication.clipboard().setText(text)

    def _on_rec_error(self, msg):
        self.overlay.hide()
        self.tray.showMessage("Wispy", msg,
                              QSystemTrayIcon.MessageIcon.Critical, 5000)

    # ── config ──────────────────────────────────────────────────

    def _load_config(self) -> dict:
        d = {"groq_api_key": os.environ.get("GROQ_API_KEY", ""),
             "groq_model": MODELS[0], "language": "",
             "clean_text": False, "engine_mode": "online",
             "local_model": LOCAL_MODELS[0]}
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE) as f:
                d.update(json.load(f))
        return d

    def _warmup_local_model(self):
        """Load local model in background if offline/hybrid mode active."""
        mode = self.config.get("engine_mode", "online")
        if mode in ("offline", "hybrid"):
            threading.Thread(target=self._do_warmup, daemon=True).start()

    def _do_warmup(self):
        try:
            from local_transcriber import LocalTranscriber
            t = LocalTranscriber(
                model_name=self.config.get("local_model", LOCAL_MODELS[0]))
            t.warmup()
        except Exception:
            pass  # ponytail: model loads lazily on first use anyway

    # ── tray ────────────────────────────────────────────────────

    def _setup_tray(self):
        self.tray = QSystemTrayIcon(_make_icon())
        self.tray.setToolTip("Wispy — click to record")
        self.tray.activated.connect(self._on_tray)

        menu = QMenu()
        menu.addAction("Toggle Recording", self.toggle_overlay)
        menu.addSeparator()
        menu.addAction("Settings…", self._show_settings)
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
        buffer, remaining_slice = self.recorder.stop()  # used in Task 2
        if buffer is None:
            return
        self.overlay.hide()
        elapsed = self.recorder.elapsed()
        if elapsed < MIN_DURATION:
            self.tray.showMessage("Wispy", "Recording too short (min 2s)",
                                  QSystemTrayIcon.MessageIcon.Information, 2000)
            return
        threading.Thread(target=self._transcribe_and_inject,
                         args=(buffer,), daemon=True).start()

    # ── transcription & injection ───────────────────────────────

    def _transcribe_and_inject(self, buffer):
        from transcriber import Transcriber
        from exceptions import TranscribeError, InvalidAudioError
        from injector import Injector, check_stop_keyword
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
        )
        inj = Injector()
        try:
            text = t.transcribe(buffer)
            if not text:
                return
            keyword = self.config.get("stop_keyword", "")
            text, should_send = check_stop_keyword(text, keyword)
            if self.config.get("copy_to_clipboard"):
                self._set_clipboard.emit(text)
            inj.inject(text, press_enter=should_send)
        except InvalidAudioError:
            pass
        except Exception as e:
            self._notify.emit("Wispy", str(e))

    def quit(self):
        self._running = False
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
