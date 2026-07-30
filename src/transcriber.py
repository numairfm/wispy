import os
import tempfile
import concurrent.futures

import groq

from recorder import encode_wav
from exceptions import InvalidAudioError, MissingKeyError, GroqError, LocalModelNotFoundError


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
        """True for network-level failures worth retrying."""
        import groq
        return isinstance(exc, (groq.APIConnectionError, groq.APITimeoutError))

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

    def _race_hybrid(self, wav_bytes, chunks):
        """Run cloud and local in parallel, return first to finish."""
        def _do_cloud():
            return self._whisper(wav_bytes, timeout=2)

        def _do_local():
            return self._transcribe_local(chunks)

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(_do_cloud), pool.submit(_do_local)]
            for future in concurrent.futures.as_completed(futures):
                try:
                    return future.result()
                except Exception:
                    continue
        raise GroqError("Both cloud and local transcription failed")

    def transcribe(self, chunks):
        if not chunks or len(chunks) < 5:
            raise InvalidAudioError("Recording too short")

        if self.engine_mode == "offline":
            return self._clean(self._transcribe_local(chunks))

        if not self.api_key:
            raise MissingKeyError("Set GROQ_API_KEY in Settings or env")

        wav_bytes = encode_wav(chunks)

        if self.engine_mode == "hybrid":
            try:
                return self._clean(self._race_hybrid(wav_bytes, chunks))
            except GroqError:
                return self._clean(self._transcribe_local(chunks))

        return self._clean(self._whisper(wav_bytes))

    def _transcribe_local(self, chunks):
        if self._local is None:
            from local_transcriber import LocalTranscriber
            self._local = LocalTranscriber(model_name=self.local_model)
        return self._local.transcribe(chunks, language=self.language)
