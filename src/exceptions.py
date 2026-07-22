class TranscribeError(Exception):
    pass

class MissingKeyError(TranscribeError):
    pass

class GroqError(TranscribeError):
    pass

class InvalidAudioError(TranscribeError):
    pass
