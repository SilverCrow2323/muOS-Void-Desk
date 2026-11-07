#!/usr/bin/env bash
# VoidDesk launcher — dispatches based on cfg.engine (py | love)
set -euo pipefail
cd "$(dirname "$0")"

APP_DIR="$(pwd)"
LOG_DIR="data/logs"; mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/desktop_$(date +%Y%m%d_%H%M%S).log"
echo "→ Log: $LOG"

# Read engine preference
ENGINE=$(python3 -c "
import json,sys
try:
    print(json.load(open('data/desk_config.json')).get('engine','love'))
except Exception:
    print('love')
" 2>/dev/null || echo "love")
[ -z "$ENGINE" ] && ENGINE="love"
echo "→ Engine: $ENGINE"

# Xephyr check (PC only, needed by LOVE engine)
if [ "$(uname -m)" != "aarch64" ] && [ "$(uname -m)" != "armv7l" ]; then
    if command -v Xephyr >/dev/null 2>&1; then
        echo "→ Xephyr OK: $(command -v Xephyr)"
    else
        echo "→ Xephyr MISSING — install: sudo apt install xserver-xephyr"
    fi
fi

export VOIDDESK_APP_DIR="$APP_DIR"
export VOIDDESK_PC=1
export VOIDDESK_FULLSCREEN=0

# Start Python service (used by both frontends)
python3 service/voiddesk_service.py >>"$LOG" 2>&1 &
SERVICE_PID=$!
echo "→ Service PID: $SERVICE_PID"
trap 'kill $SERVICE_PID 2>/dev/null || true' EXIT
sleep 0.3

# ── PYGAME frontend ──
if [ "$ENGINE" = "py" ]; then
    echo "→ Launching Pygame frontend"
    if [ ! -x ".venv_desktop/bin/python" ]; then
        echo "→ Creating Python venv (first time)..."
        python3 -m venv .venv_desktop
        ./.venv_desktop/bin/pip install --quiet --upgrade pip
        ./.venv_desktop/bin/pip install --quiet pygame psutil
    fi
    if ! ./.venv_desktop/bin/python -c 'import pygame' 2>/dev/null; then
        echo "→ Installing pygame in venv..."
        ./.venv_desktop/bin/pip install --quiet pygame psutil
    fi
    exec ./.venv_desktop/bin/python -u desktop_run.py 2>&1 | tee -a "$LOG"
fi

# ── LÖVE frontend ──
echo "→ Launching LÖVE frontend"
if [ -x "lib/love" ] && [ "$(uname -m)" = "aarch64" ]; then
    LOVE="lib/love"
    export LD_LIBRARY_PATH="$APP_DIR/lib:${LD_LIBRARY_PATH:-}"
elif command -v love >/dev/null 2>&1; then
    LOVE="love"
else
    echo "❌ LÖVE not found. Install: sudo apt install love"
    exit 1
fi

"$LOVE" love/ 2>&1 | tee -a "$LOG"
