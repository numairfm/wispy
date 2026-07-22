import wave
import io
import os
import tempfile

import groq
import numpy as np

from exceptions import InvalidAudioError, MissingKeyError, GroqError


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

    def _whisper(self, wav_bytes):
        client = groq.Groq(api_key=self.api_key)
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        try:
            tmp.write(wav_bytes)
            tmp.close()
            with open(tmp.name, "rb") as f:
                result = client.audio.transcriptions.create(
                    model=self.model,
                    file=f,
                    language=self.language or None,
                )
            return result.text.strip()
        except Exception as e:
            raise GroqError(str(e)) from e
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

    def transcribe(self, chunks):
        if not chunks or len(chunks) < 5:
            raise InvalidAudioError("Recording too short")
        if not self.api_key:
            raise MissingKeyError("Set GROQ_API_KEY in Settings or env")
        wav_bytes = self._encode_wav(chunks)
        return self._whisper(wav_bytes)
