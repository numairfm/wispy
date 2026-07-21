#!/usr/bin/env python3
from __future__ import annotations
import os, sys, json, signal, tempfile, wave, socket, threading, queue, argparse, time
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QDialog,
    QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QPushButton, QCheckBox,
    QLabel,
)
from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter, QPen

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "wispy"
CONFIG_FILE = CONFIG_DIR / "config.json"
SOCKET_DIR = Path(os.environ.get("XDG_RUNTIME_DIR", Path.home() / ".cache")) / "wispy"
SOCKET_PATH = SOCKET_DIR / "wispy.sock"
ICON_SVG = Path(__file__).parent / "wispy.svg"

MODELS = [
    "whisper-large-v3",
    "whisper-large-v3-turbo",
    "distil-whisper-large-v3-en",
]

MIN_DURATION = 2.0


# ── icon helpers ────────────────────────────────────────────────

def _draw_icon(s=64):
    pm = QPixmap(s, s)
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    m = 2
    p.setBrush(QColor(240, 240, 240))
    p.drawRoundedRect(m, m, s - 2 * m, s - 2 * m, s // 5, s // 5)
    bw, bg, n = 5, 5, 5
    total_w = n * bw + (n - 1) * bg
    bx = (s - total_w) // 2
    cy = s // 2
    hs = [9, 17, 26, 17, 9]
    p.setBrush(QColor(30, 30, 30))
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

    def _section(self, text):
        lbl = QLabel(text)
        f = lbl.font()
        f.setBold(True)
        lbl.setFont(f)
        return lbl

    def _save(self):
        self.config["groq_api_key"] = self.api_key.text().strip()
        self.config["groq_model"] = self.model.currentText()
        self.config["language"] = self.language.text().strip()
        self.config["input_device"] = self.device.currentData() or ""
        self.config["copy_to_clipboard"] = self.copy_clipboard.isChecked()
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=2)
        self.accept()


# ── app ─────────────────────────────────────────────────────────

