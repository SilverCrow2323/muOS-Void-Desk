#!/bin/sh
set -eu
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$ROOT"
if ! command -v python3 >/dev/null 2>&1; then
    echo "Void Desk requires Python 3.10+ (python3 not found)." >&2
    exit 127
fi
python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' || {
    echo "Void Desk requires Python 3.10 or newer." >&2
    exit 2
}
exec python3 "$ROOT/voiddesk.py" --py
