import threading
import time


def resolve_device(name, devices=None):
    if not name:
        return None
    if devices is None:
        import sounddevice as sd
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
