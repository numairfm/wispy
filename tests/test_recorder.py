import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from recorder import resolve_device

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
