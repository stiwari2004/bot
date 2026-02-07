#!/bin/sh
cd "$(dirname "$0")"
python3 -m pip install -r requirements.txt -q 2>/dev/null || true
exec python3 run.py "$@"
