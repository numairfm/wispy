import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from exceptions import (
    TranscribeError, MissingKeyError, GroqError, InvalidAudioError,
)

def test_hierarchy():
    assert issubclass(MissingKeyError, TranscribeError)
    assert issubclass(GroqError, TranscribeError)
    assert issubclass(InvalidAudioError, TranscribeError)

def test_hierarchy_not_each_other():
    assert not issubclass(MissingKeyError, GroqError)
    assert not issubclass(GroqError, InvalidAudioError)

def test_encode_wav_shape():
    """WAV bytes should be valid 16kHz mono int16."""
    from transcriber import Transcriber
    import numpy as np
    import wave, io
    t = Transcriber(api_key="x", model="m", language=None, clean=False)
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
    t = Transcriber(api_key="x", model="m", language=None, clean=False)
    try:
        t.transcribe([])
        assert False, "should have raised"
    except InvalidAudioError:
        pass

def test_transcribe_short_raises():
    from transcriber import Transcriber
    import numpy as np
    t = Transcriber(api_key="x", model="m", language=None, clean=False)
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
    t = Transcriber(api_key="", model="m", language=None, clean=False)
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
    t = Transcriber(api_key="test-key", model="whisper-large-v3", language="en", clean=False)
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


if __name__ == "__main__":
    test_hierarchy()
    test_hierarchy_not_each_other()
    print("All test_transcriber tests passed.")
