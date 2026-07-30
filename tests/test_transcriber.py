import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from exceptions import (
    TranscribeError, MissingKeyError, GroqError, InvalidAudioError, InjectError,
)

def test_hierarchy():
    assert issubclass(MissingKeyError, TranscribeError)
    assert issubclass(GroqError, TranscribeError)
    assert issubclass(InvalidAudioError, TranscribeError)
    assert issubclass(InjectError, TranscribeError)

def test_hierarchy_not_each_other():
    assert not issubclass(MissingKeyError, GroqError)
    assert not issubclass(GroqError, InvalidAudioError)

def test_encode_wav_shape():
    """WAV bytes should be valid 16kHz mono int16."""
    from transcriber import Transcriber
    import numpy as np
    import wave, io
    t = Transcriber(api_key="x", model="m", language=None, casual=False)
    chunk = np.zeros((16000, 1), dtype=np.float32)
    wav_bytes = t._encode_wav([chunk])
    assert isinstance(wav_bytes, bytes)
    buf = io.BytesIO(wav_bytes)
    with wave.open(buf, 'rb') as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 16000
        frames = wf.readframes(wf.getnframes())
    assert len(frames) == 16000 * 2

def test_transcribe_empty_raises():
    from transcriber import Transcriber
    t = Transcriber(api_key="x", model="m", language=None, casual=False)
    try:
        t.transcribe([])
        assert False, "should have raised"
    except InvalidAudioError:
        pass

def test_transcribe_short_raises():
    from transcriber import Transcriber
    import numpy as np
    t = Transcriber(api_key="x", model="m", language=None, casual=False)
    chunk = np.zeros((100, 1), dtype=np.float32)
    try:
        t.transcribe([chunk])  # 1 chunk < 5
        assert False, "should have raised"
    except InvalidAudioError:
        pass

def test_transcribe_no_key_raises():
    from transcriber import Transcriber
    from exceptions import MissingKeyError
    import numpy as np
    t = Transcriber(api_key="", model="m", language=None, casual=False)
    chunk = np.zeros((16000, 1), dtype=np.float32)
    try:
        t.transcribe([chunk] * 5)
        assert False, "should have raised"
    except MissingKeyError:
        pass

def test_whisper_calls_groq():
    """_whisper should call groq client and return result.text."""
    from unittest.mock import patch, MagicMock
    from transcriber import Transcriber
    t = Transcriber(api_key="test-key", model="whisper-large-v3", language="en", casual=False)
    fake_wav = b"RIFF" + b"\x00" * 100

    mock_client = MagicMock()
    mock_result = MagicMock()
    mock_result.text = " hello world "
    mock_client.audio.transcriptions.create.return_value = mock_result

    with patch("transcriber.groq") as mock_groq:
        mock_groq.Groq.return_value = mock_client
        result = t._whisper(fake_wav)

    assert result == "hello world"
    mock_client.audio.transcriptions.create.assert_called_once()


def test_casual_transform():
    from transcriber import Transcriber
    t = Transcriber(api_key="k", model="m", language=None, casual=True)
    assert t._casual("I don't know. Hey, are you there?") == "i dont know, hey, are you there?"

def test_casual_off_passes_through():
    from transcriber import Transcriber
    t = Transcriber(api_key="k", model="m", language=None, casual=False)
    assert t._casual("I DON'T Know.") == "I DON'T Know."


def test_transcribe_end_to_end():
    """Full pipeline: encode → whisper → return text."""
    from unittest.mock import patch, MagicMock
    from transcriber import Transcriber
    import numpy as np
    t = Transcriber(api_key="test-key", model="m", language=None, casual=False)
    chunks = [np.zeros((16000, 1), dtype=np.float32) for _ in range(5)]
    mock_client = MagicMock()
    mock_result = MagicMock()
    mock_result.text = "hello world"
    mock_client.audio.transcriptions.create.return_value = mock_result
    with patch("transcriber.groq") as mock_groq:
        mock_groq.Groq.return_value = mock_client
        result = t.transcribe(chunks)
    assert result == "hello world"


def test_inject_calls_ydotool():
    from unittest.mock import patch, MagicMock
    from injector import Injector
    inj = Injector()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        inj.inject("hello world")
    mock_run.assert_called_once()
    args = mock_run.call_args
    assert args[0][0] == ["ydotool", "type", "-d", "1", "-H", "1", "hello world"]


def test_inject_raises_on_failure():
    from unittest.mock import patch
    import subprocess
    from injector import Injector, InjectError
    inj = Injector()
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError
        try:
            inj.inject("hi")
            assert False, "should have raised"
        except InjectError:
            pass


def test_inject_raises_on_process_error():
    from unittest.mock import patch
    import subprocess
    from injector import Injector, InjectError
    inj = Injector()
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "ydotool")
        try:
            inj.inject("hi")
            assert False, "should have raised"
        except InjectError:
            pass


def test_copy_calls_clipboard():
    from unittest.mock import patch, MagicMock
    from injector import Injector
    inj = Injector()
    mock_clipboard = MagicMock()
    mock_app = MagicMock()
    mock_app.clipboard.return_value = mock_clipboard
    with patch("PyQt6.QtWidgets.QApplication", mock_app):
        inj.copy("test text")
    mock_app.clipboard.assert_called_once()
    mock_clipboard.setText.assert_called_once_with("test text")


if __name__ == "__main__":
    test_hierarchy()
    test_hierarchy_not_each_other()
    test_inject_calls_ydotool()
    test_inject_raises_on_failure()
    test_copy_calls_clipboard()
    print("All test_transcriber tests passed.")
