#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from main import parse_args, MIN_DURATION

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

if __name__ == "__main__":
    test_server()
    test_toggle()
    test_no_args_shows_help()
    test_help_subcommand()
    test_min_duration()
    print("All tests passed.")
