import wave
import io
import numpy as np


class Transcriber:
    def __init__(self, api_key, model, language=None, clean=False):
        self.api_key = api_key
        self.model = model
        self.language = language
        self.clean = clean

    def _encode_wav(self, chunks):
        audio = np.concatenate(chunks, axis=0)
        audio_int16 = (audio * 32767).astype(np.int16)
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(audio_int16.tobytes())
        return buf.getvalue()
