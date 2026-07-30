import io
import re
import threading
import time
import random

import httpx
import groq

from recorder import encode_wav
from exceptions import InvalidAudioError, MissingKeyError, GroqError, LocalModelNotFoundError


# Fast cloud retries: race against local processing
FAST_RETRY_BACKOFF = [1.0, 2.0]

# Background retry: continues after local wins, longer backoff
BG_INITIAL_BACKOFF = 4.0
BG_MAX_BACKOFF = 60.0
BG_MAX_ATTEMPTS = 8


DEFAULT_WHISPER_PROMPT = ""


class Transcriber:
    def __init__(self, api_key, model, language=None, casual=False,
                 engine_mode="online", local_model="base.en",
                 whisper_prompt=""):
        self.api_key = api_key
        self.model = model
        self.language = language
        self.casual = casual
        self.engine_mode = engine_mode
        self.local_model = local_model
        self.whisper_prompt = whisper_prompt or DEFAULT_WHISPER_PROMPT
        self._local = None
        self._client = None

    def get_client(self):
        if not self.api_key:
            return None
        if self._client is None:
            http_client = httpx.Client(
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10, keepalive_expiry=120.0)
            )
            self._client = groq.Groq(api_key=self.api_key, http_client=http_client)
        return self._client

    def _is_connection_error(self, exc):
        """True for network-level failures worth retrying.
        Checks the exception and its __cause__ (since _whisper wraps in GroqError)."""
        import groq
        conn_types = (groq.APIConnectionError, groq.APITimeoutError)
        if isinstance(exc, conn_types):
            return True
        cause = getattr(exc, '__cause__', None)
        return isinstance(cause, conn_types)

    def _whisper(self, wav_bytes, timeout=None):
        client = self.get_client()
        if not client:
            raise GroqError("No API key provided")
        buf = io.BytesIO(wav_bytes)
        buf.name = "speech.wav"
        try:
            result = client.audio.transcriptions.create(
                model=self.model,
                file=buf,
                language=self.language or None,
                prompt=self.whisper_prompt,
            )
            return result.text.strip()
        except Exception as e:
            raise GroqError(str(e)) from e

    def _casual(self, raw_text):
        """Casual messaging style: all lowercase, no apostrophes,
        sentence-ending periods become commas, last period stripped.
        Keeps commas, ?, !. Local + instant, no API call."""
        if not self.casual or not raw_text:
            return raw_text
        t = raw_text.lower()
        t = t.replace("'", "")      # dont, thats, im
        t = t.replace(". ", ", ")   # sentence breaks -> commas
        t = t.replace(".", "")      # any stray/trailing period
        t = re.sub(r"\s{2,}", " ", t).strip(" ,")
        return t

    def transcribe_cloud_first(self, wav_bytes, chunks):
        """Try cloud first. On connection error, race local vs cloud retries.
        Returns (text, used_local_fallback)."""
        # First cloud attempt
        try:
            return self._whisper(wav_bytes), False
        except Exception as e:
            if not self._is_connection_error(e):
                if isinstance(e, GroqError):
                    return self._transcribe_local(chunks), True
                raise

        # Connection error — start local in parallel, retry cloud
        local_result = [None]
        local_done = threading.Event()
        def run_local():
            try:
                local_result[0] = self._transcribe_local(chunks)
            finally:
                local_done.set()
        local_thread = threading.Thread(target=run_local, daemon=True)
        local_thread.start()

        # Fast cloud retries — race against local
        for backoff in FAST_RETRY_BACKOFF:
            local_done.wait(timeout=backoff)
            if local_done.is_set():
                return local_result[0], True
            try:
                return self._whisper(wav_bytes), False
            except Exception as e:
                if not self._is_connection_error(e):
                    if isinstance(e, GroqError):
                        local_done.wait()
                        return local_result[0], True
                    raise

        # Fast retries exhausted — wait for local
        local_done.wait()
        return local_result[0], True

    def retry_cloud_async(self, wav_bytes, on_success, on_fail):
        """Background retry with exponential backoff after local wins."""
        def _retry():
            backoff = BG_INITIAL_BACKOFF
            for attempt in range(BG_MAX_ATTEMPTS):
                time.sleep(backoff + random.uniform(0, backoff * 0.3))
                try:
                    text = self._whisper(wav_bytes)
                    if text:
                        on_success(text)
                        return
                except Exception as e:
                    if not self._is_connection_error(e):
                        on_fail()
                        return
                backoff = min(backoff * 2, BG_MAX_BACKOFF)
            on_fail()
        threading.Thread(target=_retry, daemon=True).start()

    def transcribe(self, chunks):
        if not chunks or len(chunks) < 5:
            raise InvalidAudioError("Recording too short")

        if self.engine_mode == "offline":
            return self._casual(self._transcribe_local(chunks))

        if not self.api_key:
            raise MissingKeyError("Set GROQ_API_KEY in Settings or env")

        wav_bytes = encode_wav(chunks)

        if self.engine_mode == "hybrid":
            text, used_local = self.transcribe_cloud_first(wav_bytes, chunks)
            return self._casual(text)

        return self._casual(self._whisper(wav_bytes))

    def _transcribe_local(self, chunks):
        if self._local is None:
            from local_transcriber import LocalTranscriber
            self._local = LocalTranscriber(model_name=self.local_model)
        return self._local.transcribe(chunks, language=self.language)
