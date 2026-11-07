#!/usr/bin/env bash
# VoidDesk – desktop launcher (LÖVE frontend + Python service) — WINDOWED
set -euo pipefail
cd "$(dirname "$0")"

APP_DIR="$(pwd)"
LOG_DIR="data/logs"; mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/desktop_$(date +%Y%m%d_%H%M%S).log"

echo "→ Log: $LOG"
echo "→ Windowed 640x480 (F11 = fullscreen toggle)"

# Explicitly windowed on PC
export VOIDDESK_FULLSCREEN=0

# Start Python service
python3 service/voiddesk_service.py >>"$LOG" 2>&1 &
SERVICE_PID=$!
echo "→ Service PID: $SERVICE_PID"
trap 'kill $SERVICE_PID 2>/dev/null || true' EXIT
sleep 0.3

# Detect LÖVE binary
export VOIDDESK_APP_DIR="$APP_DIR"
export VOIDDESK_PC=1

if [ -x "lib/love" ] && [ "$(uname -m)" = "aarch64" ]; then
    LOVE="lib/love"
    export LD_LIBRARY_PATH="$APP_DIR/lib:${LD_LIBRARY_PATH:-}"
    export VOIDDESK_FULLSCREEN=1  # device = fullscreen
elif command -v love >/dev/null 2>&1; then
    LOVE="love"
else
    echo "❌ LÖVE not found. Install: sudo apt install love"
    exit 1
fi

echo "→ LÖVE: $LOVE love/"
"$LOVE" love/ 2>&1 | tee -a "$LOG"
