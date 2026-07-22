import wave
import io
import os
import tempfile

import groq
import numpy as np

from exceptions import InvalidAudioError, MissingKeyError, GroqError

# ponytail: copied from main.py to avoid PyQt6 transitive import
CLEAN_PROMPT = """You are a light-touch speech-to-text cleaner. Your job is minimal cleanup only.

Rules:
1. Remove filler words: um, uh, er, ah, like (when used as filler, not "I like pizza"), you know, I mean, sort of, kind of.
2. Remove false starts and stutters only when the speaker immediately corrects themselves (e.g. "I I I went" → "I went").
3. DO NOT remove, rephrase, reformat, or reorder any actual content. Every sentence, every detail, every word the speaker said must stay.
4. DO NOT add formatting, bullet points, numbered lists, or line breaks unless the speaker explicitly said "number one", "bullet point", etc.
5. DO NOT summarize, shorten, or condense. If the speaker said it, it stays.
6. Fix obvious transcription typos only (e.g. "teh" → "the"). Do not change word choice.
7. Output ONLY the cleaned text. No explanations, no commentary."""


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

    def _clean(self, raw_text):
        if not self.clean or len(raw_text.split()) < 5:
            return raw_text
        try:
            client = groq.Groq(api_key=self.api_key)
            result = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": CLEAN_PROMPT},
                    {"role": "user", "content": raw_text},
                ],
                temperature=0.3,
                max_tokens=2048,
            )
            cleaned = result.choices[0].message.content.strip()
            return cleaned if cleaned else raw_text
        except Exception:
            return raw_text  # ponytail: fall back to raw, don't raise

    def transcribe(self, chunks):
        if not chunks or len(chunks) < 5:
            raise InvalidAudioError("Recording too short")
        if not self.api_key:
            raise MissingKeyError("Set GROQ_API_KEY in Settings or env")
        wav_bytes = self._encode_wav(chunks)
        return self._clean(self._whisper(wav_bytes))
