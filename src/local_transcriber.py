import io
import re
import wave
import numpy as np

from exceptions import InvalidAudioError, LocalModelNotFoundError


class LocalTranscriber:
    """Offline transcription via faster-whisper (CTranslate2, CPU/int8)."""

    def __init__(self, model_name="base.en"):
        self.model_name = model_name
        self._model = None

    def _ensure_model(self):
        if self._model is not None:
            return
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise LocalModelNotFoundError(
                "faster-whisper not installed. Run: pip install faster-whisper"
            )
        try:
            self._model = WhisperModel(
                self.model_name, device="cpu", compute_type="int8")
        except Exception as e:
            raise LocalModelNotFoundError(
                f"Could not load model '{self.model_name}': {e}"
            )

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

    def transcribe(self, chunks, language=None):
        if not chunks or len(chunks) < 5:
            raise InvalidAudioError("Recording too short")
        self._ensure_model()
        wav_bytes = self._encode_wav(chunks)
        # faster-whisper accepts file path or file-like
        import tempfile, os
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        try:
            tmp.write(wav_bytes)
            tmp.close()
            segments, info = self._model.transcribe(
                tmp.name,
                language=language or None,
                beam_size=5,
            )
            text = " ".join(seg.text for seg in segments).strip()
            text = re.sub(r'  +', ' ', text)
            return text
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

    def warmup(self):
        """Load model into memory (call from background thread)."""
        self._ensure_model()
