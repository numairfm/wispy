import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from recorder import resolve_device, Recorder

def test_resolve_device_found():
    devices = [
        {'name': 'default', 'max_input_channels': 0},
        {'name': 'mic1', 'max_input_channels': 1},
        {'name': 'mic2', 'max_input_channels': 2},
    ]
    assert resolve_device('mic1', devices=devices) == 1

def test_resolve_device_not_found():
    devices = [
        {'name': 'default', 'max_input_channels': 0},
        {'name': 'mic1', 'max_input_channels': 1},
    ]
    assert resolve_device('nonexistent', devices=devices) is None

def test_resolve_device_skips_output_only():
    devices = [
        {'name': 'speaker', 'max_input_channels': 0},
        {'name': 'mic', 'max_input_channels': 1},
    ]
    assert resolve_device('speaker', devices=devices) is None
    assert resolve_device('mic', devices=devices) == 1

def test_resolve_device_empty_name():
    devices = [{'name': 'mic', 'max_input_channels': 1}]
    assert resolve_device('', devices=devices) is None

def test_recorder_initial_level():
    r = Recorder()
    assert r.level() == 0.0

def test_recorder_stores_device():
    r = Recorder(device_name="mic1")
    assert r.device_name == "mic1"

def test_recorder_elapsed_zero_before_start():
    r = Recorder()
    assert r.elapsed() == 0.0

from unittest.mock import patch, MagicMock
import time

def test_start_sets_recording_flag():
    r = Recorder()
    mock_sd = MagicMock()
    mock_stream = MagicMock()
    mock_sd.InputStream.return_value = mock_stream
    mock_sd.query_devices.return_value = []
    with patch("recorder.sd", mock_sd):
        r.start()
    assert r._recording is True
    assert r._audio_buffer == []

def test_start_resolves_device():
    r = Recorder(device_name="mic1")
    mock_sd = MagicMock()
    mock_stream = MagicMock()
    mock_sd.InputStream.return_value = mock_stream
    mock_sd.query_devices.return_value = [
        {'name': 'speaker', 'max_input_channels': 0},
        {'name': 'mic1', 'max_input_channels': 1},
    ]
    with patch("recorder.sd", mock_sd):
        r.start()
    call_kwargs = mock_sd.InputStream.call_args
    assert call_kwargs[1]['device'] == 1 or call_kwargs[1].get('device') == 1

def test_start_clears_last_error():
    r = Recorder()
    r.last_error = "previous error"
    mock_sd = MagicMock()
    mock_sd.InputStream.return_value = MagicMock()
    mock_sd.query_devices.return_value = []
    with patch("recorder.sd", mock_sd):
        r.start()
    assert r.last_error is None

def test_start_opens_stream_in_background():
    r = Recorder()
    mock_sd = MagicMock()
    mock_sd.InputStream.return_value = MagicMock()
    mock_sd.query_devices.return_value = []
    with patch("recorder.sd", mock_sd):
        r.start()
    # start() returns immediately; stream opened in background
    # Give thread a moment to run
    time.sleep(0.1)
    mock_sd.InputStream.assert_called_once()

def test_start_stream_failure_sets_error():
    r = Recorder()
    mock_sd = MagicMock()
    mock_sd.InputStream.side_effect = RuntimeError("no device")
    mock_sd.query_devices.return_value = []
    with patch("recorder.sd", mock_sd):
        r.start()
    time.sleep(0.1)
    assert r._recording is False
    assert r.last_error == "no device"
