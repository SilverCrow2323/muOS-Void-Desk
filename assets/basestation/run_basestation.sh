#!/bin/sh
set -eu

HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PYTHON="${PYTHON:-python3}"
VENV="$HERE/.venv"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
    echo "[SPDW Hub] Python 3 is required." >&2
    exit 1
fi

if ! "$PYTHON" -c 'import tkinter' >/dev/null 2>&1; then
    echo "[SPDW Hub] Tkinter is missing. Install the system package first:" >&2
    echo "  Debian/Ubuntu: sudo apt install python3-tk python3-venv" >&2
    exit 1
fi

if [ ! -x "$VENV/bin/python" ]; then
    "$PYTHON" -m venv --system-site-packages "$VENV"
fi

"$VENV/bin/python" -m pip install --disable-pip-version-check -r "$HERE/requirements.txt"
exec "$VENV/bin/python" "$HERE/basestation.py" "$@"
