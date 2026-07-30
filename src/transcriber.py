import os
import tempfile
import threading
import time
import random

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

DEFAULT_CLEAN_PROMPT = (
    "This is raw speech-to-text output. The user is dictating. "
    "Add proper punctuation and fix sentence capitalization. "
    "Do not remove or rephrase any content. Return only the cleaned text."
)


class Transcriber:
    def __init__(self, api_key, model, language=None, clean=False,
                 engine_mode="online", local_model="base.en",
                 whisper_prompt="", clean_prompt=""):
        self.api_key = api_key
        self.model = model
        self.language = language
        self.clean = clean
        self.engine_mode = engine_mode
        self.local_model = local_model
        self.whisper_prompt = whisper_prompt or DEFAULT_WHISPER_PROMPT
        self.clean_prompt = clean_prompt or DEFAULT_CLEAN_PROMPT
        self._local = None

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
        client = groq.Groq(api_key=self.api_key, timeout=timeout)
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        try:
            tmp.write(wav_bytes)
            tmp.close()
            with open(tmp.name, "rb") as f:
                result = client.audio.transcriptions.create(
                    model=self.model,
                    file=f,
                    language=self.language or None,
                    prompt=self.whisper_prompt,
                )
            return result.text.strip()
        except Exception as e:
            raise GroqError(str(e)) from e
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

    def _clean(self, raw_text):
        if not self.clean or len(raw_text.split()) < 5:
            return raw_text
        try:
            client = groq.Groq(api_key=self.api_key)
            result = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": self.clean_prompt},
                    {"role": "user", "content": raw_text},
                ],
                temperature=0.3,
                max_tokens=2048,
            )
            cleaned = result.choices[0].message.content.strip()
            return cleaned if cleaned else raw_text
        except Exception:
            return raw_text

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
            return self._clean(self._transcribe_local(chunks))

        if not self.api_key:
            raise MissingKeyError("Set GROQ_API_KEY in Settings or env")

        wav_bytes = encode_wav(chunks)

        if self.engine_mode == "hybrid":
            text, used_local = self.transcribe_cloud_first(wav_bytes, chunks)
            return self._clean(text)

        return self._clean(self._whisper(wav_bytes))

    def _transcribe_local(self, chunks):
        if self._local is None:
            from local_transcriber import LocalTranscriber
            self._local = LocalTranscriber(model_name=self.local_model)
        return self._local.transcribe(chunks, language=self.language)
