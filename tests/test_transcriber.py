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

if __name__ == "__main__":
    test_hierarchy()
    test_hierarchy_not_each_other()
    print("All test_transcriber tests passed.")
