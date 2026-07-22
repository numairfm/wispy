import threading
import time

import numpy as np
import sounddevice as sd


def resolve_device(name, devices=None):
    if not name:
        return None
    if devices is None:
        devices = sd.query_devices()
    for i, d in enumerate(devices):
        if d['name'] == name and d['max_input_channels'] > 0:
            return i
    return None


class Recorder:
    def __init__(self, device_name=""):
        self.device_name = device_name
        self._recording = False
        self._audio_buffer = None
        self._stream = None
        self._current_level = 0.0
        self._rms_buf = [0.0] * 20
        self._start_time = 0.0
        self._audio_lock = threading.Lock()

    def level(self):
        return self._current_level

    def elapsed(self):
        if self._start_time == 0.0:
            return 0.0
        return time.monotonic() - self._start_time

    def start(self):
        self._audio_buffer = []
        self._current_level = 0.0
        self._rms_buf = [0.0] * 20
        self._start_time = time.monotonic()
        self._recording = True
        self.last_error = None
        threading.Thread(target=self._open_stream, daemon=True).start()

    def _open_stream(self):
        try:
            device = resolve_device(self.device_name)
            stream = sd.InputStream(
                callback=self._audio_cb,
                channels=1, samplerate=16000,
                dtype="float32", device=device,
            )
            stream.start()
            with self._audio_lock:
                if not self._recording:
                    stream.stop()
                    stream.close()
                    return
                self._stream = stream
        except Exception as e:
            self._recording = False
            self.last_error = str(e)

    def stop(self):
        with self._audio_lock:
            if not self._recording:
                return None
            self._recording = False
            buffer = self._audio_buffer
            self._audio_buffer = None
        stream = self._stream
        self._stream = None
        if stream:
            threading.Thread(target=self._close_stream,
                             args=(stream,), daemon=True).start()
        return buffer

    def _close_stream(self, stream):
        try:
            stream.stop()
            stream.close()
        except Exception:
            pass

    def _audio_cb(self, indata, frames, time_info, status):
        with self._audio_lock:
            if not self._recording:
                return
            self._audio_buffer.append(indata.copy())
        rms = float(np.sqrt(np.mean(indata ** 2)))
        self._rms_buf = self._rms_buf[1:] + [rms]
        noise = min(self._rms_buf) if self._rms_buf else rms
        signal = max(rms - noise, 0.0)
        raw = min(signal * 60.0, 1.0) if noise > 0.0001 else 0.0
        self._current_level = self._current_level * 0.55 + raw * 0.45
