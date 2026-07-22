import threading
import time

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

    def _audio_cb(self, indata, frames, time_info, status):
        pass  # ponytail: implemented in task 4