class WispyApp(QObject):
    _notify = pyqtSignal(str, str)
    _set_clipboard = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("Wispy")
        self.app.setQuitOnLastWindowClosed(False)

        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.config = self._load_config()
        self._running = True

        self.recording = False
        self.audio_buffer: list[np.ndarray] | None = None
        self.stream: sd.InputStream | None = None
        self.current_level = 0.0
        self._rms_buf = [0.0] * 20
        self._start_time = 0.0
        self._audio_lock = threading.Lock()

        from overlay import OverlayWindow
        self.overlay = OverlayWindow(self._stop_recording,
                                     lambda: self.current_level)
        self._ipc_queue: queue.Queue = queue.Queue()

        self._notify.connect(self._on_notify)
        self._set_clipboard.connect(self._on_set_clipboard)
        self._setup_tray()
        self._start_ipc()
        self._poll = QTimer()
        self._poll.timeout.connect(self._poll_ipc)
        self._poll.start(100)

    def _on_notify(self, title, msg):
        self.tray.showMessage(title, msg,
                              QSystemTrayIcon.MessageIcon.Critical, 5000)

    def _on_set_clipboard(self, text):
        QApplication.clipboard().setText(text)

    # ── config ──────────────────────────────────────────────────

    def _load_config(self) -> dict:
        d = {"groq_api_key": os.environ.get("GROQ_API_KEY", ""),
             "groq_model": MODELS[0], "language": ""}
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
        threading.Thread(target=self._ipc_loop, daemon=True).start()

    def _ipc_loop(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(str(SOCKET_PATH))
        sock.listen(1)
        sock.settimeout(0.5)
        while self._running:
            try:
                conn, _ = sock.accept()
                try:
                    data = conn.recv(1024)
                    if data.strip() == b"toggle":
                        self._ipc_queue.put("toggle")
                finally:
                    conn.close()
            except socket.timeout:
                continue
            except OSError:
                continue
        sock.close()
        SOCKET_PATH.unlink(missing_ok=True)

    def _poll_ipc(self):
        try:
            while self._ipc_queue.get_nowait() == "toggle":
                try:
                    self.toggle_overlay()
                except Exception as e:
                    print(f"wispy: toggle error: {e}", file=sys.stderr)
        except queue.Empty:
            pass

    # ── recording lifecycle ─────────────────────────────────────

    def toggle_overlay(self):
        if self.overlay.isVisible():
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        import sounddevice as sd
        self.audio_buffer = []
        self.current_level = 0.0
        self._rms_buf = [0.0] * 20
        self._start_time = time.monotonic()
        self.recording = True
        try:
            device = None
            dev_name = self.config.get("input_device", "")
            if dev_name:
                for i, d in enumerate(sd.query_devices()):
                    if d['name'] == dev_name and d['max_input_channels'] > 0:
                        device = i
                        break
            self.stream = sd.InputStream(callback=self._audio_cb,
                                         channels=1, samplerate=16000,
                                         dtype="float32",
                                         device=device)
            self.stream.start()
        except Exception as e:
            self.tray.showMessage("Wispy", f"Mic error: {e}",
                                  QSystemTrayIcon.MessageIcon.Critical, 5000)
            self.recording = False
            return
        self.overlay.reset()
        self.overlay.show()

    def _audio_cb(self, indata, frames, time_info, status):
        import numpy as np
        with self._audio_lock:
            if not self.recording:
                return
            self.audio_buffer.append(indata.copy())
        rms = float(np.sqrt(np.mean(indata ** 2)))
        self._rms_buf = self._rms_buf[1:] + [rms]
        noise = min(self._rms_buf) if self._rms_buf else rms
        signal = max(rms - noise, 0.0)
        raw = min(signal * 60.0, 1.0) if noise > 0.0001 else 0.0
        self.current_level = self.current_level * 0.55 + raw * 0.45

    def _stop_recording(self):
        with self._audio_lock:
            if not self.recording:
                return
            self.recording = False
            buffer = self.audio_buffer
            self.audio_buffer = None
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None
        self.overlay.hide()
        elapsed = time.monotonic() - self._start_time
        if elapsed < MIN_DURATION:
            self.tray.showMessage("Wispy", "Recording too short (min 2s)",
                                  QSystemTrayIcon.MessageIcon.Information, 2000)
            return
        threading.Thread(target=self._transcribe_and_inject,
                         args=(buffer,), daemon=True).start()

    # ── transcription & injection ───────────────────────────────

    def _transcribe_and_inject(self, buffer):
        import numpy as np
        import groq
        if not buffer or len(buffer) < 5:
            return
        try:
            audio = np.concatenate(buffer, axis=0)
            audio_int16 = (audio * 32767).astype(np.int16)

            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            try:
                with wave.open(tmp, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(16000)
                    wf.writeframes(audio_int16.tobytes())
                tmp.close()

                key = self.config.get("groq_api_key") \
                    or os.environ.get("GROQ_API_KEY", "")
                if not key:
                    self._notify.emit("Wispy",
                                      "Set GROQ_API_KEY in Settings or env")
                    return

                client = groq.Groq(api_key=key)
                with open(tmp.name, "rb") as f:
                    result = client.audio.transcriptions.create(
                        model=self.config.get("groq_model", MODELS[0]),
                        file=f,
                        language=self.config.get("language") or None,
                    )
                text = result.text.strip()
                if text:
                    if self.config.get("copy_to_clipboard"):
                        self._set_clipboard.emit(text)
                    import subprocess
                    try:
                        subprocess.run(["ydotool", "type", "-d", "1", "-H", "1", text],
                                       check=True, capture_output=True,
                                       timeout=60)
                    except FileNotFoundError:
                        self._notify.emit("Wispy",
                                          "ydotool not found — install it")
                    except subprocess.CalledProcessError as e:
                        self._notify.emit("Wispy", f"Type failed: {e}")
            finally:
                try:
                    os.unlink(tmp.name)
                except OSError:
                    pass
        except Exception as e:
            self._notify.emit("Wispy", f"Error: {e}")

    def quit(self):
        self._running = False
        self._stop_recording()
        self.app.quit()

    def run(self):
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        sys.exit(self.app.exec())


def parse_args(argv):
    """Parse CLI arguments and return the command name."""
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
