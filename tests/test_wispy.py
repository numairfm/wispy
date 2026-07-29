#!/usr/bin/env python3
import sys, os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import parse_args, MIN_DURATION
from transcriber import DEFAULT_WHISPER_PROMPT, DEFAULT_CLEAN_PROMPT, Transcriber

def test_server():
    assert parse_args(["server"]) == "server"

def test_toggle():
    assert parse_args(["toggle"]) == "toggle"

def test_no_args_shows_help():
    assert parse_args([]) == "help"

def test_help_subcommand():
    assert parse_args(["help"]) == "help"

def test_min_duration():
    assert MIN_DURATION == 2.0

def test_whisper_prompt_default():
    assert isinstance(DEFAULT_WHISPER_PROMPT, str)
    assert DEFAULT_WHISPER_PROMPT == ""

def test_clean_prompt_default():
    assert isinstance(DEFAULT_CLEAN_PROMPT, str)
    assert len(DEFAULT_CLEAN_PROMPT) > 0

def test_transcriber_custom_prompts():
    t = Transcriber(
        api_key="test", model="test",
        whisper_prompt="my prompt", clean_prompt="my clean prompt",
    )
    assert t.whisper_prompt == "my prompt"
    assert t.clean_prompt == "my clean prompt"

def test_transcriber_defaults_used_when_empty():
    t = Transcriber(api_key="test", model="test")
    assert t.whisper_prompt == DEFAULT_WHISPER_PROMPT
    assert t.clean_prompt == DEFAULT_CLEAN_PROMPT

def test_overlay_states():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from overlay import OverlayWindow
    stopped = False
    def on_stop():
        nonlocal stopped
        stopped = True

    ov = OverlayWindow(on_stop=on_stop, level_getter=lambda: 0.0)
    assert ov.state == "recording"
    ov.set_state("transcribing")
    assert ov.state == "transcribing"

    # In transcribing state, mouse press on stop button position should be ignored
    from PyQt6.QtGui import QMouseEvent
    from PyQt6.QtCore import QPointF, Qt
    event = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPointF(ov._lay["bt_x"], ov._ap["height"] / 2), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    ov.mousePressEvent(event)
    assert not stopped

    ov.reset()
    assert ov.state == "recording"

def test_toggle_ignored_during_transcribing():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from main import WispyApp
    wispy_app = WispyApp()
    try:
        wispy_app.recorder._recording = True
        wispy_app.recorder._audio_buffer = []
        wispy_app.overlay.set_state("transcribing")
        wispy_app.overlay.show()
        # toggle_overlay should be ignored when state is transcribing
        wispy_app.toggle_overlay()
        assert wispy_app.overlay.isVisible()
        assert wispy_app.overlay.state == "transcribing"
        wispy_app.overlay.hide()
    finally:
        wispy_app.recorder.stop()
        wispy_app._notifier.setEnabled(False)
        wispy_app._sock.close()
        from main import SOCKET_PATH
        SOCKET_PATH.unlink(missing_ok=True)

def test_injector_modes():
    from unittest.mock import patch
    from injector import Injector
    inj = Injector()

    with patch("subprocess.run") as mock_run:
        # paste mode (Ctrl+V with -d 12 key delay)
        inj.inject("hello", mode="paste", send_enter=False)
        mock_run.assert_called_once_with(
            ["ydotool", "key", "-d", "12", "29:1", "47:1", "47:0", "29:0"],
            check=True, capture_output=True, timeout=5,
        )

    with patch("subprocess.run") as mock_run:
        # copy mode (no subprocess call)
        inj.inject("hello", mode="copy", send_enter=False)
        mock_run.assert_not_called()

    with patch("subprocess.run") as mock_run:
        # send_enter flag
        inj.inject("hello", mode="paste", send_enter=True)
        assert mock_run.call_count == 2
        assert mock_run.call_args_list[0] == (
            (["ydotool", "key", "-d", "12", "29:1", "47:1", "47:0", "29:0"],),
            {"check": True, "capture_output": True, "timeout": 5},
        )
        assert mock_run.call_args_list[1] == (
            (["ydotool", "key", "-d", "12", "28:1", "28:0"],),
            {"check": True, "capture_output": True, "timeout": 5},
        )

def test_config_output_mode():
    import tempfile
    from pathlib import Path
    from unittest.mock import patch
    from main import WispyApp, SettingsDialog, SOCKET_PATH
    from PyQt6.QtWidgets import QApplication

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_config = Path(tmpdir) / "config.json"
        tmp_dir = Path(tmpdir)
        with patch("main.CONFIG_FILE", tmp_config), patch("main.CONFIG_DIR", tmp_dir):
            app = QApplication.instance() or QApplication([])
            wispy_app = WispyApp()
            try:
                assert wispy_app.config.get("output_mode") in ("paste", "copy")

                dlg = SettingsDialog(wispy_app.config)
                assert dlg.output_mode.count() == 2
                assert dlg.output_mode.currentIndex() == 0  # paste

                dlg.output_mode.setCurrentIndex(1)
                dlg._save()
                assert wispy_app.config.get("output_mode") == "copy"
            finally:
                wispy_app.recorder.stop()
                wispy_app._notifier.setEnabled(False)
                wispy_app._sock.close()
                SOCKET_PATH.unlink(missing_ok=True)

if __name__ == "__main__":
    test_server()
    test_toggle()
    test_no_args_shows_help()
    test_help_subcommand()
    test_min_duration()
    test_whisper_prompt_default()
    test_clean_prompt_default()
    test_transcriber_custom_prompts()
    test_transcriber_defaults_used_when_empty()
    test_injector_modes()
    test_overlay_states()
    test_toggle_ignored_during_transcribing()
    test_config_output_mode()
    print("All tests passed.")
    sys.exit(0)

