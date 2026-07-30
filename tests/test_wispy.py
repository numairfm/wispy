#!/usr/bin/env python3
import sys, os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import parse_args, MIN_DURATION
from transcriber import DEFAULT_WHISPER_PROMPT, Transcriber

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

def test_is_connection_error():
    import groq
    t = Transcriber(api_key="x", model="x")
    assert t._is_connection_error(groq.APIConnectionError(request=None)) is True
    assert t._is_connection_error(groq.APITimeoutError(request=None)) is True
    auth_err = groq.AuthenticationError.__new__(groq.AuthenticationError)
    rate_err = groq.RateLimitError.__new__(groq.RateLimitError)
    assert t._is_connection_error(auth_err) is False
    assert t._is_connection_error(rate_err) is False
    assert t._is_connection_error(Exception("generic")) is False

def test_transcriber_custom_prompts():
    t = Transcriber(
        api_key="test", model="test",
        whisper_prompt="my prompt",
    )
    assert t.whisper_prompt == "my prompt"

def test_transcriber_defaults_used_when_empty():
    t = Transcriber(api_key="test", model="test")
    assert t.whisper_prompt == DEFAULT_WHISPER_PROMPT

def test_casual_mode_transform():
    from transcriber import Transcriber
    t = Transcriber(api_key="k", model="m", casual=True)
    # all lowercase, strip apostrophes + periods, keep commas and ?, no trailing punct
    assert t._casual("I don't know. Hey, are you there?") == "i dont know, hey, are you there?"

def test_casual_mode_off_passes_through():
    from transcriber import Transcriber
    t = Transcriber(api_key="k", model="m", casual=False)
    assert t._casual("I DON'T Know.") == "I DON'T Know."

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

    # corrected state (shown briefly when background cloud retry upgrades clipboard)
    ov.set_state("corrected")
    assert ov.state == "corrected"

def test_corrected_signal_exists():
    from main import WispyApp
    assert hasattr(WispyApp, '_corrected')

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
        # paste mode (Ctrl+Shift+V with -d 12 key delay)
        inj.inject("hello", mode="paste", send_enter=False)
        mock_run.assert_called_once_with(
            ["ydotool", "key", "-d", "12", "29:1", "42:1", "47:1", "47:0", "42:0", "29:0"],
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
            (["ydotool", "key", "-d", "12", "29:1", "42:1", "47:1", "47:0", "42:0", "29:0"],),
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

def test_styles_module():
    import styles
    assert hasattr(styles, "DARK_THEME_QSS")
    assert "background-color: #18181b" in styles.DARK_THEME_QSS

def test_app_qss_applied():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from main import WispyApp, SOCKET_PATH
    wispy_app = WispyApp()
    try:
        assert "#18181b" in wispy_app.app.styleSheet()
    finally:
        wispy_app.recorder.stop()
        wispy_app._notifier.setEnabled(False)
        wispy_app._sock.close()
        SOCKET_PATH.unlink(missing_ok=True)


def test_cloud_first_cloud_success():
    t = Transcriber(api_key="test", model="whisper-large-v3-turbo")
    t._whisper = lambda wav, timeout=None: "cloud result"
    text, used_local = t.transcribe_cloud_first(b"fake-wav", [1, 2, 3, 4, 5])
    assert text == "cloud result"
    assert used_local is False


def test_cloud_first_local_wins_race():
    """Connection errors -> local processes while cloud retries -> local wins."""
    import groq
    import transcriber as tm
    import time as _time

    call_count = [0]
    def failing_whisper(wav, timeout=None):
        call_count[0] += 1
        raise groq.APIConnectionError(request=None)

    def slow_local(chunks):
        _time.sleep(0.5)  # slow so fast retries exhaust first
        return "local wins"

    t = Transcriber(api_key="test", model="whisper-large-v3-turbo")
    t._whisper = failing_whisper
    t._transcribe_local = slow_local

    old_backoff = tm.FAST_RETRY_BACKOFF
    tm.FAST_RETRY_BACKOFF = [0.01, 0.01]
    try:
        text, used_local = t.transcribe_cloud_first(b"fake-wav", [1, 2, 3, 4, 5])
        assert text == "local wins"
        assert used_local is True
        assert call_count[0] == 3  # initial + 2 fast retries
    finally:
        tm.FAST_RETRY_BACKOFF = old_backoff


def test_cloud_first_cloud_wins_during_retry():
    """Connection error then cloud recovers during fast retry."""
    import groq
    import transcriber as tm
    import time as _time

    call_count = [0]
    def recovering_whisper(wav, timeout=None):
        call_count[0] += 1
        if call_count[0] == 1:
            raise groq.APIConnectionError(request=None)
        return "cloud recovered"

    def slow_local(chunks):
        _time.sleep(1.0)  # slow so cloud retry wins
        return "local"

    t = Transcriber(api_key="test", model="whisper-large-v3-turbo")
    t._whisper = recovering_whisper
    t._transcribe_local = slow_local

    old_backoff = tm.FAST_RETRY_BACKOFF
    tm.FAST_RETRY_BACKOFF = [0.5, 2.0]  # give local time to NOT finish first
    try:
        text, used_local = t.transcribe_cloud_first(b"fake-wav", [1, 2, 3, 4, 5])
        assert text == "cloud recovered"
        assert used_local is False
        assert call_count[0] == 2
    finally:
        tm.FAST_RETRY_BACKOFF = old_backoff


def test_transcriber_client_persistence():
    from transcriber import Transcriber
    t = Transcriber(api_key="test_key", model="whisper-large-v3-turbo")
    client1 = t.get_client()
    client2 = t.get_client()
    assert client1 is client2
    assert client1 is not None


def test_whisper_uses_bytesio_without_disk(monkeypatch=None):
    import io
    from transcriber import Transcriber
    t = Transcriber(api_key="dummy_key", model="whisper-large-v3-turbo")
    
    called_with_file = [None]
    class DummyTranscriptions:
        def create(self, model, file, language=None, prompt=""):
            called_with_file[0] = file
            class Res:
                text = "hello world"
            return Res()

    class DummyAudio:
        transcriptions = DummyTranscriptions()

    class DummyGroqClient:
        audio = DummyAudio()

    t._client = DummyGroqClient()
    res = t._whisper(b"RIFFdummywavbytes")
    assert res == "hello world"
    assert isinstance(called_with_file[0], io.BytesIO)
    assert called_with_file[0].getvalue() == b"RIFFdummywavbytes"


if __name__ == "__main__":
    test_server()
    test_toggle()
    test_no_args_shows_help()
    test_help_subcommand()
    test_min_duration()
    test_whisper_prompt_default()
    test_transcriber_custom_prompts()
    test_transcriber_defaults_used_when_empty()
    test_casual_mode_transform()
    test_casual_mode_off_passes_through()
    test_injector_modes()
    test_overlay_states()
    test_toggle_ignored_during_transcribing()
    test_config_output_mode()
    test_styles_module()
    test_app_qss_applied()
    test_corrected_signal_exists()
    test_cloud_first_cloud_success()
    test_cloud_first_local_wins_race()
    test_cloud_first_cloud_wins_during_retry()
    test_transcriber_client_persistence()
    test_whisper_uses_bytesio_without_disk()
    print("All tests passed.")
    sys.exit(0)





