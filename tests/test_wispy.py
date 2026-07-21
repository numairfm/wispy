#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import parse_args, MIN_DURATION, LLM_MODEL, CLEAN_PROMPT

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

def test_llm_model():
    assert isinstance(LLM_MODEL, str) and len(LLM_MODEL) > 0

def test_clean_prompt():
    assert isinstance(CLEAN_PROMPT, str)
    assert "retraction" in CLEAN_PROMPT.lower() or "nevermind" in CLEAN_PROMPT.lower()

if __name__ == "__main__":
    test_server()
    test_toggle()
    test_no_args_shows_help()
    test_help_subcommand()
    test_min_duration()
    test_llm_model()
    test_clean_prompt()
    print("All tests passed.")
