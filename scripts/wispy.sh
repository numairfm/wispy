#!/bin/sh
set -e
DIR="$(cd "$(dirname "$0")/.." && pwd)"
exec "$DIR/.venv/bin/python3" "$DIR/src/main.py" "$@"
