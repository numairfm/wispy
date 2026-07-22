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
