#!/bin/bash

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$ROOT/app/venv/bin/python"

if [ ! -x "$PY" ]; then
    PY="$(command -v python3 || command -v python)"
fi

if [ -z "$PY" ] || [ ! -f "$PY" ]; then
    echo "Python 3 was not found. Start the tutor first or install Python 3.11+."
    exit 1
fi

"$PY" "$ROOT/tests/run_tests.py"
