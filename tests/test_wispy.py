#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import parse_args, MIN_DURATION
from transcriber import DEFAULT_WHISPER_PROMPT, DEFAULT_CLEAN_PROMPT, Transcriber

def test_server():
    assert parse_args(["server"]) == "server"

def test_toggle():
    assert parse_args(["toggle"]) == "toggle"

def test_no_args_shows_help():
    assert parse_args([]) == "help"

def test_help_subcommand():
    assert parse_args(["help"]) == "help"

def test_min_duration():
    assert MIN_DURATION == 2.0

def test_whisper_prompt_default():
    assert isinstance(DEFAULT_WHISPER_PROMPT, str)
    assert DEFAULT_WHISPER_PROMPT == ""

def test_clean_prompt_default():
    assert isinstance(DEFAULT_CLEAN_PROMPT, str)
    assert len(DEFAULT_CLEAN_PROMPT) > 0

def test_transcriber_custom_prompts():
    t = Transcriber(
        api_key="test", model="test",
        whisper_prompt="my prompt", clean_prompt="my clean prompt",
    )
    assert t.whisper_prompt == "my prompt"
    assert t.clean_prompt == "my clean prompt"

def test_transcriber_defaults_used_when_empty():
    t = Transcriber(api_key="test", model="test")
    assert t.whisper_prompt == DEFAULT_WHISPER_PROMPT
    assert t.clean_prompt == DEFAULT_CLEAN_PROMPT

if __name__ == "__main__":
    test_server()
    test_toggle()
    test_no_args_shows_help()
    test_help_subcommand()
    test_min_duration()
    test_whisper_prompt_default()
    test_clean_prompt_default()
    test_transcriber_custom_prompts()
    test_transcriber_defaults_used_when_empty()
    print("All tests passed.")
