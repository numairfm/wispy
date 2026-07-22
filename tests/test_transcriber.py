import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from exceptions import (
    TranscribeError, MissingKeyError, GroqError, InvalidAudioError,
)

def test_hierarchy():
    assert issubclass(MissingKeyError, TranscribeError)
    assert issubclass(GroqError, TranscribeError)
    assert issubclass(InvalidAudioError, TranscribeError)

def test_hierarchy_not_each_other():
    assert not issubclass(MissingKeyError, GroqError)
    assert not issubclass(GroqError, InvalidAudioError)

if __name__ == "__main__":
    test_hierarchy()
    test_hierarchy_not_each_other()
    print("All test_transcriber tests passed.")
